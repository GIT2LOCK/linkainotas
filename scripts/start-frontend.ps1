$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

Set-Location $Root
npm run dev -- --host 0.0.0.0 --port 5173
