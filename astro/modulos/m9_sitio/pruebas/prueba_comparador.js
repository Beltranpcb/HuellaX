/* ============================================================================
   ARCHIVO: modulos/m9_sitio/pruebas/prueba_comparador.js
   MODULO: m9_sitio (Lote D)
   ROL: Comprueba la lógica pura del comparador de espectros.
   LEE: modulos/m9_sitio/comparador_logica.js y los ejemplos de contratos/.
   PRODUCE: El veredicto de `node --test`.
   VERIFICACION: `node --test modulos/m9_sitio/pruebas/prueba_comparador.js` pasa.
   NOTA: Los espectros de estas pruebas son sintéticos y no representan mediciones.
   ========================================================================== */
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const L = require("../comparador_logica.js");

const RAIZ = path.resolve(__dirname, "..", "..", "..");
const EJEMPLO = path.join(RAIZ, "contratos", "ejemplos", "campo_ejemplo");
const leer = (nombre) => JSON.parse(fs.readFileSync(path.join(EJEMPLO, nombre), "utf8"));

const punto = (lam, flujo, error = 0.1, detector = 1) => ({
  longitud_onda_micras: lam, flujo_mjy: flujo, error_mjy: error, mjd: 60900, detector,
});
const espectro = (id, puntos, extra = {}) => ({ id_pareja: id, agrupacion: "banda", puntos, ...extra });
const candidato = (id, nombre = null) => ({ id_candidato: id, nombre_objeto: nombre, estado: "sin_identificar" });

test("solo entran objetos con al menos dos puntos válidos", () => {
  const campos = [{
    campo: "c1",
    meta: { origen: "sintetico" },
    candidatos: { candidatos: [candidato("p001", "Uno"), candidato("p002"), candidato("p003")] },
    espectros: { espectros: [
      espectro("p001", [punto(1, 2), punto(2, 3)]),
      espectro("p002", [punto(1, 2)]),                       // un solo punto
      // p003 no tiene espectro
    ] },
  }];
  const { objetos, sinEspectro } = L.construirObjetos(campos);
  assert.deepEqual(objetos.map((o) => o.id_objeto), ["c1/p001"]);
  assert.equal(sinEspectro, 2);
});

test("los puntos inválidos se descartan y el resto se ordena por longitud de onda", () => {
  const e = espectro("p001", [
    punto(3, 1), punto(1, 1), punto(9, 1), punto(2, 1, 0), punto(2.5, NaN), punto(1.5, 1),
  ]);
  assert.deepEqual(L.puntosValidos(e).map((p) => p.longitud_onda_micras), [1, 1.5, 3]);
});

test("el origen sale del espectro, si no del campo, si no queda sin declarar", () => {
  const base = (esp, meta) => L.construirObjetos([{
    campo: "c", meta, candidatos: { candidatos: [candidato("p001")] },
    espectros: { espectros: [esp] },
  }]).objetos[0];
  const pts = [punto(1, 1), punto(2, 1)];
  assert.equal(base(espectro("p001", pts, { origen: "real" }), { origen: "sintetico" }).origen, "real");
  assert.equal(base(espectro("p001", pts), { origen: "sintetico" }).origen, "sintetico");
  const sin = base(espectro("p001", pts), {});
  assert.equal(sin.origen, null);
  assert.equal(L.etiquetaOrigen(sin.origen), "Origen no declarado");
});

test("un objeto sin nombre catalogado se llama Sin identificar, no se inventa nombre", () => {
  const o = L.construirObjetos([{
    campo: "c", meta: {}, candidatos: { candidatos: [candidato("p004")] },
    espectros: { espectros: [espectro("p004", [punto(1, 1), punto(2, 1)])] },
  }]).objetos[0];
  assert.equal(o.nombre, "Sin identificar (c/p004)");
});

test("normalizar en lambda0 deja el flujo de referencia en 1 y escala el error", () => {
  const pts = [punto(1, 2, 0.2), punto(2, 4, 0.4), punto(3, 8, 0.8)];
  const n = L.normalizar(pts, 2);
  assert.equal(n.factor, 4);
  assert.deepEqual(n.puntos.map((p) => p.flujo_mjy), [0.5, 1, 2]);
  assert.ok(Math.abs(n.puntos[1].error_mjy - 0.1) < 1e-12);
  assert.match(n.metodo, /2,00 ± 0,25 µm/);
  assert.equal(n.aviso, null);
});

test("sin puntos cerca de lambda0 usa la mediana y lo avisa", () => {
  const pts = [punto(1, 2), punto(1.2, 4), punto(4.5, 6)];
  const n = L.normalizar(pts, 3);
  assert.equal(n.factor, 4);
  assert.match(n.metodo, /mediana/);
  assert.match(n.aviso, /Sin puntos cerca de 3,00/);
});

test("no normaliza si el flujo de referencia no es positivo", () => {
  const n = L.normalizar([punto(1, -1), punto(2, -2)], 1);
  assert.equal(n.puntos, null);
  assert.match(n.aviso, /no se puede normalizar/);
});

test("rango común y espectros sin solape son incompatibles", () => {
  const a = { puntos: [punto(1, 1), punto(2, 1)], agrupacion: "banda", origen: "real", campo: "c" };
  const b = { puntos: [punto(3, 1), punto(4, 1)], agrupacion: "banda", origen: "real", campo: "c" };
  assert.equal(L.rangoComun(a.puntos, b.puntos), null);
  const c = L.evaluarCompatibilidad(a, b, "flujo");
  assert.equal(c.estado, "incompatible");
  assert.equal(c.rangoComun, null);
});

test("compatibilidad: avisa de resolución distinta, origen distinto y datos sintéticos", () => {
  const a = { puntos: [punto(1, 1), punto(3, 1)], agrupacion: "banda", origen: "real", campo: "c1" };
  const b = { puntos: [punto(1.2, 1), punto(4, 1)], agrupacion: "detector", origen: "sintetico", campo: "c2" };
  const c = L.evaluarCompatibilidad(a, b, "flujo");
  assert.equal(c.estado, "aviso");
  assert.deepEqual(c.rangoComun, [1.2, 3]);
  const texto = c.mensajes.join(" | ");
  assert.match(texto, /Resolución distinta/);
  assert.match(texto, /mismo origen/);
  assert.match(texto, /sintéticos/);
  assert.match(texto, /campos distintos/);
  // En modo normalizado no se avisa del flujo absoluto.
  const n = L.evaluarCompatibilidad(a, b, "normalizado").mensajes.join(" | ");
  assert.doesNotMatch(n, /sintéticos: el flujo/);
});

test("dos espectros iguales de un mismo campo son compatibles sin avisos", () => {
  const a = { puntos: [punto(1, 1), punto(4, 1)], agrupacion: "banda", origen: "real", campo: "c" };
  const c = L.evaluarCompatibilidad(a, { ...a }, "flujo");
  assert.equal(c.estado, "ok");
  assert.deepEqual(c.mensajes, []);
});

test("el CSV lleva unidad, origen y escapa los nombres con comas", () => {
  const csv = L.aCsv([{ nombre: 'Objeto, "X"', origen: "sintetico", puntos: [punto(1.5, 2.25, 0.1, 3)] }], "flujo");
  const filas = csv.trim().split("\n");
  assert.equal(filas.length, 2);
  assert.equal(filas[1], '"Objeto, ""X""",flujo,1.5,2.25,0.1,mJy,3,60900,sintetico');
  assert.match(L.aCsv([{ nombre: "a", origen: null, puntos: [punto(1, 1)] }], "normalizado"), /adimensional,1,60900,no_declarado/);
});

test("las advertencias del contrato se traducen a texto y las desconocidas se conservan", () => {
  const o = { advertencias: ["plantillas_sinteticas", "codigo_nuevo"] };
  const textos = L.avisosDe(o);
  assert.match(textos[0], /sintéticas/);
  assert.equal(textos[1], "codigo_nuevo");
});

test("con los ejemplos de los contratos hay un objeto con espectro y otro sin él", () => {
  const { objetos, sinEspectro } = L.construirObjetos([{
    campo: "campo_ejemplo", meta: leer("meta.json"), candidatos: leer("candidatos.json"), espectros: leer("espectros.json"),
  }]);
  assert.equal(objetos.length, 1);
  assert.equal(sinEspectro, 1);
  assert.equal(objetos[0].id_objeto, "campo_ejemplo/p001");
  assert.equal(objetos[0].origen, "sintetico");
  assert.ok(L.avisosDe(objetos[0]).length >= 1);
});

// ------------------------------------------------------- objeto frente a plantillas
const ajuste = (tipo, chi2, gl = 7, extra = {}) => ({
  tipo, chi2_reducido: chi2, grados_libertad: gl, n_puntos: gl + 1, escala: 2, origen_plantilla: "sintetica", ...extra,
});
const objetoConAjustes = (tipo, ajustes) => ({ tipo, ajustes, advertencias: [], puntos: [] });
const PLANTILLAS = [{ tipo: "cometa", etiqueta_publica: "Hielo y CO2", longitud_onda_micras: [1, 2, 3], flujo_normalizado: [1, 2, 4] }];

test("los ajustes se ordenan por chi2 y se descartan los que no tienen grados de libertad", () => {
  const o = objetoConAjustes("cometa", [ajuste("asteroide_rocoso", 8), ajuste("cometa", 1.1), { tipo: "enana_marron", chi2_reducido: 0.5 }]);
  assert.deepEqual(L.ajustesOrdenados(o).map((a) => a.tipo), ["cometa", "asteroide_rocoso"]);
});

test("el resumen dice «más compatible» entre las evaluadas y no afirma que el objeto sea de ese tipo", () => {
  const r = L.resumenPlantillas(objetoConAjustes("cometa", [ajuste("cometa", 1.1), ajuste("asteroide_rocoso", 8)]), PLANTILLAS);
  assert.equal(r.nivel, "compatible");
  assert.match(r.texto, /Más compatible con la plantilla «Hielo y CO2» entre las 2 evaluadas/);
  assert.match(r.texto, /1,10, 7 grados de libertad, 8 puntos/);
  assert.match(r.texto, /sintética/);
  assert.doesNotMatch(r.texto, /el objeto es|es un (asteroide|cometa)|es una enana/i);
});

test("si m6 dejó el tipo indeterminado, la web no elige ninguna plantilla", () => {
  const r = L.resumenPlantillas(objetoConAjustes("indeterminado", [ajuste("cometa", 9), ajuste("asteroide_rocoso", 12)]), PLANTILLAS);
  assert.equal(r.nivel, "indeterminado");
  assert.equal(r.mejor, null);
  assert.match(r.texto, /Ninguna de las 2 plantillas/);
});

test("sin grados de libertad no se muestra ninguna métrica", () => {
  const r = L.resumenPlantillas(objetoConAjustes("cometa", [{ tipo: "cometa", chi2_reducido: 1.1 }]), PLANTILLAS);
  assert.equal(r.nivel, "sin_datos");
  assert.deepEqual(r.ajustes, []);
  assert.match(r.texto, /no se muestra ninguna métrica/);
});

test("una plantilla de bibliografía no se anuncia como sintética", () => {
  const a = ajuste("cometa", 1.1, 7, { origen_plantilla: "bibliografia" });
  assert.doesNotMatch(L.resumenPlantillas(objetoConAjustes("cometa", [a]), PLANTILLAS).texto, /sintética/);
});

test("la curva escalada multiplica por la escala del ajuste y respeta el rango", () => {
  const c = L.curvaEscalada(PLANTILLAS[0], 2, 1.5, 3);
  assert.deepEqual(c, [{ x: 2, y: 4 }, { x: 3, y: 8 }]);
  assert.deepEqual(L.curvaEscalada(PLANTILLAS[0], undefined, 1, 3), []);   // sin escala no se dibuja
  assert.deepEqual(L.curvaEscalada(null, 2, 1, 3), []);
  assert.deepEqual(L.curvaEscalada(PLANTILLAS[0], -1, 1, 3), []);
});

test("construirObjetos conserva el tipo y los ajustes del contrato", () => {
  const { objetos } = L.construirObjetos([{
    campo: "c", meta: {}, candidatos: { candidatos: [candidato("p001")] },
    espectros: { espectros: [espectro("p001", [punto(1, 1), punto(2, 1)], { tipo: "cometa", ajustes_plantilla: [ajuste("cometa", 1)] })] },
  }]);
  assert.equal(objetos[0].tipo, "cometa");
  assert.equal(objetos[0].ajustes.length, 1);
});
