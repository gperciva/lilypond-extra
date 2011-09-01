#!/usr/bin/env python
import sys
import shutil
import os
import datetime
import subprocess

### Disclaimer: proof of concept


#GIT_REPOSITORY_DIR = "~/lilypond-git/"
GIT_REPOSITORY_DIR = "~/src/lilypond/"
AUTO_COMPILE_DIR = "~/src/lilypond-auto-compile"
PREVIOUS_GOOD_COMMIT_FILENAME = "previous_good_commit.txt"
MAIN_LOG_FILENAME = "log-%s.txt"

class AutoCompile():
    ### setup
    def __init__(self):
        self.date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.git_repository_dir = os.path.expanduser(GIT_REPOSITORY_DIR)
        self.auto_compile_dir = os.path.expanduser(AUTO_COMPILE_DIR)
        self.src_dir = os.path.join(self.auto_compile_dir,
                                      'src-' + self.date)
        self.build_dir = os.path.join(self.src_dir, 'build')
        self.commit = self.get_head()
        self.prev_good_commit = self.get_previous_good_commit()
        self.main_logfile = os.path.join(
            self.auto_compile_dir,
                str(MAIN_LOG_FILENAME % self.date))
        logfile = open(self.main_logfile, 'a')
        logfile.write("Begin LilyPond compile, commit:\t%s\n" % self.commit)
        logfile.close()

    def debug(self):
        """ prints member variables """
        for key, value in self.__dict__.iteritems():
            print "%-20s %s" % (key, value)

    def get_head(self):
        os.chdir(self.git_repository_dir)
        cmd = "git rev-parse HEAD"
        p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        head = p.communicate()[0].strip()
        return head

    def get_previous_good_commit(self):
        try:
            previous_good_commit_file = open(os.path.join(
                self.auto_compile_dir,
                PREVIOUS_GOOD_COMMIT_FILENAME))
            prev_good_commit = previous_good_commit_file.read().split()[0]
        except IOError:
            prev_good_commit = ''
        return prev_good_commit

    def write_good_commit(self):
        outfile = open(os.path.join(os.path.join(
                       self.auto_compile_dir,
                       PREVIOUS_GOOD_COMMIT_FILENAME)), 'w')
        outfile.write(self.commit)

    def add_success(self, name):
        logfile = open(self.main_logfile, 'a')
        logfile.write("\tSuccess:\t\t%s\n" % name)
        logfile.close()

    def failed_build(self, name):
        logfile = open(self.main_logfile, 'a')
        logfile.write("*** FAILED BUILD ***\n")
        logfile.write("\tPrevious good commit:\t%s\n" % self.prev_good_commit)
        logfile.write("\tCurrent broken commit:\t%s\n" % self.commit)
        logfile.close()
        ### TODO: send email to -devel ?
        #cmd = "mail -s \"Failed build with %s\" lilypond-devel@gnu.org < %s" % (self.commit, self.main_logfile)
        shutil.copy(self.main_logfile, "/home/gperciva/Desktop/")

    ### actual building
    def make_directories(self):
        if os.path.exists(self.src_dir):
            shutil.rmtree(self.src_dir)
        os.chdir(self.git_repository_dir)
        cmd = "git checkout-index -a --prefix=%s/ " % (self.src_dir)
        os.system(cmd)
        os.makedirs(self.build_dir)

    def runner(self, dirname, command, name):
        logfile = open(os.path.join(self.src_dir, 'log-%s.txt'%name), 'w')
        os.chdir(dirname)
        p = subprocess.Popen(command.split(), stdout=logfile, stderr=logfile)
        p.wait()
        returncode = p.returncode
        logfile.close()
        if returncode != 0:
            self.failed_build(name)
            return False
        self.add_success(name)
        return True

    def build(self):
        self.make_directories()

        # ick, nice-ify this!
        a=self.runner(self.src_dir, "./autogen.sh --noconfigure", "autogen.sh")
        if not a:
            return False
        a=self.runner(self.build_dir, "../configure", "configure")
        if not a:
            return False
        a=self.runner(self.build_dir, "make", "make")
        if not a:
            return False
        #a=self.runner(self.build_dir, "make test", "make test")
        if not a:
            return False
        #a=self.runner(self.build_dir, "make doc", "make doc")
        if not a:
            return False

        # no problems found
        self.write_good_commit()
        return True
  

if __name__ == "__main__":
    autoCompile = AutoCompile()
    #autoCompile.debug()
    autoCompile.build()

