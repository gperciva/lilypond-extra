
EXTRA_FILES = \
	lilypond-issues-analysis.csv


all:
	texi2html \
		--split=chapter \
		--output=/tmp/gop/ \
		--top-file=index.html \
		--css-include=gop.css \
		gop.texi

upload: all
	rsync -r /tmp/gop/ graham@lilypond.org:public_html/gop/
	rsync -r "$(EXTRA_FILES)" graham@lilypond.org:public_html/gop/


