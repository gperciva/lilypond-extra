#!/usr/bin/env python
import ConfigParser
import os.path
import shutil
import sys

CONFIG_FILENAME = "~/.lilypond-patchy-config"
CONFIG_FILENAME_DEFAULT = "lilypond-patchy-config-DEFAULT"


class PatchyConfig (ConfigParser.RawConfigParser):
    def __init__ (self):
        ConfigParser.RawConfigParser.__init__ (self)
        self.config_filename = os.path.expanduser (CONFIG_FILENAME)
        if not os.path.exists (self.config_filename):
            self.copy_default_config (self.config_filename)
        self.read (self.config_filename)

    def copy_default_config (self, config_filename):
        sys.stderr.write ("Warning: using default config; please edit %s\n" % config_filename)
        shutil.copyfile (CONFIG_FILENAME_DEFAULT, config_filename)
        if sys.stdin.isatty ():
            while True:
                ans = raw_input ("Are you sure that you want to continue with the default config? (y/n) ")
                if ans.lower ().startswith ('y'):
                    break
                else:
                    sys.exit (0)

    def save (self):
        outfile = open (self.config_filename, 'w')
        self.write (outfile)
        outfile.close ()

