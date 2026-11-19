param(
    [string]$PgBin,
    [string]$Python,
    [switch]$Verificar
)

$ErrorActionPreference = 'Stop'
$backend = Split-Path -Parent $PSScriptRoot
if (-not $PgBin) { $PgBin = Join-Path $backend 'work\herramientas\pgsql\bin' }
if (-not $Python) { $Python = Join-Path $backend '.venv\Scripts\python.exe' }
$PgBin = (Resolve-Path -LiteralPath $PgBin).Path
$Python = (Resolve-Path -LiteralPath $Python).Path

function Invoke-PythonProyecto {
    & $Python -B @args
    if ($LASTEXITCODE -ne 0) { throw "Falló Python con código $LASTEXITCODE." }
}

Push-Location -LiteralPath $backend
try {
    Invoke-PythonProyecto scripts/preparar_postgres_local.py --pg-bin $PgBin
    $validar = "from django.db import connection; d = connection.settings_dict; assert (connection.vendor, d['HOST'], str(d['PORT']), d['NAME'], d['USER']) == ('postgresql', '127.0.0.1', '55432', 'farmacia', 'farmacia_app'), 'La configuración efectiva no apunta a la base local de Farmacia'"
    Invoke-PythonProyecto manage.py shell --settings=config.settings -c $validar
    foreach ($comando in @('migrate', 'configurar_roles', 'cargar_demo', 'cargar_medicamentos', 'cargar_stock_demo', 'cargar_proveedores_demo', 'crear_cuentas_demo', 'check')) {
        Invoke-PythonProyecto manage.py $comando --settings=config.settings
    }
    if ($Verificar) {
        Invoke-PythonProyecto manage.py migrate --check --settings=config.settings
        Invoke-PythonProyecto manage.py makemigrations --check --dry-run --settings=config.settings
        Invoke-PythonProyecto manage.py test operaciones.tests.test_concurrencia compras.tests.test_concurrencia catalogo.tests --noinput -v 2 --settings=config.settings
        Invoke-PythonProyecto manage.py shell --settings=config.settings -c "from django.db import connection; from django.contrib.auth.models import Group; from catalogo.models import Producto; c = connection.cursor(); c.execute('SELECT current_database(), current_setting(%s)', ['server_version']); print('Base y versión:', c.fetchone()); print('Tablas:', len(connection.introspection.table_names())); print('Grupos:', Group.objects.count()); print('Productos:', Producto.objects.count())"
    }
}
finally {
    Pop-Location
}
