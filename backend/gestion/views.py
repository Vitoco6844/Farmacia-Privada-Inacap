from datetime import date
from django.apps import apps
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect
from config.respuestas import render
from django.urls import reverse
from django.views.decorators.http import require_POST
from catalogo.models import Producto, Categoria
from .models import EventoGestion, PoliticaPrecio, PrecioProgramado, ConfiguracionAlerta
from .forms import UsuarioForm, CategoriaForm, PrecioForm, PoliticaForm, AlertaForm, CondicionForm
from .services import guardar_usuario, revisar_condicion, precio_vigente


def formulario(request, form, titulo, volver, guardar):
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                guardar(form)
        except (ValidationError, IntegrityError) as error:
            form.add_error(None, ' / '.join(error.messages) if isinstance(error, ValidationError) else
                'Otro registro utiliza esos datos. Revisa los campos e intenta nuevamente.')
        else:
            messages.success(request, 'Cambios guardados y registrados.')
            return redirect(volver)
    return render(request, 'gestion/formulario.html', dict(form=form, titulo=titulo, volver=volver))


@login_required
@permission_required('gestion.administrar_usuarios', raise_exception=True)
def usuarios(request):
    registros = get_user_model().objects.filter(is_superuser=False).select_related('trabajador').prefetch_related('groups').order_by('username')
    q = request.GET.get('q', '').strip()
    if q:
        from django.db.models import Q
        registros = registros.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(trabajador__rut__icontains=q))
    return render(request, 'gestion/usuarios.html', {'pagina': Paginator(registros, 25).get_page(request.GET.get('pagina')), 'q': q})


@login_required
@permission_required('gestion.administrar_usuarios', raise_exception=True)
def usuario_editar(request, pk=None):
    usuario = get_object_or_404(get_user_model(), pk=pk, is_superuser=False) if pk else get_user_model()()
    form = UsuarioForm(request.POST if request.method == 'POST' else None, instance=usuario)
    return formulario(request, form, 'Editar trabajador' if pk else 'Crear trabajador', 'gestion:usuarios',
        lambda f: guardar_usuario(request.user, usuario, f.cleaned_data, f.cleaned_data['grupos'],
            {k: f.cleaned_data[k] for k in ('rut', 'telefono')}, f.cleaned_data['nueva_clave']))


@login_required
@permission_required('gestion.administrar_usuarios', raise_exception=True)
@require_POST
def usuario_desactivar(request, pk):
    usuario = get_object_or_404(get_user_model(), pk=pk, is_superuser=False)
    try:
        guardar_usuario(request.user, usuario, {'is_active': False}, usuario.groups.all(), {})
    except ValidationError as error:
        messages.error(request, ' / '.join(error.messages))
    else:
        messages.success(request, 'Cuenta desactivada. Su historial se conserva.')
    return redirect('gestion:usuarios')


@login_required
@permission_required('catalogo.view_categoria', raise_exception=True)
def categorias(request):
    return render(request, 'gestion/lista.html', {'titulo': 'Categorías', 'encabezados': ['Nombre', 'Acción'],
        'filas': [(c.nombre, reverse('gestion:categoria_editar', args=[c.pk])) for c in Categoria.objects.all()],
        'crear': 'gestion:categoria_crear', 'tipo': 'editar'})


@login_required
def categoria_editar(request, pk=None):
    from .services import exigir
    exigir(request.user, 'catalogo.change_categoria' if pk else 'catalogo.add_categoria')
    obj = get_object_or_404(Categoria, pk=pk) if pk else None
    form = CategoriaForm(request.POST if request.method == 'POST' else None, instance=obj)
    def guardar(f):
        anterior = Categoria.objects.get(pk=pk).nombre if pk else ''
        c = f.save()
        EventoGestion.objects.create(usuario=request.user, accion='Guardar categoría', referencia=f'Categoría {c.pk}',
            detalle={'anterior': anterior, 'nombre': c.nombre})
    return formulario(request, form, 'Editar categoría' if pk else 'Crear categoría', 'gestion:categorias', guardar)


@login_required
@permission_required('gestion.administrar_precios', raise_exception=True)
def precios(request):
    productos = Producto.objects.all()
    return render(request, 'gestion/precios.html', {'productos': [
        {'producto': p, 'vigente': precio_vigente(p), 'politica': PoliticaPrecio.objects.filter(producto=p).first()} for p in productos],
        'historial': PrecioProgramado.objects.select_related('producto', 'usuario')[:100]})


@login_required
@permission_required('gestion.administrar_precios', raise_exception=True)
def precio_crear(request):
    form = PrecioForm(request.POST if request.method == 'POST' else None)
    def guardar(f):
        p = f.save(commit=False)
        Producto.objects.select_for_update().get(pk=p.producto_id)
        p.usuario = request.user
        p.save()
        EventoGestion.objects.create(usuario=request.user, accion='Programar precio', referencia=f'Producto {p.producto_id}',
            detalle={'precio': str(p.precio), 'desde': str(p.desde), 'hasta': str(p.hasta), 'fuente': p.fuente})
    return formulario(request, form, 'Programar precio', 'gestion:precios', guardar)


@login_required
@permission_required('gestion.administrar_precios', raise_exception=True)
def politica_editar(request, pk):
    p = get_object_or_404(Producto, pk=pk)
    obj = PoliticaPrecio.objects.filter(producto=p).first() or PoliticaPrecio(producto=p)
    form = PoliticaForm(request.POST if request.method == 'POST' else None, instance=obj)
    def guardar(f):
        Producto.objects.select_for_update().get(pk=pk)
        f.save()
        EventoGestion.objects.create(usuario=request.user, accion='Configurar límites de precio', referencia=f'Producto {pk}',
            detalle={k: str(v) for k, v in f.cleaned_data.items()})
    return formulario(request, form, f'Límites comerciales · {p.nombre}', 'gestion:precios', guardar)


@login_required
@permission_required('gestion.revisar_condicion', raise_exception=True)
def condiciones(request):
    form = CondicionForm(request.POST if request.method == 'POST' else None)
    return formulario(request, form, 'Revisión profesional de condición de venta', 'gestion:condiciones',
        lambda f: revisar_condicion(request.user, f.cleaned_data['producto'].pk, f.cleaned_data['condicion'], f.cleaned_data['motivo']))


@login_required
@permission_required('gestion.configurar_alertas', raise_exception=True)
def alertas(request):
    from datetime import timedelta
    from django.utils import timezone
    from django.db.models import Sum
    from operaciones.models import Existencia
    estados = []
    for a in ConfiguracionAlerta.objects.select_related('producto'):
        existencias = Existencia.objects.filter(lote__producto=a.producto, ubicacion=a.ubicacion)
        disponible = existencias.filter(lote__bloqueado=False, lote__producto__activo=True, lote__vencimiento__gt=timezone.localdate()).aggregate(total=Sum('cantidad'))['total'] or 0
        vencimientos = existencias.filter(cantidad__gt=0, lote__vencimiento__lte=timezone.localdate()+timedelta(days=a.dias_vencimiento)).select_related('lote')
        estados.append({'config': a, 'disponible': disponible, 'bajo': disponible <= a.stock_minimo, 'vencimientos': vencimientos})
    return render(request, 'gestion/lista.html', {'titulo': 'Umbrales de alertas', 'encabezados': ['Configuración', 'Acción'],
        'estados': estados,
        'filas': [(f'{a.producto} · {a.get_ubicacion_display()} · Stock ≤ {a.stock_minimo} · Vencimiento {a.dias_vencimiento} días',
            reverse('gestion:alerta_editar', args=[a.pk])) for a in ConfiguracionAlerta.objects.select_related('producto')],
        'crear': 'gestion:alerta_crear', 'tipo': 'editar'})


@login_required
@permission_required('gestion.configurar_alertas', raise_exception=True)
def alerta_editar(request, pk=None):
    form = AlertaForm(request.POST if request.method == 'POST' else None,
        instance=get_object_or_404(ConfiguracionAlerta, pk=pk) if pk else None)
    def guardar(f):
        a = f.save()
        EventoGestion.objects.create(usuario=request.user, accion='Configurar alerta', referencia=f'Alerta {a.pk}',
            detalle={'stock_minimo': a.stock_minimo, 'dias_vencimiento': a.dias_vencimiento, 'ubicacion': a.ubicacion})
    return formulario(request, form, 'Configurar alerta', 'gestion:alertas', guardar)


@login_required
@permission_required('gestion.ver_auditoria', raise_exception=True)
def auditoria(request):
    # Lista positiva de metadatos: nunca presentar JSON arbitrario, contraseñas, adjuntos o datos clínicos.
    eventos = []
    modulo = request.GET.get('modulo', '')
    actor = request.GET.get('actor', '').strip()
    desde, hasta = request.GET.get('desde', ''), request.GET.get('hasta', '')
    fechas = {}
    for clave, valor in [('fecha__date__gte', desde), ('fecha__date__lte', hasta)]:
        if valor:
            try:
                fechas[clave] = date.fromisoformat(valor)
            except ValueError:
                messages.error(request, 'Fecha inválida; utiliza año-mes-día.')
    modulos = ['catalogo', 'seguridad', 'compras', 'operaciones', 'gestion', 'comercio', 'clinica']
    for app in modulos:
        if modulo and modulo != app:
            continue
        for modelo in apps.get_app_config(app).get_models():
            campos = {f.name for f in modelo._meta.fields}
            if not modelo.__name__.startswith('Evento') or 'fecha' not in campos:
                continue
            qs = modelo.objects.filter(**fechas)
            campo_actor = next((c for c in ('usuario', 'actor') if c in campos), None)
            if campo_actor:
                qs = qs.select_related(campo_actor)
                if actor:
                    qs = qs.filter(**{f'{campo_actor}__username__icontains': actor})
            elif actor:
                # Eventos de acceso conservan cuenta seudonimizada.
                qs = qs.filter(cuenta__icontains=actor) if 'cuenta' in campos else qs.none()
            for e in qs.order_by('-fecha', '-pk')[:500]:
                identidad = getattr(e, campo_actor).get_username() if campo_actor and getattr(e, campo_actor) else 'Cuenta seudonimizada'
                accion = next((str(getattr(e, c)) for c in ('accion', 'resultado', 'tipo') if c in campos), 'Actualización')
                eventos.append({'fecha': e.fecha, 'modulo': app, 'actor': identidad, 'accion': accion,
                    'referencia': f'{modelo._meta.verbose_name} #{e.pk}'})
    eventos.sort(key=lambda e: e['fecha'], reverse=True)
    return render(request, 'gestion/auditoria.html', {'pagina': Paginator(eventos, 40).get_page(request.GET.get('pagina')),
        'modulos': modulos, 'modulo': modulo, 'actor': actor, 'desde': desde, 'hasta': hasta})
