$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $Root "lumina_bot\.venv\Scripts\python.exe"
$Port = if ($env:LINKAI_PROCESSING_PORT) { [int]$env:LINKAI_PROCESSING_PORT } else { 8765 }

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python do venv nao encontrado em: $Python"
}

if (-not $env:LINKAI_ALLOWED_ORIGINS) {
    $env:LINKAI_ALLOWED_ORIGINS = "https://linkai.2lock.app.br"
}

Set-Location $Root
Write-Output "Iniciando API de processamento LinkAI em 0.0.0.0:$Port"
Write-Output "Origens permitidas: $env:LINKAI_ALLOWED_ORIGINS"

& $Python -m uvicorn backend.api.server:app --host 0.0.0.0 --port $Port
