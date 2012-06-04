#!/usr/bin/env python

import time

class BuildLogfile (object):
    def __init__ (self, filename, commit):
        self.filename = filename
        self.write ("(UTC) Begin LilyPond compile, previous commit at \t%s\n" % commit)

    def write (self, text):
        logfile = open (self.filename, 'a')
        logfile.write ("%s %s" % (time.strftime ("%H:%M:%S",time.gmtime ()), text))
        logfile.close ()

    def add_success (self, name):
        self.write ("\tSuccess:\t\t%s\n" % name)

    def failed_build (self, name, prev_good_commit, bad_commit):
        text = "*** FAILED BUILD ***\n"
        text += "\t%s\n" % name
        text += "\tPrevious good commit:\t%s\n" % prev_good_commit
        text += "\tCurrent broken commit:\t%s\n" % bad_commit
        self.write (text)

    def failed_step (self, name, message):
        text = ""
        text += "*** FAILED STEP ***\n"
        text += "\t%s\n" % name
        text += "\t%s\n" % message
        self.write (text)
