param(
    [ValidateRange(1024, 65535)][int]$Port = 8765,
    [string]$DataRoot,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$studioRoot = Split-Path -Parent $PSScriptRoot

function Show-StudioError([string]$Message) {
    Add-Type -AssemblyName System.Windows.Forms
    [void][System.Windows.Forms.MessageBox]::Show($Message, 'Toon Studio', 'OK', 'Error')
}

try {
    $studioPython = Join-Path $studioRoot '.venv\Scripts\python.exe'
    $studioPythonw = Join-Path $studioRoot '.venv\Scripts\pythonw.exe'
    $studioLauncher = Join-Path $studioRoot 'launch.pyw'
    $studioDist = Join-Path $studioRoot 'frontend\dist\index.html'
    if (!(Test-Path -LiteralPath $studioPythonw) -or !(Test-Path -LiteralPath $studioDist)) {
        throw "Toon Studio is not installed yet.`n`nRun scripts/Install-ToonStudio.ps1 from this project folder, then try again. Installation prepares Python dependencies and the browser interface."
    }
    $studioCheck = Start-Process -FilePath $studioPython -ArgumentList '-c', '"import fastapi, uvicorn, PIL, jsonschema, multipart, pyrage"' -WindowStyle Hidden -Wait -PassThru
    if ($studioCheck.ExitCode -ne 0) {
        throw "Toon Studio dependencies are incomplete.`n`nRun scripts/Install-ToonStudio.ps1, then try again."
    }
    $studioArguments = @(('"{0}"' -f $studioLauncher), '--port', [string]$Port)
    if ($DataRoot) {
        if ($DataRoot.Contains('"')) { throw 'The data folder path cannot contain a quote character.' }
        # Windows command-line parsing requires terminal backslashes to be
        # doubled before the closing quote, including a volume-root path.
        $studioQuotedDataRoot = '"' + ($DataRoot -replace '(\\+)$', '$1$1') + '"'
        $studioArguments += @('--data-root', $studioQuotedDataRoot)
    }
    if ($NoBrowser) { $studioArguments += '--no-browser' }
    Start-Process -FilePath $studioPythonw -ArgumentList $studioArguments -WorkingDirectory $studioRoot -WindowStyle Hidden
} catch {
    Show-StudioError $_.Exception.Message
    exit 1
}
