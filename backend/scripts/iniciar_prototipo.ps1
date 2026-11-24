param(
    [string]$PgBin = 'C:\Program Files\PostgreSQL\18\bin',
    [int]$Puerto = 8014,
    [switch]$SinPruebas
)
# Arranque completo: dependencias + preparación de la base (configurar_entorno_local.ps1) + pruebas + servidor web.
# La preparación de PostgreSQL, migraciones, roles y datos de demostración vive solo en configurar_entorno_local.ps1.
$ErrorActionPreference = 'Stop'
$raizProyecto = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $raizProyecto
$pythonProyecto = Join-Path $raizProyecto '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonProyecto)) {
    throw 'Prepara primero .venv e instala requirements.txt según el README.'
}
Write-Host 'Comprobando e instalando dependencias del proyecto si faltan.'
& $pythonProyecto -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias. Revisa la conexión y requirements.txt.' }

& (Join-Path $PSScriptRoot 'configurar_entorno_local.ps1') -PgBin $PgBin -Python $pythonProyecto

if (-not $SinPruebas) {
    Write-Host 'Ejecutando pruebas sobre una base PostgreSQL descartable; la base del prototipo se conserva.'
    & $pythonProyecto manage.py test --noinput -v 1 --settings=config.settings
    if ($LASTEXITCODE -ne 0) { throw 'Las pruebas no pasaron. Revisa los resultados antes de demostrar.' }
}
Write-Host "Prototipo: http://127.0.0.1:$Puerto/ — accesos locales en work/accesos-locales.txt"
Write-Host 'Frontend independiente (otra terminal, carpeta frontend): node servidor-local.mjs -> http://127.0.0.1:8015/'
& $pythonProyecto manage.py runserver "127.0.0.1:$Puerto" --noreload --settings=config.settings
