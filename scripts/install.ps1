# One-line install (Windows): clone/update Aftertone, bootstrap, optional daemon start.
#
#   irm https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/install.ps1 | iex
#   # or with options:
#   & ([scriptblock]::Create((irm https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/install.ps1))) -InstallUv -StartDaemon
#
# Options:
#   -InstallDir PATH     Clone location (default: $env:USERPROFILE\aftertone)
#   -Branch NAME         Git branch (default: main)
#   -NoGlobal            Skip user-level Cursor hooks
#   -SkipAssets          Skip Hugging Face model download
#   -NoStartDaemon       Do not start tts_daemon after bootstrap
#   -NoEnableTts         Leave speak_summary.toml enabled=false
#   -Help

param(
    [string] $InstallDir = $(if ($env:AFTERTONE_INSTALL_DIR) { $env:AFTERTONE_INSTALL_DIR } else { Join-Path $env:USERPROFILE "aftertone" }),
    [string] $Branch = $(if ($env:AFTERTONE_BRANCH) { $env:AFTERTONE_BRANCH } else { "main" }),
    [switch] $NoGlobal,
    [switch] $SkipAssets,
    [switch] $NoStartDaemon,
    [switch] $NoEnableTts,
    [switch] $Help
)

$ErrorActionPreference = "Stop"

$RepoUrl = if ($env:AFTERTONE_REPO_URL) { $env:AFTERTONE_REPO_URL } else { "https://github.com/omarelkhal/aftertone.git" }

function Show-Help {
    @"
Aftertone installer (Windows) — clone to %USERPROFILE%\aftertone, uv, models, hooks, daemon, enable TTS.

One-liner (does everything; only needs git + Git Bash):
  irm https://raw.githubusercontent.com/omarelkhal/aftertone/main/scripts/install.ps1 | iex

Requires: git, Git for Windows (bash for Cursor hooks). uv and Python 3.13 are installed automatically.

Environment:
  AFTERTONE_INSTALL_DIR   Same as -InstallDir
  AFTERTONE_REPO_URL      Override git remote
  AFTERTONE_BRANCH        Same as -Branch
"@
}

if ($Help) { Show-Help; exit 0 }

function Ensure-Git {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Error "install: git is required. Install Git for Windows: https://git-scm.com/download/win"
    }
    $bash = @(
        "${env:ProgramFiles}\Git\bin\bash.exe",
        "${env:ProgramFiles(x86)}\Git\bin\bash.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $bash) {
        Write-Error "install: Git Bash not found (needed for Cursor hooks). Reinstall Git for Windows."
    }
}

function Ensure-Uv {
    $localBin = Join-Path $env:USERPROFILE ".local\bin"
    if (Test-Path $localBin) { $env:Path = "$localBin;$env:Path" }
    if (Get-Command uv -ErrorAction SilentlyContinue) { return }
    Write-Host "==> install: uv not found; running Astral installer…"
    irm https://astral.sh/uv/install.ps1 | iex
    $env:Path = "$localBin;$env:Path"
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Error "install: uv install failed. Install manually: https://docs.astral.sh/uv/"
    }
}

function Clone-OrUpdate {
    $dir = $InstallDir
    $gitEa = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    if (Test-Path (Join-Path $dir ".git")) {
        Write-Host "==> install: updating $dir ($Branch)…"
        git -C $dir fetch origin $Branch --depth 1 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { git -C $dir fetch origin $Branch 2>&1 | Out-Null }
        git -C $dir checkout $Branch 2>&1 | Out-Null
        git -C $dir pull --ff-only origin $Branch 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "==> install: local changes or diverged history; resetting to origin/$Branch…"
            git -C $dir fetch origin $Branch 2>&1 | Out-Null
            git -C $dir reset --hard "origin/$Branch" 2>&1 | Out-Null
            git -C $dir clean -fd 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) {
                $ErrorActionPreference = $gitEa
                Write-Error "install: could not reset $dir to origin/$Branch"
            }
        }
        $ErrorActionPreference = $gitEa
    } else {
        if (Test-Path $dir) {
            Write-Host "==> install: removing incomplete folder at $dir…"
            Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue
            if (Test-Path $dir) {
                $ErrorActionPreference = $gitEa
                Write-Error "install: could not remove $dir (close Cursor/terminals using it), then re-run."
            }
        }
        Write-Host "==> install: cloning $RepoUrl → $dir ($Branch)…"
        $parent = Split-Path $dir -Parent
        if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
        git clone --depth 1 --branch $Branch $RepoUrl $dir 2>&1 | Out-Null
        $ErrorActionPreference = $gitEa
        if ($LASTEXITCODE -ne 0) {
            Write-Error "install: git clone failed"
        }
    }
    return (Resolve-Path $dir).Path
}

function Invoke-Bootstrap {
    param([string] $Root)
    Write-Host "==> install: bootstrap (uv sync + assets)…"
    $env:SKIP_WEB = "1"
    if ($SkipAssets) { $env:SKIP_ASSETS = "1" }
    & (Join-Path $Root "scripts\bootstrap.ps1")
}

function Install-GlobalHooks {
    param([string] $Root)
    Write-Host "==> install: user-level Cursor hooks ($env:USERPROFILE\.cursor)…"
    Push-Location (Join-Path $Root "py")
    $pyArgs = Get-PythonVersionArg -Root $Root
    & uv run @pyArgs python install_global_hooks.py --install-dir $Root
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "install: global hooks registration failed"
    }
    Pop-Location
}

function Get-PythonVersionArg {
    param([string] $Root)
    $pvFile = Join-Path $Root "py\.python-version"
    if (Test-Path $pvFile) {
        $ver = (Get-Content $pvFile -Raw).Trim()
        if ($ver) { return @("--python", $ver) }
    }
    return @()
}

function Enable-SpokenTts {
    param([string] $Root)
    Write-Host "==> install: enabling spoken TTS in speak_summary.toml…"
    Push-Location (Join-Path $Root "py")
    $pyArgs = Get-PythonVersionArg -Root $Root
    & uv run @pyArgs python speak_summary_toggle.py on
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "install: could not set enabled=true (use /aftertone-on in Cursor)"
    }
    Pop-Location
}

function Start-TtsDaemon {
    param([string] $Root)
    Write-Host "==> install: starting tts_daemon (may take 1-2 min while models load)…"
    Push-Location (Join-Path $Root "py")
    $pyArgs = Get-PythonVersionArg -Root $Root
    $logPath = Join-Path $Root ".cursor\hooks\state\tts-daemon.log"
    & uv run @pyArgs python tts_daemon_ctl.py start --repo-root ..
    if ($LASTEXITCODE -ne 0) {
        if ((Test-Path $logPath) -and (Select-String -Path $logPath -Pattern "listening http://" -Quiet)) {
            Write-Host "==> install: tts_daemon is listening (log OK; health check was slow)"
        } else {
            Write-Warning "install: daemon start uncertain; see $logPath"
        }
    }
    Pop-Location
}

function Show-NextSteps {
    param([string] $Root)
    $cursorHooks = Join-Path $env:USERPROFILE ".cursor\hooks.json"
    @"

==> Aftertone is ready at: $Root

Installed: Python deps, ONNX assets, user Cursor hooks, tts_daemon, spoken TTS enabled in config.
Hooks file: $cursorHooks

In Cursor only:
  1. Settings -> enable Hooks
  2. Trust the workspace(s) where you want spoken summaries
  3. Optional: open $Root and use /aftertone-status to verify

Docs: $Root\README.md
"@
}

Ensure-Git
$InstallDir = Clone-OrUpdate
Ensure-Uv
Invoke-Bootstrap -Root $InstallDir

if (-not $NoGlobal) {
    Install-GlobalHooks -Root $InstallDir
}

if (-not $NoEnableTts) {
    Enable-SpokenTts -Root $InstallDir
}

if (-not $NoStartDaemon) {
    Start-TtsDaemon -Root $InstallDir
}

Show-NextSteps -Root $InstallDir
exit 0
