@echo off

cd /d %~dp0

call build_py.bat 1234 -t e:\PycharmProjects\repacktool\app-release.apk

pause