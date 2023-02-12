PREVIEW_INPUT_FILE := ""
PREVIEW_TMPDIR:= ""

build:
    pandoc {{PREVIEW_INPUT_FILE}} -o {{PREVIEW_TMPDIR}}/out.pdf

view:
    zathura {{PREVIEW_TMPDIR}}/out.pdf

