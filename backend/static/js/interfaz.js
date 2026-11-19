const aviso = document.querySelector('#aviso');
document.querySelectorAll('[data-pendiente]').forEach((button) => {
  button.addEventListener('click', () => {
    document.querySelector('#aviso-texto').textContent = `${button.dataset.pendiente} se construirá en una próxima etapa. Por ahora puedes explorar el catálogo, buscar productos y utilizar los filtros.`;
    aviso.showModal();
  });
});

const resumenVenta = document.querySelector('#venta-resumen');
if (resumenVenta) {
  const producto = document.querySelector('#id_producto');
  const cantidad = document.querySelector('#id_cantidad');
  const moneda = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });
  const actualizar = () => {
    const precio = Number(producto.selectedOptions[0]?.dataset.precio);
    const unidades = Number(cantidad.value);
    resumenVenta.textContent = Number.isFinite(precio) && Number.isInteger(unidades) && unidades > 0
      ? `Precio unitario: ${moneda.format(precio)} · Total estimado: ${moneda.format(precio * unidades)} CLP. El servidor verifica precio y stock al confirmar.`
      : 'Selecciona producto y una cantidad válida para consultar el total estimado.';
  };
  producto.addEventListener('change', actualizar);
  cantidad.addEventListener('input', actualizar);
  actualizar();
}

if (document.querySelector('#panel-actualizacion')) {
  const refrescarPanel = () => {
    if (document.visibilityState === 'visible') { const url = new URL(window.location.href); url.searchParams.set('_automatico', '1'); window.location.replace(url); }
    else window.setTimeout(refrescarPanel, 30000);
  };
  window.setTimeout(refrescarPanel, 30000);
}

// Una interacción real comunica actividad; el temporizador nunca la simula.
let ultimaActividadEnviada = 0;
for (const evento of ['pointerdown', 'keydown']) {
 document.addEventListener(evento, () => {
  if (Date.now() - ultimaActividadEnviada < 60000) return;
  ultimaActividadEnviada = Date.now();
  fetch('/cuentas/actividad/', {method: 'POST', credentials: 'same-origin', headers: {'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''}});
 }, {passive: true});
}
