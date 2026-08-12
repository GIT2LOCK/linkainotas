$ErrorActionPreference = "Stop"

$Ports = @(8765, 5173)

foreach ($Port in $Ports) {
    $Connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue

    foreach ($Connection in $Connections) {
        $TargetProcessId = $Connection.OwningProcess

        if ($TargetProcessId -and $TargetProcessId -ne $PID) {
            Write-Output "Stopping process $TargetProcessId using port $Port"
            Stop-Process -Id $TargetProcessId -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Output "LinkAI web/API ports released."
