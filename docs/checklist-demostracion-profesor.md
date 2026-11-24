# Checklist de demostración de Farmacia

Preparen cuentas ficticias de Administrador, Vendedor y Químico Farmacéutico (QF), un producto de venta directa y una receta de prueba. Para reproducir los montos de abajo, usen un producto de $1.000 y una venta en efectivo sin descuentos. Marquen las casillas durante la presentación.

## Recorrido principal

- [ ] **Acceso y modo nocturno.** Iniciar sesión y mostrar el menú del perfil. Cambiar de tema y recargar para comprobar que se conserva la preferencia. Con Vendedor, comprobar que Compras no está disponible.
- [ ] **Catálogo.** Buscar por nombre o código, aplicar un filtro de condición de venta y pulsar **Limpiar** para volver al listado.
- [ ] **Compras e inventario.** Crear una orden por 10 envases y registrar una recepción de 4. Mostrar los 6 pendientes y abrir **Ver lote en inventario**. Trasladar 2 envases de Bodega a Vitrina y comprobar el saldo en ambas ubicaciones.
- [ ] **Caja y punto de venta.** Abrir caja con $10.000. En Punto de venta, buscar, agregar y vender en efectivo 1 envase por $1.000. Comprobar que queda 1 en Vitrina y que Caja espera $11.000. Cerrar con ese monto.
- [ ] **Documento de venta.** Abrir el comprobante académico de la venta, pulsar **Simular fallo** y luego **Emitir o reintentar**. Verificar que queda emitido y que el saldo del lote sigue en 1.
- [ ] **Receta y orden de entrega.** Registrar una receta por 3 envases. Mostrar que el vendedor no puede entregar con la revisión pendiente. Aprobar con el perfil QF, entregar 2 envases desde una cuenta habilitada y abrir la orden imprimible con folio y saldo de 1 envase.
- [ ] **Turno de hoy y reportes.** Mostrar el resumen y los gráficos del turno tras registrar la venta. En Reportes, generar y descargar un reporte de inventario en PDF o Excel.

## Si el profesor pide otra comprobación

- [ ] **Usuarios y permisos.** Abrir la administración con el perfil autorizado y mostrar los roles. Comprobar que el perfil Vendedor no puede acceder a esa pantalla.
- [ ] **Auditoría.** Filtrar por módulo o actor y buscar un evento generado durante la demostración.
