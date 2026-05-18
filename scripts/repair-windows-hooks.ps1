# Repair Aftertone on Windows: global hooks only (no project hooks.json), daemon, TTS on.
# Run from any folder:
#   powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\aftertone\scripts\repair-windows-hooks.ps1"
# Or after clone:
#   powershell -ExecutionPolicy Bypass -File scripts\repair-windows-hooks.ps1

$ErrorActionPreference = "Stop"
$env:Path = "$env:USERPROFILE\.local\bin;C:\Program Files\Git\cmd;C:\Program Files\Git\bin;$env:Path"

$Install = if ($env:AFTERTONE_INSTALL_DIR) { $env:AFTERTONE_INSTALL_DIR } else { Join-Path $env:USERPROFILE "aftertone" }
if (-not (Test-Path (Join-Path $Install "py\speak_summary_prepare.py"))) {
    Write-Error "Aftertone not found at $Install. Run: irm https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/install.ps1 | iex"
}

# Remove project-level hooks that override / clash with global hooks
$here = (Get-Location).Path
$projHook = Join-Path $here ".cursor\hooks.json"
if (Test-Path $projHook) {
    Remove-Item $projHook -Force
    Write-Host "Removed project hooks.json at $projHook (use global hooks only)"
}

Write-Host "==> repair: global Cursor hooks..."
Push-Location (Join-Path $Install "py")
& uv run python install_global_hooks.py --install-dir $Install
Pop-Location

Write-Host "==> repair: enable TTS + spoken-summary rule..."
Push-Location (Join-Path $Install "py")
& uv run python speak_summary_toggle.py on
& uv run python sync_spoken_rule_lang.py
# Tag-only mode skips speech when Cursor hook JSON has no <spoken_summary> (common on Windows).
& uv run python -c @"
from pathlib import Path
p = Path(r'$Install') / '.cursor' / 'hooks' / 'speak_summary.toml'
text = p.read_text(encoding='utf-8')
if 'only_speak_spoken_summary = true' in text:
    p.write_text(text.replace('only_speak_spoken_summary = true', 'only_speak_spoken_summary = false'), encoding='utf-8')
    print('set only_speak_spoken_summary = false (heuristic fallback when tag missing in hook payload)')
"@
Pop-Location
$wrapper = Join-Path $env:USERPROFILE ".cursor\hooks\aftertone-speak_summary.cmd"
$wrapperSrc = Join-Path $Install "scripts\cursor-global\aftertone-speak_summary.cmd"
if (Test-Path $wrapperSrc) { Copy-Item $wrapperSrc $wrapper -Force }
$hooksJsonPath = Join-Path $env:USERPROFILE ".cursor\hooks.json"
$hooksObj = @{
    version = 1
    hooks = @{
        afterAgentResponse = @(
            @{
                command = "cmd /c `"$wrapper`""
                timeout = 60
            }
        )
    }
}
$hooksObj | ConvertTo-Json -Depth 6 | Set-Content $hooksJsonPath -Encoding UTF8
$ruleSrc = Join-Path $Install ".cursor\rules\spoken-summary.mdc"
if (Test-Path $ruleSrc) {
    $rulesDir = Join-Path $env:USERPROFILE ".cursor\rules"
    New-Item -ItemType Directory -Path $rulesDir -Force | Out-Null
    Copy-Item $ruleSrc (Join-Path $rulesDir "spoken-summary.mdc") -Force
}

Write-Host "==> repair: start daemon..."
Push-Location (Join-Path $Install "py")
& uv run python tts_daemon_ctl.py start --repo-root ..
Pop-Location

$hooksJson = Join-Path $env:USERPROFILE ".cursor\hooks.json"
Write-Host ""
Write-Host "Done. Global hooks: $hooksJson"
Write-Host "After one Agent reply, check:"
Write-Host "  $env:USERPROFILE\.cursor\hooks\state\cursor-hook-fired.log  (Cursor ran the wrapper)"
Write-Host "  $Install\.cursor\hooks\state\speak_summary-hook.log       (prepare_ok / post_say_done)"
Write-Host "Reload Cursor. Settings -> Hooks ON. Trust workspace."
