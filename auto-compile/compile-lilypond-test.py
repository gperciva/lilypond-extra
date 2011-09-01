#!/usr/bin/env python
import sys
import shutil
import os
import datetime
import subprocess


#GIT_REPOSITORY_DIR = "~/lilypond-git/"
GIT_REPOSITORY_DIR = "~/src/lilypond/"
AUTO_COMPILE_DIR = "~/src/lilypond-extra/auto-compile"

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

    def failed_build(self, name):
        # TODO: send email to -devel
        print "FAILED build step", name


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
        return True


    def build(self):
        self.make_directories()
        self.runner(self.src_dir, "./autogen.sh --noconfigure", "autogen.sh")
        self.runner(self.build_dir, "../configure", "configure")
        self.runner(self.build_dir, "make", "make")
    

if __name__ == "__main__":
    autoCompile = AutoCompile()
    autoCompile.debug()
    autoCompile.build()

