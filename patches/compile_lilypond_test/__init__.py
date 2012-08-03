#!/usr/bin/env python
import copy
import sys
import shutil
import os
import datetime
import shlex
import subprocess
import pipes
import email.utils
from ConfigParser import NoOptionError

stderr = sys.stderr

def info (s):
    stderr.write (s + '\n')

def warn (s):
    stderr.write ("Warning: %s\n" % s)

def error (s):
    stderr.write ("Error: %s\n" % s)

import build_logfile
import patchy_config

# enable a ramdisk
# 1. copy this line into /etc/fstab:
#      tmpfs /tmp/ramdisk tmpfs size=700M,user,exec 0 0
#    (use no # when you put into /etc/fstab)
# 2. type:
#      mount /tmp/ramdisk

# OPTIONAL: increase the size=700M to size=2048M and enable this:
BUILD_ALL_DOCS = True

config = patchy_config.PatchyConfig ()
MAIN_LOG_FILENAME = "log-%s.txt"

class NothingToDoException (Exception):
    pass

class FailedCommand (Exception):
    pass

def run (cmd, **kwargs):
    """ runs the command and returns the stdout when successful,
        otherwise raises an exception that includes the stderr """
    if not 'shell' in kwargs or kwargs['shell'] != True:
        cmd = shlex.split (cmd)
    p = subprocess.Popen (cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    stdout, stderr = p.communicate ()
    returncode = p.returncode
    if returncode != 0:
        raise FailedCommand ("Command '%s' returned non-zero exit status %d\n%s" % (cmd, returncode, stderr.strip ()))
    if stderr:
        info (stderr.strip ())
    return stdout.strip ()

try:
    try:
        git_repository_dir = os.path.expanduser (config.get ("source", "git_repository_dir"))
    except NoOptionError:
        git_repository_dir = ""
    if not (os.path.isdir (git_repository_dir) and run ("git status", cwd=git_repository_dir)):
        git_repository_dir = os.path.expanduser (os.environ["LILYPOND_GIT"])
    assert os.path.isdir (git_repository_dir) and run ("git status", cwd=git_repository_dir)
except Exception as e:
    error ("%s: non-existent directory or directory not containing a valid Git repository: %s" % (e.__class__.__name__, e))
    info ("Please set git_repository_dir in [source] section of the configuration file\n  or environment variable LILYPOND_GIT.")
    sys.exit (1)


def send_email (email_command, logfile, CC=False):
    p = os.popen (email_command, 'w')
    p.write ("From: %s\n" % config.get ("notification", "from"))
    p.write ("Reply-To: lilypond-devel@gnu.org\n")
    p.write ("To: lilypond-auto@gnu.org\n")
    if CC:
        p.write ("Cc: lilypond-devel@gnu.org\n")
    p.write ("Date: %s\n" % email.utils.formatdate  (localtime=True))
    p.write ("User-Agent: Patchy - LilyPond autobuild\n")
    p.write ("Subject: Patchy email\n\n")
    loglines = open (logfile.filename).readlines ()
    for line in loglines:
        p.write (line + "\n")
        info (line)
    p.close ()


class AutoCompile (object):
    ### setup
    def __init__ (self):
        self.date = datetime.datetime.now ().strftime ("%Y-%m-%d-%H")
        self.git_repository_dir = git_repository_dir
        self.auto_compile_dir = os.path.expanduser (
            config.get ("compiling", "auto_compile_results_dir"))
        if not os.path.exists (self.auto_compile_dir):
            os.mkdir (self.auto_compile_dir)
        self.src_build_dir = os.path.expanduser (
            config.get ("compiling", "build_dir"))
        self.build_dir = os.path.join (self.src_build_dir, 'build')
        self.commit = self.get_head ()
        self.prev_good_commit = config.get ("previous good compile", "last_known")
        self.logfile = build_logfile.BuildLogfile (
            os.path.join (self.auto_compile_dir,
                         str (MAIN_LOG_FILENAME % self.date)),
            self.commit)

    def debug (self):
        """ prints member variables """
        for key, value in self.__dict__.iteritems ():
            print "%-20s %s" % (key, value)

    def notify (self, CC=False):
        email_command = config.get ("notification", "smtp_command")
        if len (email_command) > 2:
            send_email (email_command, self.logfile, CC)
        else:
            info ("Message for you in %s" % self.logfile.filename)

    def get_head (self):
        os.chdir (self.git_repository_dir)
        return run ("git rev-parse %s/master" % config.get ("source", "git_remote_name"))

    def write_good_commit (self):
        config.set ("previous good compile", "last_known",
            self.commit)
        config.save ()

    ### repository handling
    def cleanup_directories (self):
        if os.path.exists (self.src_build_dir):
            shutil.rmtree (self.src_build_dir)

    def update_git (self):
        os.chdir (self.git_repository_dir)
        run ("git fetch")

    def make_directories (self, branch_name):
        os.chdir (self.git_repository_dir)
        run ("git branch -f test-%s %s/master" % (branch_name, config.get ("source", "git_remote_name")))
        run ("git clone -s -b test-%s -o local %s %s" % (branch_name, self.git_repository_dir, self.src_build_dir))
        os.makedirs (self.build_dir)

    def runner (self, dirname, command, issue_id=None, name=None, env=None):
        if not name:
            name = command.replace (" ", "-").replace ("/", "-")
        this_logfilename = "log-%s-%s.txt" % (str (issue_id), name)
        this_logfile = open (os.path.join (self.src_build_dir, this_logfilename), 'w')
        os.chdir (dirname)
        if type (env) is dict and env:
            updated_env = copy.copy (os.environ)
            updated_env.update (env)
        else:
            updated_env = None
        p = subprocess.Popen (shlex.split (command), stdout=this_logfile,
            stderr=subprocess.STDOUT, env=updated_env)
        p.wait ()
        returncode = p.returncode
        this_logfile.close ()
        if returncode != 0:
            self.logfile.failed_build (command,
                self.prev_good_commit, self.commit)
            raise FailedCommand ("Failed runner: %s\nSee the log file %s" % (command, this_logfilename))
        else:
            self.logfile.add_success (command)

    def prep_for_rietveld (self, issue_id=None):
        self.cleanup_directories ()
        self.update_git ()
        self.make_directories ('rietveld')

    def configure (self, issue_id=None):
        self.runner (self.src_build_dir, "./autogen.sh --noconfigure",
            issue_id, "autogen.sh")
        self.runner (self.build_dir,
            "../configure --disable-optimising",
            issue_id, "configure", env=dict (config.items ("configure_environment")))

    def patch (self, filename, reverse=False):
        os.chdir (self.src_build_dir)
        if reverse:
            cmd = "git reset --hard"
        else:
            cmd = "git apply --index %s" % filename
        try:
            run (cmd)
        except Exception as err:
            self.logfile.failed_step (cmd, err)
            raise err
        self.logfile.add_success (cmd)

    ### actual building
    def build (self, quick_make = False, issue_id=None):
        self.runner (self.build_dir, "nice make clean ",
            issue_id)
        self.runner (self.build_dir, "nice make "
            + config.get ("compiling", "extra_make_options"),
            issue_id)
        if quick_make:
            return True
        self.runner (self.build_dir, "nice make test "
            + config.get ("compiling", "extra_make_options"),
            issue_id)
        if BUILD_ALL_DOCS:
            self.runner (self.build_dir, "nice make doc "
                + config.get ("compiling", "extra_make_options"),
                issue_id)

    def regtest_baseline (self, issue_id=None):
        self.runner (self.build_dir, "nice make test-baseline "
            + config.get ("compiling", "extra_make_options"),
            issue_id)

    def regtest_check (self, issue_id=None):
        self.runner (self.build_dir, "nice make check "
            + config.get ("compiling", "extra_make_options"),
            issue_id)

    def clean (self, issue_id=None):
        self.runner (self.build_dir, "nice make clean"
            ,
            issue_id)

    def regtest_clean (self, issue_id=None):
        self.runner (self.build_dir, "nice make test-clean "
            + config.get ("compiling", "extra_make_options"),
            issue_id)

    def make_regtest_show_script (self,issue_id, title):
        script_filename = os.path.join (self.auto_compile_dir,
            "show-regtests-%s.sh" % (issue_id))
        out = open (script_filename, 'w')
        out.write ("echo %s\n" % pipes.quote  (title))
        out.write ("firefox %s\n" % os.path.join (
            self.build_dir, "show-%i/test-results/index.html" % issue_id))
        out.close ()

    def copy_regtests (self, issue_id):
        shutil.copytree (
            os.path.join (self.build_dir, "out/test-results/"),
            os.path.join (self.build_dir, "show-%i/test-results/" % issue_id))

    def merge_staging_git (self):
        if os.path.exists (self.src_build_dir):
            shutil.rmtree (self.src_build_dir)
        os.chdir (self.git_repository_dir)
        run ("git fetch")
        ### don't force a new branch here; if it already exists,
        ### we want to die.  We use the "test-master-lock" branch like
        ### a lockfile
        origin = config.get ("source", "git_remote_name")
        run ("git branch test-master-lock %s/master" % origin)
        run ("git branch -f test-staging %s/staging" % origin)
        run ("git clone -s -b test-master-lock -o local %s %s" % (self.git_repository_dir, self.src_build_dir))
        os.chdir (self.src_build_dir)
        run ("git merge --ff-only local/test-staging")

        self.commit = run ("git rev-parse HEAD")
        if self.commit == self.prev_good_commit:
            raise NothingToDoException ("Nothing to do")
        self.logfile.write ("Merged staging, now at:\t%s\n" % self.commit)
        run ("git push local test-master-lock")

        os.makedirs (self.build_dir)


    def merge_push (self):
        os.chdir (self.git_repository_dir)
        run ("git push %s test-master-lock:master" % config.get ("source", "git_remote_name"))
        self.logfile.add_success ("pushed to master\n")
        # TODO: update dev/staging in some way?

    def remove_test_master_lock (self):
        os.chdir (self.git_repository_dir)
        run ("git branch -D test-master-lock")


    def merge_staging (self):
        """ merges the staging branch, then returns whether there
        is anything to check. """
        try:
            self.merge_staging_git ()
            return True
        except NothingToDoException:
            self.logfile.add_success ("No new commits in staging")
            if config.getboolean ("notification", "notify_non_action"):
                self.notify ()
        except Exception as e:
            self.logfile.failed_step ("merge from staging", str(e))
            self.notify (CC=True)
        return False

    def handle_staging (self):
        try:
            if self.merge_staging ():
                issue_id = "staging"
                self.configure (issue_id)
                self.build (quick_make=False, issue_id=issue_id)
                self.write_good_commit ()
                self.merge_push ()
                self.write_good_commit ()
                self.notify ()
        except Exception as e:
            self.logfile.failed_step ("merge from staging", str (e))
            self.notify (CC=True)
        self.remove_test_master_lock ()

def main (patches = None):
    if not patches:
        pass
    else:
        info ("Fetching, cloning, compiling master.")
        autoCompile = AutoCompile ()
        autoCompile.prep_for_rietveld ()
        try:
            autoCompile.configure ()
            autoCompile.build (quick_make=True)
            autoCompile.regtest_baseline ()
        except Exception as err:
            error ("problem compiling master. Patchy cannot reliably continue.")
            raise err
        for patch in patches:
            issue_id = patch[0]
            patch_filename = patch[1]
            title = patch[2].encode ('ascii', 'ignore')
            info ("Issue %i: %s" % (issue_id, title))
            info ("Issue %i: Testing patch %s" % (issue_id, patch_filename))
            try:
                autoCompile.patch (patch_filename)
                autoCompile.configure (issue_id)
                autoCompile.build (quick_make=True, issue_id=issue_id)
                autoCompile.regtest_check (issue_id)
                autoCompile.copy_regtests (issue_id)
                autoCompile.make_regtest_show_script (issue_id, title)
            except Exception as err:
                error ("issue %i: Problem encountered" % issue_id)
                info (str (err))
            info ("Issue %i: Cleaning up" % issue_id)
            try:
                autoCompile.regtest_clean (issue_id)
                autoCompile.clean (issue_id)
                autoCompile.patch (patch_filename, reverse=True)
            except Exception as err:
                error ("problem cleaning up after issue %i" % issue_id)
                error ("Patchy cannot reliably continue.")
                raise err
            info ("Issue %i: Done." % issue_id)
