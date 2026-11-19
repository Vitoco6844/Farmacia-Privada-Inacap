param([string]$PgBin = 'C:\Program Files\PostgreSQL\18\bin')
$ErrorActionPreference = 'Stop'
$raizEntrega = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $raizEntrega
$pythonEntrega = Join-Path $raizEntrega '.venv\Scripts\python.exe'
$marcaEntrega = Get-Date -Format 'yyyyMMdd-HHmmss'
$carpetaEntrega = Join-Path $raizEntrega "docs\evaluacion\evidencias\local-$marcaEntrega"
New-Item -ItemType Directory -Path $carpetaEntrega -Force | Out-Null
& $pythonEntrega scripts/preparar_postgres_local.py --pg-bin $PgBin
if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar PostgreSQL.' }
& $pythonEntrega manage.py check
if ($LASTEXITCODE -ne 0) { throw 'Falló la comprobación Django.' }
& $pythonEntrega manage.py makemigrations --check --dry-run
if ($LASTEXITCODE -ne 0) { throw 'Hay modelos sin migración.' }
& $pythonEntrega scripts/registrar_pruebas.py --salida (Join-Path $carpetaEntrega 'pruebas.json')
if ($LASTEXITCODE -ne 0) { throw 'La suite falló o quedó incompleta; revisar pruebas.json y pruebas.txt.' }
& $pythonEntrega scripts/medir_rendimiento.py --salida (Join-Path $carpetaEntrega 'rendimiento-postgresql.json')
if ($LASTEXITCODE -ne 0) { throw 'No se completó la medición; no presentar resultados parciales como aprobados.' }
git rev-parse HEAD | Set-Content (Join-Path $carpetaEntrega 'commit-base.txt')
git status --short | Set-Content (Join-Path $carpetaEntrega 'cambios-locales.txt')
Write-Host "Evidencias guardadas en $carpetaEntrega. Revisar objetivos de rendimiento y pruebas omitidas."
