$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $Root "lumina_bot\.venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python do venv nao encontrado em: $Python"
}

Set-Location $Root
& $Python -m uvicorn backend.api.server:app --host 0.0.0.0 --port 8765 --reload
