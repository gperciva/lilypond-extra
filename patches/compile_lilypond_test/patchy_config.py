#!/usr/bin/env python
import ConfigParser
import os.path
import shutil
import sys

CONFIG_FILENAME = "~/.lilypond-patchy-config"

default_config = {
    "source": {
        "git_repository_dir": "~/git/lilypond-git",
        "git_remote_name": "origin",
        "bare_git_repository": "no",
        },
    "configure_environment": {},
    "compiling": {
        "extra_make_options": "-j3 CPU_COUNT=3",
        "build_dir": "/tmp/lilypond-autobuild/",
        "auto_compile_results_dir": "~/lilypond-auto-compile-results/",
        "lock_check_interval": "30",
        "lock_check_count": "0",
        },
    "notification": {
        "notify_non_action": "yes",
        "notify_lock": "no",
        "from": "patchy",
        "smtp_command": "#msmtp -C ~/.msmtp-patchy -t",
        "subject": "Patchy email",
        "signature": "",
        },
    "staging": {
        "last_known_good_build": "",
        "build_dir": "",
        "web_install_dir": "",
        "notification_to": "lilypond-auto@gnu.org",
        "notification_cc": "lilypond-devel@gnu.org",
        },
    "translation": {
        "last_known_good_build": "",
        "build_dir": "",
        "web_install_dir": "",
        "notification_to": "lilypond-auto@gnu.org",
        "notification_cc": "translations@lilynet.net",
        }
    }

class PatchyConfig (ConfigParser.RawConfigParser):
    def __init__ (self):
        ConfigParser.RawConfigParser.__init__ (self)
        for (name, section) in default_config.items ():
            self.add_section (name)
            for (option, value) in section.items ():
                self.set (name, option, value)
        self.config_filename = os.path.expanduser (CONFIG_FILENAME)
        if not os.path.exists (self.config_filename):
            self.copy_default_config (self.config_filename)
        self.read (self.config_filename)

    def copy_default_config (self, config_filename):
        sys.stderr.write ("Warning: using default config; please edit %s\n" % config_filename)
        self.write (open (config_filename, 'w'))
        if sys.stdin.isatty ():
            while True:
                ans = raw_input ("Are you sure that you want to continue with the default config? (y/[n]) ")
                if ans.lower ().startswith ('y'):
                    break
                else:
                    sys.exit (0)

    def save (self):
        outfile = open (self.config_filename, 'w')
        self.write (outfile)
        outfile.close ()

    # Override default method that downcase option names; we want
    # option names to be case-sensitive because some of them are
    # used to set environment variables
    def optionxform (self, s):
        return s
