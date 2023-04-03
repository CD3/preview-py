import typer
import tempfile
import preview.handlers
import asyncio
import pathlib
import logging

app = typer.Typer()



@app.command()
def main(
        input_file:pathlib.Path = typer.Argument(default=None),
        debug:bool=typer.Option(False,help="Log debug information to a log file."),
        log_file:pathlib.Path = typer.Option("/dev/stdout",help="Log file name."),
        print_example_handler:str = typer.Option(str,help="Print an example handler file."),
        list_example_handler_filenames:bool = typer.Option(False,help="Print list of known example handler files."),
        tmpdir:pathlib.Path = typer.Option(None,help="Specify a directory to use at the temporary directory. Useful for testing.")
        ):
    if list_example_handler_filenames:
        print("These files have example implementations that you can view with the --print-example-handler <FILENAME> option.")
        for file in preview.handlers.get_example_handler_filenames():
            print(f"  {file}")
        print("Other implementations can be used, and other filetype can be supported by providing your own file.")
        print("For example, if `preview` finds a file named `justfile.foo`, it will use it to preview any files ending.")
        print("with `.foo`. The `justfile.foo` file just needs to provide a `build` and `view` recipes. See the example")
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
    logging.basicConfig(filename=log_file,level=LOGLEVEL)

    try:
        handler = preview.handlers.find_a_handler(input_file)
        handler.tmpdir = tmpdir

        asyncio.run(handler.preview(input_file))
    except Exception as e:
        print(f"There was an error: {e}")





