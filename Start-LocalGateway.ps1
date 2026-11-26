param([string]$PythonExe = 'python')
$ErrorActionPreference = 'Stop'
$resolvedPython = (Get-Command $PythonExe -ErrorAction Stop).Source
# Test-only launcher. No production backend or application database is used.
$managerRoot = Join-Path $PSScriptRoot 'Noviokro-RC1-Custom'
$managerBackend = Join-Path $managerRoot 'backend'
$stateDirectory = Join-Path $managerRoot '.local-state'
if (-not $env:NOVIOKRO_ADMIN_KEY) {
    throw 'Set NOVIOKRO_ADMIN_KEY in this terminal to your local manager admin key. The launcher does not create or print secrets.'
}
& $resolvedPython -c "import fastapi, uvicorn, httpx, sqlalchemy, psycopg"
if ($LASTEXITCODE -ne 0) { throw 'Install the manager backend requirements in this Python environment first.' }
New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null
$stateFile = (Join-Path $stateDirectory 'manager.db').Replace('\','/')
$env:DATABASE_URL = 'sqlite:///' + $stateFile
$env:NOVIOKRO_V12_DATABASE_URL = $env:DATABASE_URL
$env:NOVIOKRO_SERVICE_NOVEAM_BACKEND = 'http://127.0.0.1:8000'
$env:NOVIOKRO_NOVEAM_GATEWAY_ENABLED = '1'
$env:NOVIOKRO_NOVEAM_FRONTEND_ORIGINS = 'http://127.0.0.1:5500,http://localhost:5500'
Write-Output 'Starting local test gateway on 127.0.0.1:8002; NOVEAM upstream is 127.0.0.1:8000.'
Write-Output 'Stop the previous manager process first if port 8002 is already occupied.'
Push-Location -LiteralPath $managerBackend
try { & $resolvedPython -m uvicorn app.main:app --host 127.0.0.1 --port 8002 }
finally { Pop-Location }
