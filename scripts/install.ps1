# ─── local-commit Windows installer ──────────────────────────────────────
# Usage (run in PowerShell as admin, or just user-scope):
#   irm https://git.io/local-commit-ps1 | iex
#
# Or download & run:
#   curl -fsSLo install.ps1 https://git.io/local-commit-ps1
#   powershell -ExecutionPolicy Bypass -File install.ps1
#
# Detects best install method:
#   1. pip install  (if Python 3.9+ available)
#   2. Pre-built .exe from GitHub Releases
#   3. Docker Desktop (if installed)
# ────────────────────────────────────────────────────────────────────────────

$Repo = "your-org/local-commit"
$Version = "0.1.0"

function Write-Info  { Write-Host "  i  $args" -ForegroundColor Cyan }
function Write-Ok    { Write-Host "  +  $args" -ForegroundColor Green }
function Write-Warn  { Write-Host "  !  $args" -ForegroundColor Yellow }
function Write-Err   { Write-Host "  x  $args" -ForegroundColor Red }

Write-Host ""
Write-Host "  local-commit installer"
Write-Host ""

# ── Method 1: pip ────────────────────────────────────────────────────────

$Python = $null

# Try python launcher first, then python
foreach ($cmd in @("py -3", "python")) {
    try {
        $ver = & cmd /c "($cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')") 2>nul"
        if ($ver -match "(\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor  = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 9) {
                $Python = $cmd
                break
            }
        }
    } catch {}
}

if ($Python) {
    Write-Info "Detected Python $(& cmd /c "$Python --version 2>nul")"

    try {
        & cmd /c "$Python -m pip --version" 2>$null | Out-Null
        Write-Info "Installing via pip…"

        # Try PyPI, then GitHub source
        $result = & cmd /c "$Python -m pip install local-commit 2>nul"
        if ($LASTEXITCODE -ne 0) {
            Write-Warn "Not on PyPI — installing from source"
            $tmp = [System.IO.Path]::GetTempPath()
            $zip = Join-Path $tmp "local-commit.zip"
            $extracted = Join-Path $tmp "local-commit-src"

            Remove-Item -Recurse -Force $extracted -ErrorAction SilentlyContinue
            Invoke-WebRequest -Uri "https://github.com/$Repo/archive/refs/tags/v$Version.zip" -OutFile $zip
            Expand-Archive -Path $zip -DestinationPath $tmp -Force
            $folder = (Get-ChildItem "$tmp\local-commit-*" -Directory)[0].FullName

            & cmd /c "$Python -m pip install -e `"$folder`""
        }

        Write-Ok "local-commit installed!"
        Write-Host ""
        Write-Host "  Next:"
        Write-Host "    local-commit --setup"
        Write-Host "    cd my-project && local-commit"
        Write-Host ""
        return
    } catch {
        Write-Warn "pip install failed — trying binary download"
    }
}

# ── Method 2: Pre-built .exe ─────────────────────────────────────────────

try {
    $Arch = if ([Environment]::Is64BitOperatingSystem) { "x86_64" } else { "x86" }
    $Binary = "local-commit_windows_$Arch.exe"
    $Url = "https://github.com/$Repo/releases/download/v$Version/$Binary"
    $Dest = "$env:LOCALAPPDATA\Programs\local-commit"

    Write-Info "Downloading pre-built binary: $Binary"

    New-Item -ItemType Directory -Path $Dest -Force | Out-Null
    Invoke-WebRequest -Uri $Url -OutFile "$Dest\local-commit.exe"

    # Add to PATH (user scope)
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($currentPath -notlike "*$Dest*") {
        [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$Dest", "User")
        $env:PATH += ";$Dest"
    }

    Write-Ok "Installed to $Dest\local-commit.exe (added to user PATH)"
    Write-Host ""
    Write-Host "  Next:"
    Write-Host "    local-commit --setup     (one-time model download)"
    Write-Host "    local-commit"
    Write-Host ""
    return
} catch {
    Write-Warn "Binary download failed — trying Docker"
}

# ── Method 3: Docker ─────────────────────────────────────────────────────

try {
    docker --version | Out-Null
    Write-Info "Docker Desktop detected — pulling image…"
    docker pull "ghcr.io/$Repo`:latest"
    Write-Ok "Docker image ready!"
    Write-Host ""
    Write-Host '  alias lc="docker run --rm -v local-commit-model:/root/.local-commit'
    Write-Host '    -v \"`$(pwd):/repo\" -w /repo local-commit"'
    Write-Host "    lc --setup"
    Write-Host "    lc"
    Write-Host ""
    return
} catch {
    Write-Err "No install method worked."
    Write-Host ""
    Write-Host "  Please install manually:"
    Write-Host "    1. Install Python 3.9+ from https://python.org"
    Write-Host "    2. Run: pip install local-commit"
    Write-Host "    3. Run: local-commit --setup"
    exit 1
}
