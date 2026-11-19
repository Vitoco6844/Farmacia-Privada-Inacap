const $ = (id) => document.getElementById(id);
const moneda = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP" });

function fila(tabla, valores) {
  const nueva = tabla.insertRow();
  for (const valor of valores) {
    const celda = nueva.insertCell();
    if (valor instanceof HTMLElement) celda.append(valor);
    else celda.textContent = valor;
  }
}

function enviarFormulario(formulario) {
  return new URLSearchParams(new FormData(formulario));
}

function convertirPartidas(datos, prefijo, partidas) {
  datos.set(`${prefijo}-TOTAL_FORMS`, partidas.length);
  datos.set(`${prefijo}-INITIAL_FORMS`, 0);
  partidas.forEach((campos, i) => {
    for (const [nombre, valor] of Object.entries(campos)) {
      datos.set(`${prefijo}-${i}-${nombre}`, valor);
    }
  });
  return datos;
}

export function iniciarCompras({ api, mensaje, mostrarError, mostrarModulo, abrirOperacion }) {
  const crear = $("crear-orden");
  const recibir = $("recibir-orden");
  const buscarStock = $("buscar-stock");
  const partidas = $("partidas-orden");
  let permisos = {};
  let orden;
  let tokenOrden;
  let tokenRecepcion;
  let paginaCompras = 1;
  let paginaStock = 1;
  let filtroStock = {};
  let ultimoLote;
  let sesion = 0;

  function ejecutar(control, accion) {
    return async (evento) => {
      evento?.preventDefault();
      if (control.disabled) return;
      control.disabled = true;
      const actual = sesion;
      try {
        await accion(() => actual === sesion);
      } catch (error) {
        if (actual === sesion) await mostrarError(error);
      } finally {
        control.disabled = false;
      }
    };
  }

  function paginador(modulo, resultado) {
    $(`${modulo}-pagina`).textContent = `Página ${resultado.pagina} de ${resultado.paginas}`;
    $(`${modulo}-anterior`).disabled = resultado.pagina <= 1;
    $(`${modulo}-siguiente`).disabled = resultado.pagina >= resultado.paginas;
  }

  async function listarOrdenes(numero, vigente) {
    const datos = await api(`compras/ordenes/?pagina=${numero}`);
    if (!vigente()) return;
    paginaCompras = datos.pagina;
    $("ordenes").replaceChildren();
    for (const item of datos.ordenes) {
      const enlace = document.createElement("button");
      enlace.type = "button";
      enlace.textContent = `OC-${item.id}`;
      enlace.addEventListener("click", ejecutar(enlace, async (activa) => {
        const solicitada = await api(`compras/ordenes/${item.id}/`);
        if (activa()) mostrarOrden(solicitada);
      }));
      fila($("ordenes"), [enlace, item.proveedor, item.estadoTexto, moneda.format(item.total)]);
    }
    paginador("compras", datos);
    if (!$("compras").hidden) mensaje(datos.ordenes.length ? "" : "Aún no hay órdenes de compra.");
  }

  async function listarStock(numero, vigente) {
    const parametros = new URLSearchParams({ ...filtroStock, pagina: numero });
    const datos = await api(`inventario/?${parametros}`);
    if (!vigente()) return;
    paginaStock = datos.pagina;
    $("existencias").replaceChildren();
    for (const item of datos.existencias) {
      fila($("existencias"), [`${item.codigo} · ${item.producto}`, item.lote, item.vencimiento,
        item.ubicacionTexto, item.cantidad]);
    }
    paginador("stock", datos);
    if (!$("inventario").hidden) mensaje(datos.existencias.length ? "" : "No se encontraron existencias.");
  }

  function mostrarOrden(datos) {
    orden = datos;
    recibir.hidden = true;
    $("detalle-orden").hidden = false;
    $("titulo-orden").textContent = `OC-${datos.id} · ${datos.proveedor}`;
    $("estado-orden").textContent = datos.estadoTexto;
    $("lineas-orden").replaceChildren();
    for (const item of datos.lineas) {
      fila($("lineas-orden"), [`${item.codigo} · ${item.nombre}`, item.solicitada, item.recibida, item.pendiente]);
    }
    $("recepciones").replaceChildren();
    for (const item of datos.recepciones || []) {
      const li = document.createElement("li");
      li.textContent = `Recepción ${item.referencia} · ${new Date(item.fecha).toLocaleDateString("es-CL")}`;
      $("recepciones").append(li);
    }
    $("nueva-recepcion").hidden = !permisos.recibirOrden || !["pendiente", "parcial"].includes(datos.estado);
    $("ver-lote").hidden = !permisos.inventario || ultimoLote?.orden !== datos.id;
    $("anular-orden").hidden = !permisos.anularOrden || datos.estado !== "pendiente";
  }

  function agregarPartida() {
    if (partidas.children.length >= 20) return;
    const nueva = $("plantilla-partida").content.firstElementChild.cloneNode(true);
    nueva.querySelector(".quitar").addEventListener("click", () => {
      if (partidas.children.length > 1) nueva.remove();
    });
    partidas.append(nueva);
  }

  $("ir-compras").addEventListener("click", ejecutar($("ir-compras"), async (vigente) => {
    mostrarModulo("compras");
    await listarOrdenes(1, vigente);
    if (vigente() && orden) {
      const seleccion = orden;
      const actual = await api(`compras/ordenes/${seleccion.id}/`);
      if (vigente() && orden === seleccion) mostrarOrden(actual);
    }
  }));
  $("ir-inventario").addEventListener("click", ejecutar($("ir-inventario"), async (vigente) => {
    mostrarModulo("inventario");
    await listarStock(1, vigente);
  }));
  $("nueva-orden").addEventListener("click", ejecutar($("nueva-orden"), async (vigente) => {
    const datos = await api("compras/ordenes/nueva/");
    if (!vigente()) return;
    crear.reset();
    tokenOrden = datos.token;
    const campo = crear.elements.namedItem("proveedor");
    campo.replaceChildren(new Option("Selecciona un proveedor", ""));
    (datos.proveedores || []).forEach((p) => campo.add(new Option(`${p.codigo} · ${p.nombre}`, p.id)));
    partidas.replaceChildren();
    agregarPartida();
    crear.hidden = false;
    if (!datos.proveedores.length) mensaje("No hay proveedores activos.");
  }));
  $("agregar-partida").addEventListener("click", agregarPartida);
  $("cancelar-orden").addEventListener("click", () => { crear.hidden = true; });
  crear.addEventListener("submit", ejecutar(crear.querySelector("[type=submit]"), async (vigente) => {
    const datos = new URLSearchParams({
      token: tokenOrden,
      proveedor: crear.elements.namedItem("proveedor").value,
      observaciones: crear.elements.namedItem("observaciones").value,
    });
    const lineas = Array.from(partidas.children, (grupo) =>
      Object.fromEntries(Array.from(grupo.querySelectorAll("input"), (campo) => [campo.name, campo.value.trim()])));
    const actual = await api("compras/ordenes/nueva/", "POST", convertirPartidas(datos, "lineas", lineas));
    if (!vigente()) return;
    crear.hidden = true;
    mostrarOrden(actual);
    await listarOrdenes(1, vigente);
    if (vigente()) mensaje(`Orden OC-${actual.id} creada. El inventario se actualiza al recibir los productos.`);
  }));
  $("nueva-recepcion").addEventListener("click", ejecutar($("nueva-recepcion"), async (vigente) => {
    const seleccion = orden;
    const datos = await api(`compras/ordenes/${seleccion.id}/recibir/`);
    if (!vigente() || orden !== seleccion) return;
    tokenRecepcion = datos.token;
    recibir.reset();
    const campo = recibir.elements.namedItem("linea");
    campo.replaceChildren();
    for (const item of orden.lineas.filter((l) => l.pendiente > 0)) {
      campo.add(new Option(`${item.nombre} · ${item.pendiente} pendientes`, item.id));
    }
    recibir.hidden = false;
  }));
  $("cancelar-recepcion").addEventListener("click", () => { recibir.hidden = true; });
  $("anular-orden").addEventListener("click", () => abrirOperacion(`anular/${orden.id}`));
  recibir.addEventListener("submit", ejecutar(recibir.querySelector("[type=submit]"), async (vigente) => {
    const seleccion = orden;
    const campos = Object.fromEntries(enviarFormulario(recibir));
    const { referencia, ...partida } = campos;
    const datos = new URLSearchParams({ referencia, token: tokenRecepcion });
    const actual = await api(`compras/ordenes/${seleccion.id}/recibir/`, "POST",
      convertirPartidas(datos, "partidas", [partida]));
    if (!vigente()) return;
    const lote = partida.codigo.trim().toUpperCase();
    const producto = actual.lineas.find((l) => String(l.id) === partida.linea).codigo;
    ultimoLote = { orden: actual.id, lote, producto, ubicacion: partida.ubicacion };
    if (orden === seleccion) mostrarOrden(actual);
    await listarOrdenes(paginaCompras, vigente);
    if (vigente()) mensaje(`Recepción registrada para OC-${actual.id}. Existencias actualizadas.`);
  }));
  $("ver-lote").addEventListener("click", ejecutar($("ver-lote"), async (vigente) => {
    const { lote, producto, ubicacion } = ultimoLote;
    filtroStock = { lote, producto, ubicacion };
    buscarStock.elements.namedItem("q").value = lote;
    buscarStock.elements.namedItem("ubicacion").value = ubicacion;
    mostrarModulo("inventario");
    await listarStock(1, vigente);
  }));
  buscarStock.addEventListener("submit", ejecutar(buscarStock.querySelector("button"), async (vigente) => {
    filtroStock = Object.fromEntries(enviarFormulario(buscarStock));
    await listarStock(1, vigente);
  }));
  for (const [modulo, listar, numero] of [
    ["compras", listarOrdenes, () => paginaCompras], ["stock", listarStock, () => paginaStock],
  ]) {
    for (const [direccion, cambio] of [["anterior", -1], ["siguiente", 1]]) {
      const control = $(`${modulo}-${direccion}`);
      control.addEventListener("click", async () => {
        const actual = sesion;
        try {
          await listar(numero() + cambio, () => actual === sesion);
        } catch (error) {
          if (actual === sesion) await mostrarError(error);
        }
      });
    }
  }

  return (actuales = {}) => {
    sesion += 1;
    permisos = actuales;
    orden = ultimoLote = tokenOrden = tokenRecepcion = null;
    filtroStock = {};
    buscarStock.reset();
    crear.hidden = recibir.hidden = $("detalle-orden").hidden = true;
    $("ordenes").replaceChildren();
    $("existencias").replaceChildren();
    $("ir-compras").hidden = !permisos.compras;
    $("ir-inventario").hidden = !permisos.inventario;
    $("nueva-orden").hidden = !permisos.crearOrden;
  };
}
