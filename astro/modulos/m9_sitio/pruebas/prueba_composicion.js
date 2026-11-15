/* ============================================================================
   ARCHIVO: modulos/m9_sitio/pruebas/prueba_composicion.js
   MODULO: m9_sitio (Lote D)
   ROL: Comprueba la lógica pura de la sección «Composición espectral».
   LEE: modulos/m9_sitio/composicion_logica.js y contratos/ejemplos/campo_ejemplo/espectros.json.
   PRODUCE: El veredicto de `node --test`.
   VERIFICACION: `node --test modulos/m9_sitio/pruebas/prueba_composicion.js` pasa.
   NOTA: Las composiciones de estas pruebas son inventadas.
   ========================================================================== */
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const K = require("../composicion_logica.js");

const RAIZ = path.resolve(__dirname, "..", "..", "..");

const mol = (formula, estado, valor, extra = {}) => ({
  molecula: { H2O: "agua", CH4: "metano", CO2: "dioxido_de_carbono", CO: "monoxido_de_carbono", NH3: "amoniaco" }[formula],
  formula, banda_micras: [3.2, 3.45], estado, rasgo: valor === null ? null : valor < 0 ? "absorcion" : "emision",
  metrica: valor === null ? null : { nombre: "significancia_sigma", valor, incertidumbre: null, grados_libertad: 1 },
  explicacion: "x", ambigua_con: [], referencia: "ref", resolucion_espectral: 35, advertencias: [], ...extra,
});
const punto = (l) => ({ longitud_onda_micras: l, flujo_mjy: 1, error_mjy: 0.1 });
const espectro = (moleculas, puntos = [punto(1), punto(2)]) => ({
  puntos, composicion: { version_metodo: "1.0", continuo: "local", origen_referencias: "bibliografia", moleculas },
});

test("la sección solo se muestra con espectro utilizable y composición publicada", () => {
  assert.equal(K.debeMostrarse(null), false);
  assert.equal(K.debeMostrarse({ puntos: [punto(1), punto(2)] }), false);              // sin composición
  assert.equal(K.debeMostrarse(espectro([])), false);                                   // composición vacía
  assert.equal(K.debeMostrarse(espectro([mol("CH4", "sin_rasgo", 0.3)], [punto(1)])), false); // un solo punto
  assert.equal(K.debeMostrarse(espectro([mol("CH4", "sin_rasgo", 0.3)])), true);
});

test("las moléculas se ordenan por evidencia y luego por |S|", () => {
  const orden = K.ordenadas([
    mol("NH3", "datos_insuficientes", null), mol("H2O", "candidata", -3.2), mol("CO", "sin_rasgo", 0.4),
    mol("CH4", "detectada", -12.7), mol("CO2", "candidata", 4.1),
  ]).map((m) => m.formula);
  assert.deepEqual(orden, ["CH4", "CO2", "H2O", "CO", "NH3"]);
});

test("la métrica se escribe en sigmas con grados de libertad, y sin métrica lo dice", () => {
  assert.equal(K.textoMetrica(mol("CH4", "detectada", -12.69)), "S = −12,7 σ · 1 g.l.");
  assert.match(K.textoMetrica(mol("CO", "datos_insuficientes", null)), /Sin métrica/);
  assert.doesNotMatch(K.textoMetrica(mol("CH4", "detectada", -12.69)), /%/);
});

test("banda, resolución y sentido del rasgo en texto", () => {
  assert.equal(K.textoBanda(mol("CH4", "detectada", -5)), "3,20–3,45 µm · R ≈ 35");
  assert.equal(K.textoRasgo(mol("CH4", "detectada", -5)), "absorción");
  assert.equal(K.textoRasgo(mol("CO2", "detectada", 5)), "emisión");
  assert.equal(K.textoRasgo(mol("CO", "sin_rasgo", null)), null);
});

test("las alternativas físicas se traducen y las desconocidas se leen igual", () => {
  const m = mol("H2O", "candidata", -3.6, { ambigua_con: ["minerales_hidratados_OH", "otra_cosa_rara"] });
  assert.deepEqual(K.textoAlternativas(m), ["minerales hidratados (OH)", "otra cosa rara"]);
});

test("el resumen nunca cuenta una candidata como detección", () => {
  const sin = K.resumen(espectro([mol("H2O", "candidata", -3.6), mol("CO2", "candidata", 4.4), mol("CH4", "sin_rasgo", 0.1)]).composicion);
  assert.match(sin, /^Ninguna molécula cumple los criterios de detección/);
  assert.match(sin, /2 candidata · 1 sin rasgo/);
  const una = K.resumen(espectro([mol("CH4", "detectada", -12.7), mol("H2O", "sin_rasgo", 0.2)]).composicion);
  assert.match(una, /^Una molécula cumple todos los criterios/);
});

test("las regiones de referencia llevan fórmula, ventana y estado", () => {
  assert.deepEqual(K.regiones(espectro([mol("CH4", "detectada", -12.7)]).composicion),
    [{ formula: "CH4", bajo: 3.2, alto: 3.45, estado: "detectada" }]);
});

test("el ejemplo del contrato trae una composición que la web puede mostrar", () => {
  const doc = JSON.parse(fs.readFileSync(path.join(RAIZ, "contratos", "ejemplos", "campo_ejemplo", "espectros.json"), "utf8"));
  const e = doc.espectros[0];
  assert.equal(K.debeMostrarse(e), true);
  assert.ok(K.ordenadas(e.composicion.moleculas).every((m) => K.ESTADO[m.estado]));
});
