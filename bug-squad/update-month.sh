#!/bin/sh
LAST_MONTH=2011-05
THIS_MONTH=2011-06
wget ftp://lists.gnu.org/bug-lilypond/$THIS_MONTH
cat $LAST_MONTH $THIS_MONTH > combined.mbox
python scrape.py

