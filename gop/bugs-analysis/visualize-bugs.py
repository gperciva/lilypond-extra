#!/usr/bin/env python
import datetime

filename = "lilypond-issues-analysis-trim-duplicates.csv"

lines = open(filename).readlines()
# hack; need to get ^M
#splitchar = lines[0][108]
#lines = lines[0].split(splitchar)
#lines = lines.split()
lines = lines[1:]

def parsedate(text):
    if not text:
        return None
    if text[0] == '"':
        text = text[1:-1].split('-')
    else:
        text = text.split('-')
    date = datetime.datetime(int(text[0]), int(text[1]), int(text[2]))
    return date

data = []
for line in lines:
    splitline = line.split(',')
    issuenumber = splitline[0]
    opendate = parsedate(splitline[1])
    closedate = parsedate(splitline[2])
    #print issuenumber, opendate, closedate
    if not opendate or not closedate:
        continue
    datum = (opendate, closedate)
    data.append( datum )
earliest = min( map(lambda x: x[0], data))
latest = max( map(lambda x: x[1], data))

diffs = []
for datum in data:
    deltaopen = (datum[0] - earliest).days
    deltaclose = (datum[1] - earliest).days
    delta = deltaclose - deltaopen
    diffs.append( (deltaopen, deltaclose, delta) )

out=open("bugs-dates.txt", "w")
plotdata = []
for diff in diffs:
    line = "%i %i %i %i\n" % (diff[0], 0, diff[2], 1)
    out.write(line)
out.close()


releases = ["2011-01-12",
  "2011-02-09",
  "2011-03-13",
  "2011-03-29",
  "2011-04-03",
  "2011-04-07",
  "2011-05-30"]

def add_lines(values, filename, height):
    diffed = []
    for rel in values:
        opendate = parsedate(rel)
        deltaopen = (opendate - earliest).days
        deltaclose = deltaopen
        diffed.append( (deltaopen, deltaclose, 0) )

    out=open(filename, "w")
    plotdata = []
    for diff in diffed:
        line = "%i %i %i %.3f\n" % (diff[0], 0, diff[2], height)
        out.write(line)
    out.close()

add_lines(releases, "release-dates.txt", 1.2)

sixmonths = [
    "2010-01-01",
    "2010-07-01",
    "2011-01-01",
    "2011-07-01",
    ]
add_lines(sixmonths, "sixmonths-dates.txt", 1.6)

extra = [
    "2010-03-19", # bug squad begins regtest comparisons, but stops
    "2010-08-04", # phil starts regtest comparisons
    ]
add_lines(extra, "extra-dates.txt", 1.4)


