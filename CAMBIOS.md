# Registro de cambios · 23 y 24 de noviembre de 2026

Este documento resume los cambios hechos al prototipo después de la revisión completa del 23/11/2026. Están separados en **cambios de funcionalidad** (reglas, validaciones, errores y estructura del código) y **cambios visuales** (lo que se ve en pantalla). Al final hay instrucciones para verificar y una lista de temas pendientes.

Estado al cierre: **210 pruebas automáticas aprobadas** sobre PostgreSQL. Esto incluye 18 pruebas nuevas en [`backend/config/test_correcciones.py`](backend/config/test_correcciones.py), 7 de gráficos en [`backend/operaciones/tests/test_graficos.py`](backend/operaciones/tests/test_graficos.py) y las pruebas de venta y concurrencia trasladadas al punto de venta real. También se revisaron en vivo las dos interfaces (Django en `8014` y frontend en `8015`).

---

## Parte 1 · Cambios de funcionalidad

### 1.1 Errores corregidos

| # | Problema | Corrección | Archivos principales |
|---|---|---|---|
| 1 | Un adjunto de receta **rechazado** por el QF se seguía descargando desde la ruta de Django `/clinica/adjunto/<id>/` (la API del frontend sí lo bloqueaba). | Ahora responde 404 y el enlace de descarga ya no aparece en el detalle de la receta. | `clinica/views.py`, `clinica/templates/clinica/detalle.html` |
| 2 | **Error 500** al abrir `?editar=abc` en pacientes, prescriptores y convenios. | Un identificador no numérico ahora responde 404. Se agregó la función compartida `id_numerico()`. | `config/respuestas.py`, `clinica/views.py`, `comercio/views.py` |
| 3 | **Error 500** en el libro de controlados al enviar un asiento no numérico (también por la API). | Muestra el aviso «Asiento inexistente.». | `clinica/views.py` |
| 4 | El ingreso manual de inventario aceptaba **lotes vencidos o que vencen hoy** sin advertir (Compras sí los rechazaba). | Se mantiene la posibilidad de registrarlos, para dejar constancia de stock vencido encontrado, pero se exige marcar una **confirmación explícita**. Sin ella se rechaza. | `operaciones/forms.py` |
| 5 | La **factura** aceptaba cualquier texto como RUT (por ejemplo «abc»). | Se valida y normaliza el RUT del receptor (ver 1.2). | `comercio/services.py` |
| 6 | Un producto desactivado **no se podía reactivar** desde ninguna interfaz. | Nuevo botón «Reactivar producto» en la ficha (Django y frontend). Queda registrado en el historial con la acción `reactivar`. | `catalogo/views.py`, `catalogo/urls.py`, `catalogo/models.py`, migración `catalogo/0004`, `config/ui_api.py` |
| 7 | La **recuperación de contraseña** decía «enviado» pero el correo nunca salía en local (no hay servidor SMTP). | En desarrollo, sin `EMAIL_HOST` configurado, los correos se guardan como archivos en `backend/work/correos/`. En despliegue se sigue usando SMTP. | `config/settings.py` |
| 8 | Una receta ya revisada se podía **volver a aprobar o rechazar** sin control. | Solo se aprueban recetas pendientes. El rechazo es definitivo. Revocar una receta aprobada exige escribir el motivo. | `clinica/services.py`, plantillas de detalle (Django y frontend) |
| 9 | Al **crear** un producto, el administrador elegía cualquier condición de venta, incluida «Receta retenida», sin pasar por el QF. | Si quien crea el producto no es Químico Farmacéutico, el producto nace «Por verificar» y no se vende hasta que el QF lo revise en «Revisión de productos». | `catalogo/forms.py`, `catalogo/views.py` |
| 10 | Se aceptaban **categorías duplicadas** que solo cambiaban en mayúsculas («Categoría Prueba» y «categoría prueba»). | Se rechazan sin distinguir mayúsculas ni espacios extra. | `gestion/forms.py` |
| 11a | Las fechas inválidas de un convenio mostraban un mensaje técnico interno (`convenio_fechas_validas`). | Ahora dice «La fecha de término no puede ser anterior a la de inicio.». | `comercio/views.py` |
| 11b | La auditoría mostraba referencias poco útiles («evento gestion #10»). | Muestra el registro afectado: «Producto RS-903», «Orden OC-2», «Receta #4», «Usuario 7», etc., sin exponer datos clínicos. | `gestion/views.py` |
| 12 | Una orden de compra **completa o anulada** seguía mostrando el formulario «Registrar recepción», aunque cualquier envío se rechazaba. | Ahora muestra el aviso «Esta orden está … y no admite nuevas recepciones» con enlaces para volver. El reenvío del mismo formulario sigue procesándose, para conservar la protección contra duplicados. | `compras/views.py`, `templates/compras/formulario.html` |

### 1.2 Validación de RUT chileno

Hay un único validador en [`backend/config/rut.py`](backend/config/rut.py):

- Acepta `12.345.678-5`, `12345678-5`, `123456785` y la `k` en minúscula.
- Calcula el dígito verificador (módulo 11) y guarda siempre la forma normalizada `12345678-5`. La función `formatear_rut()` devuelve `12.345.678-5`.

Dónde se usa:

| Lugar | Regla |
|---|---|
| Trabajadores (Usuarios y permisos) | RUT obligatorio. Reemplaza la validación anterior, que estaba escrita por separado. |
| Factura en el punto de venta | RUT del receptor obligatorio y válido. |
| Prescriptores | RUT obligatorio. |
| Pacientes y retirantes | RUT obligatorio, salvo que se marque **«Documento extranjero (pasaporte u otro)»** para personas sin RUT. |

> Los pacientes y prescriptores registrados antes de este cambio con identificadores como «PAC-T1» pedirán un RUT válido (o la marca de documento extranjero) cuando se editen.

### 1.3 Duplicados eliminados o unificados

| Duplicado | Qué se hizo |
|---|---|
| **Dos flujos de venta**: la «venta rápida» antigua de `operaciones` y el punto de venta de `comercio`. | Se eliminó la venta rápida (servicio `confirmar_venta`, `VentaForm` y su rama en la vista y la plantilla), que ya no tenía ninguna ruta. Antes, sus pruebas se movieron al punto de venta real. **Importante:** las pruebas de concurrencia (dos vendedores y la última unidad, doble confirmación) antes probaban el flujo sin uso; ahora prueban el que usa la app. |
| **Dos sistemas de alertas de stock**: el «stock mínimo» del producto y las «Alertas por ubicación», que no se conectaban entre sí. | El panel y «Productos bajo mínimo» combinan ambos en una sola lista, con una columna **Motivo** («Total bajo el mínimo del producto», «Vitrina bajo su umbral» o «Bodega bajo su umbral»). Los avisos de vencimiento usan el plazo configurado por producto, o 60 días si no tiene. |
| **Código sin uso** en la interfaz. | Se eliminaron el diálogo «EN DESARROLLO» (ningún botón lo abría) y el cálculo de total de la venta rápida en `static/js/interfaz.js` y `templates/base.html`. |
| **Dos scripts de arranque** con los mismos pasos. | `scripts/iniciar_prototipo.ps1` ahora instala dependencias, llama a `scripts/configurar_entorno_local.ps1` (la única definición de la preparación de la base), corre las pruebas y levanta la web. Nuevas opciones `-Puerto` y `-SinPruebas`. |
| **Hojas de estilo copiadas** en el frontend. | `frontend/servidor-local.mjs` sirve `estilos.css`, `tema-oscuro.css` y `tema.js` directamente desde `backend/static/`. Se borraron las copias de `frontend/`. |

### 1.4 Otros cambios de comportamiento

- **Puerto de Django:** `iniciar_prototipo.ps1` arranca en `127.0.0.1:8014`, el puerto que espera el frontend independiente. Antes usaba el 8000.

### 1.5 Duplicados que se mantienen a propósito

- **Dos interfaces** (plantillas de Django y frontend independiente): la duplicación es intencional, porque el frontend reemplazará a las plantillas. Falta decidir cuándo dejar de mantener las plantillas.
- **Indicadores y Reporte de ventas:** comparten filtros, pero uno agrupa por producto y suma recetas, y el otro lista líneas y exporta a PDF y Excel. Fusionarlos cambia la navegación; queda como decisión del equipo.

---

## Parte 2 · Cambios visuales

### 2.1 Modo nocturno (implementado)

- **Interruptor:** en la barra superior de ambas interfaces y en las pantallas de ingreso y recuperación de contraseña.
- **Preferencia:** sin elección guardada se sigue el tema del sistema operativo. La elección se recuerda en el navegador. El tema se aplica antes de dibujar la página, así que no hay destello blanco.
- **Paleta «botica de noche»:** verdes muy oscuros en lugar del gris azulado habitual. Fondo `#0D1412`, superficies `#141E1B`, texto `#E3ECE8` y verde de acción `#4CC9A3`. Los textos cumplen contraste ≥ 4.5:1.
- **Cobertura:** panel, catálogo, inventario, punto de venta, caja, documentos, recetas, controlados, compras, reportes, gestión y formularios, incluidas las hojas propias de los módulos de comercio y clínica.
- **Archivos:** [`backend/static/css/tema-oscuro.css`](backend/static/css/tema-oscuro.css) y [`backend/static/js/tema.js`](backend/static/js/tema.js). Los usan las plantillas de Django y también el frontend.

### 2.2 Gráficos del panel del turno (implementado)

El Inicio de Django y la nueva pantalla **«Turno de hoy»** del frontend independiente muestran cuatro gráficos calculados con datos reales de la base:

| Gráfico | Qué muestra | Quién lo ve |
|---|---|---|
| Ventas por hora | Ventas de hoy por hora local (Santiago), desde la primera venta hasta la hora actual, con la hora más fuerte indicada. | Quien puede consultar ventas |
| Última semana | Los últimos 7 días, con hoy destacado y su monto escrito sobre la barra. Reemplaza las barras horizontales anteriores. | Quien puede consultar ventas |
| Estado de la vitrina | Barra segmentada con los productos activos al día, bajo mínimo o agotados en vitrina, con ícono, cantidad y ejemplos. Usa la misma lista de reposición del panel. | Todos los roles con acceso al inventario |
| Cómo pagaron hoy | Efectivo, tarjeta y transferencia, con monto y porcentaje. | Quien puede consultar ventas |

- Al pasar el mouse, o al recorrerlos con el teclado, cada barra muestra su detalle y atenúa las demás.
- «Ventas por hora» y «Última semana» tienen la opción «Ver datos como tabla».
- Sin ventas, cada gráfico muestra un estado vacío que explica qué hacer.
- Los colores se validaron para daltonismo en modo claro (`#078560` y `#B5DCCB` en la serie; `#078560`, `#B87A00` y `#B23A2B` en los estados) y en modo nocturno (`#229C73`, `#1F4D3D`, `#B8891A` y `#C93F5A`).
- Archivos: cálculos en `operaciones/graficos.py`; dibujo en `templates/operaciones/panel.html` y en `frontend/operaciones.js` (función `grafico`); API en `config/ui_comercio.py` (`panel`); estilos compartidos en `static/css/estilos.css` y `tema-oscuro.css`.

### 2.3 Cambios visibles en pantallas existentes

| Pantalla | Cambio |
|---|---|
| Ficha de producto inactivo | Sección «Reactivar producto». |
| Crear producto (sin rol QF) | La condición aparece bloqueada en «Por verificar», con una explicación. |
| Detalle de receta | La revisión muestra «Aprobar» o «Rechazar» solo si está pendiente, «Revocar aprobación» si está aprobada y nada si fue rechazada. Los adjuntos rechazados no muestran «Descargar». |
| Pacientes y retirantes | Campo «RUT o documento» y casilla «Documento extranjero». |
| Prescriptores | Campo «RUT del profesional». |
| Ingreso de inventario | Casilla «Confirmo que registro un lote vencido o que vence hoy». |
| Recibir orden completa o anulada | Aviso en lugar del formulario. |
| Productos bajo mínimo | Nueva columna «Motivo», con el detalle de vitrina y bodega. |
| Panel (inicio) | La tarjeta de vencimientos indica «60 días o el plazo configurado». Cuatro gráficos nuevos (ver 2.2). |
| Frontend · menú | Nuevo acceso «Turno de hoy». |
| Auditoría | Referencias legibles del registro afectado. |

### 2.4 Propuesta de rediseño (solo maqueta, sin implementar)

Se preparó una maqueta interactiva aparte del código, con tres pantallas: panel del turno, catálogo nocturno y hoja de sistema. Propone:

- **Íconos propios:** diez íconos de trazo fino dibujados a partir de objetos de la farmacia, en lugar de símbolos sueltos como ▦ o ↗.
- **Voz de mesón chileno:** por ejemplo, «Así va el turno», «Despachar en mesón», «Por reponer en vitrina» y «Recetas esperando al QF».
- **Color con significado:**

  | Color | Código | Significado |
  |---|---|---|
  | Verde | `#0E7A5F` | Se puede despachar |
  | Ámbar | `#B87A00` | Por verificar o vence pronto |
  | Rojo | `#B23A2B` | Bloquea la venta |
  | Azul | `#1F5F9E` | Receta simple |
  | Violeta | `#5B3FA8` | Controlado |

- **Estados vacíos con contexto:** cada uno dice qué pasa y qué hacer, con un botón de acción.
- **Detalle memorable:** la cruz del logo se enciende en verde con la caja abierta, se pone ámbar si hay algo que atender y queda gris con la caja cerrada.
- **Gráficos en el panel del turno:** ya implementados en la app (ver 2.2).

La maqueta es privada. Para revisarla con el equipo hay que compartirla desde su menú «Compartir».

---

## Cómo verificar

Desde `backend/` en PowerShell, para preparar la base, correr las pruebas y levantar Django en `8014`:

```powershell
.\scripts\iniciar_prototipo.ps1
```

En otra terminal, desde `frontend/`, para el frontend en `8015`:

```powershell
node servidor-local.mjs
```

Para correr solo las pruebas de estos cambios:

```powershell
.\.venv\Scripts\python.exe manage.py test config.test_correcciones operaciones --noinput --settings=config.settings
```

## Pendientes

- Decidir el reemplazo definitivo de las plantillas de Django por el frontend independiente.
- Decidir si se fusionan Indicadores y Reporte de ventas.
- Decidir si se implementa el resto de la propuesta de rediseño (2.4), total o parcialmente.
- Los pacientes y prescriptores antiguos sin RUT deberán corregirse al editarlos.
