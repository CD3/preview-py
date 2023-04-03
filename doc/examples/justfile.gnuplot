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
