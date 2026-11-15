/* ============================================================================
   ARCHIVO: modulos/m9_sitio/pruebas/prueba_identificar.js
   MODULO: m9_sitio (Lote D)
   ROL: Comprueba la lógica pura de «Identificar»: WCS contra astropy, conversión
        lienzo <-> píxel, detección cercana y lectura de SkyBoT.
   LEE: modulos/m9_sitio/identificar_logica.js y pruebas/wcs_referencia.json (astropy).
   PRODUCE: El veredicto de `node --test`.
   VERIFICACION: `node --test modulos/m9_sitio/pruebas/prueba_identificar.js` pasa.
   NOTA: La respuesta de SkyBoT de estas pruebas copia el formato real del servicio
         (consultado el 2026-11-14) con valores de ejemplo.
   ========================================================================== */
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const I = require("../identificar_logica.js");

const REFERENCIA = JSON.parse(fs.readFileSync(path.join(__dirname, "wcs_referencia.json"), "utf8"));
const META = { tamano_pixeles: { ancho: 600, alto: 600 }, escala_segarc_por_pixel: 6.15,
  wcs: REFERENCIA.casos[0].wcs };

test("la proyección TAN coincide con astropy a menos de 1 mas en todos los casos", () => {
  for (const caso of REFERENCIA.casos) {
    for (const p of caso.puntos) {
      const r = I.pixelACielo(caso.wcs, p.x, p.y);
      const sep = I.separacionSegarc(r.ra_grados, r.dec_grados, p.ra_grados, p.dec_grados);
      assert.ok(sep < 0.001, `${caso.nombre} (${p.x}, ${p.y}): ${sep}″`);
    }
  }
});

test("sin WCS TAN no hay coordenadas", () => {
  assert.equal(I.tieneWcs({}), false);
  assert.equal(I.tieneWcs({ wcs: { proyeccion: "SIN", cd: [[1, 0], [0, 1]] } }), false);
  assert.equal(I.tieneWcs(META), true);
});

test("lienzo y rejilla son inversos y la y se invierte", () => {
  const p = I.lienzoAPixel(META, 0, 600);           // esquina inferior izquierda del lienzo
  assert.deepEqual(p, { x: -0.5, y: -0.5 });
  const q = I.lienzoAPixel(META, 300, 300);
  assert.deepEqual(q, { x: 299.5, y: 299.5 });
  const l = I.pixelALienzo(META, 120.25, 40.75);
  const v = I.lienzoAPixel(META, l.cx, l.cy);
  assert.ok(Math.abs(v.x - 120.25) < 1e-9 && Math.abs(v.y - 40.75) < 1e-9);
  const grande = { ...META, tamano_pixeles: { ancho: 1200, alto: 300 } };
  assert.deepEqual(I.lienzoAPixel(grande, 300, 300), { x: 599.5, y: 149.5 });
});

test("la separación angular es correcta en el ecuador, en el polo y al cruzar RA = 0", () => {
  assert.ok(Math.abs(I.separacionSegarc(10, 0, 10.001, 0) - 3.6) < 1e-6);
  assert.ok(Math.abs(I.separacionSegarc(359.9995, 0, 0.0005, 0) - 3.6) < 1e-6);
  assert.ok(I.separacionSegarc(0, 89.9999, 180, 89.9999) < 0.73);
});

test("formatos de coordenadas y fechas", () => {
  assert.equal(I.sexagesimal(150.0, true), "10h 00m 00.00s");
  assert.equal(I.sexagesimal(-2.5, false), "−02° 30′ 00.0″");
  assert.equal(I.mjdAJd(60000), 2460000.5);
  assert.equal(I.mjdAIso(60000.5), "2023-02-25T12:00:00Z");
});

test("el clic se pega a una detección solo si está a menos del radio", () => {
  const cands = [
    { id_candidato: "p001", posicion_a: { x: 100, y: 100 } },
    { id_candidato: "p002", posicion_a: { x: 103, y: 100 } },
    { id_candidato: "p003" },
  ];
  assert.equal(I.deteccionCercana(cands, 101, 100).id_candidato, "p001");
  assert.equal(I.deteccionCercana(cands, 102.6, 100).id_candidato, "p002");
  assert.equal(I.deteccionCercana(cands, 120, 100), null);
});

test("la URL de SkyBoT lleva la época en JD, el radio en grados y el observador", () => {
  const u = new URL(I.urlSkybot(150, 2, 60000, 36));
  assert.equal(u.hostname, "ssp.imcce.fr");
  assert.equal(u.searchParams.get("-ep"), "2460000.500000");
  assert.equal(u.searchParams.get("-rd"), "0.010000");
  assert.equal(u.searchParams.get("-loc"), "500");
  assert.equal(u.searchParams.get("-mime"), "json");
});

const SKYBOT = [
  { Num: "", Name: "2014 RR73", "RA (hms)": "09 59 51.6075", "DEC (dms)": "+02 00 50.171", Class: "MB>Outer",
    "VMag (mag)": 23.4, "Err (arcsec)": 0.245, "d (arcsec)": 135.4, "dRA (arcsec/h)": -25.56, "dDEC (arcsec/h)": 13.53,
    ssodnet: { ssocard: "https://ssp.imcce.fr/webservices/ssodnet/api/ssocard/2014_RR73" } },
  { Num: "1766", Name: "Slipher", "RA (hms)": "10 00 00.0000", "DEC (dms)": "+02 00 01.000", Class: "MB>Inner",
    "VMag (mag)": 16.1, "Err (arcsec)": 0.05, "d (arcsec)": 1.0, "dRA (arcsec/h)": 30, "dDEC (arcsec/h)": 0 },
  { Num: "", Name: "C/2025 A1", "RA (hms)": "09 59 59.5000", "DEC (dms)": "-02 00 00.000", Class: "Comet>LP" },
];

test("SkyBoT se lee, se ordena por separación y la clase se traduce", () => {
  const c = I.leerSkybot(SKYBOT, 150.0, 2.0);
  assert.deepEqual(c.map((x) => x.nombre), ["(1766) Slipher", "2014 RR73", "C/2025 A1"]);
  assert.ok(Math.abs(c[0].separacion_segarc - 1.0) < 0.01);
  assert.equal(c[0].designacion, "1766");
  assert.equal(c[0].clase_objeto, "asteroide");
  assert.equal(c[2].clase_objeto, "cometa");
  assert.equal(c[2].incertidumbre_segarc, null);
  assert.ok(Math.abs(c[0].movimiento_segarc_h - 30) < 1e-9);
  assert.deepEqual(I.leerSkybot(null, 150, 2), []); // 204: sin objetos
});

test("veredicto: una dentro es compatible, varias ambigua, ninguna sin coincidencia concluyente", () => {
  const una = I.clasificar(I.leerSkybot(SKYBOT, 150.0, 2.0), 6.15);
  assert.equal(una.veredicto, "coincidencia_compatible");
  assert.equal(una.coincidencias.filter((c) => c.dentro).length, 1);
  assert.ok(Math.abs(una.coincidencias[0].tolerancia_segarc - 3 * Math.hypot(3.075, 0.05)) < 1e-9);
  const ninguna = I.clasificar(I.leerSkybot(SKYBOT.slice(0, 1), 150.0, 2.0), 6.15);
  assert.equal(ninguna.veredicto, "sin_coincidencia_concluyente");
  const dos = [SKYBOT[1], { ...SKYBOT[1], Num: "9", Name: "Otro", "RA (hms)": "10 00 00.2000" }];
  assert.equal(I.clasificar(I.leerSkybot(dos, 150.0, 2.0), 6.15).veredicto, "coincidencia_ambigua");
  assert.match(una.criterio, /3·√/);
  assert.doesNotMatch(I.VEREDICTO.sin_coincidencia_concluyente, /Planeta X|nuevo/i);
});
