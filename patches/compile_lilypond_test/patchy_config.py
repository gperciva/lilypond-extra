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
    "server": {
        "tests_results_install_dir": "",
        "doc_base_url": "",
        "tests_results_base_url": "",
        },
    "configure_environment": {},
    "compiling": {
        "cache_data_file": "~/.lilypond-patchy-cache",
        "extra_make_options": "-j3 CPU_COUNT=3",
        "build_dir": "/tmp/lilypond-autobuild/",
        "auto_compile_results_dir": "~/lilypond-auto-compile-results/",
        "lock_check_interval": "30",
        "lock_check_count": "0",
        "build_user": "",
        "build_wrapper": "sudo -u %u",
        "patch_test_build_docs": "no",
        "patch_test_copy_docs": "no",
        },
    "runner_limits": {
        "RLIMIT_CPU": "540,600",
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
        "build_dir": "",
        "web_install_dir": "",
        "notification_to": "lilypond-auto@gnu.org",
        "notification_cc": "lilypond-devel@gnu.org",
        },
    "master": {
        "build_dir": "",
        "web_install_dir": "",
        "notification_to": "lilypond-auto@gnu.org",
        "notification_cc": "lilypond-devel@gnu.org",
        },
    "translation": {
        "build_dir": "",
        "web_install_dir": "",
        "notification_to": "lilypond-auto@gnu.org",
        "notification_cc": "translations@lilynet.net",
        }
    }

cache_stub = {
    "compiling": {
        "lock_pid": "",
        },
    "staging": {
        "last_known_good_build": "",
        },
    "master": {
        "last_known_good_build": "",
        },
    "translation": {
        "last_known_good_build": "",
        },
}

class PatchyConfig (ConfigParser.RawConfigParser):
    def __init__ (self, filename=CONFIG_FILENAME, default_config=default_config):
        ConfigParser.RawConfigParser.__init__ (self)
        for (name, section) in default_config.items ():
            self.add_section (name)
            for (option, value) in section.items ():
                self.set (name, option, value)
        self.config_filename = os.path.expanduser (filename)
        if (filename == CONFIG_FILENAME
            and not os.path.exists (self.config_filename)):
            self.copy_default_config ()
        self.read (self.config_filename)

    def copy_default_config (self):
        sys.stderr.write ("Warning: using default config; please edit %s\n"
                          % self.config_filename)
        self.write (open (self.config_filename, 'w'))
        if sys.stdin.isatty ():
            ans = raw_input (
                "Are you sure that you want to continue with the default config? (y/[n]) ")
            if not ans.lower ().startswith ('y'):
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
