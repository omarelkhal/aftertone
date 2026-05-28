@echo off
setlocal

set "INSTALL_FILE=%USERPROFILE%\.cursor\hooks\aftertone-install-dir"
if exist "%INSTALL_FILE%" (
  set /p AFTERTONE_INSTALL_DIR=<"%INSTALL_FILE%"
) else if not "%AFTERTONE_INSTALL_DIR%"=="" (
  rem keep existing AFTERTONE_INSTALL_DIR
) else if not "%AFTERTONE_REPO%"=="" (
  set "AFTERTONE_INSTALL_DIR=%AFTERTONE_REPO%"
) else (
  set "AFTERTONE_INSTALL_DIR=%USERPROFILE%\aftertone"
)

cd /d "%AFTERTONE_INSTALL_DIR%\py"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m aftertone.hook_run --stdin
) else (
  uv run python -m aftertone.hook_run --stdin
)
