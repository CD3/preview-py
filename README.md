# Preview

`preview` is a tool for "previewing" files that require a compilatoin step, like LaTeX, Markdown, and more.
It works by managing a "build" step and a "view" step, so it can be used to live-preview many different types of files, and if you
filetype is not already supported, it is simple to add support for it.

# Usage

Install with `pip`

```
$ pip install filepreviewer
```

to preview a file, just pass it to the `preview` command

```
$ preview file_to_preview.md
```

# How it works

`preview` uses a handler to launch a view process in the background, and then run
build process when the source file is changed. For example, the `just` handler can
use a justfile like this

<!---begin
type = "file include"
filename = "doc/examples/justfile.md"
code-fence = true
code-fence-lang = "make"
--->
```make
PREVIEW_INPUT_FILE := ""
PREVIEW_TMPDIR:= ""

preview-build:
    pandoc {{PREVIEW_INPUT_FILE}} -o {{PREVIEW_TMPDIR}}/out.pdf

preview-view:
    zathura {{PREVIEW_TMPDIR}}/out.pdf

```
<!---
end--->
to preview Markdown files by compiling them to a PDF (using Pandoc) and opening then PDF with Zathura, which does automatic reload.

You can use any tool(s) you want to build and view your file. The only requirement is that view process _should block_. `preview` will launch it in the background and exit when it returns.

# Examples

To preview a Gnuplot script you could use [sexpect](https://github.com/clarkwang/sexpect) to open gnuplot and load the script.

<!---begin
type = "file include"
filename = "doc/examples/justfile.gnuplot"
code-fence = true
code-fence-lang = "make"
--->
```make
PREVIEW_INPUT_FILE := ""
PREVIEW_TMPDIR:= ""

preview-build:
    #! /bin/bash
    if [[ -e preview-gnuplot.sock ]]
    then
      sexpect -sock preview-gnuplot.sock send 'load "{{PREVIEW_INPUT_FILE}}"' -cr
      sexpect -sock preview-gnuplot.sock expect
    fi

preview-view:
    sexpect -sock preview-gnuplot.sock spawn gnuplot
    just --justfile {{justfile()}} PREVIEW_INPUT_FILE={{PREVIEW_INPUT_FILE}} PREVIEW_TMPDIR={{PREVIEW_TMPDIR}} preview-build
    zenity --info --no-markup --text="Click 'OK' when you are done to close the preview."
    sexpect -sock preview-gnuplot.sock send 'exit' -cr
    sexpect -sock preview-gnuplot.sock wait
```
<!---
end--->

The use of [Zenity](https://help.gnome.org/users/zenity/stable/) here is
required to keep the view process from returning immediatly, which would cause
preview to terminate.

# Handlers

Currently, Preview supports [`just`](https://help.gnome.org/users/zenity/stable/) and
Make for handing the build and view steps.

### Just handler

To use the just handler, create a file named `justfile.<file_extension>` that defines
a `preview-build` and `preview-view` recipe, as well as two variables named `PREVIEW_INPUT_FILE` and `PREVIEW_TMPDIR`. Preview will pass the name of the file being previewed, and the path to a temporary directory that is created for the hander to use.

### Make handler

To use the make handler, create a file named `makefile.<file_extension>` that
defines the `preview-build` and `preview-view` targets. Preview will set two variables
named `PREVIEW_INPUT_FILE` and `PREVIEW_TMPDIR` that contain the name of the file being previewed, and the path to a temporary directory that is created for the hander to use.
