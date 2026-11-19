from django.urls import path
from . import views

app_name = 'compras'
urlpatterns = [
    path('', views.ordenes, name='ordenes'),
    path('nueva/', views.nueva_orden, name='nueva_orden'),
    path('ordenes/<int:pk>/', views.orden_detalle, name='orden_detalle'),
    path('ordenes/<int:pk>/recibir/', views.nueva_recepcion, name='nueva_recepcion'),
    path('ordenes/<int:pk>/anular/', views.anular, name='anular'),
    path('recepciones/<int:pk>/', views.recepcion_detalle, name='recepcion_detalle'),
    path('proveedores/', views.proveedores, name='proveedores'),
    path('proveedores/nuevo/', views.nuevo_proveedor, name='nuevo_proveedor'),
    path('proveedores/<int:pk>/editar/', views.editar_proveedor, name='editar_proveedor'),
]
