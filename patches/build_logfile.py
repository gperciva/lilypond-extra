#!/usr/bin/env python


class BuildLogfile():
    def __init__(self, filename, commit):
        self.filename = filename
        self.write("Begin LilyPond compile, commit:\t%s\n" % commit)

    def write(self, text):
        logfile = open(self.filename, 'a')
        logfile.write("%s" % text)
        logfile.close()

    def add_success(self, name):
        self.write("\tSuccess:\t\t%s\n" % name)

    def failed_build(self, name):
        text = "*** FAILED BUILD ***\n"
        text += "\t%s\n" % name
        text += "\tPrevious good commit:\t%s\n" % self.prev_good_commit
        text += "\tCurrent broken commit:\t%s\n" % self.commit
        self.write(text)

    def failed_step(self, name, message):
        text = ""
        text += "*** FAILED STEP ***\n"
        text += "\t%s\n" % name
        text += "\t%s\n" % message
        self.write(text)



