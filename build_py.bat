@echo off

set dir=%~dp0

echo python %dir%\pysrc\build.py

call python %dir%\pysrc\build.py %*

