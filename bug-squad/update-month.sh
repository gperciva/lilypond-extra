#!/bin/sh

# overkill ,)
# LAST_MONTH=`date +"%Y"`-`printf "%02d" $[$(date +"%m")-1]`

WEBDIR="/var/www/somewhere/else/html/lilypond"

DOM=`date +"%d"`

if [ $DOM -eq 1 ] ; then
	LAST_MONTH=`date +"%Y-%m" --date="2 month ago"`
	THIS_MONTH=`date +"%Y-%m" --date="1 month ago"`
else
	LAST_MONTH=`date +"%Y-%m" --date="1 month ago"`
	THIS_MONTH=`date +"%Y-%m"`
fi
	
wget -c ftp://lists.gnu.org/bug-lilypond/$LAST_MONTH
wget -c ftp://lists.gnu.org/bug-lilypond/$THIS_MONTH

COMBINED=${LAST_MONTH}--${THIS_MONTH}.mbox
cat $LAST_MONTH $THIS_MONTH > $COMBINED

$HOME/bin/scrape.py $COMBINED

ln -s maybe-missing-emails---${LAST_MONTH}--${THIS_MONTH}.html \
      maybe-missing-emails---current.html

mv maybe-missing-emails* $WEBDIR

# bzip2 < $COMBINED > `basename $COMBINED`.bz2
# rm $LAST_MONTH $THIS_MONTH $COMBINED
rm $COMBINED
