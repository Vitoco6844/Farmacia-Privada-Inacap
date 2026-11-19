from django.urls import include, path
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from seguridad.views import IngresarView, RecuperarView, actividad

urlpatterns = [
    path('api/v1/operaciones/', include('config.ui_api')),
    path('api/v1/', include('seguridad.api')),
    path('api/v1/', include('compras.api')),
    path('cuentas/actividad/', actividad, name='actividad'),
    path('cuentas/recuperar/', RecuperarView.as_view(), name='password_reset'),
    path('cuentas/recuperar/enviado/', auth_views.PasswordResetDoneView.as_view(template_name='registration/recuperar_enviado.html'), name='password_reset_done'),
    path('cuentas/restablecer/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/restablecer.html'), name='password_reset_confirm'),
    path('cuentas/restablecer/listo/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/restablecer_listo.html'), name='password_reset_complete'),
    path('cuentas/ingresar/', IngresarView.as_view(), name='login'),
    path('cuentas/salir/', auth_views.LogoutView.as_view(), name='logout'),
    path('administracion/login/', IngresarView.as_view(), name='login_administracion'),
    path('administracion/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='operaciones:panel', permanent=False)),
    path('clinica/', include('clinica.urls')),
    path('comercio/', include('comercio.urls')),
    path('gestion/', include('gestion.urls')),
    path('productos/', include('catalogo.urls')),
    path('compras/', include('compras.urls')),
    path('', include('operaciones.urls')),
]
