$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
python scripts/run_ci_locally.py @args
exit $LASTEXITCODE
