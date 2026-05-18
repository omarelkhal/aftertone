# One-shot dev setup: Python venv (uv), Hugging Face assets if missing.
# Usage (from repo root):
#   powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
# Options (env):
#   $env:SKIP_WEB = "1"       — skip npm in web/
#   $env:SKIP_ASSETS = "1"    — skip model download
#   $env:FORCE_ASSETS = "1"   — re-download assets

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Py = Join-Path $Root "py"
$Web = Join-Path $Root "web"

Write-Host "==> bootstrap: repo root $Root"

function Ensure-Uv {
    if (Get-Command uv -ErrorAction SilentlyContinue) { return }
    $local = Join-Path $env:USERPROFILE ".local\bin"
    if (Test-Path (Join-Path $local "uv.exe")) {
        $env:Path = "$local;$env:Path"
    }
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Error "bootstrap: 'uv' not found. Install: https://docs.astral.sh/uv/getting-started/installation/ or re-run install.ps1 -InstallUv"
    }
}

Ensure-Uv

$pyVersionFile = Join-Path $Py ".python-version"
$pythonArg = @()
if (Test-Path $pyVersionFile) {
    $ver = (Get-Content $pyVersionFile -Raw).Trim()
    if ($ver) {
        Write-Host "==> bootstrap: ensuring Python $ver (onnxruntime wheels)…"
        Push-Location $Py
        uv python install $ver | Out-Host
        $pythonArg = @("--python", $ver)
        Pop-Location
    }
}

Write-Host "==> bootstrap: uv sync (Python deps + venv under py/)"
Push-Location $Py
if ($pythonArg.Count -gt 0) { uv sync @pythonArg } else { uv sync }
Pop-Location

if ($env:SKIP_ASSETS -ne "1") {
    $ttsJson = Join-Path $Root "assets\onnx\tts.json"
    if ((-not (Test-Path $ttsJson)) -or ($env:FORCE_ASSETS -eq "1")) {
        Write-Host "==> bootstrap: fetching ONNX assets from Hugging Face (Supertone/supertonic-3)…"
        Push-Location $Py
        if ($pythonArg.Count -gt 0) {
            uv run @pythonArg --with huggingface_hub python fetch_assets.py
        } else {
            uv run --with huggingface_hub python fetch_assets.py
        }
        Pop-Location
    } else {
        Write-Host "==> bootstrap: assets/onnx/tts.json present; skip download (set FORCE_ASSETS=1 to re-fetch)"
    }
} else {
    Write-Host "==> bootstrap: SKIP_ASSETS=1 - not downloading models"
}

if ($env:SKIP_WEB -ne "1" -and (Test-Path (Join-Path $Web "package.json"))) {
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Write-Host "==> bootstrap: npm install (web/)"
        Push-Location $Web
        npm install
        Pop-Location
    } else {
        Write-Warning "bootstrap: npm not found; skipping web/ (install Node.js or set SKIP_WEB=1)"
    }
} elseif ($env:SKIP_WEB -eq "1") {
    Write-Host "==> bootstrap: SKIP_WEB=1 - skipping npm in web/"
} else {
    Write-Host "==> bootstrap: no web/package.json - skipping web"
}

function Install-WindowsProjectHooks {
    $hooksWin = Join-Path $Root ".cursor\hooks.windows.json"
    $hooksDst = Join-Path $Root ".cursor\hooks.json"
    if (-not (Test-Path $hooksWin)) { return }
    Copy-Item -Path $hooksWin -Destination $hooksDst -Force
    Write-Host "==> bootstrap: Windows project hooks -> .cursor/hooks.json (.cmd wrappers; bash is not on Cursor PATH)"
}

Install-WindowsProjectHooks

Write-Host "==> bootstrap: done."
Write-Host "    Python: cd py; uv run python example_onnx.py"
Write-Host '    TTS hook smoke (Git Bash): bash py/test_speak_summary_pipeline.sh'
