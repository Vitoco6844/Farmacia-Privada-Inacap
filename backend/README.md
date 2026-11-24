# Proyecto de Farmacia Privada INACAP

Entrega del 20 de octubre: [estado por rúbrica y documentos finales](docs/evaluacion/cierre-evaluacion.md). Para guardar pruebas y medición en PostgreSQL: `.\scripts\verificar_entrega.ps1`. La base estructurada elegida es la evaluada por el profesor, según aclaración del usuario; no se requiere otra base para este prototipo.

Prototipo académico Django/PostgreSQL: acceso por roles y límite de intentos, panel con indicadores y alertas, catálogo persistente, inventario por lotes y venta rápida con FEFO. Cantidades, códigos y lotes de demostración; seis medicamentos con precios referenciales publicados y fuente consultada el 19 de octubre de 2026.

## Preparación de la evaluación

El estado vigente y la trazabilidad de los 15 criterios están en [cierre-evaluacion.md](docs/evaluacion/cierre-evaluacion.md). La entrega del **20 de octubre de 2026** corresponde a un **prototipo funcional**, con dedicación declarada de 3–5 horas diarias por integrante. El informe técnico confirma Django, PostgreSQL, HTML/CSS/JavaScript, monolito modular y Kanban. Los documentos distinguen implementación, diseño pendiente e integración simulada.

El [cronograma de cierre](docs/evaluacion/plan-cierre.md) establece tareas, responsables y dependencias sin inventar un reparto histórico. La [matriz de botones y pruebas](docs/evaluacion/pruebas-interfaz.md) describe resultados esperados, acciones que deben rechazarse y funciones pendientes. El [contraste inicial del informe](docs/evaluacion/revision-informe.md) se conserva como antecedente; el estado de la entrega lo determina el documento de cierre.

Por decisión del equipo comunicada el 15 de octubre, se usarán exclusivamente bases estructuradas: PostgreSQL será la única base de datos. Los adjuntos privados conservarán sus referencias y metadatos en PostgreSQL.

## Iniciar en Windows

Con el entorno virtual y PostgreSQL 18 instalados, abre PowerShell en esta carpeta y ejecuta:

```powershell
.\scripts\iniciar_prototipo.ps1
```

El iniciador instala dependencias y llama a `configurar_entorno_local.ps1` (la única definición de la preparación de la base) para preparar una instancia PostgreSQL aislada en `work/postgres`, en `127.0.0.1:55432`, sin tocar servicios o bases existentes. Crea `.env` privado, aplica migraciones, configura roles, carga datos y ejecuta las pruebas en una base descartable `test_farmacia`. Si fallan, se detiene antes de iniciar la web. Se necesita permiso local para crear la base de pruebas; el rol de esta instancia de desarrollo tiene `CREATEDB` y no es superusuario. Ese privilegio no corresponde a un despliegue productivo.

Visita http://127.0.0.1:8014/ (el puerto que espera el frontend independiente; se cambia con `-Puerto`). Para iniciar más rápido sin pruebas: `.\scripts\iniciar_prototipo.ps1 -SinPruebas`. Los usuarios de demostración son `admin_demo` y `vendedor_demo`. Sus contraseñas aleatorias se guardan en `work/accesos-locales.txt`; no se versionan ni se restablecen al volver a iniciar. Para detener la web, presiona Ctrl+C. El clúster local se puede detener con `pg_ctl -D work/postgres stop`, usando el ejecutable de tu instalación de PostgreSQL.

Para otra ruta de instalación: `.\scripts\iniciar_prototipo.ps1 -PgBin 'C:\ruta\PostgreSQL\bin'`. Si ya usas tu propio servidor, completa `.env` desde `.env.example` y ejecuta los pasos Django del iniciador manualmente; el preparador aislado no reemplaza una configuración existente.

En otro computador, prepara una vez el entorno. Se probó Python 3.12 con Django 5.2.17:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Qué tenemos

- Plantilla común con menú, barra superior y diseño adaptable.
- Catálogo persistente con ocho productos ficticios iniciales y seis medicamentos de referencia; seis registros por página.
- Búsqueda por nombre/código/código de barras y filtros combinables.
- Estado sin resultados y navegación entre páginas.
- Agregar, ver, editar y desactivar productos con permisos y registro de cambios. Desactivar conserva el historial; modificar la condición de venta requiere un flujo técnico todavía pendiente.
- Inicio/cierre de sesión, rechazo de cuentas inactivas y expiración por inactividad de 15 minutos. Límite persistente: cinco fallos por cuenta o treinta por origen, con bloqueo temporal de 15 minutos; cubre también el ingreso de administración.
- Inicio con ventas del día, importe, tendencia de siete días y alertas de stock/vencimientos; actualización cada 30 segundos con la pestaña visible. Los datos comerciales requieren permiso de consulta de ventas.
- Stock mínimo configurable por producto; alerta al alcanzar o bajar ese valor, incluyendo productos sin existencias.
- Inventario por lote y ubicación, ingreso, traslado, historial y vencimientos próximos en 60 días.
- Venta rápida de un producto de venta directa por operación, desde vitrina, con precio histórico y asignación FEFO. No es un carrito ni un sistema tributario.
- Reintentos de ingreso, traslado y venta con claves de operación para impedir aplicación duplicada.
- Los lotes vencidos, bloqueados, que vencen hoy y los productos inactivos no se venden; las condiciones de receta o pendientes tampoco están habilitadas.
- Reportes de ventas e inventario con filtros, PDF/Excel y registro de generación por usuario. El administrador exporta ambos; el químico exporta inventario; vendedor y técnico no reciben permisos de exportación.
- [Fuentes de los seis precios y reglas de la carga](docs/evaluacion/precios-referencia.md).

## Recorrido de demostración

1. Ingresar como `admin_demo`, abrir Productos y revisar una ficha `MED-001` a `MED-006`, su presentación, precio y enlace de fuente.
2. Abrir Inventario. Para cada medicamento se cargan 8 envases de vitrina en un lote cercano, 12 en uno de vencimiento posterior, 20 en bodega y 3 vencidos que no se pueden vender. Todo el stock es ficticio. Repetir la carga no repone lo vendido.
3. Registrar un traslado de bodega a vitrina, o un ingreso con lote, vencimiento y cantidad; comprobar el historial.
4. Abrir Ventas → Nueva venta. Vender 10 envases de Paracetamol o Aspirina. Con stock inicial intacto se toman 8 del lote cercano y 2 del posterior. El comprobante conserva lotes, cantidades, precio y responsable.
5. Consultar inventario y comprobar el descuento; verificar que los vencidos y bodega no se utilizaron. Intentar una venta superior al stock disponible y comprobar el rechazo.
6. Como vendedor, consultar productos/inventario y registrar ventas. Las rutas directas de ingreso, traslado y edición de productos deben rechazar el acceso. El técnico puede operar inventario, pero no registrar ventas.

## Verificar este bloque

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test catalogo operaciones seguridad compras --noinput -v 2
```

Las pruebas de concurrencia requieren PostgreSQL y usan conexiones simultáneas: última unidad, doble confirmación y doble ingreso. El [registro de verificación del 19 de octubre](docs/evaluacion/verificacion-inventario-ventas.md) distingue lo realmente ejecutado de lo pendiente por las restricciones de conexión de la sesión de desarrollo. No confundir las comprobaciones de una base temporal con validación de concurrencia en PostgreSQL.

## Dónde trabajar

- `templates/base.html`: estructura visual compartida.
- `templates/catalogo/lista.html`: contenido del catálogo.
- `static/css/estilos.css`: colores, tamaños y distribución.
- `static/js/interfaz.js`: avisos de las funciones pendientes.
- `catalogo/datos_demo.py`: productos de ejemplo.
- `catalogo/views.py`: preparación y filtrado de los datos para la pantalla.
- `config/settings.py`: configuración local de Django.

Una plantilla es la presentación HTML; la vista recibe la solicitud y prepara los datos. Los modelos de `catalogo` representan categorías, productos, historial y referencias; `operaciones` contiene lotes, existencias, movimientos y ventas. Sus servicios aplican validaciones y transacciones; las vistas comprueban permisos y las operaciones vuelven a comprobarlos en el servidor.

La configuración local con `DEBUG=true` es para desarrollo. Siguen pendientes facturación/devoluciones a proveedores, caja, gestión de recetas, autorización de controlados, convenios, recuperación de cuentas, segundo factor y despliegue/respaldos verificados. La auditoría implementada cubre cambios de catálogo, proveedores, órdenes, recepciones y movimientos, no todos los accesos del sistema. Las pantallas pendientes conservan avisos explícitos.

Antes de la evaluación: ejecutar las migraciones, cargas y pruebas sobre PostgreSQL, recorrer las pantallas, completar la matriz de botones con evidencia real y realizar la revisión de usuario. Los precios son referencias publicadas, sin sincronización automática; cuatro medicamentos se dejan con condición Por verificar y bloqueados para venta.

## Trabajar en equipo

Cada integrante debe clonar el repositorio y crear su propio entorno virtual siguiendo las instrucciones anteriores. El entorno `.venv` no se comparte.

Antes de comenzar una tarea, con los cambios anteriores guardados:

```powershell
git switch main
git pull --ff-only
git switch -c nombre-de-la-tarea
```

Al terminar un avance, revisa los archivos antes de subirlos:

```powershell
git status
git diff
git add archivo-modificado
git commit -m "Describe el avance"
git push -u origin nombre-de-la-tarea
```

Abre una pull request en GitHub para revisar e incorporar los cambios a `main`.

## Qué se comparte

Se incluyen código, plantillas, estilos, JavaScript, datos de demostración, fuentes de precios, migraciones, pruebas y `requirements.txt`.

Se excluyen entornos virtuales, cachés, `.env`, credenciales, bases de datos locales, respaldos, archivos de usuarios, logs y configuración personal del editor. `.gitignore` no detecta contraseñas escritas dentro del código: revisa siempre los cambios antes de hacer commit.

`settings.py` exige una clave privada desde el entorno o `.env`. Fuera del modo local se requieren HTTPS y configuración de despliegue adecuada; las cookies seguras y la redirección HTTPS se activan al deshabilitar DEBUG.


## Panel y documentación de cierre

La página inicial es `/inicio/`. Las ventas del día se delimitan por fechas locales de Santiago; la tendencia cubre hoy y los seis días anteriores. El stock mínimo suma bodega y vitrina de lotes vigentes/no bloqueados, sin contar unidades vencidas. Un lote con stock en dos ubicaciones cuenta una sola vez en las alertas de vencimiento. El mínimo se configura en el formulario de producto. Los productos activos sin lotes también pueden generar alerta.

La consulta de indicadores fallida muestra un error y no cifras cero. La actualización automática no supone una garantía de disponibilidad ni reemplaza mediciones de rendimiento.

Documentos actualizados: [arquitectura 4 + 1 y modelo ER](docs/evaluacion/arquitectura-prototipo.md), [seguridad y defensa](docs/evaluacion/seguridad-y-defensa.md), [comportamiento de botones](docs/evaluacion/pruebas-interfaz.md) y [verificación del panel y acceso](docs/evaluacion/verificacion-panel-acceso.md).


## Reportes y descargas

Detén el servidor y ejecuta `scripts/iniciar_prototipo.ps1`. El iniciador comprueba las dependencias de `requirements.txt` (incluye ReportLab y openpyxl), aplica migraciones y configura los permisos. Se requiere conexión a Internet la primera vez que falten paquetes. Los archivos se generan íntegramente en la aplicación local, sin depender de servicios externos de exportación.

Como `admin_demo`, abre Reportes y elige Ventas o Inventario. En Ventas puedes filtrar Desde/Hasta (inclusive, hora Santiago) y nombre/código histórico. La primera consulta muestra 30 días; al limpiar los campos de fecha se consultan todos. En Inventario puedes filtrar producto/lote, ubicación y estado. El inventario corresponde al momento de generar el archivo, no a existencias históricas de una fecha pasada.

Consultar actualiza la tabla y sus totales. Descargar PDF o Descargar Excel usa los mismos campos actuales del formulario. La descarga contiene todo el resultado filtrado, no solo la página visible. Se limita a 5.000 filas por archivo: si se supera, se solicita acotar filtros y no se trunca silenciosamente.

Los archivos incluyen filtros, usuario y fecha/hora de generación. Excel conserva números/fechas, autofiltro, cabeceras fijas y textos como texto, sin ejecutarlos como fórmulas. Si un total excede la precisión de 15 dígitos de Excel se almacena como texto exacto. El PDF maneja textos largos y repite cabeceras al pasar de página. Ambos admiten resultados vacíos. El reporte comercial conserva nombres y precios del detalle de venta.

`EventoReporte` registra generación, tipo, formato, usuario, filtros, filas e importe; no certifica que el navegador completara la descarga. La administración técnica ofrece consulta de esos registros sin edición/borrado en su interfaz.

Ver [pruebas y límites de reportes](docs/evaluacion/verificacion-reportes.md) y la ampliación de la [matriz de botones](docs/evaluacion/pruebas-interfaz.md).

## Compras y recepciones parciales

Detén el servidor y ejecuta `.\scripts\iniciar_prototipo.ps1`. El iniciador aplica la migración de compras, configura permisos y crea dos proveedores ficticios. La carga no crea órdenes ni incrementa existencias y conserva los proveedores que ya hayas modificado.

Como administrador, entra a Compras → Nueva orden. Selecciona proveedor, producto, cantidad y costo por envase CLP. Agregar producto permite incluir hasta 20 productos distintos. Crear una orden conserva nombres y costos históricos sin cambiar el stock ni los precios de venta.

En la orden, Registrar recepción solicita una referencia de entrega única para esa orden. Registra solo lo entregado: producto de la orden, lote, vencimiento futuro, destino y envases. Agregar partida permite dividir entre lotes o ubicaciones (hasta 30 partidas). Cada partida genera un ingreso trazable. Si falla alguna, se revierte toda la recepción. Marca Excluir esta fila para omitirla al guardar.

Prueba una orden de 20 envases: recibe 8 con referencia GUIA-DEMO-001 (estado parcial, saldo 12) y luego 12 con GUIA-DEMO-002 (completa, saldo 0). El stock aumenta 8 y después 12. Reenviar el mismo formulario recupera el registro sin duplicar stock; reutilizar la referencia en una recepción nueva se rechaza. No se admite superar lo pendiente, recibir lotes vencidos/bloqueados o productos inactivos. Si el lote existente tiene otro vencimiento, se rechaza toda la recepción.

El administrador gestiona proveedores, crea y anula órdenes. El técnico y el químico consultan órdenes (incluidos costos) y registran recepciones; el vendedor no accede a compras. Solo se anulan órdenes sin recepciones, con motivo obligatorio, conservando historial. Los registros de cambios de proveedor y creación/anulación pueden consultarse en la administración técnica con permiso y sin edición/borrado.

No se implementan en este bloque devolución/corrección de recepciones, facturación tributaria, pagos, integración real con proveedores ni impresión/exportación de órdenes. Ver [verificación y guion de compras](docs/evaluacion/verificacion-compras.md).
