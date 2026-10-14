param(
    [ValidateRange(1024, 65535)][int]$Port = 8765,
    [switch]$NoDialog
)

$ErrorActionPreference = 'Stop'
$studioUrl = "http://127.0.0.1:$Port"
# This helper contacts loopback only; do not involve system proxy discovery.
[System.Net.WebRequest]::DefaultWebProxy = $null

function Test-StudioDisconnected($ErrorRecord) {
    $studioConnectionError = $ErrorRecord.Exception
    while ($studioConnectionError) {
        if ($studioConnectionError -is [System.Net.WebException] -and
            $studioConnectionError.Response -eq $null -and
            $studioConnectionError.Status -eq [System.Net.WebExceptionStatus]::ConnectFailure) {
            return $true
        }
        if ($studioConnectionError -is [System.Net.Sockets.SocketException] -and
            $studioConnectionError.SocketErrorCode -eq [System.Net.Sockets.SocketError]::ConnectionRefused) {
            return $true
        }
        $studioConnectionError = $studioConnectionError.InnerException
    }
    return $false
}

function Test-StudioPortListening {
    # The OS endpoint table remains reliable after the HTTP server closes, when
    # PowerShell may report a timeout instead of a connection-refused exception.
    # Wildcard listeners also accept loopback connections on this exact port.
    try {
        $studioEndpoints = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
        $studioLoopbackListeners = @($studioEndpoints | Where-Object {
            $_.Port -eq $Port -and (
                [System.Net.IPAddress]::IsLoopback($_.Address) -or
                $_.Address.Equals([System.Net.IPAddress]::Any) -or
                $_.Address.Equals([System.Net.IPAddress]::IPv6Any)
            )
        })
        return ($studioLoopbackListeners.Count -gt 0)
    } catch {
        # Failure to inspect the OS must never be treated as proof of shutdown.
        return $null
    }
}

try {
    try {
        $studioHealth = Invoke-RestMethod -Uri "$studioUrl/api/health" -TimeoutSec 2
    } catch {
        if ((Test-StudioDisconnected $_) -or (Test-StudioPortListening) -eq $false) {
            Write-Output 'Toon Studio is already stopped.'
            exit 0
        }
        throw 'The local Toon Studio service did not answer. Wait for its current operation to finish, then try again.'
    }
    if ($studioHealth.app -ne 'toon-studio' -or $studioHealth.mode -ne 'platform_build') {
        throw "Port $Port belongs to another application. This helper will only stop Toon Studio's local platform build."
    }
    try {
        $studioBootstrap = Invoke-RestMethod -Uri "$studioUrl/api/bootstrap" -TimeoutSec 3
        if (!$studioBootstrap.csrf_token) { throw 'Missing local shutdown token.' }
        $studioHeaders = @{ 'X-CSRF-Token' = [string]$studioBootstrap.csrf_token }
        $studioStopReply = Invoke-RestMethod -Uri "$studioUrl/api/shutdown" -Method Post -Headers $studioHeaders -Body '' -ContentType 'application/octet-stream' -TimeoutSec 5
        if ($studioStopReply.status -ne 'stopping') { throw 'Unexpected local shutdown response.' }
    } catch {
        throw 'Toon Studio did not accept the stop request. Reload the app and try again. No other process was stopped.'
    }
    $studioTimer = [System.Diagnostics.Stopwatch]::StartNew()
    $studioStopped = $false
    while ($studioTimer.Elapsed.TotalSeconds -lt 15) {
        Start-Sleep -Milliseconds 200
        if ((Test-StudioPortListening) -eq $false) { $studioStopped = $true; break }
        try {
            [void](Invoke-RestMethod -Uri "$studioUrl/api/health" -TimeoutSec 1)
        } catch {
            if ((Test-StudioDisconnected $_) -or (Test-StudioPortListening) -eq $false) {
                $studioStopped = $true
                break
            }
        }
    }
    if (!$studioStopped) { throw 'Toon Studio is still finishing a local operation. Wait a moment, then try stopping it again.' }
    Write-Output 'Toon Studio stopped.'
    exit 0
} catch {
    if ($NoDialog) { Write-Error $_.Exception.Message -ErrorAction Continue; exit 1 }
    Add-Type -AssemblyName System.Windows.Forms
    [void][System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'Toon Studio', 'OK', 'Error')
    exit 1
}
