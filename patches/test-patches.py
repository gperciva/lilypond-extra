#!/usr/bin/env python

import sys
import projecthosting_patches

def main():
    patchy = projecthosting_patches.PatchBot()
    patchy.do_new_check()

if __name__ == "__main__":
    main()

