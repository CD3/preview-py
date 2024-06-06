import asyncio
import hashlib
import logging
import pathlib
import subprocess
import sys
import tempfile

import typer

import preview.handlers

from .file_monitor import *

app = typer.Typer()
app2 = typer.Typer()


@app.command()
def main(
    input_file: pathlib.Path = typer.Argument(default=None),
    debug: bool = typer.Option(False, help="Log debug information to a log file."),
    log_file: pathlib.Path = typer.Option("/dev/stdout", help="Log file name."),
    print_example_handler: str = typer.Option(
        str, help="Print an example handler file."
    ),
    list_example_handler_filenames: bool = typer.Option(
        False, help="Print list of known example handler files."
    ),
    tmpdir: pathlib.Path = typer.Option(
        None,
        help="Specify a directory to use at the temporary directory. Useful for testing.",
    ),
):
    if list_example_handler_filenames:
        print(
            "These files have example implementations that you can view with the --print-example-handler <FILENAME> option."
        )
        for file in preview.handlers.get_example_handler_filenames():
            print(f"  {file}")
        print(
            "Other implementations can be used, and other filetype can be supported by providing your own file."
        )
        print(
            "For example, if `preview` finds a file named `justfile.foo`, it will use it to preview any files ending."
        )
        print(
            "with `.foo`. The `justfile.foo` file just needs to provide a `build` and `view` recipes. See the example"
        )
        print("files for... well, examples.")
        return 0

    if print_example_handler:
        text = preview.handlers.get_example_handler_file_content(print_example_handler)
        print(text)
        return 0

    if not input_file:
        print("ERROR: Missing argument INPUT_FILE")
        return 1

    LOGLEVEL = logging.DEBUG if debug else logging.ERROR
    logging.basicConfig(filename=log_file, level=LOGLEVEL)

    try:
        handler = preview.handlers.find_a_handler(input_file)
        handler.tmpdir = tmpdir

        asyncio.run(handler.preview(input_file))
    except Exception as e:
        print(f"There was an error: {e}")


async def get_stream_reader(device) -> asyncio.StreamReader:
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader(loop=loop)
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, device)
    return reader


@app2.command()
def preview_gnupot(input_file: pathlib.Path):
    input_file = input_file.absolute()

    async def preview_gnuplot_script(script: pathlib.Path):
        gnuplot_proc = await asyncio.create_subprocess_exec(
            "gnuplot",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            # env={"PYTHONUNBUFFERED": "1"},
        )

        stdin = await get_stream_reader(sys.stdin)

        alive = True

        prev_hash = None
        while alive:
            if script.exists():
                curr_hash = hashlib.md5(script.read_bytes()).hexdigest()
                if curr_hash != prev_hash:
                    prev_hash = curr_hash
                    gnuplot_proc.stdin.write(f"load '{script}'\n".encode())
                    await gnuplot_proc.stdin.drain()

            try:
                o = await asyncio.wait_for(gnuplot_proc.stdout.readline(), 0.01)
                print(" stdout:", o.decode(), end="")
            except asyncio.TimeoutError:
                pass
            try:
                o = await asyncio.wait_for(gnuplot_proc.stderr.readline(), 0.01)
                print("STDERR:", o.decode(), end="")
            except asyncio.TimeoutError:
                pass

            try:
                i = await asyncio.wait_for(stdin.readline(), 0.01)

                if i.decode().strip().lower() == "q":
                    alive = False
                else:
                    gnuplot_proc.stdin.write(i)
                    gnuplot_proc.stdin.write(f"load '{script}'\n".encode())
                    await gnuplot_proc.stdin.drain()

            except asyncio.TimeoutError:
                pass

        gnuplot_proc.stdin.write(b"exit\n")
        await gnuplot_proc.stdin.drain()
        await gnuplot_proc.wait()

    asyncio.run(preview_gnuplot_script(input_file))
