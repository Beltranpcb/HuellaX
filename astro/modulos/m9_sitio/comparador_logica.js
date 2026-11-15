/* ============================================================================
   ARCHIVO: modulos/m9_sitio/comparador_logica.js
   MODULO: m9_sitio (Lote D)
   ROL: Reúne la lógica pura del comparador de espectros: qué objetos tienen un
        espectro válido, cómo se normalizan y si dos espectros se pueden comparar.
   LEE: Nada por sí mismo; recibe los JSON ya cargados (meta, candidatos, espectros).
   PRODUCE: window.HXComparador (navegador) o module.exports (node --test).
   FUNCIONAMIENTO PREVISTO:
     1. construirObjetos: un objeto por pareja con espectro válido  ->  lista del selector
     2. normalizar: divide por el flujo en lambda0 (o por la mediana)  ->  forma espectral
     3. evaluarCompatibilidad: rango común, resolución, origen  ->  estado y avisos
     4. resumenPlantillas / curvaEscalada: redacta la compatibilidad objeto-plantilla y escala la curva
   5. aCsv: serie visible  ->  texto CSV
   VERIFICACION: pruebas/prueba_comparador.js (node --test).
   NOTA: No calcula ninguna clasificación ni estadística entre objetos: comparar
         dos espectros observados no es comparar con plantillas (eso lo hace m6).
   ========================================================================== */
(function (raiz, fabrica) {
  if (typeof module === "object" && module.exports) module.exports = fabrica();
  else raiz.HXComparador = fabrica();
})(this, function () {
  "use strict";

  const LAMBDA_MIN = 0.75;
  const LAMBDA_MAX = 5.0;
  const MINIMO_PUNTOS = 2;
  const SOLAPE_MINIMO_MICRAS = 0.5;
  const VENTANA_NORMALIZACION = 0.25; // semiancho en micras

  const TEXTO_ORIGEN = {
    real: "Datos reales de SPHEREx",
    sintetico: "Demostración (datos sintéticos)",
    pendiente: "Pendiente de datos",
  };

  const TEXTO_ADVERTENCIA = {
    plantillas_sinteticas: "Las plantillas de referencia son sintéticas, no curvas de bibliografía.",
    cuerpo_negro_fuera_de_rango:
      "Un cuerpo negro ajustado entre 0,75 y 5 µm no fija por sí solo la temperatura de un cuerpo frío.",
    luz_reflejada_y_termica: "El flujo mezcla luz solar reflejada y emisión térmica.",
    senal_ruido_baja: "Señal/ruido baja: los puntos tienen mucha incertidumbre.",
    agrupado_por_detector: "Espectro promediado por detector: solo 6 puntos anchos.",
    cobertura_espectral_parcial: "El espectro no cubre todo el rango de SPHEREx.",
    resolucion_incompatible: "La resolución espectral no es comparable.",
    errores_correlacionados: "Hay errores correlacionados entre canales.",
  };

  const esNumero = (v) => typeof v === "number" && Number.isFinite(v);

  function puntoValido(p) {
    return (
      p &&
      esNumero(p.longitud_onda_micras) &&
      p.longitud_onda_micras >= LAMBDA_MIN &&
      p.longitud_onda_micras <= LAMBDA_MAX &&
      esNumero(p.flujo_mjy) &&
      esNumero(p.error_mjy) &&
      p.error_mjy > 0
    );
  }

  /** Puntos utilizables, ordenados por longitud de onda. */
  function puntosValidos(espectro) {
    if (!espectro || !Array.isArray(espectro.puntos)) return [];
    return espectro.puntos
      .filter(puntoValido)
      .slice()
      .sort((a, b) => a.longitud_onda_micras - b.longitud_onda_micras);
  }

  function etiquetaOrigen(origen) {
    return TEXTO_ORIGEN[origen] || "Origen no declarado";
  }

  /**
   * campos: [{ campo, meta, candidatos, espectros }] ya cargados.
   * Devuelve { objetos, sinEspectro }: solo entran los objetos con un espectro
   * válido (al menos MINIMO_PUNTOS puntos utilizables).
   */
  function construirObjetos(campos) {
    const objetos = [];
    let sinEspectro = 0;
    for (const c of campos) {
      const espectros = (c.espectros && c.espectros.espectros) || c.espectros || [];
      const candidatos = (c.candidatos && c.candidatos.candidatos) || c.candidatos || [];
      const porPareja = new Map(espectros.map((e) => [e.id_pareja, e]));
      for (const cand of candidatos) {
        const esp = porPareja.get(cand.id_candidato);
        const puntos = puntosValidos(esp);
        if (!esp || puntos.length < MINIMO_PUNTOS) {
          sinEspectro += 1;
          continue;
        }
        const origen = esp.origen || (c.meta && c.meta.origen) || null;
        objetos.push({
          id_objeto: `${c.campo}/${cand.id_candidato}`,
          campo: c.campo,
          id_candidato: cand.id_candidato,
          nombre: cand.nombre_objeto || `Sin identificar (${c.campo}/${cand.id_candidato})`,
          estado: cand.estado,
          origen,
          agrupacion: esp.agrupacion || null,
          tipo: esp.tipo || null,
          ajustes: Array.isArray(esp.ajustes_plantilla) ? esp.ajustes_plantilla : [],
          advertencias: Array.isArray(esp.advertencias) ? esp.advertencias : [],
          puntos,
        });
      }
    }
    return { objetos, sinEspectro };
  }

  function mediana(valores) {
    const v = valores.slice().sort((a, b) => a - b);
    const m = Math.floor(v.length / 2);
    return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
  }

  /**
   * Normaliza dividiendo flujo y error por un factor. Con lambda0 usa la media
   * del flujo en lambda0 ± 0,25 µm; sin puntos en esa ventana, o sin lambda0,
   * usa la mediana de todo el espectro y lo dice en `metodo`.
   * No propaga la incertidumbre del propio factor.
   */
  function normalizar(puntos, lambda0) {
    let factor = null;
    let metodo;
    let aviso = null;
    if (esNumero(lambda0)) {
      const ventana = puntos.filter((p) => Math.abs(p.longitud_onda_micras - lambda0) <= VENTANA_NORMALIZACION);
      if (ventana.length) {
        factor = ventana.reduce((s, p) => s + p.flujo_mjy, 0) / ventana.length;
        metodo =
          `flujo medio en ${lambda0.toFixed(2).replace(".", ",")} ± 0,25 µm ` +
          `(${ventana.length} ${ventana.length === 1 ? "punto" : "puntos"})`;
      } else {
        aviso = `Sin puntos cerca de ${lambda0.toFixed(2).replace(".", ",")} µm: se usa la mediana.`;
      }
    }
    if (factor === null) {
      factor = mediana(puntos.map((p) => p.flujo_mjy));
      metodo = "mediana del flujo de todo el espectro";
    }
    if (!esNumero(factor) || factor <= 0) {
      return { puntos: null, factor: null, metodo, aviso: "El flujo de referencia no es positivo: no se puede normalizar." };
    }
    return {
      puntos: puntos.map((p) => ({ ...p, flujo_mjy: p.flujo_mjy / factor, error_mjy: p.error_mjy / factor })),
      factor,
      metodo,
      aviso,
    };
  }

  function rango(puntos) {
    return [puntos[0].longitud_onda_micras, puntos[puntos.length - 1].longitud_onda_micras];
  }

  function rangoComun(a, b) {
    const ra = rango(a);
    const rb = rango(b);
    const bajo = Math.max(ra[0], rb[0]);
    const alto = Math.min(ra[1], rb[1]);
    return bajo < alto ? [bajo, alto] : null;
  }

  /**
   * Decide si A y B se pueden comparar. estado: ok | aviso | incompatible.
   * Las unidades son siempre mJy (contrato espectros.schema.json).
   */
  function evaluarCompatibilidad(a, b, modo) {
    const mensajes = [];
    const comun = rangoComun(a.puntos, b.puntos);
    if (!comun) {
      return {
        estado: "incompatible",
        rangoComun: null,
        mensajes: ["Los dos espectros no comparten ningún intervalo de longitud de onda."],
      };
    }
    let estado = "ok";
    const aviso = (texto) => {
      estado = "aviso";
      mensajes.push(texto);
    };
    if (comun[1] - comun[0] < SOLAPE_MINIMO_MICRAS) aviso("El intervalo común es estrecho (menos de 0,5 µm).");
    if (a.agrupacion && b.agrupacion && a.agrupacion !== b.agrupacion) {
      aviso("Resolución distinta: uno está promediado por detector y el otro tiene un punto por banda.");
    }
    if (a.origen !== b.origen) aviso("Los dos objetos no tienen el mismo origen de datos.");
    if (modo === "flujo" && (a.origen === "sintetico" || b.origen === "sintetico")) {
      aviso("Hay datos sintéticos: el flujo absoluto no tiene valor físico.");
    }
    if (modo === "flujo" && a.campo !== b.campo) {
      aviso("Objetos de campos distintos: el flujo medido solo es comparable si la calibración lo es.");
    }
    return { estado, rangoComun: comun, mensajes };
  }

  function avisosDe(objeto) {
    return objeto.advertencias.map((codigo) => TEXTO_ADVERTENCIA[codigo] || codigo);
  }

  const ETIQUETA_TIPO = {
    asteroide_rocoso: "asteroide rocoso",
    asteroide_oscuro: "asteroide oscuro",
    cometa: "cometa",
    enana_marron: "enana marrón",
  };

  /** Etiqueta pública de una plantilla; si plantillas.json no está, la del tipo. */
  function etiquetaPlantilla(tipo, plantillas) {
    const p = (plantillas || []).find((x) => x.tipo === tipo);
    return (p && p.etiqueta_publica) || ETIQUETA_TIPO[tipo] || tipo;
  }

  /** Ajustes con grados de libertad y chi2 finitos, del más al menos compatible. */
  function ajustesOrdenados(objeto) {
    return objeto.ajustes
      .filter((a) => esNumero(a.chi2_reducido) && Number.isInteger(a.grados_libertad) && a.grados_libertad >= 1)
      .slice()
      .sort((a, b) => a.chi2_reducido - b.chi2_reducido);
  }

  /**
   * Resumen de la comparación objeto-plantilla. La decisión del tipo la toma m6:
   * aquí solo se redacta con la cautela del contrato («más compatible entre las
   * evaluadas»), sin recalcular ni afirmar que el objeto «es» de ese tipo.
   */
  function resumenPlantillas(objeto, plantillas) {
    const ajustes = ajustesOrdenados(objeto);
    if (!ajustes.length) {
      return { nivel: "sin_datos", ajustes, mejor: null,
        texto: "No hay χ² con grados de libertad para este objeto: no se muestra ninguna métrica." };
    }
    const mejor = ajustes.find((a) => a.tipo === objeto.tipo) || null;
    if (!mejor) {
      return { nivel: "indeterminado", ajustes, mejor: null,
        texto: `Ninguna de las ${ajustes.length} plantillas evaluadas reproduce el espectro dentro del umbral de m6.` };
    }
    const sintetica = mejor.origen_plantilla !== "bibliografia";
    return { nivel: "compatible", ajustes, mejor,
      texto: `Más compatible con la plantilla «${etiquetaPlantilla(mejor.tipo, plantillas)}» entre las ${ajustes.length} evaluadas ` +
        `(χ² reducido ${mejor.chi2_reducido.toFixed(2).replace(".", ",")}, ${mejor.grados_libertad} grados de libertad, ` +
        `${mejor.n_puntos === undefined ? "?" : mejor.n_puntos} puntos)` +
        (sintetica ? ". La plantilla es sintética: no es un espectro de referencia medido." : ".") };
  }

  /** Curva de la plantilla multiplicada por la escala del ajuste, dentro de [min, max] µm. */
  function curvaEscalada(plantilla, escala, minimo, maximo) {
    if (!plantilla || !esNumero(escala) || escala <= 0) return [];
    const salida = [];
    for (let i = 0; i < plantilla.longitud_onda_micras.length; i++) {
      const x = plantilla.longitud_onda_micras[i];
      if (x >= minimo && x <= maximo) salida.push({ x, y: plantilla.flujo_normalizado[i] * escala });
    }
    return salida;
  }

  function celda(texto) {
    const s = String(texto);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  }

  /** CSV de la serie visible: una fila por punto de cada objeto. */
  function aCsv(series, modo) {
    const filas = ["objeto,modo,longitud_onda_micras,flujo,error,unidad,detector,mjd,origen"];
    for (const s of series) {
      for (const p of s.puntos) {
        filas.push(
          [
            celda(s.nombre),
            modo,
            p.longitud_onda_micras,
            p.flujo_mjy,
            p.error_mjy,
            modo === "normalizado" ? "adimensional" : "mJy",
            p.detector === undefined ? "" : p.detector,
            p.mjd === undefined ? "" : p.mjd,
            s.origen || "no_declarado",
          ].join(",")
        );
      }
    }
    return filas.join("\n") + "\n";
  }

  return {
    LAMBDA_MIN,
    LAMBDA_MAX,
    puntosValidos,
    etiquetaOrigen,
    construirObjetos,
    normalizar,
    rangoComun,
    evaluarCompatibilidad,
    avisosDe,
    etiquetaPlantilla,
    ajustesOrdenados,
    resumenPlantillas,
    curvaEscalada,
    aCsv,
  };
});
