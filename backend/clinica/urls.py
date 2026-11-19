from django.urls import path
from . import views
app_name='clinica'
urlpatterns=[path('',views.recetas,name='recetas'),path('nueva/',views.receta_crear,name='receta_crear'),path('receta/<int:pk>/',views.receta_detalle,name='receta_detalle'),path('pacientes/',views.personas,name='pacientes'),path('prescriptores/',views.personas,{'tipo':'prescriptor'},name='prescriptores'),path('adjunto/<int:pk>/',views.descargar,name='descargar'),path('entrega/<int:pk>/imprimir/',views.imprimir,name='imprimir'),path('controlados/',views.controlados,name='controlados')]
