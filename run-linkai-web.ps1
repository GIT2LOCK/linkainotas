$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DevScript = Join-Path $Root "scripts\dev-web.ps1"

& $DevScript
