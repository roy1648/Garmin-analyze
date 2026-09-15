<#
.SYNOPSIS
    Smoke test for the packaged Streamlit UI EXE.

.DESCRIPTION
    Starts the UI EXE, waits until the process listens on a TCP port,
    requests that port over HTTP, and stops the process it started.

    The port is read from the process's own listening sockets instead of
    its console output, because stdout of a redirected frozen Python
    process is buffered and may never reach a log file.

    The launcher opens the default browser, so a tab may appear.

.PARAMETER Exe
    Path to garmin-tcx-ai-ui.exe.

.PARAMETER TimeoutSeconds
    How long to wait for the server to answer before failing.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_ui_exe.ps1
#>
param(
    [string]$Exe = "dist\garmin-tcx-ai-ui\garmin-tcx-ai-ui.exe",
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Exe)) {
    Write-Host "[ERROR] UI EXE not found at: $Exe"
    exit 1
}

$exePath = (Resolve-Path $Exe).Path
Write-Host "[INFO] Starting $exePath"
# -NoNewWindow uses CreateProcess instead of ShellExecute, which can be
# denied when this script itself runs from a nested cmd.exe. The UI EXE
# console output is interleaved with this script's output.
$proc = Start-Process -FilePath $exePath -WorkingDirectory (Split-Path $exePath) -NoNewWindow -PassThru

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$url = $null
$status = $null

try {
    while ((Get-Date) -lt $deadline) {
        if ($proc.HasExited) {
            Write-Host "[ERROR] UI EXE exited early with code $($proc.ExitCode)."
            exit 1
        }

        if (-not $url) {
            $listen = Get-NetTCPConnection -State Listen -OwningProcess $proc.Id -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($listen) {
                $url = "http://localhost:$($listen.LocalPort)/"
                Write-Host "[INFO] UI EXE is listening on $url"
            }
        }

        if ($url) {
            try {
                $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
                $status = $response.StatusCode
                if ($status -eq 200) { break }
            } catch {
                $status = $null
            }
        }

        Start-Sleep -Seconds 2
    }
}
finally {
    if (-not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
}

if ($status -eq 200) {
    Write-Host "[SUCCESS] UI EXE served $url with HTTP 200."
    exit 0
}

if ($url) {
    Write-Host "[ERROR] UI EXE listened on $url but did not answer HTTP 200 within $TimeoutSeconds seconds."
} else {
    Write-Host "[ERROR] UI EXE did not open a listening port within $TimeoutSeconds seconds."
}
exit 1
