
#EXTRA_FILES =

all: extra docs

extra:
	mkdir -p /tmp/gliss
#	cp $(EXTRA_FILES) /tmp/gliss/

docs: extra
	texi2html \
		-I bugs-analysis/ \
		--split=chapter \
		--output=/tmp/gliss/ \
		--top-file=index.html \
		--css-include=gliss.css \
		gliss.texi

show:
	firefox /tmp/gliss/index.html

upload: all
	rsync -r /tmp/gliss/ graham@lilypond.org:public_html/gliss/


