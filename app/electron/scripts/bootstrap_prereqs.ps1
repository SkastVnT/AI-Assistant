<#
bootstrap_prereqs.ps1 - auto-install Python 3.11, Node 20, Git for AI-Assistant LITE.

Strategy
--------
1. Detect each tool. If a working version is found, record its path and skip.
2. If missing, try winget (Windows 10 1809+ ships it; Win11 has it by default).
   winget handles UAC itself; we use --scope user to avoid admin where possible.
3. If winget is unavailable, fall back to direct download + silent per-user install.
4. Write the discovered Python path to <payload>\.python_path so installer-lite.nsh
   can chain setup_lite.py without re-detecting.

Logs to <payload>\logs\bootstrap.log.

Exit codes:
  0 = success (Python at minimum is available)
  1 = Python could not be installed (fatal - chatbot needs it)
  2 = bad arguments
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string] $PayloadRoot
)

$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

if (-not (Test-Path $PayloadRoot)) {
    Write-Host "PayloadRoot does not exist: $PayloadRoot"
    exit 2
}

$logDir = Join-Path $PayloadRoot 'logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logPath = Join-Path $logDir 'bootstrap.log'

function Log([string]$msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format HH:mm:ss), $msg
    Write-Host $line
    Add-Content -Path $logPath -Value $line -Encoding UTF8
}

Log ("=" * 70)
Log "bootstrap_prereqs.ps1 starting"
Log "PayloadRoot: $PayloadRoot"
Log "PSVersion  : $($PSVersionTable.PSVersion)"

# ---------- shared helpers ----------------------------------------------------

function Test-Cmd([string]$name) {
    $c = Get-Command $name -ErrorAction SilentlyContinue
    if ($c) { return $c.Source } else { return $null }
}

function Has-Winget() {
    return [bool](Test-Cmd 'winget')
}

function Download-File([string]$url, [string]$out) {
    Log "downloading $url"
    try {
        # Use TLS 1.2 - older Windows defaults can fail on PyPI / python.org.
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing
        return $true
    } catch {
        Log "download failed: $_"
        return $false
    }
}

# ---------- Python 3.11 -------------------------------------------------------

function Find-Python311() {
    # Prefer py launcher if present (handles multiple installs cleanly).
    $py = Test-Cmd 'py'
    if ($py) {
        $out = & $py -3.11 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) {
            $exe = $out.Trim()
            if (Test-Path $exe) {
                Log "found Python 3.11 via py launcher: $exe"
                return $exe
            }
        }
    }
    # Search common locations.
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:ProgramFiles\Python311\python.exe",
        "${env:ProgramFiles(x86)}\Python311\python.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) {
            $ver = & $c -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
            if ($ver -eq '3.11') {
                Log "found Python 3.11: $c"
                return $c
            }
        }
    }
    return $null
}

function Install-Python311() {
    Log "installing Python 3.11..."
    if (Has-Winget) {
        Log "trying winget (per-user scope)..."
        # --scope user installs to %LOCALAPPDATA%\Programs\Python - no admin.
        & winget install --id Python.Python.3.11 --scope user --silent `
            --accept-package-agreements --accept-source-agreements `
            --disable-interactivity 2>&1 | ForEach-Object { Log "[winget] $_" }
        if ($LASTEXITCODE -eq 0) {
            $p = Find-Python311
            if ($p) { return $p }
        }
        Log "winget install did not yield a usable Python - falling back to direct download"
    }
    # Direct download from python.org. 3.11.9 is the last 3.11 with a Windows installer.
    $url = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'
    $tmp = Join-Path $env:TEMP "python-3.11.9-amd64.exe"
    if (-not (Download-File $url $tmp)) { return $null }
    Log "running silent per-user install..."
    # InstallAllUsers=0 + DefaultJustForMeTargetDir keeps install in %LOCALAPPDATA%
    # -> no UAC. PrependPath=1 puts python on PATH. Include_launcher=1 enables py.exe.
    $args = @(
        '/quiet',
        'InstallAllUsers=0',
        'PrependPath=1',
        'Include_launcher=1',
        'Include_test=0',
        'Include_doc=0',
        'SimpleInstall=1',
        "TargetDir=$env:LOCALAPPDATA\Programs\Python\Python311"
    )
    $p = Start-Process -FilePath $tmp -ArgumentList $args -Wait -PassThru
    Log "python installer exit code: $($p.ExitCode)"
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    # Refresh PATH for current process.
    $env:Path = [Environment]::GetEnvironmentVariable('Path','User') + ';' + [Environment]::GetEnvironmentVariable('Path','Machine')
    return Find-Python311
}

# ---------- Node 20 -----------------------------------------------------------

function Find-Node() {
    $n = Test-Cmd 'node'
    if ($n) {
        $v = & $n --version 2>$null
        if ($v -match '^v(\d+)\.') {
            $major = [int]$Matches[1]
            if ($major -ge 18) {
                Log "found Node $v at $n"
                return $n
            }
        }
    }
    return $null
}

function Install-Node() {
    Log "installing Node.js LTS..."
    if (Has-Winget) {
        & winget install --id OpenJS.NodeJS.LTS --scope user --silent `
            --accept-package-agreements --accept-source-agreements `
            --disable-interactivity 2>&1 | ForEach-Object { Log "[winget] $_" }
        $env:Path = [Environment]::GetEnvironmentVariable('Path','User') + ';' + [Environment]::GetEnvironmentVariable('Path','Machine')
        $n = Find-Node
        if ($n) { return $n }
        Log "winget node install failed - falling back to MSI"
    }
    # Direct MSI from nodejs.org (LTS 20.x). msiexec /qn ALLUSERS="" -> per-user.
    $url = 'https://nodejs.org/dist/v20.18.1/node-v20.18.1-x64.msi'
    $tmp = Join-Path $env:TEMP 'node-v20.18.1-x64.msi'
    if (-not (Download-File $url $tmp)) { return $null }
    $log = Join-Path $logDir 'node-msi.log'
    $p = Start-Process -FilePath msiexec.exe -ArgumentList @(
        '/i', "`"$tmp`"", '/qn', 'ALLUSERS=""', "/L*v `"$log`""
    ) -Wait -PassThru
    Log "node msi exit code: $($p.ExitCode)"
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    $env:Path = [Environment]::GetEnvironmentVariable('Path','User') + ';' + [Environment]::GetEnvironmentVariable('Path','Machine')
    return Find-Node
}

# ---------- Git ---------------------------------------------------------------

function Find-Git() {
    $g = Test-Cmd 'git'
    if ($g) { Log "found git at $g"; return $g }
    return $null
}

function Install-Git() {
    Log "installing Git..."
    if (Has-Winget) {
        & winget install --id Git.Git --scope user --silent `
            --accept-package-agreements --accept-source-agreements `
            --disable-interactivity 2>&1 | ForEach-Object { Log "[winget] $_" }
        $env:Path = [Environment]::GetEnvironmentVariable('Path','User') + ';' + [Environment]::GetEnvironmentVariable('Path','Machine')
        $g = Find-Git
        if ($g) { return $g }
    }
    # PortableGit fallback: zero-touch, no admin, no installer at all.
    $url = 'https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/PortableGit-2.45.2-64-bit.7z.exe'
    $tmp = Join-Path $env:TEMP 'PortableGit.7z.exe'
    if (-not (Download-File $url $tmp)) { return $null }
    $dst = Join-Path $env:LOCALAPPDATA 'Programs\PortableGit'
    New-Item -ItemType Directory -Path $dst -Force | Out-Null
    Log "extracting PortableGit to $dst"
    $p = Start-Process -FilePath $tmp -ArgumentList @('-o', "`"$dst`"", '-y') -Wait -PassThru
    Log "PortableGit extractor exit: $($p.ExitCode)"
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    $exe = Join-Path $dst 'cmd\git.exe'
    if (Test-Path $exe) {
        # Add to user PATH for next session (best-effort).
        $userPath = [Environment]::GetEnvironmentVariable('Path','User')
        if ($userPath -notlike "*$dst\cmd*") {
            [Environment]::SetEnvironmentVariable('Path', "$userPath;$dst\cmd", 'User')
        }
        Log "git available at $exe"
        return $exe
    }
    return $null
}

# ---------- main flow ---------------------------------------------------------

$pythonPath = Find-Python311
if (-not $pythonPath) {
    $pythonPath = Install-Python311
}
if (-not $pythonPath) {
    Log "FATAL: could not obtain Python 3.11 - chatbot will not start"
    exit 1
}
Log "Python ready: $pythonPath"
# Persist for installer-lite.nsh + setup_lite.py.
Set-Content -Path (Join-Path $PayloadRoot '.python_path') -Value $pythonPath -Encoding ASCII

$nodePath = Find-Node
if (-not $nodePath) { $nodePath = Install-Node }
if ($nodePath) { Log "Node ready: $nodePath" } else { Log "WARN: Node not available (chatbot still works without it)" }

$gitPath = Find-Git
if (-not $gitPath) { $gitPath = Install-Git }
if ($gitPath) { Log "Git ready: $gitPath" } else { Log "WARN: Git not available (only needed for self-update via git pull)" }

# ---------- chain into setup_lite.py ------------------------------------------
Log "chaining into setup_lite.py (online pip install) ..."
$setupScript = Join-Path $PayloadRoot 'scripts\setup_lite.py'
if (-not (Test-Path $setupScript)) {
    Log "FATAL: setup_lite.py missing at $setupScript"
    exit 1
}
& $pythonPath $setupScript $PayloadRoot
$rc = $LASTEXITCODE
Log "setup_lite.py exit code: $rc"
exit $rc
