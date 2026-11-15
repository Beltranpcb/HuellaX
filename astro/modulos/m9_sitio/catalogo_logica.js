/* ============================================================================
   ARCHIVO: modulos/m9_sitio/catalogo_logica.js
   MODULO: m9_sitio (Lote D)
   ROL: Lógica pura del catálogo navegable: búsqueda, filtros y textos de cada
        objeto de catalogo.json.
   LEE: Nada por sí mismo; recibe catalogo.json ya cargado.
   PRODUCE: window.HXCatalogo (navegador) o module.exports (node --test).
   VERIFICACION: pruebas/prueba_catalogo.js (node --test).
   NOTA: No calcula ninguna similitud: la métrica viene de m7 (indice_catalogo.py).
         Aquí solo se filtra y se redacta.
   ========================================================================== */
(function (raiz, fabrica) {
  if (typeof module === "object" && module.exports) module.exports = fabrica();
  else raiz.HXCatalogo = fabrica();
})(this, function () {
  "use strict";

  const UMBRAL_FORMA_COMPATIBLE = 2; // chi2 reducido; ≈1 significa diferencias del orden de los errores

  const CLASE = {
    asteroide: "Asteroide",
    cometa: "Cometa",
    planeta_enano: "Planeta enano",
    estrella: "Estrella",
    enana_marron: "Enana marrón",
    galaxia: "Galaxia",
    desconocida: "Sin clase catalogada",
  };
  const ESTADO = {
    conocido: "Conocido (en catálogo)",
    sin_identificar: "Sin identificación concluyente",
    artefacto_descartado: "Artefacto descartado",
  };
  const ESPECTRO = {
    real: "Espectro real",
    sintetico: "Espectro de demostración",
    no_declarado: "Espectro (origen no declarado)",
    pendiente: "Espectro pendiente",
    ninguno: "Sin espectro",
  };
  const TIPO = {
    asteroide_rocoso: "roca con silicatos",
    asteroide_oscuro: "cuerpo primitivo oscuro",
    cometa: "hielo y CO2",
    enana_marron: "enana marrón con metano",
    indeterminado: "ninguna plantilla compatible",
  };

  const sinAcentos = (s) =>
    String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();

  const tieneEspectro = (o) => ["real", "sintetico", "no_declarado"].includes(o.datos.espectro);

  /**
   * filtros: { texto, clasificacion, estado, soloConEspectro }. Un filtro vacío no filtra.
   * El texto busca en nombre y designación; en el identificador solo si contiene «/».
   */
  function filtrar(objetos, filtros) {
    const f = filtros || {};
    const texto = sinAcentos(f.texto);
    return objetos.filter((o) => {
      if (f.clasificacion && o.clasificacion !== f.clasificacion) return false;
      if (f.estado && o.estado_identificacion !== f.estado) return false;
      if (f.soloConEspectro && !tieneEspectro(o)) return false;
      if (!texto) return true;
      // El id (campo/pareja) solo se busca si el texto lo parece, y el nombre solo si es un
      // nombre catalogado: el de un objeto sin identificar («Sin identificar (slipher/p002)»)
      // lo genera m7 con el id. Así «slipher» no trae los objetos sin identificar del campo.
      const nombre = o.estado_identificacion === "conocido" ? o.nombre : null;
      const campos = texto.includes("/") ? [nombre, o.designacion, o.id_objeto] : [nombre, o.designacion];
      return campos.some((v) => sinAcentos(v).includes(texto));
    });
  }

  /** Clases presentes, en el orden de CLASE, para el filtro. */
  function clasesPresentes(objetos) {
    const presentes = new Set(objetos.map((o) => o.clasificacion));
    return Object.keys(CLASE).filter((c) => presentes.has(c));
  }

  function titulo(o) {
    return o.designacion && !o.nombre.includes(o.designacion) ? `${o.nombre} — ${o.designacion}` : o.nombre;
  }

  function textoClasificacion(o) {
    if (o.clasificacion === "desconocida" || !o.clasificacion) return "Sin clase catalogada";
    return `${CLASE[o.clasificacion] || o.clasificacion} · fuente: ${o.fuente_clasificacion || "no declarada"}`;
  }

  /** El tipo espectral es de m6 y se redacta como compatibilidad, nunca como identidad. */
  function textoTipoEspectral(o) {
    if (!tieneEspectro(o) || !o.tipo_espectral) return null;
    if (o.tipo_espectral === "indeterminado") return "Ninguna plantilla reproduce el espectro dentro del umbral de m6.";
    return `Más compatible con la plantilla «${TIPO[o.tipo_espectral] || o.tipo_espectral}» entre las evaluadas.`;
  }

  /** Relacionados con nombre resuelto; los que no están en el catálogo se descartan. */
  function relacionados(o, porId) {
    const r = o.relacionados || { misma_clasificacion: [], espectros_similares: [] };
    return {
      misma: r.misma_clasificacion.map((id) => porId.get(id)).filter(Boolean),
      similares: r.espectros_similares
        .filter((s) => porId.has(s.id_objeto))
        .map((s) => ({ ...s, objeto: porId.get(s.id_objeto), compatible: s.valor <= UMBRAL_FORMA_COMPATIBLE })),
    };
  }

  return {
    UMBRAL_FORMA_COMPATIBLE,
    CLASE,
    ESTADO,
    ESPECTRO,
    sinAcentos,
    tieneEspectro,
    filtrar,
    clasesPresentes,
    titulo,
    textoClasificacion,
    textoTipoEspectral,
    relacionados,
  };
});
