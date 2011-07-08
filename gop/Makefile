
EXTRA_FILES = \
	bugs-analysis/lilypond-issues-analysis.csv \
	bugs-analysis/lilypond-issues-analysis-trim-duplicates.csv \
	bugs-analysis/bugs-2.13-visualization.png \
	bugs-analysis/zoom-2.13-visualization.png

all: extra docs

extra:
	mkdir -p /tmp/gop
	cp $(EXTRA_FILES) /tmp/gop/

docs: extra
	texi2html \
		-I bugs-analysis/ \
		--split=chapter \
		--output=/tmp/gop/ \
		--top-file=index.html \
		--css-include=gop.css \
		gop.texi

upload: all
	rsync -r /tmp/gop/ graham@lilypond.org:public_html/gop/


