# Órdenes de compra, recepción e inventario

Desde el frontend local en [Farmacia](http://127.0.0.1:8015/), ingresar con la cuenta ficticia de Administrador. Las cuentas de demostración se guardan en `backend/work/accesos-locales.txt`.

1. En **Catálogo**, copiar el código exacto de un producto activo.
2. En **Compras → Nueva orden**, seleccionar un proveedor activo, ingresar el código, 10 envases y el costo por envase en CLP. Se pueden agregar hasta 20 productos distintos. **Crear orden** guarda el pedido. Las existencias se actualizan al recibir.
3. Abrir la orden y pulsar **Registrar recepción**. Seleccionar el producto, ingresar una referencia, un lote, un vencimiento futuro, **Bodega** y 4 envases.
4. Confirmar. El detalle muestra **Recepción parcial**, con 10 pedidos, 4 recibidos y 6 pendientes. La interfaz recibe un lote por confirmación y permite continuar en otra recepción.
5. Pulsar **Ver lote en inventario**. La consulta usa producto, lote y ubicación. Para un lote nuevo, deben figurar 4 envases en Bodega. La pantalla también permite buscar productos y lotes y filtrar por ubicación.

Los perfiles sin permiso de compras no ven ese módulo. El servidor valida los permisos igualmente. Un vendedor puede consultar inventario. Una recepción exige autorización para registrar recepciones e ingresos de lotes.

La API usa los formularios, claves firmadas por usuario y servicios transaccionales existentes. La prueba de integración verifica la protección CSRF, la recepción parcial, el reenvío idempotente, el rechazo de un exceso y la consulta de stock. El alcance de esta etapa cubre selección de proveedores activos, creación y consulta de órdenes, recepción e inventario por lote. La administración de proveedores, la anulación de órdenes, traslados y alertas requieren integración adicional.
