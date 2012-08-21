#!/usr/bin/env python
import copy
import sys
import glob
import os
import datetime
import shlex
import subprocess
import time
import pipes
import email.utils
import traceback
import resource
import hashlib
TRACEBACK_LIMIT = 40

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
#
# If you build docs (for instance for testing staging branch),
# increase the size=700M to size=2048M.

config = patchy_config.PatchyConfig ()

def set_limits (config_section="runner_limits"):
    for (name, value) in config.items (config_section):
        if value and name in resource.__dict__:
            if "," in value:
                parsed_value = map (int, value.split (","))
            else:
                parsed_value = int (value)
                parsed_value = (parsed_value, parsed_value)
            resource.setrlimit (resource.__dict__[name], parsed_value)
set_limits ("self_limits")

cache = patchy_config.PatchyConfig (
    config.get ("compiling", "cache_data_file"),
    patchy_config.cache_stub)
build_user = config.get ("compiling", "build_user")
build_wrapper = config.get ("compiling", "build_wrapper").replace (
    "%u", build_user)

MAIN_LOG_FILENAME = "log-%s.txt"

class ActiveLock (Exception):
    pass

class FailedCommand (Exception):
    pass

class NothingToDoException (Exception):
    pass

class VersionControlError (Exception):
    pass

class DuplicateBuildException (Exception):
    pass

def remote_branch_name (branch):
    if config.getboolean ("source", "bare_git_repository"):
        return branch
    else:
        return "%s/%s" % (config.get ("source", "git_remote_name"), branch)

def run (cmd, wrapped=False, **kwargs):
    """ runs the command and returns the stdout when successful,
        otherwise raises an exception that includes the stderr """
    if 'shell' in kwargs and kwargs["shell"] == True:
        if wrapped and build_user:
            cmd = shlex.split ('%s /bin/bash -c "%s"' % (build_wrapper, cmd))
            del kwargs["shell"]
    else:
        if wrapped and build_user:
            cmd = build_wrapper + " " + cmd
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
    p.write (logfile.log_record)
    info (logfile.log_record)
    signature = config.get ("notification", "signature")
    if signature:
        p.write ("--\n%s\n" % signature)
    p.close ()


class AutoCompile (object):
    ### setup
    def __init__ (self, branch="staging"):
        global stderr
        self.branch = branch
        self.date = datetime.datetime.now ().strftime ("%Y-%m-%d-%H")
        self.lock_check_count = config.getint ("compiling",
                                               "lock_check_count")
        self.git_repository_dir = git_repository_dir
        self.auto_compile_dir = os.path.expanduser (
            config.get ("compiling", "auto_compile_results_dir"))
        if not os.path.exists (self.auto_compile_dir):
            os.mkdir (self.auto_compile_dir)
        self.src_build_dir = os.path.normpath (os.path.expanduser (
            config.get ("compiling", "build_dir")))
        special_build_dir = config.get (branch, "build_dir")
        if special_build_dir:
            self.src_build_dir = os.path.expanduser (special_build_dir)
        self.build_dir = os.path.normpath (os.path.join (
                self.src_build_dir,
                "../build-%s"
                % os.path.basename (os.path.normpath (self.src_build_dir))))
        self.commit = self.get_head (branch)
        self.logfile = build_logfile.BuildLogfile (
            os.path.join (self.auto_compile_dir,
                         str (MAIN_LOG_FILENAME % self.date)),
            self.commit)
        stderr = self.logfile
        self.prev_good_commit = cache.get (branch, "last_known_good_build")
        self.notification_to = config.get (branch, "notification_to")
        self.notification_cc_replyto = config.get (branch, "notification_cc")
        self.web_install_dir = config.get (branch, "web_install_dir")
        self.log_dir = os.path.normpath (os.path.join (
                self.src_build_dir, '../lilypond-log'))
        if not os.path.exists (self.log_dir):
            os.makedirs (self.log_dir)

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
        cache.set (branch, "last_known_good_build",
            self.commit)
        cache.save ()

    ### repository handling
    def cleanup_directories (self):
        if os.path.exists (self.src_build_dir):
            run ("rm -rf %s" % self.src_build_dir, wrapped=True)
        if os.path.exists (self.build_dir):
            run ("rm -rf %s" % self.build_dir, wrapped=True)

    def install_web (self):
        # security measure for use in shell command
        dest = self.web_install_dir.translate (None, ';$`()[]{}|&|')
        if not (dest and os.path.isdir (os.path.dirname (dest))):
            return
        if os.path.exists (dest):
            run ("rm -rf %s" % dest, wrapped=True)
        run ("mkdir -p %s" % dest, wrapped=True)
        web_root = os.path.join (self.build_dir, "out-www", "offline-root")
        os.chdir (web_root)
        run ("find -not -type d |xargs %s/scripts/build/out/mass-link hard . %s" %
             (self.build_dir, dest), wrapped=True, shell=True)
        try:
            doc_url = os.path.join (
                config.get ("server", "doc_base_url"),
                os.path.basename (os.path.normpath (dest)))
        except:
            doc_url = dest
        self.logfile.add_success ("installed documentation in %s" % doc_url)

    def update_git (self):
        os.chdir (self.git_repository_dir)
        run ("git fetch")

    def make_directories (self, branch, selection=('source', 'build')):
        if 'source' in selection:
            os.chdir (self.git_repository_dir)
            run ("git branch -f test-%s %s" % (branch, remote_branch_name (branch)))
            run ("git clone -s -b test-%s -o local %s %s"
                 % (branch, self.git_repository_dir, self.src_build_dir),
                 wrapped=True)
        if 'build' in selection:
            run ("mkdir -p %s" % self.build_dir, wrapped=True)

    def runner (self, dirname, command, issue_id=None, name=None, env=None):
        if not name:
            name = command.replace (" ", "-").replace ("/", "-")
        this_logfilename = "log-%s-%s.txt" % (str (issue_id), name)
        this_logfile = open (os.path.join (self.log_dir, this_logfilename), 'w')
        os.chdir (dirname)
        if type (env) is dict and env:
            updated_env = copy.copy (os.environ)
            updated_env.update (env)
        else:
            updated_env = None
        if build_user:
            command = build_wrapper + " " + command
        p = subprocess.Popen (shlex.split (command), stdout=this_logfile,
            stderr=subprocess.STDOUT, env=updated_env, preexec_fn=set_limits)
        p.wait ()
        returncode = p.returncode
        this_logfile.close ()
        if returncode != 0:
            self.logfile.failed_build (command,
                self.prev_good_commit, self.commit)
            raise FailedCommand ("Failed runner: %s\nSee the log file %s" % (command, this_logfilename))
        else:
            self.logfile.add_success (command)

    def test_issue (self, issue_id, patch_filename, title):
        self.patch (patch_filename, issue_id)
        self.configure (issue_id)
        self.build (patch_test=True, issue_id=issue_id)
        public_results_dir = self.copy_logs (issue_id)
        public_results_dir = self.copy_regtests (issue_id)
        if not config.get (
            "server", "tests_results_install_dir"):
            self.make_regtest_show_script (issue_id, title)
        return public_results_dir

    def cleanup_issue (self, issue_id, patch_filename):
        self.clean (issue_id, target="test")
        if config.getboolean ("compiling", "patch_test_build_docs"):
            self.clean (issue_id, target="doc")
        self.clean (issue_id)
        os.chdir (self.src_build_dir)
        run ("git reset --hard", wrapped=True)

    def configure (self, issue_id=None):
        self.runner (self.src_build_dir, "./autogen.sh --noconfigure",
            issue_id, "autogen.sh")
        self.runner (self.build_dir,
            os.path.join (self.src_build_dir, "configure") + " --disable-optimising",
            issue_id, "configure", env=dict (config.items ("configure_environment")))

    def patch (self, filename, issue_id):
        os.chdir (self.src_build_dir)
        run ("git reset --hard", wrapped=True)
        run ("git clean -f -d -x", wrapped=True)
        self.runner (self.src_build_dir,
                     "git apply --index %s" % filename,
                     issue_id)

    ### actual building
    def build (self, patch_prepare=False, patch_test=False, issue_id=None):
        self.clean (issue_id)
        self.runner (self.build_dir, "nice make "
            + config.get ("compiling", "extra_make_options"),
            issue_id)
        if patch_test:
            self.runner (self.build_dir, "nice make check "
                         + config.get ("compiling", "extra_make_options"),
                         issue_id)
        else:
            if patch_prepare:
                test_suffix = "-baseline"
            else:
                test_suffix = ""
            self.runner (self.build_dir, "nice make test%s " % test_suffix
                         + config.get ("compiling", "extra_make_options"),
                         issue_id)
        if (not (patch_prepare or patch_test)
            or config.getboolean ("compiling", "patch_test_build_docs")):
            self.runner (self.build_dir, "nice make doc "
                         + config.get ("compiling", "extra_make_options"),
                         issue_id)

    def clean (self, issue_id=None, target="all"):
        if target == "all":
            clean_prefix = ""
        else:
            clean_prefix = target + "-"
        self.runner (self.build_dir, "nice make %sclean" % clean_prefix,
            issue_id)

    def make_regtest_show_script (self,issue_id, title):
        script_filename = os.path.join (self.auto_compile_dir,
            "show-regtests-%s.sh" % (issue_id))
        out = open (script_filename, 'w')
        out.write ("echo %s\n" % pipes.quote  (title))
        out.write ("firefox %s\n" % os.path.join (
            self.build_dir, "../show-%i/test-results/index.html" % issue_id))
        out.close ()

    def process_build_files (self, issue_id, target,
                             working_directory, command, wrapped=True):
        str_issue_id = str (issue_id).translate (None, ';$`()[]{}|&|')
        web_results_dir = config.get ("server", "tests_results_install_dir")
        if web_results_dir:
            dest = os.path.join (web_results_dir, str_issue_id, target)
            public_dest = os.path.join (
                config.get ("server", "tests_results_base_url"),
                "%s/" % str_issue_id,
                target)
        else:
            dest = os.path.join (self.build_dir,
                                 "../show-%s" % str_issue_id,
                                 target)
            public_dest = dest
        dest = dest.translate (None, ';$`()[]{}|&|')
        public_dest = public_dest.translate (None, ';$`()[]{}|&|')
        run ("mkdir -p %s" % dest, wrapped=wrapped)
        if wrapped:
            run ("chmod 0775 %s" % dest, wrapped=True)
        os.chdir (working_directory)
        run (command % locals (), wrapped=wrapped, shell=True)
        return public_dest

    def copy_regtests (self, issue_id):
        if (config.getboolean ("compiling", "patch_test_build_docs")
            and config.getboolean ("compiling", "patch_test_copy_docs")):
            self.process_build_files (
                issue_id,
                "docs",
                os.path.join (self.build_dir, "out-www/offline-root"),
                "find -not -type d |xargs ../../scripts/build/out/mass-link hard . %(dest)s")
        return self.process_build_files (
            issue_id,
            "test-results",
            os.path.join (self.build_dir, "out/test-results/"),
            "find -not -type d |xargs ../../scripts/build/out/mass-link hard . %(dest)s")

    def copy_logs (self, issue_id):
        results_dir = self.process_build_files (
            issue_id,
            ".",
            self.build_dir,
            "find . -name '*.log' |xargs scripts/build/out/mass-link hard . %(dest)s")
        self.copy_outer_logs (issue_id)
        return results_dir

    def copy_outer_logs (self, issue_id):
        web_results_dir = config.get ("server", "tests_results_install_dir")
        if web_results_dir:
            dest = os.path.join (web_results_dir, str (issue_id))
        else:
            dest = os.path.join (self.build_dir,
                                 "../show-%s" % str (issue_id))
        run ("ln -f %s/log-%s-*.txt %s" %
             (self.log_dir, str (issue_id), dest),
             shell=True)

    def copy_build_tree (self, issue_id):
        results_dir = self.process_build_files (
            issue_id,
            ".",
            self.build_dir,
            "find -not -type d -and -not -type l |xargs scripts/build/out/mass-link hard . %(dest)s")
        self.copy_outer_logs (issue_id)
        return results_dir

    def merge_git_branch (self, branch, require_directories=False):
        self.update_git ()
        ### Don't force a new branch here; if it already exists, we
        ### want to fail unless a previous Patchy instance has died.
        ### We use the "test-master-lock" branch like a lockfile.
        try:
            run ("git branch test-master-lock %s" % remote_branch_name ("master"))
        except FailedCommand as e:
            try:
                previous_pid = cache.get ("compiling", "lock_pid").strip ()
                # This is an assertion test, PLEASE KEEP THIS LINE
                int (previous_pid)
                if not previous_pid:
                    raise e
                if os.path.isdir (os.path.join ("/proc", previous_pid)):
                    raise ActiveLock ("Another instance (PID %s) is already running." % previous_pid)
                else:
                    self.logfile.write (
                        "test-master-lock and PID entry exist but previous Patchy\n" +
                        "run (PID %s) died, resetting test-master-lock anyway." %
                        previous_pid)
                    run ("git branch -f test-master-lock %s" % remote_branch_name ("master"))
            except ActiveLock:
                raise
            except Exception as e1:
                warn ("exception occured while looking for other running Patchy instances: %s"
                      % str (e1))
                raise e
        cache.set ("compiling", "lock_pid", str (os.getpid ()))
        cache.save ()
        self.commit = run ("git rev-parse %s" % remote_branch_name (branch))
        if self.commit == self.prev_good_commit:
            if require_directories:
                if not os.path.exists (self.src_build_dir):
                    self.make_directories (branch, ('source',))
                if not os.path.exists (self.build_dir):
                    self.make_directories (branch, ('build',))
            raise NothingToDoException ("Nothing to do")
        self.cleanup_directories ()
        self.make_directories (branch)
        self.logfile.write ("Merged %s, now at:\t%s\n" % (branch, self.commit))

    def merge_push (self):
        os.chdir (self.git_repository_dir)
        run ("git fetch")
        if run ("git log -1 %s..test-staging" % remote_branch_name ("staging")):
            raise VersionControlError (
                "Branch staging has been reset to some parent commit,\n" +
                "aborting operation without pushing.")
        origin_head = remote_branch_name ("HEAD")
        if not run ("git log -1 %s..test-staging" % origin_head):
            if run ("git log -1 test-staging..%s" % origin_head):
                self.logfile.write ("origin has a newer revision than test-staging, not pushing.")
                return
            else:
                self.logfile.write (
                    "this Git revision has already been pushed by an operator other than this Patchy.")
                raise DuplicateBuildException ()
        run ("git push %s test-staging:master" % config.get ("source", "git_remote_name"))
        self.logfile.add_success ("pushed to master\n")

    def remove_test_master_lock (self):
        os.chdir (self.git_repository_dir)
        run ("git branch -D test-master-lock")
        cache.remove_option ("compiling", "lock_pid")
        cache.save ()

    def merge_branch (self, branch, notify=True, **kwargs):
        """ merges a branch, then returns whether there
        is anything to check. """
        while self.lock_check_count >= 0:
            try:
                self.merge_git_branch (branch, **kwargs)
                self.clear_baseline_data ()
                return True
            except NothingToDoException:
                self.logfile.add_success ("No new commits in %s" % branch)
                if notify and config.getboolean ("notification", "notify_non_action"):
                    self.notify ()
                return False
            except ActiveLock as e:
                if self.lock_check_count:
                    self.logfile.write (str (e))
                    self.lock_check_count -= 1
                    time.sleep (60 * config.getint ("compiling", "lock_check_interval"))
                else:
                    self.logfile.failed_step ("merge from %s" % branch, str(e))
                    if notify:
                        if config.getboolean ("notification", "notify_lock"):
                            self.notify ()
                    sys.exit (3)
            except Exception as e:
                self.logfile.failed_step ("merge from %s" % branch, str(e))
                self.logfile.write (traceback.format_exc (TRACEBACK_LIMIT))
                if notify:
                    self.notify (CC=True)
                sys.exit (3)

    def handle_staging (self):
        try:
            if self.merge_branch (self.branch):
                issue_id = self.branch
                self.configure (issue_id)
                self.build (issue_id=issue_id)
                self.write_good_commit ()
                self.merge_push ()
                self.write_good_commit ()
                self.install_web ()
                self.notify ()
        except DuplicateBuildException:
            try:
                self.install_web ()
            except Exception as e:
                self.logfile.failed_step ("merge from staging", str(e))
                self.logfile.write (traceback.format_exc (TRACEBACK_LIMIT))
            self.notify ()
        except Exception as e:
            self.logfile.failed_step ("merge from staging", str (e))
            self.logfile.write (traceback.format_exc (TRACEBACK_LIMIT))
            self.notify (CC=True)
        self.remove_test_master_lock ()

    def checksum_baseline (self):
        h = hashlib.sha1 (self.commit)
        for dir_basename in (".", "abc2ly", "lilypond-book",
                             "midi", "musicxml"):
            dir = os.path.join (self.build_dir,
                                "input/regression",
                                dir_basename,
                                "out-test-baseline")
            for root, subdirs, files in os.walk (dir):
                for f in files:
                    h.update (
                        open (os.path.join (root, f)).read ())
        return h.hexdigest ()

    def register_baseline (self):
        cache.set (self.branch, "test_baseline_checksum", self.checksum_baseline ())
        cache.save ()

    def clear_baseline_data (self):
        try:
            cache.remove_option (self.branch, "test_baseline_checksum")
        except:
            info ("Branch %s: no data to clear." % self.branch)
        cache.save ()

    def need_baseline_rebuild (self):
        "Returns True when some baseline results miss."
        try:
            old_checksum  = cache.get (self.branch, "test_baseline_checksum")
        except:
            self.logfile.write (
                "Could not find checksum of previous test baseline, must rebuild.")
            return True
        check = old_checksum != self.checksum_baseline ()
        if check:
            self.logfile.write (
                "Git revision has not changed but checksum of test baseline has, must rebuild.")
        else:
            self.logfile.write (
                "Using test baseline from previous build.")
        return check

    def build_branch (self, patch_prepare=False):
        try:
            if (self.merge_branch (self.branch,
                                   notify=not patch_prepare,
                                   require_directories=True)
                or (patch_prepare and self.need_baseline_rebuild ())):
                self.configure (self.branch)
                self.build (patch_prepare=patch_prepare, issue_id=self.branch)
                self.write_good_commit (self.branch)
                if patch_prepare:
                    self.register_baseline ()
                    return
                self.install_web ()
                self.notify ()
        except Exception as e:
            self.logfile.failed_step ("build %s" % self.branch, str (e))
            self.logfile.write (traceback.format_exc (TRACEBACK_LIMIT))
            if patch_prepare:
                raise
            self.notify (CC=True)
        if not patch_prepare:
            self.remove_test_master_lock ()
