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
