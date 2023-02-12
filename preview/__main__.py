import typer
import tempfile
import preview.handlers
import asyncio
import pathlib

app = typer.Typer()



@app.command()
def main(
        input_file:pathlib.Path,
        verbose:bool=typer.Option(False,help="Print status information."),
        debug:bool=typer.Option(False,help="Print more status information.")
        ):
    handler = preview.handlers.find_handler(input_file)

    asyncio.run(handler.preview(input_file))





