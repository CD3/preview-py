from .file_monitor import *
from .utils import *
import tempfile
import pathlib
import os
from collections import OrderedDict

'''
Handlers are what execute the build and view steps required to preview a file, and allow the
user to specify how these steps are completed.
'''

class BaseHandler:
    def __init__(self):
        self.environ = {}

    async def preview(self,input_file:pathlib.Path):
        input_file_monitor = FileMonitor(input_file)
        async def build_and_wait():
            build_proc = await self.build()
            return await build_proc.communicate()


        with tempfile.TemporaryDirectory() as tmpdir:
            self.environ["PREVIEW_TMPDIR"] = tmpdir
            self.environ["PREVIEW_INPUT_FILE"] = str(input_file.absolute())
            os.environ.update(self.environ)

            await input_file_monitor.run_if_modified(build_and_wait)

            view_proc = await self.view()


            while True:
                '''
                Start polling.
                  - if view process has been stopped, then exit
                  - if not, build the input file if it has been modified
                '''
                try:
                    output = await asyncio.wait_for(view_proc.wait(),timeout=0.1)
                    return
                except asyncio.exceptions.TimeoutError:
                    output = await input_file_monitor.run_if_modified(build_and_wait)
                





class JustHandler(BaseHandler):
    '''Use `just` to execute build and view task.'''
    def __init__(self,justfile):
        super().__init__()
        self.justfile = justfile

    async def build(self):
        vars = [ f"{k}='{self.environ[k]}'" for k in self.environ]
        proc = await async_run("just","-f",self.justfile,*vars,"build")
        output = await proc.communicate()
        if proc.returncode != 0:
            alert(text="There was a problem during build phase.\nCommand Output:\n"+output[0].decode('utf-8')+"\n")

        return proc

    async def view(self):
        vars = [ f"{k}='{self.environ[k]}'" for k in self.environ]
        proc = await async_run("just","-f",self.justfile,*vars,"view")
        return proc

    


def find_handler(input_file:pathlib.Path):

    filetype = input_file.suffix.strip(".")
    if filetype == "markdown":
        filetype = "md"

    handlers = OrderedDict()
    handlers["{input_file_parent}/justfile.{filetype}" ] = JustHandler
    handlers["~/.preview/justfile.{filetype}"] =  JustHandler
    handlers["{input_file}.justfile"] =  JustHandler

    for handler_file_template in handlers:
        handler_file = pathlib.Path(handler_file_template.format(input_file=input_file,input_file_parent=input_file.parent,filetype=filetype))
        if handler_file.exists():
            return handlers[handler_file_template](handler_file)

    raise RuntimeError(f"Could not find a handler for filtype `{filetype}` to preview `{input_file}`.")
        

