from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from config.respuestas import render
from django.views.decorators.http import require_POST
from .forms import ProductoForm
from .models import Categoria, EventoCatalogo, Producto


def snapshot(producto):
    return {campo: str(getattr(producto, campo)) for campo in (
        'codigo', 'barras', 'nombre', 'presentacion', 'categoria_id', 'condicion', 'precio', 'activo', 'stock_minimo')}


@login_required
@permission_required('catalogo.view_producto', raise_exception=True)
def lista(request):
    q = request.GET.get('q', '').strip()
    categoria = request.GET.get('categoria', '')
    condicion = request.GET.get('condicion', '')
    estado = request.GET.get('estado', '')
    todos = Producto.objects.all()
    productos = todos.select_related('categoria')
    if q:
        productos = productos.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q) | Q(barras__icontains=q))
    if categoria:
        productos = productos.filter(categoria__nombre=categoria)
    if condicion:
        productos = productos.filter(condicion=condicion)
    if estado in ('activo', 'inactivo'):
        productos = productos.filter(activo=estado == 'activo')
    pagina = Paginator(productos, 6).get_page(request.GET.get('pagina'))
    params = request.GET.copy()
    params.pop('pagina', None)
    return render(request, 'catalogo/lista.html', {
        'pagina': pagina, 'params': params.urlencode(), 'q': q, 'categoria': categoria,
        'condicion': condicion, 'estado': estado, 'categorias': Categoria.objects.values_list('nombre', flat=True),
        'condiciones': Producto.Condicion.values, 'total': todos.count(),
        'activos': todos.filter(activo=True).count(),
        'con_receta': todos.filter(condicion__in=[Producto.Condicion.SIMPLE, Producto.Condicion.RETENIDA]).count(),
        'por_verificar': todos.filter(condicion=Producto.Condicion.VERIFICAR).count(),
    })


@login_required
@permission_required('catalogo.view_producto', raise_exception=True)
def detalle(request, pk):
    return render(request, 'catalogo/detalle.html', {
        'producto': get_object_or_404(Producto.objects.select_related('categoria'), pk=pk),
    })


def formulario(request, producto=None):
    form = ProductoForm(request.POST if request.method == 'POST' else None, instance=producto)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                anterior = snapshot(Producto.objects.get(pk=producto.pk)) if producto else {}
                guardado = form.save()
                EventoCatalogo.objects.create(producto=guardado, usuario=request.user,
                    accion='editar' if producto else 'crear', anterior=anterior, posterior=snapshot(guardado))
        except IntegrityError:
            form.add_error(None, 'Otro registro utiliza ese código o código de barras. Revisa los datos.')
        else:
            messages.success(request, 'Producto actualizado.' if producto else 'Producto creado.')
            return redirect('catalogo:detalle', pk=guardado.pk)
    return render(request, 'catalogo/formulario.html', {'form': form, 'producto': producto})


@login_required
@permission_required('catalogo.add_producto', raise_exception=True)
def crear(request):
    return formulario(request)


@login_required
@permission_required('catalogo.change_producto', raise_exception=True)
def editar(request, pk):
    return formulario(request, get_object_or_404(Producto, pk=pk))


@login_required
@permission_required('catalogo.change_producto', raise_exception=True)
@require_POST
def desactivar(request, pk):
    with transaction.atomic():
        producto = get_object_or_404(Producto.objects.select_for_update(), pk=pk)
        if producto.activo:
            anterior = snapshot(producto)
            producto.activo = False
            producto.save(update_fields=['activo', 'actualizado'])
            EventoCatalogo.objects.create(producto=producto, usuario=request.user, accion='desactivar',
                anterior=anterior, posterior=snapshot(producto))
    messages.success(request, 'Producto inactivo. Se conserva su historial.')
    return redirect('catalogo:detalle', pk=pk)
