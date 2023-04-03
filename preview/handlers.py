from .file_monitor import *
from .utils import *
import tempfile
import pathlib
import os
from collections import OrderedDict
import logging
import datetime
import pkgutil
import textwrap
import itertools
import contextlib

@contextlib.contextmanager
def temporary_directory(dirname = None):
    if dirname is None:
        with tempfile.TemporaryDirectory() as t:
            yield t
    else:
        dirpath = pathlib.Path(dirname)
        if not dirpath.exists():
            dirpath.mkdir(parents=True)
        yield str(dirpath)


'''
Handlers are what execute the build and view steps required to preview a file, and allow the
user to specify how these steps are completed.
'''

class BaseHandler:
    def __init__(self,tmpdir=None):
        self.environ = {}
        self.tmpdir = tmpdir

    async def preview(self,input_file:pathlib.Path):
        input_file_monitor = FileMonitor(input_file)
        async def build_and_wait():
            build_proc = await self.build()
            return await build_proc.communicate()


        with temporary_directory(self.tmpdir) as tmpdir:
            self.environ["PREVIEW_TMPDIR"] = tmpdir
            self.environ["PREVIEW_INPUT_FILE"] = str(input_file.absolute())
            os.environ.update(self.environ)

            build_proc = await self.build()
            await build_proc.communicate()

            if build_proc.returncode != 0:
                # if build does not succeed initially,
                # quit
                return
            
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
                    output = await view_proc.communicate()
                    if view_proc.returncode != 0:
                        alert(text="There was a problem during the view phase.\nCommand Output:\n"+output[0].decode('utf-8')+"\n")
                    return
                except asyncio.exceptions.TimeoutError:
                    output = await input_file_monitor.run_if_modified(build_and_wait)
                





class JustHandler(BaseHandler):
    '''Use `just` to execute build and view task.'''
    def __init__(self,justfile):
        super().__init__()
        self.justfile = justfile

    async def build(self):
        proc = await async_run("just","-f",self.justfile,"--list")
        output = await proc.communicate()
        build_recipe = "build"
        if "preview-build" in output[0].decode('utf-8'):
            build_recipe = "preview-build"
        vars = [ f"{k}='{self.environ[k]}'" for k in self.environ]
        proc = await async_run("just","-f",self.justfile,*vars,build_recipe)
        output = await proc.communicate()
        if proc.returncode != 0:
            alert(text="There was a problem during build phase.\nCommand Output:\n"+output[0].decode('utf-8')+"\n")
        logging.debug(output[0].decode('utf-8')+"\n")

        return proc

    async def view(self):
        proc = await async_run("just","-f",self.justfile,"--list")
        output = await proc.communicate()
        view_recipe = "view"
        if "preview-view" in output[0].decode('utf-8'):
            view_recipe = "preview-view"
        vars = [ f"{k}='{self.environ[k]}'" for k in self.environ]
        proc = await async_run("just","-f",self.justfile,*vars,view_recipe)
        return proc

class MakeHandler(BaseHandler):
    '''Use `make` to execute build and view task.'''
    def __init__(self,makefile):
        super().__init__()
        self.makefile = makefile

    async def build(self):
        vars = [ f"{k}='{self.environ[k]}'" for k in self.environ]
        proc = await async_run("make","-f",self.makefile,*vars,"preview-build")
        output = await proc.communicate()
        if proc.returncode != 0:
            alert(text="There was a problem during build phase.\nCommand Output:\n"+output[0].decode('utf-8')+"\n")
        logging.debug(output[0].decode('utf-8')+"\n")

        return proc

    async def view(self):
        vars = [ f"{k}='{self.environ[k]}'" for k in self.environ]
        proc = await async_run("make","-f",self.makefile,*vars,"preview-view")
        return proc

    


def find_a_handler(input_file:pathlib.Path):

    filetype = input_file.suffix.strip(".")
    if filetype == "markdown":
        filetype = "md"

    handlers = OrderedDict()
    handlers["{input_file_parent}/justfile.{filetype}" ] = JustHandler
    handlers["{HOME}/.preview/justfile.{filetype}"] =  JustHandler
    handlers["{input_file}.justfile"] =  JustHandler
    handlers["{input_file_parent}/makefile.{filetype}" ] = MakeHandler
    handlers["{HOME}/.preview/makefile.{filetype}"] =  MakeHandler
    handlers["{input_file}.makefile"] =  MakeHandler

    for handler_file_template in handlers:
        handler_file = pathlib.Path(handler_file_template.format(input_file=input_file,input_file_parent=input_file.parent,filetype=filetype,HOME=pathlib.Path().home()))
        if handler_file.exists():
            logging.debug(f"Looking for '{handler_file}': Found")
            return handlers[handler_file_template](handler_file)
        else:
            logging.debug(f"Looking for '{handler_file}': Not Found")

    raise RuntimeError(f"Could not find a handler for filtype `{filetype}` to preview `{input_file}`.")
        
def get_example_handler_filenames():
    filenames = []

    filenames += map( lambda elem : f"{elem[0]}.{elem[1]}", itertools.product( ['justfile','makefile'], ['md','tex','gnuplot'] ) )
    
    return filenames

def get_example_handler_file_content(filename:str):
    filename = str(filename)
    text = f"\nUnrecognized handler filename: `{filename}`"
    if filename == "justfile.md":
        text = '''
        PREVIEW_INPUT_FILE := ""
        PREVIEW_TMPDIR:= ""

        build:
            pandoc {{PREVIEW_INPUT_FILE}} -o {{PREVIEW_TMPDIR}}/out.pdf

        view:
            zathura {{PREVIEW_TMPDIR}}/out.pdf
        '''
    if filename == "justfile.tex":
        text = '''
        PREVIEW_INPUT_FILE := ""
        PREVIEW_TMPDIR:= ""

        build:
            bash -c 'cd {{PREVIEW_TMPDIR}} && ln -sf {{PREVIEW_INPUT_FILE}} && arara -v {{PREVIEW_INPUT_FILE}}'

        view:
            zathura {{PREVIEW_TMPDIR}}/{{file_stem(PREVIEW_INPUT_FILE)}}.pdf
        '''
    if filename == "justfile.gnuplot":
        text = '''
        PREVIEW_INPUT_FILE := ""
        PREVIEW_TMPDIR:= ""

        build:
            #! /bin/bash
            if [[ -e preview-gnuplot.sock ]]
            then
              sexpect -sock preview-gnuplot.sock send 'load "{{PREVIEW_INPUT_FILE}}"' -cr
              sexpect -sock preview-gnuplot.sock expect
            fi

        view:
            sexpect -sock preview-gnuplot.sock spawn gnuplot
            just --justfile {{justfile()}} PREVIEW_INPUT_FILE={{PREVIEW_INPUT_FILE}} PREVIEW_TMPDIR={{PREVIEW_TMPDIR}} build
            zenity --info --no-markup --text="Click 'OK' when you are done to close the preview."
            sexpect -sock preview-gnuplot.sock send 'exit' -cr
            sexpect -sock preview-gnuplot.sock wait
        '''
    if filename == "makefile.md":
        text = '''
        Coming soon...
        '''
    if filename == "makefile.tex":
        text = '''
        Coming soon...
        '''
    if filename == "makefile.gnuplot":
        text = '''
        Coming soon...
        '''

    return textwrap.dedent(text)[1:]
