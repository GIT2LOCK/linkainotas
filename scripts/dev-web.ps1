$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $Root "lumina_bot\.venv\Scripts\python.exe"
$Runner = Join-Path $Root "scripts\dev.py"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python do venv nao encontrado em: $Python"
}

Set-Location $Root
& $Python $Runner
