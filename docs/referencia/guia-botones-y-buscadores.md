# Guía de botones, búsquedas y límites por pantalla

Describe los controles principales implementados en Farmacia-PI-Ampliada. Es una guía del código, no un registro de que se haya probado cada acción en navegador. Los controles disponibles dependen del rol y los permisos.

## 1. Cómo funcionan los buscadores

Las barras de texto admiten letras, números y combinaciones. No están restringidas a «solo letras» o «solo números», excepto la búsqueda específica del número de orden indicada abajo. Buscar no modifica registros.

«Parcial» significa que el texto puede estar dentro del campo: `para` puede encontrar `Paracetamol`. Los ejemplos requieren que exista un registro coincidente. No hay búsqueda inteligente por sinónimos ni corrección de errores de escritura; tampoco se garantiza equivalencia entre palabras con y sin tildes.

| Pantalla | Qué acepta y dónde busca | Qué no busca / límites |
|---|---|---|
| Productos | Texto parcial en nombre, código interno y código de barras. Ej.: `para`, `MED`, `001` o parte del código de barras. | No busca por precio ni por stock. Categoría, condición y estado tienen selectores separados. |
| Inventario | Texto parcial en nombre del producto, código del producto, código del lote y código de barras. Admite letras, números y códigos mixtos. | No interpreta el texto como cantidad o fecha de vencimiento. Usar los selectores de ubicación y estado. |
| Compras | Texto parcial en nombre del proveedor y nombre/código de los productos de la orden. Si se escriben únicamente dígitos, también busca el número exacto de orden: `12`. | `OC-12` no se interpreta como el número de orden 12. No busca por importe ni fecha. |
| Punto de venta | Nombre y código interno parciales; código de barras completo y exacto. Busca al escribir, al pulsar Enter o al pulsar Buscar. | Solo productos activos; devuelve hasta 20 resultados. Aparecer en resultados no garantiza stock ni autorización para vender. No consulta precio o lote por texto. |
| Recetas y entregas | Nombre o identificador del paciente, ambos por coincidencia parcial. Puede incluir letras o números según el dato guardado. | No busca por número de receta, producto ni nombre del prescriptor. Muestra hasta 200 recetas. |
| Usuarios y permisos | Usuario, nombres, apellidos o RUT por coincidencia parcial. | No busca por correo ni rol; no lista superusuarios. Para RUT, conviene usar dígitos sin puntos, como se guarda en el formulario. |
| Auditoría: Responsable | Filtra la identidad del responsable de los eventos mostrados. Se combina con módulo y fechas. | No es una búsqueda general dentro de todos los detalles de cada evento. No modifica ni elimina registros. |

En listados, **Buscar/Filtrar** aplica los criterios; **Limpiar/Restablecer** vuelve a la consulta predeterminada. **Anterior/Siguiente** cambia de página, no modifica datos. Las pantallas sin barra de búsqueda no incorporan ese filtro por el solo hecho de mostrar una tabla.

## 2. Acceso, recuperación y navegación

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Ingresar | Comprueba usuario y contraseña e inicia sesión si están habilitados. | No crea una cuenta ni concede permisos adicionales. Los intentos repetidos pueden bloquear temporalmente el acceso. |
| Olvidé mi contraseña / Enviar enlace | Solicita recuperación mediante el correo asociado. | En la demo el correo se guarda en `work/correos`; no se envía por un servicio externo. La confirmación no demuestra que exista una cuenta con ese correo. |
| Guardar contraseña | Cambia la clave usando un enlace válido y las validaciones de contraseña. | No permite usar un enlace vencido o inválido. |
| Menú lateral | Abre las pantallas habilitadas para la cuenta. | Ver un enlace no sustituye los permisos comprobados por el servidor. |
| Salir | Cierra la sesión. | No cierra la caja comercial ni borra operaciones. |
| 404: Volver al inicio / Ir a iniciar sesión | Lleva al inicio si hay sesión, o al acceso si no la hay. | No recupera el registro inexistente. |

## 3. Inicio y alertas de stock

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Nueva venta | Abre el punto de venta. | No registra una venta al pulsarlo; se necesita caja abierta para cobrar. |
| Ver inventario / Ver todos / Ver historial | Abre el listado correspondiente a la sección. | No corrige el stock ni resuelve una alerta. |
| Volver a consultar | Reintenta cargar la información cuando se muestra un error. | No repara por sí solo una conexión o configuración incorrecta. |
| Ver lotes, en alertas | Abre las existencias del producto. | No compra ni repone automáticamente. |

## 4. Productos: catálogo, ficha y formulario

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Categoría / Condición / Estado + Filtrar | Combina estos criterios con el texto buscado. | Filtrar no cambia la categoría ni la condición del producto. |
| Agregar producto / Guardar producto | Registra los datos válidos de un producto. | Crear un producto no genera stock: hace falta ingreso o recepción. |
| Ver | Abre la ficha y sus datos disponibles. | No modifica el producto. |
| Editar / Guardar cambios | Actualiza los campos permitidos y conserva registro del cambio. | La condición profesional de un producto existente se gestiona en Revisión de productos. No reescribe precios históricos de ventas. |
| Confirmar desactivación | Marca el producto como inactivo. | No lo borra ni elimina sus ventas o lotes históricos. |
| Consultar ficha de la farmacia | Abre la referencia externa guardada. | No sincroniza automáticamente precio ni disponibilidad con esa farmacia. |
| Consultar lotes y existencias | Abre el inventario correspondiente. | No suma ni descuenta unidades. |
| Cancelar | Sale del formulario. | No guarda lo que se escribió sin confirmar. |

## 5. Inventario e historial de movimientos

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Ubicación / Estado del lote | Filtra existencias por ubicación y condición del lote. | No traslada productos ni modifica vencimientos. |
| Registrar ingreso / Guardar ingreso | Registra lote, vencimiento, ubicación y cantidad; aumenta existencias y deja movimiento. | No crea por sí solo una orden de compra ni una venta. Las cantidades deben ser válidas. |
| Trasladar / Confirmar traslado | Mueve cantidad del origen al destino y registra el movimiento. | No aumenta el stock total ni permite trasladar más del disponible. |
| Historial de movimientos | Consulta ingresos, traslados y salidas registradas. | No ofrece un botón para borrar o revertir esos movimientos. |

## 6. Compras, órdenes y recepciones

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Estado + Filtrar | Acota las órdenes según su estado y búsqueda. | No cambia su estado. |
| Nueva orden / Agregar producto | Abre la orden y agrega filas de productos/cantidades/costos. | Agregar una fila no guarda la orden ni ingresa mercadería. |
| Excluir esta fila | Marca una partida para no incluirla al guardar. | No elimina un producto del catálogo. |
| Crear orden | Guarda la solicitud de compra validada. | No aumenta inventario hasta registrar una recepción. |
| Abrir OC / Ver orden y saldo | Muestra cantidades solicitadas, recibidas, pendientes e historial. | Consultar no recibe automáticamente el saldo. |
| Registrar recepción | Guarda lo recibido con sus lotes y aumenta existencias; admite recepción parcial. | No permite superar lo pendiente ni registrar una recepción en una orden anulada. |
| Anular y conservar historial | Solicita anular la orden con motivo y validación del servicio. | No borra el historial ni equivale a devolver físicamente la mercadería recibida. |

## 7. Proveedores

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Nuevo proveedor / Guardar proveedor | Registra los datos del proveedor. | No envía pedidos, correos ni solicitudes a una empresa real. |
| Editar | Actualiza sus datos mediante formulario. | No representa una búsqueda o verificación externa del proveedor. |

## 8. Caja

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Fondo inicial / Abrir mi caja | Abre la caja de la cuenta con el efectivo inicial indicado. | No es una venta. No permite otra caja abierta simultánea para esa cuenta. |
| Tipo, monto, motivo / Registrar movimiento | Registra un ingreso o retiro de efectivo con motivo. | No vende productos ni modifica inventario. |
| Nueva venta | Abre el POS para trabajar con la caja. | No cobra al pulsar el enlace. |
| Efectivo contado / Confirmar cierre | Compara efectivo contado con esperado y cierra la caja. | No suma pagos con tarjeta o transferencia como efectivo físico. Si hay diferencia, requiere explicación. |
| Historial mostrado | Permite consultar cierres y operaciones disponibles en pantalla. | No incluye reapertura o borrado de cierres desde esos controles. |

## 9. Punto de venta

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Buscar / Enter / escribir | Consulta productos según la tabla de buscadores de esta guía. | No reserva unidades. Un lector de barras debe introducir el código como texto; no se abre una cámara. |
| Pulsar resultado | Añade una unidad al carrito; si ya existe, incrementa la cantidad. | Todavía no guarda la venta ni descuenta stock. |
| Cantidad | Cambia envases del carrito y recalcula el importe mostrado. | El ajuste visual no confirma disponibilidad; el servidor valida al cobrar. |
| Quitar | Retira la fila del carrito. | No elimina el producto del catálogo ni anula una venta previa. |
| Medio de pago | Selecciona efectivo, tarjeta o transferencia para el registro del cobro. | No conecta con un banco ni procesa una tarjeta real. |
| Convenio vigente | Calcula el beneficio estimado del convenio seleccionado. | No verifica afiliación con una institución externa; no se acumula con descuento manual. |
| Descuento manual (%) | Calcula una rebaja estimada; el servidor comprueba los límites por producto. | Un porcentaje escrito no garantiza que sea autorizado. Se deshabilita al elegir convenio. |
| Documento académico | Elige boleta o factura; la factura requiere los datos del receptor. | No emite un documento tributario real ni conecta con el SII. |
| Número interno de receta | Referencia una receta existente mediante su ID numérico. | No es un buscador por paciente ni permite escribir el nombre de un medicamento. |
| Número de quien retira | Referencia el ID de la persona registrada; vacío indica retiro por el paciente. | No corresponde al RUT ni crea una persona nueva. |
| Relación / autorización de retiro | Registra la referencia para retiro por un tercero. | No obtiene una autorización externa ni valida una firma digital. |
| Consultar recetas | Abre el listado de recetas. | No selecciona automáticamente una para la venta. |
| Confirmar venta | Valida caja, stock, precios, descuentos y requisitos clínicos; registra venta, cobro y movimientos. Genera entrega cuando corresponde y abre el documento. | No permite carrito vacío ni sustituye aprobación QF. No emite todavía el documento académico: la emisión se confirma aparte. |
| Mi caja / Abrir caja | Abre la pantalla de caja. | No cierra ni abre caja sin completar su formulario. |

## 10. Ventas y documento de venta

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Ver comprobante | Muestra el detalle histórico de la venta. | No permite cambiar cantidades ni anular la venta desde esa pantalla. |
| Documento, pago y descuentos | Abre el documento con importes, medio de pago y estado de emisión. | No realiza un nuevo cobro. |
| Emitir documento | Ejecuta la emisión académica y registra su estado. | No se comunica con el SII. |
| Simular fallo de emisión | Genera un error de emisión para demostrar el manejo del fallo. | No cancela la venta ni devuelve stock. |
| Reintentar emisión | Reintenta el documento existente después del error. | No crea otra venta ni vuelve a descontar existencias. |
| Orden de entrega | Abre la orden asociada, cuando existe una entrega. | No genera una segunda dispensación. |

## 11. Recetas y entregas

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Buscar paciente | Filtra por nombre o identificador del paciente. | No busca por folio/número de receta. |
| Registrar receta / Guardar receta | Guarda paciente, prescriptor, fechas y partidas; queda pendiente de revisión QF. | No aprueba automáticamente, no entrega productos y no descuenta stock. |
| Registrar paciente / prescriptor | Abre el formulario correspondiente en otra pestaña. | No incorpora automáticamente una persona nueva al selector de la pestaña original sin recargarla. |
| Ver detalle | Muestra partidas, saldos, adjuntos, revisión y entregas vinculadas. | No cambia estados por consultar. |
| Aprobar receta / Rechazar receta | Registra la decisión profesional y observaciones con los permisos exigidos. | Un Administrador sin el rol/permisos profesionales no sustituye al QF. Aprobar no vende ni entrega. |
| Cantidad exacta / Autorizar una entrega hoy | Autoriza producto y cantidad para una dispensación controlada del día. | No es autorización ilimitada: se consume al utilizarla y no registra por sí sola una venta. |
| Adjuntar documento | Guarda un archivo privado validado de tipo PDF/JPG/PNG, con límite de 10 MB. | No lee automáticamente el contenido para completar la receta ni realiza análisis antivirus. |
| Descargar | Descarga el adjunto mediante una ruta protegida y registra la descarga. | No convierte el archivo en público. Requiere permiso. |
| Marcar revisado / Rechazar archivo | Actualiza el estado de revisión del adjunto. | No equivale a aprobar o rechazar la receta completa. |
| Ver orden de entrega | Abre la constancia de una entrega ya registrada. | No vuelve a entregar productos ni descuenta otra vez stock. |

## 12. Pacientes, retirantes y prescriptores

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Guardar registro / Guardar cambios | Crea o actualiza datos de la persona en su formulario. | No crea una cuenta de acceso, una receta ni una autorización profesional. |
| Editar / Cancelar edición | Carga un registro para editarlo o abandona la edición. | No borra recetas ni entregas históricas asociadas. |

## 13. Libro de controlados

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Ver entrega | Abre la orden vinculada al asiento. | No altera el libro. |
| Motivo / Registrar compensación | Registra una compensación trazable con motivo, conservando el asiento original. | No borra el asiento, no anula la venta, no repone stock y no revierte la entrega. Requiere autorización profesional. |

## 14. Orden imprimible

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Imprimir del navegador (Ctrl+P) | Abre el diálogo para imprimir o guardar como PDF la orden con su folio y datos históricos. | No hay un botón propio que emita otro documento; reimprimir conserva el folio. No es documento tributario. |
| Volver a la receta | Abre la receta vinculada. | No modifica la entrega ni su constancia histórica. |

## 15. Convenios

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Guardar convenio | Crea o guarda nombre, porcentaje, tope y vigencia según el formulario. | No firma un convenio real ni conecta con aseguradoras. |
| Editar / Cancelar | Carga el convenio para cambiarlo o abandona la edición. | No recalcula ventas históricas que ya utilizaron un beneficio. |

## 16. Usuarios y permisos

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Buscar | Busca usuario, nombre, apellido o RUT según la primera tabla. | No muestra contraseñas. |
| Crear trabajador / Guardar cambios | Guarda cuenta, datos de trabajador y roles seleccionados con validaciones. | No crea superusuarios desde este formulario. Sin roles, la cuenta no recibe acceso a las operaciones. |
| Roles | Asigna los grupos de negocio seleccionados; admite varios. | Ser Administrador no concede automáticamente la función profesional QF. |
| Contraseña inicial / nueva | Establece la clave al crear; al editar, solo la cambia si se completa. | Dejarla vacía al editar conserva la contraseña; no muestra ni recupera la antigua. |
| Confirmar desactivación | Deshabilita el acceso de la cuenta permitida por las reglas. | No borra su historial. Existen restricciones para proteger la cuenta propia y al último administrador. |

## 17. Categorías, precios y revisión de productos

| Pantalla / control | Qué hace | Qué no hace / condición |
|---|---|---|
| Categorías: Agregar / Editar / Guardar | Crea o renombra una categoría. | No crea productos ni asigna todos los productos a esa categoría automáticamente. |
| Precios: Programar precio | Guarda un precio con vigencia para el producto. | No cambia importes históricos; se aplica al cálculo del precio vigente según fechas y reglas. |
| Precios: Configurar límites | Configura precio máximo, descuento máximo y referencia según el formulario. | No consulta automáticamente un servicio de Cenabast ni obtiene su aprobación. |
| Revisión de productos: Guardar cambios | Registra una condición de venta y motivo mediante revisión profesional. | No vende el producto ni aprueba recetas asociadas. Exige el rol/permisos QF. |

## 18. Alertas por ubicación

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Configurar alerta / Guardar cambios | Guarda producto, ubicación, stock mínimo y horizonte de vencimiento. | No agrega existencias ni crea pedidos de reposición. |
| Editar | Modifica los umbrales usados para mostrar alertas. | No cambia la fecha real del lote ni elimina stock vencido. |
| Estados mostrados | Permiten consultar el stock frente al umbral y los lotes dentro del horizonte. | No envían notificaciones externas automáticamente. |

## 19. Reportes

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Ventas / Inventario / Compras | Cambia el tipo de reporte. | No transforma registros de un módulo en otro. |
| Filtros / Consultar | Aplica los campos disponibles para ese reporte: fechas, producto, categoría, proveedor u otros selectores presentes. | No es búsqueda libre por cualquier columna. Un filtro solo afecta la consulta. |
| Restablecer | Vuelve a los valores de consulta predeterminados. | No borra operaciones ni configuraciones. |
| Descargar PDF / Descargar Excel | Exporta los resultados filtrados y registra la exportación. | No modifica la base. Requiere permiso y hasta 5.000 filas; si se supera, hay que acotar filtros. |

Los reportes de ventas por partidas utilizan precios históricos brutos; no se deben confundir automáticamente con el copago neto después de descuentos/convenios. El reporte de compras muestra importes pedidos y estados de orden; no es una conciliación bancaria.

## 20. Indicadores

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Fechas / Producto / Categoría | Selecciona el período y alcance de los indicadores. | No admite un rango inicial posterior al final. |
| Actualizar indicadores | Recalcula la consulta de ventas, productos, recetas y entregas para los filtros. | No produce ventas nuevas ni hace predicciones de demanda. |
| Restablecer / Ver reporte de ventas | Recupera la consulta predeterminada o abre el reporte. | No elimina indicadores ni registros. |

## 21. Auditoría

| Control | Qué hace | Qué no hace / condición |
|---|---|---|
| Módulo / Responsable / Desde / Hasta / Filtrar | Selecciona eventos de los módulos, responsable y período. | No examina todas las acciones posibles del computador; reúne los eventos registrados por la aplicación. |
| Limpiar filtros / Anterior / Siguiente | Restablece la consulta o recorre páginas. | No limpia ni elimina el historial. |
| Tabla de eventos | Muestra responsable, fecha, acción y referencias disponibles. | Es de consulta: no permite editar o borrar eventos. La consulta limita la recuperación a 500 eventos por origen, por lo que no es una exportación histórica exhaustiva. |

## Para explicar durante la demostración

**Consultar** muestra información; **guardar/confirmar** modifica datos si pasan las validaciones; **emitir documento** es una simulación académica. Las cantidades e identificadores numéricos no son barras de búsqueda. No hay botones de relleno en esta guía: se describen acciones conectadas al código y se aclaran sus límites.
