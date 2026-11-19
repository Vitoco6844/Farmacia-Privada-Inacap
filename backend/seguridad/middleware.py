"""El refresco de indicadores no cuenta como actividad de la persona."""
import time
from django.contrib.auth import logout
from django.shortcuts import redirect, render


class PaginaNoEncontradaMiddleware:
    """Presenta el error de navegación incluso en la demo con DEBUG activo."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (response.status_code == 404
                and request.method in ('GET', 'HEAD')
                and request.accepts('text/html')
                and response.get('Content-Type', '').startswith('text/html')):
            response = render(request, '404.html', status=404)
            response['Cache-Control'] = 'private, no-store'
        return response


class InactividadMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            ahora = time.time()
            ultima = request.session.get('ultima_actividad_humana', ahora)
            if ahora - ultima >= 900:
                logout(request)
                if not request.path_info.startswith('/api/v1/'):
                    return redirect('login')
            elif request.GET.get('_automatico') != '1':
                request.session['ultima_actividad_humana'] = ahora
            elif 'ultima_actividad_humana' not in request.session:
                request.session['ultima_actividad_humana'] = ahora
        response = self.get_response(request)
        if request.user.is_authenticated:
            response['Cache-Control'] = 'private, no-store'
        return response
