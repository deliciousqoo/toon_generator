param(
    [switch]$CreateDesktopShortcut,
    [switch]$RebuildFrontend
)

# Run this script explicitly to install packages. Normal launch never installs.
$ErrorActionPreference = 'Stop'
$studioRoot = Split-Path -Parent $PSScriptRoot
$studioRuntime = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies'

function Invoke-StudioCommand([string]$Executable, [string[]]$Parameters) {
    & $Executable @Parameters
    if ($LASTEXITCODE -ne 0) { throw "Installation command failed (exit $LASTEXITCODE): $Executable" }
}

function Find-StudioPython {
    $studioCandidates = @()
    $studioPyCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($studioPyCommand) { $studioCandidates += @{ Executable = $studioPyCommand.Source; Prefix = @('-3') } }
    $studioBundledPython = Join-Path $studioRuntime 'python\python.exe'
    if (Test-Path -LiteralPath $studioBundledPython) { $studioCandidates += @{ Executable = $studioBundledPython; Prefix = @() } }
    foreach ($studioName in @('python', 'python3')) {
        $studioCommand = Get-Command $studioName -ErrorAction SilentlyContinue
        if ($studioCommand -and $studioCommand.Source -notmatch 'WindowsApps') {
            $studioCandidates += @{ Executable = $studioCommand.Source; Prefix = @() }
        }
    }
    foreach ($studioCandidate in $studioCandidates) {
        $studioVersionArguments = $studioCandidate.Prefix + @('-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)')
        & $studioCandidate.Executable @studioVersionArguments 2>$null
        if ($LASTEXITCODE -eq 0) { return $studioCandidate }
    }
    throw 'Python 3.12 or newer was not found. Install Python from python.org with the Python launcher enabled, then run this installer again.'
}

try {
    $studioRequirements = Join-Path $studioRoot 'requirements.txt'
    if (!(Test-Path -LiteralPath $studioRequirements)) { throw 'requirements.txt is missing. Restore the complete source package before installing.' }
    $studioBase = Find-StudioPython
    $studioVenv = Join-Path $studioRoot '.venv'
    $studioPython = Join-Path $studioVenv 'Scripts\python.exe'
    $studioPythonw = Join-Path $studioVenv 'Scripts\pythonw.exe'
    if (!(Test-Path -LiteralPath $studioPython)) {
        Write-Host 'Creating the project Python environment...'
        Invoke-StudioCommand $studioBase.Executable ($studioBase.Prefix + @('-m', 'venv', '--without-pip', $studioVenv))
    }
    Invoke-StudioCommand $studioPython @('-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)')
    $studioDependencyCheck = @'
import importlib.metadata as metadata
import pathlib, sys
for line in pathlib.Path(sys.argv[1]).read_text(encoding='utf-8').splitlines():
    line = line.split('#', 1)[0].strip()
    if not line:
        continue
    if '==' not in line:
        sys.exit(1)
    name, version = line.split('==', 1)
    try:
        if metadata.version(name.strip()) != version.strip():
            sys.exit(1)
    except metadata.PackageNotFoundError:
        sys.exit(1)
'@
    & $studioPython -c $studioDependencyCheck $studioRequirements
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Installing pinned Python dependencies...'
        $studioPipProbe = $studioBase.Prefix + @('-c', 'import importlib.util, sys; sys.exit(0 if importlib.util.find_spec(''pip'') else 1)')
        & $studioBase.Executable @studioPipProbe
        if ($LASTEXITCODE -ne 0) {
            # Standard Python distributions include ensurepip; the bundled
            # runtime already supplies pip even when ensurepip is unavailable.
            Invoke-StudioCommand $studioBase.Executable ($studioBase.Prefix + @('-m', 'ensurepip', '--upgrade'))
        }
        Invoke-StudioCommand $studioBase.Executable ($studioBase.Prefix + @('-m', 'pip', '--python', $studioPython, 'install', '-r', $studioRequirements))
    }
    Invoke-StudioCommand $studioPython @('-c', 'import fastapi, uvicorn, PIL, jsonschema, multipart, pyrage, httpx, langgraph; from langgraph.checkpoint.sqlite import SqliteSaver')
    if (!(Test-Path -LiteralPath $studioPythonw)) { throw 'The Python environment has no pythonw.exe. Use a standard Windows Python 3.12+ installation and recreate the environment.' }
    $studioFrontend = Join-Path $studioRoot 'frontend'
    if ($RebuildFrontend -or !(Test-Path -LiteralPath (Join-Path $studioFrontend 'dist\index.html'))) {
        $studioNodeCommand = Get-Command node -ErrorAction SilentlyContinue
        $studioNode = if ($studioNodeCommand) { $studioNodeCommand.Source } else { Join-Path $studioRuntime 'node\bin\node.exe' }
        $studioPnpmCommand = Get-Command pnpm -ErrorAction SilentlyContinue
        $studioPnpm = if ($studioPnpmCommand) { $studioPnpmCommand.Source } else { Join-Path $studioRuntime 'bin\fallback\pnpm.cmd' }
        if (!(Test-Path -LiteralPath $studioNode) -or !(Test-Path -LiteralPath $studioPnpm)) {
            throw 'The browser interface needs a build. Install Node.js 22.12+ and pnpm 10, or use a package that already includes frontend/dist. Then run this installer again.'
        }
        $studioOldPath = $env:PATH
        $env:PATH = (Split-Path -Parent $studioNode) + ';' + $studioOldPath
        Push-Location $studioFrontend
        try {
            Write-Host 'Installing and building the browser interface...'
            Invoke-StudioCommand $studioNode @('-e', "const [a,b]=process.versions.node.split('.').map(Number);if(a<22||(a===22&&b<12))process.exit(1)")
            Invoke-StudioCommand $studioPnpm @('install', '--frozen-lockfile', '--ignore-scripts')
            # The only dependency build needed by Vite is esbuild. No unrelated
            # dependency lifecycle scripts are enabled.
            Invoke-StudioCommand $studioPnpm @('rebuild', 'esbuild')
            Invoke-StudioCommand $studioPnpm @('run', 'build')
        } finally {
            Pop-Location
            $env:PATH = $studioOldPath
        }
    }
    $studioShell = New-Object -ComObject WScript.Shell
    $studioShortcutTargets = @((Join-Path $studioRoot 'Toon Studio.lnk'))
    if ($CreateDesktopShortcut) {
        $studioShortcutTargets += Join-Path ([Environment]::GetFolderPath('Desktop')) 'Toon Studio.lnk'
    }
    foreach ($studioShortcutPath in $studioShortcutTargets) {
        # Keep an existing shortcut instead of silently replacing user settings.
        if (Test-Path -LiteralPath $studioShortcutPath) { continue }
        $studioShortcut = $studioShell.CreateShortcut($studioShortcutPath)
        $studioShortcut.TargetPath = $studioPythonw
        $studioShortcut.Arguments = '"' + (Join-Path $studioRoot 'launch.pyw') + '"'
        $studioShortcut.WorkingDirectory = $studioRoot
        $studioShortcut.Description = 'Toon Studio - local synthetic pipeline'
        $studioShortcut.WindowStyle = 7
        $studioShortcut.Save()
    }
    Write-Host 'Toon Studio is installed. Open Toon Studio.lnk or Start-ToonStudio.cmd. The app listens on http://127.0.0.1:8765 only.'
} catch {
    Write-Error $_.Exception.Message
    exit 1
}
