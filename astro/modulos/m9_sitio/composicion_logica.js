/* ============================================================================
   ARCHIVO: modulos/m9_sitio/composicion_logica.js
   MODULO: m9_sitio (Lote D)
   ROL: Lógica pura de la sección «Composición espectral»: cuándo se muestra,
        en qué orden y con qué textos. No calcula nada: los estados vienen de m6.
   LEE: Nada por sí mismo; recibe un espectro de espectros.json con su composicion.
   PRODUCE: window.HXComposicion (navegador) o module.exports (node --test).
   VERIFICACION: pruebas/prueba_composicion.js (node --test).
   ========================================================================== */
(function (raiz, fabrica) {
  if (typeof module === "object" && module.exports) module.exports = fabrica();
  else raiz.HXComposicion = fabrica();
})(this, function () {
  "use strict";

  const ORDEN = ["detectada", "candidata", "compatible", "sin_rasgo", "datos_insuficientes"];
  const ESTADO = {
    detectada: "Detectada",
    candidata: "Candidata",
    compatible: "Compatible",
    sin_rasgo: "Sin rasgo",
    datos_insuficientes: "Datos insuficientes",
  };
  const MOLECULA = {
    agua: "agua",
    metano: "metano",
    dioxido_de_carbono: "dióxido de carbono",
    monoxido_de_carbono: "monóxido de carbono",
    amoniaco: "amoníaco",
  };
  const ALTERNATIVA = {
    minerales_hidratados_OH: "minerales hidratados (OH)",
    hidrocarburos_con_enlace_CH: "hidrocarburos con enlace C-H",
    metano_2_3_micras: "banda de metano a 2,3 µm",
  };

  const coma = (n, d) => Number(n).toFixed(d).replace(".", ",").replace("-", "−");

  function puntosUtiles(espectro) {
    return ((espectro && espectro.puntos) || []).filter(
      (p) => Number.isFinite(p.longitud_onda_micras) && Number.isFinite(p.flujo_mjy) && p.error_mjy > 0
    );
  }

  /** Solo hay sección si existe un espectro utilizable y m6 publicó su composición. */
  function debeMostrarse(espectro) {
    return Boolean(
      espectro && espectro.composicion && Array.isArray(espectro.composicion.moleculas) &&
      espectro.composicion.moleculas.length && puntosUtiles(espectro).length >= 2
    );
  }

  /** Por nivel de evidencia y, dentro de cada nivel, por |S| decreciente. */
  function ordenadas(moleculas) {
    const s = (m) => (m.metrica ? Math.abs(m.metrica.valor) : -1);
    return moleculas.slice().sort((a, b) => ORDEN.indexOf(a.estado) - ORDEN.indexOf(b.estado) || s(b) - s(a));
  }

  function textoMetrica(m) {
    if (!m.metrica) return "Sin métrica: faltan datos para calcularla.";
    const gl = m.metrica.grados_libertad ? ` · ${m.metrica.grados_libertad} g.l.` : "";
    return `S = ${coma(m.metrica.valor, 1)} σ${gl}`;
  }

  function textoBanda(m) {
    return `${coma(m.banda_micras[0], 2)}–${coma(m.banda_micras[1], 2)} µm` +
      (m.resolucion_espectral ? ` · R ≈ ${m.resolucion_espectral}` : "");
  }

  function textoRasgo(m) {
    return { absorcion: "absorción", emision: "emisión" }[m.rasgo] || null;
  }

  function textoAlternativas(m) {
    return (m.ambigua_con || []).map((a) => ALTERNATIVA[a] || a.replace(/_/g, " "));
  }

  /** Frase de resumen que nunca convierte una candidata en detección. */
  function resumen(composicion) {
    const n = {};
    for (const m of composicion.moleculas) n[m.estado] = (n[m.estado] || 0) + 1;
    const partes = ORDEN.filter((e) => n[e]).map((e) => `${n[e]} ${ESTADO[e].toLowerCase()}`);
    const cabeza = n.detectada
      ? `${n.detectada === 1 ? "Una molécula cumple" : n.detectada + " moléculas cumplen"} todos los criterios de detección del método.`
      : "Ninguna molécula cumple los criterios de detección del método.";
    return `${cabeza} (${partes.join(" · ")})`;
  }

  /** Ventanas de referencia que se dibujan como franjas: teóricas, no medidas. */
  function regiones(composicion) {
    return composicion.moleculas.map((m) => ({ formula: m.formula, bajo: m.banda_micras[0], alto: m.banda_micras[1], estado: m.estado }));
  }

  return { ORDEN, ESTADO, MOLECULA, puntosUtiles, debeMostrarse, ordenadas, textoMetrica, textoBanda, textoRasgo, textoAlternativas, resumen, regiones };
});
