#!/usr/bin/env python

import sys
import projecthosting_patches
from compile_lilypond_test import config

def main (issues_id = None):
    patchy = projecthosting_patches.PatchBot ()
    if issues_id:
        issues = patchy.get_issues (issues_id)
    elif config.get ("server", "tests_results_base_url"):
        issues = patchy.get_testable_issues ()
    else:
        issues = patchy.get_new_patches ()
    patchy.do_check (issues)

if __name__ == "__main__":
    issues_id = sys.argv[1:]
    main (issues_id)
