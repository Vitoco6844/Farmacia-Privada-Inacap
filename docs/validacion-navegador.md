# Validación local en navegador

Fecha: 19/11/2026. Frontend independiente, Django y PostgreSQL. Recorrido automatizado mediante Playwright en Microsoft Edge sin ventana, con las cuentas ficticias de Administrador, Vendedor y Químico Farmacéutico. Se usó una base PostgreSQL temporal y se eliminó al finalizar.

| Recorrido | Resultado esperado | Resultado observado |
|---|---|---|
| Compra y recepción parcial | Pedir 10 envases, recibir 4 en Bodega y dejar 6 pendientes. | Coincidió. El enlace de inventario abrió el lote con 4 envases. |
| Traslado | Trasladar 2 envases de Bodega a Vitrina. | Vitrina mostró 2 envases del lote. |
| Venta y caja | Vender un envase por $1.000. Con un fondo de $10.000, cerrar por $11.000. | Coincidió. Quedó 1 envase en Vitrina. |
| Comprobante académico | Simular fallo y reintentar en el documento asociado a la venta. | El documento cambió de fallo a emitido y el stock siguió en 1. |
| Receta y permisos | Impedir la entrega antes de la aprobación QF. Tras aprobar, entregar 2 de 3 y dejar 1 pendiente. | Coincidió. El intento rechazado mantuvo el stock en 5 y la entrega lo bajó a 3. El vendedor no vio el acceso a Compras. |
| Orden de entrega | Abrir la orden con folio y activar el comando de impresión. | Se comprobó el folio y que el botón llama a la función de impresión. |
| Reportes | Descargar el reporte de inventario en PDF y Excel. | Ambas descargas terminaron correctamente. |
| Ancho reducido | Abrir Catálogo, Compras, Inventario y Operaciones a 390 px sin desbordamiento horizontal de la página. | Se cumplieron las cuatro comprobaciones. |

Los resultados cubren estos recorridos. Quedan para una validación posterior la revisión visual de pantallas secundarias, las pruebas de carga y la restauración de respaldos. El despliegue queda para una etapa posterior.
