/* ============================================================================
   ARCHIVO: modulos/m9_sitio/identificar_logica.js
   MODULO: m9_sitio (Lote D)
   ROL: Lógica pura de «Identificar»: clic -> píxel -> RA/DEC con el WCS publicado,
        detección marcada más cercana y lectura de las efemérides de SkyBoT (IMCCE).
   LEE: Nada por sí mismo; recibe meta.json (con wcs), candidatos y respuestas de SkyBoT.
   PRODUCE: window.HXIdentificar (navegador) o module.exports (node --test).
   VERIFICACION: pruebas/prueba_identificar.js, contra valores de astropy (wcs_referencia.json).
   NOTA: Sin `meta.wcs` no se calcula ninguna coordenada: un píxel no es una posición en el cielo.
         Criterio de coincidencia (documentado en la interfaz): separación <= 3 * sqrt(s_obs^2 + s_efe^2),
         con s_obs = medio píxel y s_efe el error de la efeméride. Una sola dentro: compatible;
         varias: ambigua; ninguna: sin coincidencia concluyente. Nunca se da un porcentaje.
   ========================================================================== */
(function (raiz, fabrica) {
  if (typeof module === "object" && module.exports) module.exports = fabrica();
  else raiz.HXIdentificar = fabrica();
})(this, function () {
  "use strict";

  const LADO_LIENZO = 600;
  const RAD = Math.PI / 180;
  const RADIO_BUSQUEDA_SEGARC = 60;  // radio de la consulta a SkyBoT
  const SIGMAS_COINCIDENCIA = 3;
  const RADIO_SNAP_PIXELES = 4;      // clic a menos de 4 píxeles de una detección: se toma la detección
  const URL_SKYBOT = "https://ssp.imcce.fr/webservices/skybot/api/conesearch.php";

  const tieneWcs = (meta) => Boolean(meta && meta.wcs && meta.wcs.proyeccion === "TAN" && Array.isArray(meta.wcs.cd));

  /** Proyección gnomónica inversa (WCS, Calabretta & Greisen 2002). Píxel base 0 -> grados ICRS. */
  function pixelACielo(wcs, x, y) {
    const dx = x - wcs.crpix_x;
    const dy = y - wcs.crpix_y;
    const xi = (wcs.cd[0][0] * dx + wcs.cd[0][1] * dy) * RAD;
    const eta = (wcs.cd[1][0] * dx + wcs.cd[1][1] * dy) * RAD;
    const a0 = wcs.crval_ra_grados * RAD;
    const d0 = wcs.crval_dec_grados * RAD;
    const den = Math.cos(d0) - eta * Math.sin(d0);
    const ra = a0 + Math.atan2(xi, den);
    const dec = Math.atan2(Math.sin(d0) + eta * Math.cos(d0), Math.hypot(xi, den));
    return { ra_grados: ((ra / RAD) % 360 + 360) % 360, dec_grados: dec / RAD };
  }

  /**
   * Lienzo (600 x 600, y hacia abajo) -> rejilla del campo (base 0, y hacia arriba).
   * El píxel i de la rejilla cubre [i - 0,5, i + 0,5].
   */
  function lienzoAPixel(meta, cx, cy) {
    const sx = meta.tamano_pixeles.ancho / LADO_LIENZO;
    const sy = meta.tamano_pixeles.alto / LADO_LIENZO;
    return { x: cx * sx - 0.5, y: (LADO_LIENZO - cy) * sy - 0.5 };
  }

  function pixelALienzo(meta, x, y) {
    const sx = meta.tamano_pixeles.ancho / LADO_LIENZO;
    const sy = meta.tamano_pixeles.alto / LADO_LIENZO;
    return { cx: (x + 0.5) / sx, cy: LADO_LIENZO - (y + 0.5) / sy };
  }

  /** Separación angular (haversine), en segundos de arco. */
  function separacionSegarc(ra1, dec1, ra2, dec2) {
    const p1 = dec1 * RAD;
    const p2 = dec2 * RAD;
    const h = Math.sin((p2 - p1) / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(((ra2 - ra1) * RAD) / 2) ** 2;
    return (2 * Math.asin(Math.min(1, Math.sqrt(h)))) / RAD * 3600;
  }

  function sexagesimal(grados, horas) {
    const signo = grados < 0 ? "−" : horas ? "" : "+";
    let v = Math.abs(horas ? grados / 15 : grados);
    const a = Math.floor(v);
    v = (v - a) * 60;
    const b = Math.floor(v);
    const c = (v - b) * 60;
    const dos = (n) => String(n).padStart(2, "0");
    return `${signo}${dos(a)}${horas ? "h" : "°"} ${dos(b)}${horas ? "m" : "′"} ${c.toFixed(horas ? 2 : 1).padStart(horas ? 5 : 4, "0")}${horas ? "s" : "″"}`;
  }

  const mjdAJd = (mjd) => mjd + 2400000.5;

  function mjdAIso(mjd) {
    return new Date(Date.UTC(1858, 10, 17) + mjd * 86400000).toISOString().replace(".000Z", "Z");
  }

  /** Detección (posición en la época A) a menos de `radio` píxeles del clic, la más cercana. */
  function deteccionCercana(candidatos, x, y, radio = RADIO_SNAP_PIXELES) {
    let mejor = null;
    let distancia = radio;
    for (const c of candidatos || []) {
      if (!c.posicion_a) continue;
      const d = Math.hypot(c.posicion_a.x - x, c.posicion_a.y - y);
      if (d <= distancia) {
        mejor = c;
        distancia = d;
      }
    }
    return mejor;
  }

  /** URL de la consulta cone search de SkyBoT para la época dada (JD, observador geocéntrico 500). */
  function urlSkybot(ra, dec, mjd, radioSegarc = RADIO_BUSQUEDA_SEGARC) {
    const p = new URLSearchParams({
      "-ep": mjdAJd(mjd).toFixed(6), "-ra": ra.toFixed(6), "-dec": dec.toFixed(6),
      "-rd": (radioSegarc / 3600).toFixed(6), "-mime": "json", "-loc": "500", "-objFilter": "111", "-refsys": "EQJ2000",
    });
    return `${URL_SKYBOT}?${p}`;
  }

  function hmsAGrados(texto, horas) {
    const t = String(texto).trim();
    const signo = t.startsWith("-") ? -1 : 1;
    const [a, b, c] = t.replace(/^[+-]/, "").split(/\s+/).map(Number);
    return signo * (a + b / 60 + c / 3600) * (horas ? 15 : 1);
  }

  function claseDe(texto) {
    const t = String(texto || "");
    if (/^Comet/i.test(t)) return "cometa";
    if (/Dwarf/i.test(t)) return "planeta_enano";
    if (/^(MB|NEA|Mars|Hungaria|Trojan|Centaur|KBO|TNO|Hilda)/i.test(t)) return "asteroide";
    return "desconocida";
  }

  /**
   * Respuesta de SkyBoT (lista JSON; vacía o null si el servicio devolvió 204) -> coincidencias
   * con separación recalculada respecto a la posición observada, ordenadas por separación.
   */
  function leerSkybot(respuesta, ra, dec) {
    if (!Array.isArray(respuesta)) return [];
    return respuesta
      .map((r) => {
        const raC = hmsAGrados(r["RA (hms)"], true);
        const decC = hmsAGrados(r["DEC (dms)"], false);
        const num = r.Num !== undefined && r.Num !== null && String(r.Num).trim() !== "" ? String(r.Num).trim() : null;
        return {
          nombre: num ? `(${num}) ${r.Name}` : String(r.Name),
          designacion: num,
          clase_skybot: r.Class || null,
          clase_objeto: claseDe(r.Class),
          ra_grados: raC,
          dec_grados: decC,
          separacion_segarc: separacionSegarc(ra, dec, raC, decC),
          incertidumbre_segarc: Number.isFinite(r["Err (arcsec)"]) ? r["Err (arcsec)"] : null,
          magnitud_v: Number.isFinite(r["VMag (mag)"]) ? r["VMag (mag)"] : null,
          movimiento_segarc_h: Number.isFinite(r["dRA (arcsec/h)"]) && Number.isFinite(r["dDEC (arcsec/h)"])
            ? Math.hypot(r["dRA (arcsec/h)"], r["dDEC (arcsec/h)"]) : null,
          enlace: (r.ssodnet && r.ssodnet.ssocard) || null,
          catalogo: "skybot_imcce",
        };
      })
      .sort((a, b) => a.separacion_segarc - b.separacion_segarc);
  }

  /** Tolerancia de cada coincidencia y veredicto global con el criterio documentado. */
  function clasificar(coincidencias, escalaSegarcPorPixel) {
    const sObs = escalaSegarcPorPixel / 2;
    const conTolerancia = coincidencias.map((c) => {
      const tol = SIGMAS_COINCIDENCIA * Math.hypot(sObs, c.incertidumbre_segarc || 0);
      return { ...c, tolerancia_segarc: tol, dentro: c.separacion_segarc <= tol };
    });
    const dentro = conTolerancia.filter((c) => c.dentro).length;
    const veredicto = dentro === 0 ? "sin_coincidencia_concluyente" : dentro === 1 ? "coincidencia_compatible" : "coincidencia_ambigua";
    return { veredicto, coincidencias: conTolerancia, criterio: `separación ≤ ${SIGMAS_COINCIDENCIA}·√(σobs² + σefeméride²), σobs = ${(sObs).toFixed(2).replace(".", ",")}″ (medio píxel)` };
  }

  const VEREDICTO = {
    coincidencia_compatible: "Coincidencia compatible",
    coincidencia_ambigua: "Coincidencia ambigua: varios objetos dentro de la tolerancia",
    sin_coincidencia_concluyente: "Objeto no identificado en los catálogos consultados",
  };

  return {
    LADO_LIENZO, RADIO_BUSQUEDA_SEGARC, RADIO_SNAP_PIXELES, VEREDICTO,
    tieneWcs, pixelACielo, lienzoAPixel, pixelALienzo, separacionSegarc, sexagesimal, mjdAJd, mjdAIso,
    deteccionCercana, urlSkybot, hmsAGrados, claseDe, leerSkybot, clasificar,
  };
});
