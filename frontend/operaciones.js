const $ = (id) => document.getElementById(id);
const pesos = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP" });

function crear(tag, texto) {
  const elemento = document.createElement(tag);
  if (texto !== undefined) elemento.textContent = texto;
  return elemento;
}

function boton(texto, accion) {
  const control = crear("button", texto);
  control.type = "button";
  control.addEventListener("click", accion);
  return control;
}

function valor(dato) {
  if (typeof dato === "boolean") return dato ? "Sí" : "No";
  return dato ?? "—";
}

function rutaApi(ruta) {
  const [camino, consulta] = ruta.split("?");
  return `operaciones/${camino}/${consulta ? "?" + consulta : ""}`;
}

function tabla(datos, abrir) {
  const region = crear("div");
  region.className = "tabla";
  region.tabIndex = 0;
  region.setAttribute("role", "region");
  region.setAttribute("aria-label", datos.nombre || "Resultados");
  const table = crear("table");
  const cabecera = table.createTHead().insertRow();
  datos.columnas.forEach((nombre) => {
    const th = crear("th", nombre);
    th.scope = "col";
    cabecera.append(th);
  });
  const cuerpo = table.createTBody();
  for (const fila of datos.filas) {
    const tr = cuerpo.insertRow();
    for (const dato of fila) {
      const td = tr.insertCell();
      if (dato?.ruta) td.append(boton(dato.titulo, () => abrir(dato.ruta)));
      else td.textContent = valor(dato);
    }
  }
  if (!datos.filas.length) {
    const td = cuerpo.insertRow().insertCell();
    td.colSpan = datos.columnas.length;
    td.textContent = "No hay registros.";
  }
  region.append(table);
  return region;
}

function campo(datos) {
  let control;
  if (datos.tipo === "select" || datos.tipo === "multiple") {
    control = crear("select");
    control.multiple = datos.tipo === "multiple";
    const elegidos = [].concat(datos.valor ?? []).map(String);
    for (const [v, t] of datos.opciones) {
      const opcion = new Option(t, v);
      if (datos.valor !== undefined && datos.valor !== null) opcion.selected = elegidos.includes(v);
      control.add(opcion);
    }
  } else if (datos.tipo === "textarea") {
    control = crear("textarea");
    control.value = datos.valor ?? "";
  } else {
    control = crear("input");
    control.type = datos.tipo;
    if (datos.tipo === "checkbox") control.checked = Boolean(datos.valor);
    else if (datos.tipo !== "file") control.value = datos.valor ?? "";
    else control.accept = ".pdf,.jpg,.jpeg,.png";
  }
  control.name = datos.nombre;
  control.required = Boolean(datos.requerido);
  control.disabled = Boolean(datos.deshabilitado);
  for (const propiedad of ["min", "max", "step", "maxLength"]) {
    if (datos[propiedad] !== undefined && propiedad in control) control[propiedad] = datos[propiedad];
  }
  if (datos.tipo === "password") control.autocomplete = "new-password";
  if (datos.tipo === "hidden") return control;
  const label = crear("label", datos.etiqueta);
  label.append(control);
  if (datos.ayuda) label.append(crear("small", datos.ayuda));
  return label;
}

function montarPartidas(form, spec) {
  const contenedor = crear("div");
  const total = form.elements.namedItem(`${spec.prefijo}-TOTAL_FORMS`);
  let cantidad = 0;
  function agregar() {
    if (cantidad >= spec.grupos.length) return;
    const bloque = crear("fieldset");
    bloque.append(crear("legend", `Producto ${cantidad + 1}`));
    const campos = crear("div");
    campos.className = "campos";
    campos.append(...spec.grupos[cantidad].map(campo));
    bloque.append(campos);
    contenedor.append(bloque);
    cantidad += 1;
    total.value = cantidad;
    mas.disabled = cantidad >= spec.grupos.length;
    quitar.disabled = cantidad <= 1;
  }
  const mas = boton("Agregar otro producto", agregar);
  const quitar = boton("Quitar último producto", () => {
    if (cantidad <= 1) return;
    contenedor.lastElementChild.remove();
    cantidad -= 1;
    total.value = cantidad;
    mas.disabled = false;
    quitar.disabled = cantidad <= 1;
  });
  const acciones = crear("div");
  acciones.className = "acciones";
  acciones.append(mas, quitar);
  form.append(contenedor, acciones);
  agregar();
}

function montarCarrito(form, api, alError, confirmar) {
  const carrito = new Map();
  const vista = crear("div");
  vista.className = "carrito";
  const texto = crear("label", "Buscar producto para venta");
  const busqueda = crear("input");
  busqueda.type = "search";
  busqueda.maxLength = 100;
  busqueda.placeholder = "Nombre, código o código de barras";
  texto.append(busqueda);
  const resultados = crear("div");
  resultados.className = "acciones";
  resultados.setAttribute("aria-live", "polite");
  const contenido = crear("div");
  const bruto = crear("p");
  const medio = form.elements.namedItem("convenio");
  const descuento = form.elements.namedItem("descuento");
  medio.addEventListener("change", () => {
    descuento.disabled = Boolean(medio.value);
    if (descuento.disabled) descuento.value = "0";
  });
  function mostrarSubtotal() {
    const subtotal = Array.from(carrito.values()).reduce((suma, o) => suma + Number(o.precio) * o.cantidad, 0);
    bruto.textContent = `Subtotal estimado: ${pesos.format(subtotal)}. El servidor calcula el total al confirmar.`;
  }
  function redibujar() {
    const filas = Array.from(carrito.values(), (o) => {
      const cantidad = crear("input");
      cantidad.type = "number";
      cantidad.min = 1;
      cantidad.max = 1000000;
      cantidad.required = true;
      cantidad.value = o.cantidad;
      cantidad.setAttribute("aria-label", `Envases de ${o.nombre}`);
      cantidad.addEventListener("input", () => {
        o.cantidad = Number(cantidad.value);
        mostrarSubtotal();
      });
      return [o.nombre, pesos.format(o.precio), cantidad, boton("Quitar", () => {
        carrito.delete(o.id);
        redibujar();
      })];
    });
    const vistaCarrito = tabla({ columnas: ["Producto", "Precio", "Cantidad", ""], filas: [] }, () => {});
    const cuerpo = vistaCarrito.querySelector("tbody");
    if (filas.length) cuerpo.replaceChildren();
    for (const fila of filas) {
      const tr = cuerpo.insertRow();
      for (const celda of fila) {
        const td = tr.insertCell();
        if (celda instanceof HTMLElement) td.append(celda);
        else td.textContent = celda;
      }
    }
    contenido.replaceChildren(vistaCarrito);
    mostrarSubtotal();
    confirmar.disabled = carrito.size === 0;
  }
  const buscar = boton("Buscar", async () => {
    const q = busqueda.value.trim();
    resultados.replaceChildren();
    if (!q) return;
    buscar.disabled = true;
    try {
      const respuesta = await api(rutaApi(`pos-buscar?${new URLSearchParams({ q })}`));
      for (const p of respuesta.productos) {
        resultados.append(boton(`Agregar ${p.codigo} · ${p.nombre} · ${pesos.format(p.precio)}`, () => {
          if (carrito.has(p.id)) {
            const actual = carrito.get(p.id);
            actual.cantidad = Math.min(1000000, actual.cantidad + 1);
          } else if (carrito.size < 100) carrito.set(p.id, { ...p, cantidad: 1 });
          redibujar();
        }));
      }
      if (!respuesta.productos.length) resultados.textContent = "No se encontraron productos.";
    } catch (error) {
      await alError(error);
    } finally {
      buscar.disabled = false;
    }
  });
  busqueda.addEventListener("keydown", (evento) => {
    if (evento.key === "Enter") {
      evento.preventDefault();
      buscar.click();
    }
  });
  vista.append(texto, buscar, resultados, contenido, bruto);
  form.prepend(vista);
  redibujar();
  return () => Array.from(carrito.values(), (o) => ({ producto_id: o.id, cantidad: o.cantidad }));
}

export function iniciarOperaciones({ api, mensaje, mostrarError, mostrarModulo }) {
  const menu = $("menu-operaciones");
  const pantalla = $("pantalla-operacion");
  const contenido = $("datos-operacion");
  let secuencia = 0;
  let historial = [];
  let rutaActual;

  function mostrarMenu() {
    secuencia += 1;
    historial = [];
    rutaActual = null;
    mostrarModulo("operaciones");
    pantalla.hidden = true;
    menu.hidden = false;
  }

  async function abrir(ruta, recordar = true) {
    if (ruta === "@compras" || ruta === "@inventario") {
      $(`ir-${ruta.slice(1)}`).click();
      return;
    }
    const actual = ++secuencia;
    try {
      const datos = await api(rutaApi(ruta));
      if (actual !== secuencia) return;
      if (datos.archivo) {
        const url = URL.createObjectURL(datos.archivo);
        const descarga = crear("a");
        descarga.href = url;
        descarga.download = datos.nombre;
        document.body.append(descarga);
        descarga.click();
        descarga.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        mensaje("Descarga solicitada.");
        return;
      }
      if (recordar && rutaActual && rutaActual !== ruta) historial.push(rutaActual);
      rutaActual = ruta;
      mostrarModulo("operaciones", ruta, datos.titulo);
      menu.hidden = true;
      pantalla.hidden = false;
      $("titulo-operacion").textContent = datos.titulo;
      contenido.replaceChildren();
      if (datos.nota) contenido.append(crear("p", datos.nota));
      if (datos.resumen?.length) {
        const resumen = crear("dl");
        resumen.className = "resumen";
        for (const [nombre, v] of datos.resumen) {
          const bloque = crear("div");
          bloque.append(crear("dt", nombre), crear("dd", valor(v)));
          resumen.append(bloque);
        }
        contenido.append(resumen);
      }
      if (datos.enlaces?.length || datos.imprimir) {
        const enlaces = crear("div");
        enlaces.className = "acciones";
        for (const item of datos.enlaces || []) enlaces.append(boton(item.titulo, () => abrir(item.ruta)));
        if (datos.imprimir) enlaces.append(boton("Imprimir orden", () => window.print()));
        contenido.append(enlaces);
      }
      for (const spec of datos.formularios || []) contenido.append(formulario(spec, ruta));
      for (const datosTabla of datos.tablas || []) {
        if (datosTabla.nombre) contenido.append(crear("h2", datosTabla.nombre));
        contenido.append(tabla(datosTabla, abrir));
      }
      if (datos.paginas > 1) {
        const paginador = crear("div");
        paginador.className = "paginas";
        for (const [texto, diferencia] of [["Anterior", -1], ["Siguiente", 1]]) {
          const control = boton(texto, () => {
            const [camino, consulta] = ruta.split("?");
            const params = new URLSearchParams(consulta);
            params.set("pagina", datos.pagina + diferencia);
            abrir(`${camino}?${params}`, false);
          });
          control.disabled = datos.pagina + diferencia < 1 || datos.pagina + diferencia > datos.paginas;
          if (diferencia === 1) paginador.append(crear("span", `Página ${datos.pagina} de ${datos.paginas}`));
          paginador.append(control);
        }
        contenido.append(paginador);
      }
      mensaje((datos.avisos || []).join(" "));
      $("titulo-operacion").focus();
    } catch (error) {
      if (actual === secuencia) await mostrarError(error);
    }
  }

  function formulario(spec, ruta) {
    const form = crear("form");
    form.className = "panel";
    const campos = crear("div");
    campos.className = "campos";
    campos.append(...spec.campos.map(campo));
    form.append(campos);
    const confirmar = crear("button", spec.titulo);
    confirmar.type = "submit";
    if (spec.grupos?.length) montarPartidas(form, spec);
    const items = spec.carrito ? montarCarrito(form, api, mostrarError, confirmar) : null;
    form.append(confirmar);
    form.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      if (confirmar.disabled || (spec.confirmar && !window.confirm(spec.confirmar))) return;
      confirmar.disabled = true;
      try {
        const datos = new FormData(form);
        if (spec.metodo === "GET") {
          const query = new URLSearchParams(datos);
          await abrir(`${ruta.split("?")[0]}?${query}`, false);
          return;
        }
        if (items) datos.set("items", JSON.stringify(items()));
        const resultado = await api(rutaApi(spec.ruta || ruta), "POST", datos);
        await abrir(resultado.destino || ruta, false);
        if (resultado.mensaje) mensaje(resultado.mensaje);
      } catch (error) {
        await mostrarError(error);
      } finally {
        confirmar.disabled = false;
      }
    });
    return form;
  }

  $("ir-operaciones").addEventListener("click", mostrarMenu);
  $("volver-operaciones").addEventListener("click", () => {
    if (historial.length) abrir(historial.pop(), false);
    else mostrarMenu();
  });
  return {
    abrir,
    configurar(pantallas = []) {
      secuencia += 1;
      rutaActual = null;
      historial = [];
      contenido.replaceChildren();
      const grupos = new Map();
      for (const item of pantallas) {
        if (!grupos.has(item.grupo)) {
          const bloque = crear("section");
          bloque.className = "panel";
          bloque.append(crear("h2", item.grupo));
          const acciones = crear("div");
          acciones.className = "acciones";
          bloque.append(acciones);
          grupos.set(item.grupo, bloque);
        }
        grupos.get(item.grupo).querySelector(".acciones").append(boton(item.titulo, () => abrir(item.ruta)));
      }
      $("grupos-operaciones").replaceChildren(...grupos.values());
      $("ir-operaciones").hidden = pantallas.length === 0;
      pantalla.hidden = true;
      menu.hidden = false;
    },
  };
}
