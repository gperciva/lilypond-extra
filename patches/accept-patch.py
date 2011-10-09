#!/usr/bin/env python

import sys
import projecthosting_patches

def main(issue_id):
    patchy = projecthosting_patches.PatchBot()
    patchy.accept_patch(issue_id)

if __name__ == "__main__":
    main(sys.argv[1])

