# Operaciones del frontend independiente

Entrar a [Farmacia local](http://127.0.0.1:8015/) y abrir **Operaciones**. El menú depende de los permisos configurados en Django. Las cuentas ficticias `admin_demo`, `vendedor_demo`, `tecnico_demo` y `qf_demo` se encuentran en `backend/work/accesos-locales.txt`. Usar la cuenta QF para las decisiones clínicas.

| Bloque | Recorrido de aceptación |
|---|---|
| Compras e inventario | Crear o editar un proveedor. Desde Compras, anular con motivo una orden pendiente sin recepciones. Recibir otra orden y trasladar stock de Bodega a Vitrina desde Operaciones. Consultar movimientos, stock mínimo y alertas por ubicación. |
| Caja y ventas | Abrir caja con fondo. Buscar un producto con stock apto en Vitrina, agregar cantidad y confirmar. Revisar venta, descuento y convenio si corresponde. Abrir el documento académico, simular un fallo y reintentar. Cerrar caja con efectivo contado y motivo si hay diferencia. |
| Clínica | Registrar paciente, prescriptor y receta con productos. Revisar como QF y, si el producto es controlado, autorizar la cantidad. Referenciar la receta en Punto de venta. Consultar saldo, asientos del libro y orden imprimible. Adjuntar respaldos ficticios y comprobar permisos de revisión y descarga. |
| Administración | Desde Catálogo, crear o editar un producto. En Operaciones, gestionar categorías, trabajadores, roles y precios. Aplicar filtros en Indicadores y Auditoría. Abrir los reportes y comprobar PDF o Excel con los permisos correspondientes. |

La venta usa el stock vigente de Vitrina. Los lotes vencidos al día de la venta o bloqueados no se consideran disponibles. El subtotal del carrito es orientativo y el backend calcula el cobro definitivo. Documentos y convenios se utilizan en modo académico.

En clínica, el perfil QF puede revisar archivos en cuarentena mediante el acceso privado. El frontend bloquea la descarga de archivos rechazados a través de la API. Marcar el archivo como revisado y aprobar la receta son decisiones distintas.

Las rutas JSON mantienen la validación y los permisos de los formularios y servicios existentes. Los archivos se descargan mediante rutas autorizadas. Los pasos de [puesta en marcha](primer-flujo-api.md) siguen siendo los mismos.
