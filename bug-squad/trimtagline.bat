@echo off
rem
rem -- trimtagline.bat --
rem

rem -- Get only file name, no extension:
set LY=%~n1

IF filename%LY%==filename (
	echo Usage: %0 test[.ly].
) ELSE (
	echo \header { tagline = ##f } | lilypond -dinclude-settings=- --png %LY%

	rem -- This is ImageMagick's "convert.exe":
	imconvert %LY%.png -trim %LY%-trim.png
)

rem
rem -- Note, you need to copy/rename convert.exe
rem -- to something like imconvert.exe
rem -- because windows already has convert.exe in the path.
rem
rem
rem -- Note, if you can not (or do not want to) install ImageMagick,
rem -- you can use this "kind of trimming":
rem echo \header { tagline = ##f } | lilypond -dinclude-settings=- -dbackend=eps -dno-aux-files --png %LY%
rem
rem -- This will produce "almost as vertically trimmed as above" png,
rem -- but leave full "linewidth".
rem
