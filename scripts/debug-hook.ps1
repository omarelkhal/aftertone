# Replay a hook JSON file through speak_summary.sh (same path Cursor uses).
# Usage:
#   powershell -File scripts\debug-hook.ps1
#   powershell -File scripts\debug-hook.ps1 -HookJson path\to\hook.json

param(
    [string] $HookJson = "",
    [string] $InstallDir = $(Join-Path $env:USERPROFILE "aftertone")
)

$ErrorActionPreference = "Stop"
$bash = "${env:ProgramFiles}\Git\bin\bash.exe"
if (-not (Test-Path $bash)) { throw "Git Bash required" }

if (-not (Test-Path (Join-Path $InstallDir "py\speak_summary_prepare.py"))) {
    $InstallDir = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
}

if (-not $HookJson) {
    $HookJson = Join-Path $InstallDir ".cursor\hooks\state\_debug_hook_full.json"
    if (-not (Test-Path $HookJson)) {
        throw "Provide -HookJson or save Cursor hook payload to $HookJson"
    }
}

$log = Join-Path $InstallDir ".cursor\hooks\state\speak_summary-hook.log"
Write-Host "==> piping $HookJson through speak_summary.sh"
Write-Host "    log: $log"
$repoUnix = ($InstallDir -replace '\\', '/').Replace('C:', '/c').Replace('c:', '/c')
Get-Content $HookJson -Raw | & $bash -lc "export AFTERTONE_REPO=$repoUnix AFTERTONE_INSTALL_DIR=$repoUnix; `"$repoUnix/.cursor/hooks/speak_summary.sh`""
Write-Host ""
Write-Host "==> last log lines:"
if (Test-Path $log) { Get-Content $log -Tail 8 }
