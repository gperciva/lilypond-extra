#!/usr/bin/env python

import compile_lilypond_test
import sys

def main (branch):
    patchy = compile_lilypond_test.AutoCompile (branch)
    patchy.build_branch ()

if __name__ == "__main__":
    if not len (sys.argv) == 2:
        sys.stderr.write (
            "%s: must be called with exactly one argument to tell a branch to build"
            % sys.argv[0])
    main(sys.argv[1])
