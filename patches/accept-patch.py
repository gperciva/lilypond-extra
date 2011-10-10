#!/usr/bin/env python

import sys
import projecthosting_patches

def main(issue_id, reason):
    patchy = projecthosting_patches.PatchBot()
    patchy.accept_patch(issue_id, reason)

if __name__ == "__main__":
    issue_id = sys.argv[1]
    reason = ' '.join( sys.argv[2:])
    main(issue_id, reason)

