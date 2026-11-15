/* ============================================================================
   ARCHIVO: modulos/m9_sitio/pruebas/prueba_sitio.js
   MODULO: m9_sitio (Lote D)
   ROL: Comprueba que los datos que consume la web tienen la forma del contrato.
   LEE: contratos/ejemplos/campos.json y campo_ejemplo/{meta,candidatos,espectros}.json;
        opcionalmente datos/m7_publicacion/.
   PRODUCE: El veredicto de `node --test`.
   VERIFICACION: `node --test modulos/m9_sitio/pruebas/prueba_sitio.js` pasa.
   ========================================================================== */
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const RAIZ = path.resolve(__dirname, "..", "..", "..");
const EJEMPLOS = path.join(RAIZ, "contratos", "ejemplos");
const PUBLICADO = path.join(RAIZ, "datos", "m7_publicacion");

const CLASES = ["candidata", "no_concluyente"];
const ESTADOS = ["conocido", "sin_identificar", "artefacto_descartado"];
const TIPOS = ["asteroide_rocoso", "asteroide_oscuro", "cometa", "enana_marron", "indeterminado", null];

function leer(...partes) {
  return JSON.parse(fs.readFileSync(path.join(...partes), "utf8"));
}

/** Devuelve la lista de campos a comprobar: los ejemplos y, si existe, lo publicado. */
function conjuntos() {
  const lista = [
    {
      nombre: "ejemplos de los contratos",
      campos: leer(EJEMPLOS, "campos.json"),
      dir: (campo) => path.join(EJEMPLOS, campo),
    },
  ];
  if (fs.existsSync(path.join(PUBLICADO, "campos.json"))) {
    lista.push({
      nombre: "datos publicados",
      campos: leer(PUBLICADO, "campos.json"),
      dir: (campo) => path.join(PUBLICADO, campo),
    });
  }
  return lista;
}

for (const conjunto of conjuntos()) {
  test(`${conjunto.nombre}: campos.json declara ruta y número de candidatos`, () => {
    assert.equal(conjunto.campos.version_contrato, "1");
    assert.ok(Array.isArray(conjunto.campos.campos) && conjunto.campos.campos.length > 0);
    for (const campo of conjunto.campos.campos) {
      assert.match(campo.campo, /^[a-z0-9_]+$/);
      assert.equal(campo.ruta, campo.campo);
      assert.ok(Number.isInteger(campo.numero_candidatos));
      assert.ok(campo.numero_candidatos >= 0);
    }
  });

  test(`${conjunto.nombre}: meta.json trae centro, épocas y nombres de imagen`, () => {
    for (const campo of conjunto.campos.campos) {
      const meta = leer(conjunto.dir(campo.ruta), "meta.json");
      assert.equal(meta.campo, campo.campo);
      assert.equal(typeof meta.centro.ra_grados, "number");
      assert.equal(typeof meta.centro.dec_grados, "number");
      assert.ok(meta.escala_segarc_por_pixel > 0);
      assert.ok(meta.horas_entre_a_b > 0);
      for (const papel of ["epoca_a", "epoca_b", "plantilla"]) {
        assert.ok(meta.epocas[papel].mjd > 0, `${papel}.mjd`);
        assert.ok(meta.epocas[papel].id_exposicion.length > 0, `${papel}.id_exposicion`);
      }
      assert.equal(meta.imagenes.epoca_a, "epoca_a.png");
      assert.equal(meta.imagenes.epoca_b, "epoca_b.png");
      assert.equal(meta.imagenes.diferencia, "diferencia.png");
    }
  });

  test(`${conjunto.nombre}: cada candidato tiene posiciones A y B completas`, () => {
    for (const campo of conjunto.campos.campos) {
      const doc = leer(conjunto.dir(campo.ruta), "candidatos.json");
      assert.equal(doc.campo, campo.campo);
      assert.equal(doc.candidatos.length, campo.numero_candidatos);
      for (const cand of doc.candidatos) {
        assert.match(cand.id_candidato, /^p[0-9]{3}$/);
        assert.ok(ESTADOS.includes(cand.estado), cand.estado);
        assert.ok(CLASES.includes(cand.clase_movimiento), cand.clase_movimiento);
        assert.ok(TIPOS.includes(cand.tipo), String(cand.tipo));
        for (const pos of ["posicion_a", "posicion_b"]) {
          const p = cand[pos];
          assert.equal(typeof p.x, "number", `${pos}.x`);
          assert.equal(typeof p.y, "number", `${pos}.y`);
          assert.equal(typeof p.mjd, "number", `${pos}.mjd`);
          assert.ok(p.ra_grados >= 0 && p.ra_grados <= 360, `${pos}.ra_grados`);
          assert.ok(p.dec_grados >= -90 && p.dec_grados <= 90, `${pos}.dec_grados`);
        }
        assert.ok(cand.velocidad_segarc_por_hora >= 0);
        assert.ok(cand.separacion_segarc >= 0);
      }
    }
  });

  test(`${conjunto.nombre}: cada espectro corresponde a un candidato con espectro`, () => {
    for (const campo of conjunto.campos.campos) {
      const cands = leer(conjunto.dir(campo.ruta), "candidatos.json").candidatos;
      const esps = leer(conjunto.dir(campo.ruta), "espectros.json").espectros;
      const conEspectro = new Set(cands.filter((c) => c.tiene_espectro).map((c) => c.id_candidato));
      const ids = new Set(esps.map((e) => e.id_pareja));

      assert.deepEqual([...ids].sort(), [...conEspectro].sort());
      for (const esp of esps) {
        assert.ok(["banda", "detector"].includes(esp.agrupacion));
        assert.ok(esp.puntos.length > 0);
        for (const punto of esp.puntos) {
          assert.ok(punto.longitud_onda_micras >= 0.75 && punto.longitud_onda_micras <= 5.0);
          // Con datos reales, el flujo de un objeto débil puede salir negativo por el ruido:
          // el contrato no le pone mínimo. Solo tiene que ser un número.
          assert.ok(Number.isFinite(punto.flujo_mjy));
          assert.ok(punto.error_mjy > 0);
          assert.ok(punto.mjd > 0);
          assert.ok(punto.detector >= 1 && punto.detector <= 6);
        }
        if (esp.temperatura_k !== null) {
          const wien = 2898 / esp.temperatura_k;
          assert.ok(Math.abs(wien - esp.pico_wien_micras) < 0.02, "pico de Wien coherente");
        }
      }
    }
  });
}

test("m9_sitio no escribe datos: solo hay lectores en su código", () => {
  const dir = path.join(RAIZ, "modulos", "m9_sitio");
  const archivos = fs.readdirSync(dir).filter((f) => f.endsWith(".js"));
  assert.ok(archivos.length >= 8);
  for (const archivo of archivos) {
    const texto = fs.readFileSync(path.join(dir, archivo), "utf8");
    assert.ok(!/fetch\([^)]*,\s*\{\s*method:\s*["'](POST|PUT|DELETE)/i.test(texto), archivo);
  }
});
