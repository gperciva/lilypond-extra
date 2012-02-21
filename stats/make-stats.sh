#!/bin/sh

TMPDIR=~/tmp/
GITSTATS=~/src/gitstats/gitstats

ONE_YEAR=$TMPDIR/stats-1year/
THREE_MONTHS=$TMPDIR/stats-3months/
ALL=$TMPDIR/stats-all/

SERVER_ONE_YEAR=graham@lilypond.org:public_html/gitstats-1year/
SERVER_THREE_MONTHS=graham@lilypond.org:public_html/gitstats-3months/
SERVER_ALL=graham@lilypond.org:public_html/gitstats-all/

mkdir -p $ONE_YEAR
mkdir -p $THREE_MONTHS
mkdir -p $ALL

cd $LILYPOND_GIT
$GITSTATS \
  -c commit_begin=`git rev-list -1 --until="1 year ago" origin` \
  $LILYPOND_GIT $ONE_YEAR
cd $ONE_YEAR
ln -s authors.html AUTHORS.html
rsync -a $ONE_YEAR/* $SERVER_ONE_YEAR/

$GITSTATS \
  -c commit_begin=`git rev-list -1 --until="3 months ago" origin` \
  $LILYPOND_GIT $THREE_MONTHS
cd $THREE_MONTHS
ln -s authors.html AUTHORS.html
rsync -a $THREE_MONTHS/* $SERVER_THREE_MONTHS/

$GITSTATS \
  $LILYPOND_GIT $ALL
cd $ALL
ln -s authors.html AUTHORS.html
rsync -a $ALL/* $SERVER_ALL/


