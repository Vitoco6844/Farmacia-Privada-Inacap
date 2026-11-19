# Checklist breve para demostrar en el navegador

Versión ampliada local — 20 de octubre de 2026. Guion basado en rutas, permisos y funcionalidades del código. Las casillas están pendientes: se marcan después de realizar cada acción, no por existir el código.

Preparación: servidor local activo, cuentas de demostración de Administrador y Químico Farmacéutico, productos activos con existencias y datos ficticios. Usar una caja abierta o abrirla cuando corresponda. Duración orientativa: 15–20 minutos con datos preparados.

| Listo | Pantalla | Acción que se puede mostrar y resultado esperado |
|---|---|---|
| [ ] | Acceso | Ingresar con una cuenta válida y mostrar el menú de su rol. Una contraseña incorrecta no permite entrar. |
| [ ] | Catálogo y categorías | Buscar un producto por nombre o código, abrir su ficha y mostrar precio, categoría y condición de venta. Crear una categoría de demostración y comprobar que aparece. |
| [ ] | Inventario | Consultar lotes y existencias; trasladar una unidad entre bodega y vitrina. Deben cambiar ambas cantidades y quedar registrado el movimiento. |
| [ ] | Compras | Abrir una orden de prueba y registrar una recepción parcial. Se muestran lo recibido y lo pendiente, y aumenta el inventario del lote recibido. |
| [ ] | Caja | Abrir con un fondo inicial si no hay caja abierta; registrar un ingreso o retiro con motivo y comprobar el saldo esperado. Dejar el cierre para después de la venta. |
| [ ] | Punto de venta | Buscar un producto de venta directa con stock, agregarlo, cambiar cantidad y cobrar. Se registra una venta y disminuye el stock. |
| [ ] | Documento de venta | Abrir el documento asociado a esa venta y emitirlo en modo académico. Si se demuestra un reintento, no debe generar una segunda venta. No es emisión tributaria real. |
| [ ] | Recetas y entrega | Abrir una receta preparada; con el rol farmacéutico revisarla. Para una venta con receta, mostrar la entrega asociada y abrir su orden imprimible con folio. |
| [ ] | Convenios y precios | Mostrar un convenio vigente y su beneficio en el POS; abrir precios para mostrar vigencia y límites. El descuento manual y el convenio no se acumulan. |
| [ ] | Alertas | Consultar stock bajo o vencimientos por ubicación y abrir su configuración. Usar un producto de prueba cuyo stock esté bajo el mínimo configurado. |
| [ ] | Indicadores, reportes y auditoría | Filtrar un período que incluya las operaciones de prueba, descargar un reporte y consultar su registro en auditoría. Los importes brutos y el total pagado pueden diferir por descuentos. |
| [ ] | Usuarios y cierre | Mostrar la asignación de roles sin modificar la cuenta con la que se presenta. Volver a caja, ingresar el efectivo contado y cerrar; una diferencia requiere motivo. |

## Solo si el profesor solicita más detalle

- [ ] Controlados: con el rol farmacéutico, autorizar producto y cantidad de una receta; realizar la venta con una cuenta habilitada para caja y mostrar el asiento generado. La autorización es de un solo uso.
- [ ] Permisos: entrar con Vendedor y comprobar que no puede administrar usuarios ni aprobar recetas. Ocultar un enlace no sustituye comprobar que la ruta rechaza el acceso.

Si algo falla, anotar pantalla, acción y mensaje; dejar la casilla sin marcar. No crear operaciones repetidas solo para llenar la lista.

Registro de la demostración: fecha ______ / integrante ______ / incidencias ______.

La evidencia automática y las comprobaciones manuales ya realizadas se distinguen en [plan-pruebas-final.md](plan-pruebas-final.md).
