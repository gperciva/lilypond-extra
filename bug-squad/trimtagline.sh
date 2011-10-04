#!/bin/bash

#
# You need to have lilypond and ImageMagick's convert
# in the $PATH.
#

ly=${1:?Usage: $0 test[.ly]}

# resolution for image generation (default 150):
res=${2:-150}

# strip extension, if any:
lynoext=${ly%%.ly}

# process test file:
echo "\\header { tagline = ##f }" | lilypond -dinclude-settings=- -dresolution=$res --png $ly

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
