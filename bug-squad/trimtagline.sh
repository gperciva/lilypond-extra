#!/bin/bash

#
# You need to have lilypond and ImageMagick's convert
# in the $PATH.
#

ly=${1:?Usage: $0 test[.ly]}

# strip extension, if any:
lynoext=${ly%%.ly}

# process test file:
echo "\\header { tagline = ##f }" | lilypond -dinclude-settings=- --png $ly

# trim PNG:
convert ${lynoext}.png -trim ${lynoext}-trim.png

# do we want to overwrite "original" PNG?
mv ${lynoext}-trim.png ${lynoext}.png


##
## Note, if we wanted to remove explicitly set tagline,
## we could use this command instead of above:
##
# ( cat test.ly ; echo "\\header { tagline = \"\" }" ) \
#	| lilypond --png -o test -
##
## (and then, anyway: convert ... -trim ... && mv ...
##
