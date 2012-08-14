#!/usr/bin/env python
import copy
import sys
import shutil
import os
import datetime
import shlex
import subprocess
import time
import pipes
import email.utils
from ConfigParser import NoOptionError

stderr = sys.stderr
PID_FILE = "patchy.pid"

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

class ActiveLock (Exception):
    pass

class FailedCommand (Exception):
    pass

class NothingToDoException (Exception):
    pass

class VersionControlError (Exception):
    pass

class WastedBuildException (Exception):
    pass

def remote_branch_name (branch):
    if config.getboolean ("source", "bare_git_repository"):
        return branch
    else:
        return "%s/%s" % (config.get ("source", "git_remote_name"), branch)

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
    if not (os.path.isdir (git_repository_dir) and run ("git log -1", cwd=git_repository_dir)):
        git_repository_dir = os.path.expanduser (os.environ["LILYPOND_GIT"])
    assert os.path.isdir (git_repository_dir) and run ("git log -1", cwd=git_repository_dir)
except Exception as e:
    error ("%s: non-existent directory or directory not containing a valid Git repository: %s" % (e.__class__.__name__, e))
    info ("Please set git_repository_dir in [source] section of the configuration file\n  or environment variable LILYPOND_GIT.")
    sys.exit (1)


def send_email (email_command, logfile, to, cc_replyto, CC=False):
    p = os.popen (email_command, 'w')
    p.write ("From: %s\n" % config.get ("notification", "from"))
    p.write ("Reply-To: %s\n" % cc_replyto)
    p.write ("To: %s\n" % to)
    if CC:
        p.write ("Cc: %s\n" % cc_replyto)
    p.write ("Date: %s\n" % email.utils.formatdate  (localtime=True))
    p.write ("User-Agent: Patchy - LilyPond autobuild\n")
    p.write ("Subject: %s\n\n" % config.get ("notification", "subject"))
    loglines = open (logfile.filename).readlines ()
    for line in loglines:
        p.write (line)
        info (line)
    p.close ()


class AutoCompile (object):
    ### setup
    def __init__ (self, branch="staging"):
        self.branch = branch
        self.date = datetime.datetime.now ().strftime ("%Y-%m-%d-%H")
        self.lock_check_count = config.getint ("compiling",
                                               "lock_check_count")
        self.git_repository_dir = git_repository_dir
        self.auto_compile_dir = os.path.expanduser (
            config.get ("compiling", "auto_compile_results_dir"))
        if not os.path.exists (self.auto_compile_dir):
            os.mkdir (self.auto_compile_dir)
        self.src_build_dir = os.path.expanduser (
            config.get ("compiling", "build_dir"))
        special_build_dir = config.get (branch, "build_dir")
        if special_build_dir:
            self.src_build_dir = os.path.expanduser (special_build_dir)
        self.build_dir = os.path.join (self.src_build_dir, 'build')
        self.commit = self.get_head (branch)
        self.logfile = build_logfile.BuildLogfile (
            os.path.join (self.auto_compile_dir,
                         str (MAIN_LOG_FILENAME % self.date)),
            self.commit)
        self.prev_good_commit = config.get (branch, "last_known_good_build")
        self.notification_to = config.get (branch, "notification_to")
        self.notification_cc_replyto = config.get (branch, "notification_cc")
        self.web_install_dir = config.get (branch, "web_install_dir")

    def debug (self):
        """ prints member variables """
        for key, value in self.__dict__.iteritems ():
            print "%-20s %s" % (key, value)

    def notify (self, CC=False):
        email_command = config.get ("notification", "smtp_command")
        if len (email_command) > 2:
            send_email (email_command, self.logfile, self.notification_to,
                        self.notification_cc_replyto, CC)
        else:
            info ("Message for you in %s" % self.logfile.filename)

    def get_head (self, branch="master"):
        os.chdir (self.git_repository_dir)
        return run ("git rev-parse %s" %
                    remote_branch_name (branch))

    def write_good_commit (self, branch="staging"):
        config.set (branch, "last_known_good_build",
            self.commit)
        config.save ()

    ### repository handling
    def cleanup_directories (self):
        if os.path.exists (self.src_build_dir):
            shutil.rmtree (self.src_build_dir)

    def install_web (self):
        # security measure for use in shell command
        dest = self.web_install_dir.translate (None, ';$`()[]{}|&|')
        if not (dest and os.path.isdir (os.path.dirname (dest))):
            return
        if os.path.exists (dest):
            shutil.rmtree (dest)
        os.makedirs (dest)
        web_root = os.path.join (self.build_dir, "out-www", "offline-root")
        os.chdir (web_root)
        run ("find -not -type d |xargs %s/scripts/build/out/mass-link hard . %s" %
             (self.build_dir, dest), shell=True)
        self.logfile.add_success ("installed documentation")

    def update_git (self):
        os.chdir (self.git_repository_dir)
        run ("git fetch")

    def make_directories (self, branch_name):
        os.chdir (self.git_repository_dir)
        run ("git branch -f test-%s %s/master" % (branch_name, remote_branch_name ("master")))
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

    def merge_git_branch (self, branch):
        os.chdir (self.git_repository_dir)
        run ("git fetch")
        ### Don't force a new branch here; if it already exists, we
        ### want to fail unless a previous Patchy instance has died.
        ### We use the "test-master-lock" branch like a lockfile.
        try:
            run ("git branch test-master-lock %s" % remote_branch_name ("master"))
        except FailedCommand as e:
            pid_file_path = os.path.join (self.build_dir, PID_FILE)
            if os.path.isfile (pid_file_path):
                previous_pid = open (pid_file_path).read ()
                if os.path.isdir (os.path.join ("/proc", previous_pid)):
                    raise ActiveLock ("Another instance (PID %s) is already running." % previous_pid)
                else:
                    self.logfile.write (
                        "test-master-lock and PID file exist but previous Patchy\n" +
                        "run (PID %s) died, resetting test-master-lock anyway." %
                        previous_pid)
                    run ("git branch -f test-master-lock %s" % remote_branch_name ("master"))
            else:
                raise
        run ("git branch -f test-%s %s" % (branch, remote_branch_name (branch)))
        if os.path.exists (self.src_build_dir):
            shutil.rmtree (self.src_build_dir)
        run ("git clone -s -b test-%s -o local %s %s" % (branch, self.git_repository_dir, self.src_build_dir))
        os.chdir (self.src_build_dir)
        run ("git merge --ff-only local/test-%s" % branch)

        self.commit = run ("git rev-parse HEAD")
        if self.commit == self.prev_good_commit:
            raise NothingToDoException ("Nothing to do")
        self.logfile.write ("Merged %s, now at:\t%s\n" % (branch, self.commit))
        run ("git push local test-%s" % branch)

        os.makedirs (self.build_dir)
        pid_file_path = os.path.join (self.build_dir, PID_FILE)
        open (pid_file_path, 'w').write (str (os.getpid ()))


    def merge_push (self):
        os.chdir (self.git_repository_dir)
        run ("git fetch")
        if run ("git log -1 %s..test-staging" % remote_branch_name ("staging")):
            raise VersionControlError (
                "Branch staging has been reset to some parent commit,\n" +
                "aborting operation without pushing")
        origin_head = remote_branch_name ("HEAD")
        if not run ("git log -1 %s..test-staging" % origin_head):
            if run ("git log -1 test-staging..%s" % origin_head):
                self.logfile.write ("origin has a newer revision than test-staging, not pushing")
                return
            else:
                raise WastedBuildException ()
        run ("git push %s test-staging:master" % config.get ("source", "git_remote_name"))
        self.logfile.add_success ("pushed to master\n")

    def remove_test_master_lock (self):
        os.chdir (self.git_repository_dir)
        run ("git branch -D test-master-lock")
        run ("rm -f %s" % os.path.join (self.build_dir, PID_FILE))

    def merge_branch (self, branch):
        """ merges a branch, then returns whether there
        is anything to check. """
        while self.lock_check_count >= 0:
            try:
                self.merge_git_branch (branch)
                return True
            except NothingToDoException:
                self.logfile.add_success ("No new commits in %s" % branch)
                if config.getboolean ("notification", "notify_non_action"):
                    self.notify (CC=True)
                return False
            except ActiveLock as e:
                if self.lock_check_count:
                    self.logfile.write (str (e))
                    self.lock_check_count -= 1
                    time.sleep (60 * config.getint ("compiling", "lock_check_interval"))
                else:
                    self.logfile.failed_step ("merge from %s" % branch, str(e))
                    if config.getboolean ("notification", "notify_lock"):
                        self.notify (CC=True)
            except Exception as e:
                self.logfile.failed_step ("merge from %s" % branch, str(e))
                self.notify (CC=True)
                return False

    def handle_staging (self):
        try:
            if self.merge_branch (self.branch):
                issue_id = self.branch
                self.configure (issue_id)
                self.build (quick_make=False, issue_id=issue_id)
                self.write_good_commit ()
                self.merge_push ()
                self.write_good_commit ()
                self.install_web ()
                self.notify ()
        except WastedBuildException:
            pass
        except Exception as e:
            self.logfile.failed_step ("merge from staging", str (e))
            self.notify (CC=True)
        self.remove_test_master_lock ()

    def build_branch (self):
        try:
            if self.merge_branch (self.branch):
                issue_id = self.branch
                self.configure (issue_id)
                self.build (quick_make=False, issue_id=issue_id)
                self.write_good_commit (self.branch)
                self.install_web ()
                self.notify ()
        except Exception as e:
            self.logfile.failed_step ("build %s" % self.branch, str (e))
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
