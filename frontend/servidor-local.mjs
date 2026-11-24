import http from "node:http";
import { createReadStream } from "node:fs";

const host = "127.0.0.1";
const port = 8015;
const archivos = new Map([
  ["/", ["index.html", "text/html; charset=utf-8"]],
  ["/estilos.css", ["estilos.css", "text/css; charset=utf-8"]],
  // Estilos y tema compartidos: una sola fuente en el backend, sin copias en esta carpeta.
  ["/tema-oscuro.css", ["../backend/static/css/tema-oscuro.css", "text/css; charset=utf-8"]],
  ["/tema.js", ["../backend/static/js/tema.js", "text/javascript; charset=utf-8"]],
  ["/tema-farmacia.css", ["../backend/static/css/estilos.css", "text/css; charset=utf-8"]],
  ["/app.js", ["app.js", "text/javascript; charset=utf-8"]],
  ["/compras.js", ["compras.js", "text/javascript; charset=utf-8"]],
  ["/operaciones.js", ["operaciones.js", "text/javascript; charset=utf-8"]],
]);
const rutasApi = new Set([
  "/api/v1/sesion/", "/api/v1/sesion/ingresar/", "/api/v1/sesion/salir/", "/api/v1/productos/",
  "/api/v1/compras/ordenes/", "/api/v1/compras/ordenes/nueva/", "/api/v1/inventario/",
]);

http.createServer((req, res) => {
  if (req.headers.host !== `${host}:${port}`) {
    res.writeHead(400).end();
    return;
  }
  const ruta = req.url.split("?")[0];
  const orden = /^\/api\/v1\/compras\/ordenes\/\d+\/(recibir\/)?$/.test(ruta);
  const operacion = /^\/api\/v1\/operaciones\/[a-z-]+\/(\d+\/)?$/.test(ruta);
  if (rutasApi.has(ruta) || orden || operacion) {
    const headers = {};
    for (const campo of ["host", "cookie", "origin", "referer", "content-type", "content-length", "x-csrftoken", "accept"]) {
      if (req.headers[campo]) headers[campo] = req.headers[campo];
    }
    const backend = http.request({ host, port: 8014, path: req.url, method: req.method, headers }, (r) => {
      res.writeHead(r.statusCode, r.headers);
      r.pipe(res);
    });
    backend.setTimeout(8000, () => backend.destroy());
    backend.on("error", () => {
      if (res.headersSent) return res.destroy();
      res.writeHead(502, { "Content-Type": "application/json", "Cache-Control": "no-store" });
      res.end(JSON.stringify({ error: "El backend local no está disponible." }));
    });
    req.on("aborted", () => backend.destroy());
    req.pipe(backend);
    return;
  }
  const archivo = archivos.get(ruta);
  if (!archivo || req.method !== "GET") {
    res.writeHead(404).end();
    return;
  }
  const stream = createReadStream(new URL(archivo[0], import.meta.url));
  stream.once("error", () => res.writeHead(500).end());
  stream.once("open", () => {
    res.writeHead(200, {
      "Content-Type": archivo[1], "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
      "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; form-action 'self'",
    });
    stream.pipe(res);
  });
}).listen(port, host, () => console.log(`Frontend local en http://${host}:${port}/`));
