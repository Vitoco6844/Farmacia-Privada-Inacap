param([string]$PgBin = 'C:\Program Files\PostgreSQL\18\bin')
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
& $pythonProyecto scripts/preparar_postgres_local.py --pg-bin $PgBin
if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar PostgreSQL. Revisa la configuración local.' }
foreach ($comando in @('migrate', 'configurar_roles', 'cargar_demo', 'cargar_medicamentos', 'cargar_stock_demo', 'cargar_proveedores_demo', 'crear_cuentas_demo', 'check')) {
    & $pythonProyecto manage.py $comando
    if ($LASTEXITCODE -ne 0) { throw "Falló $comando. No se iniciará el servidor." }
}
Write-Host 'Ejecutando pruebas sobre una base PostgreSQL descartable; la base del prototipo se conserva.'
& $pythonProyecto manage.py test catalogo operaciones seguridad compras --noinput -v 2
if ($LASTEXITCODE -ne 0) { throw 'Las pruebas no pasaron. Revisa los resultados antes de demostrar.' }
Write-Host 'Prototipo: http://127.0.0.1:8000/ — accesos locales en work/accesos-locales.txt'
& $pythonProyecto manage.py runserver 127.0.0.1:8000 --noreload
