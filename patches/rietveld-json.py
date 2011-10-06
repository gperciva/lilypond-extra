#!/usr/bin/env python

import urllib2

url = "http://codereview.appspot.com"
data = "/api/5096046"

request = urllib2.Request(url + data)
response = urllib2.urlopen(request).read()

print response

# http://code.google.com/p/rietveld/wiki/APIs

