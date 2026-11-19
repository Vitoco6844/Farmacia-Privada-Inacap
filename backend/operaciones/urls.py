from django.urls import path
from . import views
from . import vistas_reportes, ampliacion

app_name = 'operaciones'
urlpatterns = [
    path('reportes/compras/', ampliacion.compras, name='reporte_compras'),
    path('indicadores/', ampliacion.analisis, name='analisis'),
    path('reportes/', vistas_reportes.inicio, name='reportes'),
    path('reportes/ventas/', vistas_reportes.ventas, name='reporte_ventas'),
    path('reportes/inventario/', vistas_reportes.inventario, name='reporte_inventario'),
    path('inicio/', views.panel, name='panel'),
    path('inventario/alertas-stock/', views.alertas_stock, name='alertas_stock'),
    path('inventario/', views.inventario, name='inventario'),
    path('inventario/ingreso/', views.ingreso, name='ingreso'),
    path('inventario/traslado/', views.traslado, name='traslado'),
    path('inventario/movimientos/', views.movimientos, name='movimientos'),
    path('ventas/', views.ventas, name='ventas'),
    path('ventas/nueva/', views.nueva_venta, name='nueva_venta'),
    path('ventas/<int:pk>/', views.venta_detalle, name='venta_detalle'),
]
