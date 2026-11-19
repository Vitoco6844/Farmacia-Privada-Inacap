import { iniciarCompras } from "./compras.js";
import { iniciarOperaciones } from "./operaciones.js";

const $ = (id) => document.getElementById(id);
const ingreso = $("ingreso");
const busqueda = $("busqueda");
const moneda = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP" });
let csrfToken;
let filtros = {};
let pagina = 1;
let paginas = 1;
let permisos = {};

function mensaje(texto = "") {
  $("mensaje").textContent = texto;
}

const accesos = [
  ["ventas", "↗", "Ventas"], ["caja", "▥", "Caja"], ["recetas", "▧", "Recetas y entregas"],
  ["controlados", "⊕", "Controlados"], ["convenios", "◇", "Convenios"],
  [["reporte-ventas", "reporte-inventario", "reporte-compras"], "▥", "Reportes"],
  ["pos", "＋", "Punto de venta"], ["indicadores", "▤", "Indicadores"],
  ["usuarios", "♙", "Usuarios y permisos", true], ["auditoria", "◷", "Auditoría", true],
  ["categorias", "▦", "Categorías", true], ["precios", "$", "Precios y descuentos", true],
  ["alertas", "◉", "Alertas por ubicación", true], ["condiciones", "✓", "Revisión de productos", true],
];

function configurarAccesos(pantallas = []) {
  const permitidas = new Set(pantallas.map((item) => item.ruta));
  $("accesos-trabajo").replaceChildren();
  $("accesos-administracion").replaceChildren();
  for (const [opciones, icono, etiqueta, admin] of accesos) {
    const ruta = [].concat(opciones).find((opcion) => permitidas.has(opcion));
    if (!ruta) continue;
    const boton = document.createElement("button");
    const marca = document.createElement("span");
    marca.setAttribute("aria-hidden", "true");
    marca.textContent = icono;
    boton.type = "button";
    boton.className = "nav-item";
    boton.dataset.ruta = ruta;
    boton.append(marca, " " + etiqueta);
    boton.addEventListener("click", () => operaciones.abrir(ruta));
    $(admin ? "accesos-administracion" : "accesos-trabajo").append(boton);
  }
  const tieneAdmin = Boolean($("accesos-administracion").children.length);
  $("titulo-administracion").hidden = $("accesos-administracion").hidden = !tieneAdmin;
}

async function api(ruta, method = "GET", body) {
  const headers = { Accept: "application/json" };
  if (method === "POST") headers["X-CSRFToken"] = csrfToken;
  const respuesta = await fetch(`/api/v1/${ruta}`, { method, body, headers });
  if (respuesta.ok && respuesta.headers.get("Content-Disposition")?.includes("attachment")) {
    const cabecera = respuesta.headers.get("Content-Disposition");
    const nombre = cabecera.match(/filename="([^"]+)"/i)?.[1] ?? "descarga";
    return { archivo: await respuesta.blob(), nombre };
  }
  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) {
    const error = new Error(datos.error || "No se pudo completar la solicitud.");
    error.status = respuesta.status;
    throw error;
  }
  return datos;
}

function mostrarSesion(datos) {
  csrfToken = datos.csrfToken;
  const activa = Boolean(datos.usuario);
  document.body.classList.toggle("login-body", !activa);
  $("usuario").textContent = datos.usuario || "";
  $("avatar").textContent = datos.usuario?.slice(0, 2).toUpperCase() || "";
  $("usuario-rol").textContent = (datos.roles || []).join(" · ");
  for (const id of ["barra-lateral", "barra-superior", "pie-pagina"]) $(id).hidden = !activa;
  $("cuenta").hidden = !activa;
  $("modulos").hidden = !activa;
  permisos = datos.permisos || {};
  prepararCompras(permisos);
  operaciones.configurar(datos.pantallas);
  configurarAccesos(datos.pantallas);
  $("nuevo-producto").hidden = !permisos.crearProducto;
  $("columna-editar").hidden = !permisos.editarProducto;
  $("campo-estado").hidden = !permisos.editarProducto;
  busqueda.elements.namedItem("estado").disabled = !permisos.editarProducto;
  mostrarModulo(activa ? "catalogo" : null);
  $("acceso").hidden = activa;
  ingreso.querySelector("button").disabled = false;
  if (!activa) $("filas").replaceChildren();
}

function mostrarModulo(modulo, ruta, titulo) {
  const secciones = { catalogo: "Productos", compras: "Compras", inventario: "Inventario", operaciones: "Operaciones" };
  for (const nombre of ["catalogo", "compras", "inventario", "operaciones"]) {
    $(nombre).hidden = nombre !== modulo;
    if (nombre === modulo) $(`ir-${nombre}`).setAttribute("aria-current", "page");
    else $(`ir-${nombre}`).removeAttribute("aria-current");
  }
  const acceso = Array.from(document.querySelectorAll(".nav-item[data-ruta]")).find((item) => item.dataset.ruta === ruta?.split("?")[0]);
  for (const item of document.querySelectorAll(".nav-item[data-ruta]")) item.removeAttribute("aria-current");
  if (acceso) {
    $("ir-operaciones").removeAttribute("aria-current");
    acceso.setAttribute("aria-current", "page");
  }
  $("seccion-actual").textContent = titulo || secciones[modulo] || "Productos";
  mensaje();
}

async function mostrarError(error) {
  if (error.status === 401) {
    mostrarSesion({ csrfToken, usuario: null });
    try {
      mostrarSesion(await api("sesion/"));
    } catch (recuperacion) {
      mensaje(recuperacion.message);
      return;
    }
  }
  mensaje(error.message);
}

const operaciones = iniciarOperaciones({ api, mensaje, mostrarError, mostrarModulo });
const prepararCompras = iniciarCompras({ api, mensaje, mostrarError, mostrarModulo, abrirOperacion: operaciones.abrir });
$("nuevo-producto").addEventListener("click", () => operaciones.abrir("producto-nuevo"));
$("ir-catalogo").addEventListener("click", () => {
  mostrarModulo("catalogo");
  cargarProductos(pagina);
});

function habilitarPaginas() {
  $("anterior").disabled = pagina <= 1;
  $("siguiente").disabled = pagina >= paginas;
}

function actualizarOpciones(id, valores, etiqueta) {
  const select = $(id);
  const valor = select.value;
  select.replaceChildren(new Option(etiqueta, ""), ...valores.map((v) => new Option(v, v)));
  select.value = valores.includes(valor) ? valor : "";
}

function textoElemento(tag, valor, clase) {
  const elemento = document.createElement(tag);
  elemento.textContent = valor;
  if (clase) elemento.className = clase;
  return elemento;
}

function filaProducto(producto) {
  const fila = document.createElement("tr");
  const codigo = fila.insertCell();
  codigo.className = "code";
  codigo.textContent = producto.codigo;
  const nombre = document.createElement("div");
  nombre.className = "product";
  const icono = textoElemento("span", producto.iniciales, `product-icon${producto.categoria === "Insumos" ? " blue" : ""}`);
  icono.setAttribute("aria-hidden", "true");
  const descripcion = document.createElement("div");
  descripcion.append(textoElemento("strong", producto.nombre), textoElemento("small", producto.presentacion));
  nombre.append(icono, descripcion);
  fila.insertCell().append(nombre);
  fila.insertCell().textContent = producto.categoria;
  fila.insertCell().append(textoElemento("span", producto.condicion,
    producto.condicion === "Venta directa" ? "condition" : "condition prescription"));
  const precio = fila.insertCell();
  precio.className = "price";
  precio.textContent = moneda.format(producto.precio);
  fila.insertCell().append(textoElemento("span", producto.activo ? "● Activo" : "● Inactivo",
    producto.activo ? "status" : "status inactive"));
  if (permisos.editarProducto) {
    const editar = textoElemento("button", "Editar", "button");
    editar.type = "button";
    editar.addEventListener("click", () => operaciones.abrir(`producto-editar/${producto.id}`));
    fila.insertCell().append(editar);
  }
  return fila;
}

async function cargarProductos(numero) {
  const buscar = busqueda.querySelector("button");
  buscar.disabled = $("anterior").disabled = $("siguiente").disabled = true;
  $("filas").replaceChildren();
  $("pagina").textContent = "";
  mensaje("Consultando productos…");
  try {
    const params = new URLSearchParams({ ...filtros, pagina: numero });
    const datos = await api(`productos/?${params}`);
    if ($("catalogo").hidden) return;
    pagina = datos.pagina;
    paginas = datos.paginas;
    for (const [id, key] of [["total-productos", "total"], ["total-activos", "activos"], ["total-receta", "receta"]]) {
      $(id).textContent = String(datos.resumen[key]).padStart(2, "0");
    }
    $("resultado-productos").textContent = datos.total;
    actualizarOpciones("filtro-categoria", datos.categorias, "Todas las categorías");
    actualizarOpciones("filtro-condicion", datos.condiciones, "Todas las condiciones");
    $("pagina").textContent = `Página ${pagina} de ${paginas}`;
    $("filas").append(...datos.productos.map(filaProducto));
    if (!datos.total) {
      const vacio = $("filas").insertRow().insertCell();
      vacio.colSpan = permisos.editarProducto ? 7 : 6;
      vacio.className = "empty";
      vacio.textContent = "No encontramos productos. Prueba con otro nombre o cambia los filtros.";
    }
    mensaje();
  } catch (error) {
    pagina = paginas = 1;
    await mostrarError(error);
  } finally {
    buscar.disabled = false;
    habilitarPaginas();
  }
}

ingreso.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const boton = ingreso.querySelector("button");
  boton.disabled = true;
  mensaje("Iniciando sesión…");
  try {
    const campos = new URLSearchParams(new FormData(ingreso));
    mostrarSesion(await api("sesion/ingresar/", "POST", campos));
    ingreso.reset();
    filtros = {};
    busqueda.reset();
    await cargarProductos(1);
  } catch (error) {
    mensaje(error.message);
  } finally {
    ingreso.elements.namedItem("password").value = "";
    boton.disabled = false;
  }
});

busqueda.addEventListener("submit", (evento) => {
  evento.preventDefault();
  if (busqueda.querySelector("button").disabled) return;
  filtros = Object.fromEntries(new FormData(busqueda));
  cargarProductos(1);
});
$("limpiar-catalogo").addEventListener("click", () => {
  if (busqueda.querySelector("button").disabled) return;
  busqueda.reset();
  filtros = {};
  cargarProductos(1);
});
$("anterior").addEventListener("click", () => cargarProductos(pagina - 1));
$("siguiente").addEventListener("click", () => cargarProductos(pagina + 1));
$("salir").addEventListener("click", async () => {
  $("salir").disabled = true;
  try {
    mostrarSesion(await api("sesion/salir/", "POST"));
    mensaje("Sesión cerrada.");
  } catch (error) {
    mensaje(error.message);
  } finally {
    $("salir").disabled = false;
  }
});

api("sesion/").then((datos) => {
  mostrarSesion(datos);
  return datos.usuario ? cargarProductos(1) : undefined;
}).catch((error) => mensaje(error.message));
