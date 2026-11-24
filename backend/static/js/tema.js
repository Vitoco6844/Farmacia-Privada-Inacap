/* Tema claro / nocturno. Se carga en <head> (sin defer) para aplicar el tema antes de pintar la página y evitar
   el destello blanco. Sin preferencia guardada se respeta la del sistema operativo. */
(function () {
  var CLAVE = 'farmacia-tema';
  var raiz = document.documentElement;

  function guardado() {
    try { return localStorage.getItem(CLAVE); } catch (e) { return null; }
  }

  function sistema() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'oscuro' : 'claro';
  }

  function aplicar(tema) {
    raiz.setAttribute('data-tema', tema);
    document.querySelectorAll('[data-tema-toggle]').forEach(function (boton) {
      var oscuro = tema === 'oscuro';
      boton.setAttribute('aria-pressed', String(oscuro));
      boton.setAttribute('title', oscuro ? 'Cambiar a modo claro' : 'Cambiar a modo nocturno');
      var texto = boton.querySelector('.tema-texto');
      if (texto) texto.textContent = oscuro ? 'Modo claro' : 'Modo nocturno';
    });
  }

  aplicar(guardado() || sistema());

  if (window.matchMedia) {
    var consulta = window.matchMedia('(prefers-color-scheme: dark)');
    var alCambiar = function () { if (!guardado()) aplicar(sistema()); };
    if (consulta.addEventListener) consulta.addEventListener('change', alCambiar);
  }

  function crearBoton(flotante) {
    var boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'tema-toggle' + (flotante ? ' tema-flotante' : '');
    boton.setAttribute('data-tema-toggle', '');
    boton.innerHTML = '<span class="tema-icono" aria-hidden="true"></span><span class="tema-texto"></span>';
    return boton;
  }

  document.addEventListener('DOMContentLoaded', function () {
    // Botón en la barra superior (junto a la cuenta) o flotante en pantallas sin barra (ingreso, recuperación).
    var destino = document.querySelector('[data-tema-destino]') || document.querySelector('.topbar .user');
    if (!document.querySelector('[data-tema-toggle]')) {
      if (destino) destino.insertBefore(crearBoton(false), destino.firstChild);
      else document.body.appendChild(crearBoton(true));
    }
    document.addEventListener('click', function (evento) {
      var boton = evento.target.closest('[data-tema-toggle]');
      if (!boton) return;
      var nuevo = raiz.getAttribute('data-tema') === 'oscuro' ? 'claro' : 'oscuro';
      try { localStorage.setItem(CLAVE, nuevo); } catch (e) { /* sin almacenamiento: solo esta visita */ }
      aplicar(nuevo);
    });
    aplicar(raiz.getAttribute('data-tema'));
  });
})();
