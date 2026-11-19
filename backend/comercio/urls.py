from django.urls import path
from . import views
app_name='comercio'
urlpatterns=[path('pos/',views.pos,name='pos'),path('buscar/',views.buscar,name='buscar'),path('caja/',views.caja,name='caja'),path('convenios/',views.convenios,name='convenios'),path('documentos/<int:pk>/',views.documento,name='documento')]
