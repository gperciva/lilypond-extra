#!/usr/bin/env python

import compile_lilypond_test

def main():
    patchy = compile_lilypond_test.AutoCompile ()
    patchy.handle_staging ()

if __name__ == "__main__":
    main()

