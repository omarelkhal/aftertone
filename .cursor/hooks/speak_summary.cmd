@echo off
REM Project-level Cursor hook: Git Bash + speak_summary.sh (bash is often missing from Cursor PATH on Windows).
setlocal EnableExtensions
set "BASH=%ProgramFiles%\Git\bin\bash.exe"
if not exist "%BASH%" set "BASH=%ProgramFiles(x86)%\Git\bin\bash.exe"
if not exist "%BASH%" exit /b 0

for %%I in ("%~dp0..") do set "REPO=%%~fI"
if exist "%USERPROFILE%\.cursor\hooks\aftertone-install-dir" (
  set /p INSTALL=<"%USERPROFILE%\.cursor\hooks\aftertone-install-dir"
  if exist "%INSTALL%\py\speak_summary_prepare.py" set "REPO=%INSTALL%"
)
set "AFTERTONE_REPO=%REPO%"
set "AFTERTONE_INSTALL_DIR=%REPO%"
"%BASH%" "%~dp0speak_summary.sh"
exit /b 0
