PREVIEW_INPUT_FILE := ""
PREVIEW_TMPDIR:= ""

preview-build:
    pandoc {{PREVIEW_INPUT_FILE}} -o {{PREVIEW_TMPDIR}}/out.pdf

preview-view:
    zathura {{PREVIEW_TMPDIR}}/out.pdf

