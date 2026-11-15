/* ============================================================================
   ARCHIVO: modulos/m9_sitio/pruebas/prueba_catalogo.js
   MODULO: m9_sitio (Lote D)
   ROL: Comprueba la lógica pura del catálogo navegable.
   LEE: modulos/m9_sitio/catalogo_logica.js y contratos/ejemplos/catalogo.json.
   PRODUCE: El veredicto de `node --test`.
   VERIFICACION: `node --test modulos/m9_sitio/pruebas/prueba_catalogo.js` pasa.
   NOTA: Los objetos de estas pruebas son inventados.
   ========================================================================== */
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const C = require("../catalogo_logica.js");

const RAIZ = path.resolve(__dirname, "..", "..", "..");

const objeto = (id, nombre, extra = {}) => ({
  id_objeto: id, campo: id.split("/")[0], id_candidato: id.split("/")[1], nombre, designacion: null,
  estado_identificacion: "conocido", clasificacion: "desconocida", fuente_clasificacion: null,
  datos: { imagen: true, trayectoria: true, espectro: "sintetico" }, n_puntos_espectrales: 10,
  tipo_espectral: "asteroide_rocoso", relacionados: { misma_clasificacion: [], espectros_similares: [] }, ...extra,
});

const OBJETOS = [
  objeto("a/p001", "(1766) Slipher", { designacion: "1766", clasificacion: "asteroide", fuente_clasificacion: "m5" }),
  objeto("a/p002", "Sin identificar (a/p002)", { estado_identificacion: "sin_identificar", datos: { imagen: true, trayectoria: true, espectro: "ninguno" } }),
  objeto("b/p001", "3I/ATLAS", { designacion: "3I", clasificacion: "cometa", fuente_clasificacion: "m5" }),
  objeto("b/p002", "Núcleo de prueba", { clasificacion: "asteroide", datos: { imagen: false, trayectoria: true, espectro: "pendiente" } }),
];

test("la búsqueda ignora mayúsculas y acentos; el id solo cuenta si se escribe con «/»", () => {
  assert.deepEqual(C.filtrar(OBJETOS, { texto: "SLIPHER" }).map((o) => o.id_objeto), ["a/p001"]);
  assert.deepEqual(C.filtrar(OBJETOS, { texto: "nucleo" }).map((o) => o.id_objeto), ["b/p002"]);
  assert.deepEqual(C.filtrar(OBJETOS, { texto: "3i" }).map((o) => o.id_objeto), ["b/p001"]);
  assert.deepEqual(C.filtrar(OBJETOS, { texto: "b/p00" }).length, 2);
  assert.equal(C.filtrar(OBJETOS, {}).length, 4);
  // el nombre del campo no basta: «a» no trae a/p002 por su id
  assert.deepEqual(C.filtrar([objeto("slipher/p002", "Sin nombre")], { texto: "slipher" }), []);
  // el nombre generado de un objeto sin identificar no cuenta como nombre
  const sinId = objeto("slipher/p002", "Sin identificar (slipher/p002)", { estado_identificacion: "sin_identificar" });
  assert.deepEqual(C.filtrar([sinId], { texto: "slipher" }), []);
  assert.equal(C.filtrar([sinId], { texto: "slipher/p002" }).length, 1);
});

test("los filtros por clase, identificación y espectro se combinan", () => {
  assert.deepEqual(C.filtrar(OBJETOS, { clasificacion: "asteroide" }).map((o) => o.id_objeto), ["a/p001", "b/p002"]);
  assert.deepEqual(C.filtrar(OBJETOS, { estado: "sin_identificar" }).map((o) => o.id_objeto), ["a/p002"]);
  assert.deepEqual(C.filtrar(OBJETOS, { soloConEspectro: true }).map((o) => o.id_objeto), ["a/p001", "b/p001"]);
  assert.deepEqual(C.filtrar(OBJETOS, { clasificacion: "asteroide", soloConEspectro: true }).map((o) => o.id_objeto), ["a/p001"]);
});

test("un espectro pendiente o inexistente no cuenta como disponible; uno sin origen declarado sí, sin decir que es real", () => {
  assert.equal(C.tieneEspectro(OBJETOS[1]), false);
  assert.equal(C.tieneEspectro(OBJETOS[3]), false);
  const sinOrigen = objeto("c/p001", "X", { datos: { imagen: true, trayectoria: true, espectro: "no_declarado" } });
  assert.equal(C.tieneEspectro(sinOrigen), true);
  assert.doesNotMatch(C.ESPECTRO.no_declarado, /real/i);
});

test("las clases del filtro salen de los objetos, en orden fijo", () => {
  assert.deepEqual(C.clasesPresentes(OBJETOS), ["asteroide", "cometa", "desconocida"]);
});

test("el título añade la designación solo si el nombre no la lleva ya", () => {
  assert.equal(C.titulo(OBJETOS[0]), "(1766) Slipher");
  assert.equal(C.titulo(objeto("v/p001", "Vesta", { designacion: "4" })), "Vesta — 4");
});

test("la clasificación cita su fuente y la clase desconocida no inventa una", () => {
  assert.equal(C.textoClasificacion(OBJETOS[0]), "Asteroide · fuente: m5");
  assert.equal(C.textoClasificacion(OBJETOS[1]), "Sin clase catalogada");
});

test("el tipo espectral se redacta como compatibilidad y solo con espectro", () => {
  assert.match(C.textoTipoEspectral(OBJETOS[0]), /Más compatible con la plantilla «roca con silicatos» entre las evaluadas/);
  assert.equal(C.textoTipoEspectral(OBJETOS[1]), null);
  assert.match(C.textoTipoEspectral(objeto("c/p002", "Y", { tipo_espectral: "indeterminado" })), /Ninguna plantilla/);
});

test("relacionados separa misma clase y similares, y marca la forma compatible por el umbral", () => {
  const base = objeto("a/p001", "A", { relacionados: {
    misma_clasificacion: ["b/p002", "z/p999"],
    espectros_similares: [
      { id_objeto: "b/p001", metrica: "chi2_reducido_entre_formas", valor: 1.2, rango_comun_micras: [1, 4], normalizacion: "mediana", n_puntos: 9 },
      { id_objeto: "a/p002", metrica: "chi2_reducido_entre_formas", valor: 7.5, rango_comun_micras: [1, 4], normalizacion: "mediana", n_puntos: 9 },
    ] } });
  const porId = new Map(OBJETOS.map((o) => [o.id_objeto, o]));
  const r = C.relacionados(base, porId);
  assert.deepEqual(r.misma.map((o) => o.id_objeto), ["b/p002"]);  // z/p999 no está en el catálogo
  assert.deepEqual(r.similares.map((s) => [s.objeto.id_objeto, s.compatible]), [["b/p001", true], ["a/p002", false]]);
});

test("el ejemplo del contrato se puede filtrar sin errores", () => {
  const ej = JSON.parse(fs.readFileSync(path.join(RAIZ, "contratos", "ejemplos", "catalogo.json"), "utf8"));
  const lista = C.filtrar(ej.objetos, { soloConEspectro: true });
  assert.equal(lista.length, 1);
  assert.equal(C.textoClasificacion(lista[0]), "Sin clase catalogada");
});
