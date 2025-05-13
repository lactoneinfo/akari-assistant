@echo off
setlocal
set SPEED=%1
shift

set TEXT=
:loop
if "%~1"=="" goto done
set TEXT=%TEXT% %1
shift
goto loop
:done

set SEIKA="assistantseika\SeikaSay2\SeikaSay2.exe"
set OUTPUT="output.wav"
%SEIKA% -cid 60051 -save %OUTPUT% -volume 1.0 -speed %SPEED% -intonation 1.0 -t "%TEXT%"
