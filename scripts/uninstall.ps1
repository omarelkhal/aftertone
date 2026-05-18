# Remove Aftertone install + global Cursor integration (Windows).
#
#   powershell -ExecutionPolicy Bypass -File scripts\uninstall.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\uninstall.ps1 -InstallDir D:\aftertone
#
# Does NOT remove a dev clone (e.g. Desktop\aftertone) unless -InstallDir points there.

param(
    [string] $InstallDir = $(if ($env:AFTERTONE_INSTALL_DIR) { $env:AFTERTONE_INSTALL_DIR } else { Join-Path $env:USERPROFILE "aftertone" }),
    [switch] $Help
)

$ErrorActionPreference = "Stop"

function Show-Help {
    @"
Aftertone uninstall (Windows)

Removes:
  - Install directory (default: %USERPROFILE%\aftertone)
  - User-level Cursor hook, commands, and spoken-summary rule
  - Stops tts_daemon on the configured port

Does not remove: uv, Git, or your dev git clone unless -InstallDir targets it.

  powershell -ExecutionPolicy Bypass -File scripts\uninstall.ps1
"@
}

if ($Help) { Show-Help; exit 0 }

$InstallDir = [System.IO.Path]::GetFullPath($InstallDir)
$Cursor = Join-Path $env:USERPROFILE ".cursor"
$HooksJson = Join-Path $Cursor "hooks.json"

Write-Host "==> uninstall: stop TTS daemon..."
$env:Path = "$(Join-Path $env:USERPROFILE '.local\bin');$env:Path"
if (Test-Path (Join-Path $InstallDir "py\tts_daemon_ctl.py")) {
    Push-Location (Join-Path $InstallDir "py")
    try {
        if (Get-Command uv -ErrorAction SilentlyContinue) {
            uv run python tts_daemon_ctl.py stop --repo-root ".." 2>&1 | Out-Null
        }
    } catch { }
    Pop-Location
}
try {
    $conn = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($conn) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        Write-Host "    stopped process on port 8765 (pid $($conn.OwningProcess))"
    }
} catch { }

Write-Host "==> uninstall: remove Aftertone from $HooksJson..."
if (Test-Path $HooksJson) {
    $py = @"
import json
from pathlib import Path

p = Path(r"$HooksJson")
data = json.loads(p.read_text(encoding="utf-8-sig"))
hooks = data.get("hooks") or {}
out = {}
for event, entries in hooks.items():
    if not isinstance(entries, list):
        out[event] = entries
        continue
    kept = [
        e for e in entries
        if isinstance(e, dict) and "aftertone-speak_summary" not in (e.get("command") or "")
    ]
    if kept:
        out[event] = kept
data["hooks"] = out
p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print("hooks.json updated")
"@
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        $py | uv run python -
    } else {
        $py | python -
    }
}

Write-Host "==> uninstall: remove global Cursor Aftertone files..."
$hookFiles = @(
    "aftertone-speak_summary.cmd",
    "aftertone-speak_summary.sh",
    "aftertone-root.sh",
    "aftertone-install-dir"
)
foreach ($f in $hookFiles) {
    $path = Join-Path $Cursor "hooks\$f"
    if (Test-Path $path) { Remove-Item $path -Force; Write-Host "    removed $path" }
}
$stateLog = Join-Path $Cursor "hooks\state\cursor-hook-fired.log"
if (Test-Path $stateLog) { Remove-Item $stateLog -Force }

Get-ChildItem (Join-Path $Cursor "commands") -Filter "aftertone-*.md" -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item $_.FullName -Force
    Write-Host "    removed $($_.FullName)"
}
$rule = Join-Path $Cursor "rules\spoken-summary.mdc"
if (Test-Path $rule) { Remove-Item $rule -Force; Write-Host "    removed $rule" }

Write-Host "==> uninstall: remove install directory $InstallDir ..."
if (Test-Path $InstallDir) {
  $retries = 3
  for ($i = 1; $i -le $retries; $i++) {
    try {
      Remove-Item -LiteralPath $InstallDir -Recurse -Force -ErrorAction Stop
      Write-Host "    removed $InstallDir"
      break
    } catch {
      if ($i -eq $retries) { throw }
      Write-Host "    retry $i/$retries (close Cursor terminals using the folder)..."
      Start-Sleep 2
    }
  }
} else {
  Write-Host "    (not present)"
}

Write-Host ""
Write-Host "Done. Aftertone uninstalled."
Write-Host "Reload Cursor. Reinstall when ready:"
Write-Host "  irm https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/install.ps1 | iex"
