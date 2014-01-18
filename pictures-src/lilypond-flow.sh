#!/bin/bash
# convert the given .tex file to a pdf, a normal and a small PNG.
# To be used for lilypond-flow image and its translations.
#
# Usage: run it from inside the directory and pass the language
# extension as its single parameter (I will not perform any checks).
# The script will first run pdflatex on the the .tex file,
# then run two instances of convert on it.
#
# Afterwards copy/move the image files to the 'pictures' directory.
#
# Requirements:
# - pdflatex with all used packages
# - convert (ImageMagick)

base="lilypond-flow"

echo Running pdflatex on $base$1.tex ...

pdflatex $base$1.tex

echo Convert to two PNG files ...

convert -density 300x300 $base$1.pdf $base$1.png
convert -density 100x100  $base$1.pdf $base-small$1.png
