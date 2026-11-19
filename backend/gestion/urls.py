from django.urls import path
from . import views

app_name = 'gestion'
urlpatterns = [
    path('usuarios/', views.usuarios, name='usuarios'),
    path('usuarios/nuevo/', views.usuario_editar, name='usuario_crear'),
    path('usuarios/<int:pk>/editar/', views.usuario_editar, name='usuario_editar'),
    path('usuarios/<int:pk>/desactivar/', views.usuario_desactivar, name='usuario_desactivar'),
    path('categorias/', views.categorias, name='categorias'),
    path('categorias/nueva/', views.categoria_editar, name='categoria_crear'),
    path('categorias/<int:pk>/', views.categoria_editar, name='categoria_editar'),
    path('precios/', views.precios, name='precios'),
    path('precios/nuevo/', views.precio_crear, name='precio_crear'),
    path('precios/<int:pk>/limites/', views.politica_editar, name='politica_editar'),
    path('condiciones/', views.condiciones, name='condiciones'),
    path('alertas/', views.alertas, name='alertas'),
    path('alertas/nueva/', views.alerta_editar, name='alerta_crear'),
    path('alertas/<int:pk>/', views.alerta_editar, name='alerta_editar'),
    path('auditoria/', views.auditoria, name='auditoria'),
]
