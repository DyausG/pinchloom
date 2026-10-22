param([switch]$Mouse)
$ErrorActionPreference='Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    if($Mouse){ & '.venv\Scripts\python.exe' run.py --mouse }
    else{ & '.venv\Scripts\python.exe' run.py }
} finally { Pop-Location }
