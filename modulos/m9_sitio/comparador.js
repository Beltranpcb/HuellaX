/* ============================================================================
   ARCHIVO: modulos/m9_sitio/comparador.js
   MODULO: m9_sitio (Lote D)
   ROL: Dibuja el comparador de espectros: dos selectores, el gráfico con
        incertidumbres y los avisos de compatibilidad.
   LEE: datos/m7_publicacion/<campo>/{meta,candidatos,espectros}.json de todos
        los campos del índice (vía HX.leerDatos); lógica en comparador_logica.js.
   PRODUCE: El contenido de #panel-comparar.
   VERIFICACION: Con dos objetos con espectro se ven dos curvas con barras de
                 error; el modo «normalizado» indica el método y la longitud de onda.
   ========================================================================== */
(function () {
  "use strict";

  const HX = (window.HX = window.HX || {});
  const L = window.HXComparador;

  const ESTILO = [
    { color: "#FFB347", dash: [], punto: "circle", etiqueta: "A" },
    { color: "#7DD3FC", dash: [6, 4], punto: "rect", etiqueta: "B" },
  ];

  // Cuatro estilos de línea para las plantillas: se distinguen sin depender del color.
  const ESTILO_PLANTILLA = [
    { color: "#4ADE80", dash: [2, 3] },
    { color: "#C084FC", dash: [8, 3, 2, 3] },
    { color: "#F87171", dash: [10, 4] },
    { color: "#94A3B8", dash: [1, 4] },
  ];

  const est = {
    cargado: false,
    promesa: null,
    objetos: [],
    sinEspectro: 0,
    a: null,
    b: null,
    modo: "flujo",
    lambda0: 2.0,
    grafico: null,
    plantillas: null, // plantillas.json publicado (o null)
    plantillasCargadas: false,
    x: null, // [min, max] del zoom, null = rango completo
  };

  const $ = (id) => document.getElementById(id);
  const coma = (n, d) => Number(n).toFixed(d).replace(".", ",");

  const objetoPorId = (id) => est.objetos.find((o) => o.id_objeto === id) || null;

  // ------------------------------------------------------------------ carga
  // Una sola carga aunque la pidan a la vez la pestaña y el catálogo.
  function cargarTodo() {
    if (!est.promesa) est.promesa = cargarTodoUnaVez();
    return est.promesa;
  }

  async function cargarTodoUnaVez() {
    estado("Cargando espectros de todos los campos…");
    try {
      const campos = [];
      for (const c of HX.estado.indice) {
        try {
          const [meta, candidatos, espectros] = await Promise.all([
            HX.leerDatos(`${c.ruta}/meta.json`),
            HX.leerDatos(`${c.ruta}/candidatos.json`),
            HX.leerDatos(`${c.ruta}/espectros.json`),
          ]);
          campos.push({ campo: c.campo, meta, candidatos, espectros });
        } catch (error) {
          console.warn(`Campo ${c.campo} sin datos espectrales`, error);
        }
      }
      try {
        est.plantillas = (await HX.leerDatos("plantillas.json")).plantillas || null;
      } catch (error) {
        est.plantillas = null; // opcional: sin él solo se muestra la tabla
      }
      const { objetos, sinEspectro } = L.construirObjetos(campos);
      est.objetos = objetos;
      est.sinEspectro = sinEspectro;
      est.cargado = true;
      est.a = objetos[0] ? objetos[0].id_objeto : null;
      est.b = objetos[1] ? objetos[1].id_objeto : null;
      pintarSelectores();
      refrescar();
    } catch (error) {
      console.error(error);
      estado("Error al leer los datos publicados. Sirve la web con un servidor local y recarga.");
    }
  }

  /** Abre el comparador con A y B elegidos (B puede ser null). Lo usa el catálogo. */
  HX.abrirComparacion = async function (idA, idB) {
    HX.mostrarVista("analisis");
    await cargarTodo();
    est.a = objetoPorId(idA) ? idA : est.a;
    est.b = idB && objetoPorId(idB) ? idB : null;
    if (est.modo === "plantillas" && est.b) est.modo = "flujo";
    est.x = null;
    pintarSelectores();
    HX.mostrarPestana("comparar");
    refrescar();
  };

  function estado(texto) {
    const el = $("cmp-estado");
    if (el) el.textContent = texto || "";
  }

  // -------------------------------------------------------------- selectores
  function pintarSelectores() {
    for (const [id, valor, opcional] of [["cmp-a", est.a, false], ["cmp-b", est.b, true]]) {
      const sel = $(id);
      if (!sel) continue;
      sel.innerHTML = "";
      if (opcional) sel.add(new Option("— ninguno —", ""));
      for (const o of est.objetos) {
        sel.add(new Option(`${o.nombre} · ${o.id_objeto} · ${o.puntos.length} pts · ${L.etiquetaOrigen(o.origen)}`, o.id_objeto));
      }
      sel.value = valor || "";
    }
    const nota = $("cmp-sin-espectro");
    if (nota) {
      nota.textContent = est.sinEspectro
        ? `${est.sinEspectro} candidato${est.sinEspectro === 1 ? "" : "s"} sin espectro válido: no se pueden seleccionar.`
        : "";
    }
  }

  // ------------------------------------------------------------------ series
  function series() {
    const lista = [];
    const avisos = [];
    const ids = est.modo === "plantillas" ? [[0, est.a]] : [[0, est.a], [1, est.b]];
    for (const [i, id] of ids) {
      const o = objetoPorId(id);
      if (!o) continue;
      let puntos = o.puntos;
      let metodo = null;
      if (est.modo === "normalizado") {
        const n = L.normalizar(puntos, est.lambda0);
        if (!n.puntos) {
          avisos.push(`${o.nombre}: ${n.aviso}`);
          continue;
        }
        puntos = n.puntos;
        metodo = n.metodo;
        if (n.aviso) avisos.push(`${o.nombre}: ${n.aviso}`);
      }
      lista.push({ ...o, puntos, metodo, estilo: ESTILO[i] });
    }
    return { lista, avisos };
  }

  // --------------------------------------------------------------- gráfico
  const pluginBarras = {
    id: "barrasError",
    afterDatasetsDraw(chart) {
      const { ctx, scales } = chart;
      chart.data.datasets.forEach((ds, i) => {
        if (!chart.isDatasetVisible(i)) return;
        ctx.save();
        ctx.strokeStyle = ds.borderColor;
        ctx.lineWidth = 1;
        ctx.setLineDash([]);
        if (ds.esPlantilla) return;
        ds.data.forEach((p) => {
          const x = scales.x.getPixelForValue(p.x);
          const y1 = scales.y.getPixelForValue(p.y - p.e);
          const y2 = scales.y.getPixelForValue(p.y + p.e);
          ctx.beginPath();
          ctx.moveTo(x, y1);
          ctx.lineTo(x, y2);
          ctx.moveTo(x - 3, y1);
          ctx.lineTo(x + 3, y1);
          ctx.moveTo(x - 3, y2);
          ctx.lineTo(x + 3, y2);
          ctx.stroke();
        });
        ctx.restore();
      });
    },
  };

  // Fondo opaco para que la figura descargada no salga transparente.
  const pluginFondo = {
    id: "fondoFigura",
    beforeDraw(chart) {
      const { ctx, width, height } = chart;
      ctx.save();
      ctx.globalCompositeOperation = "destination-over";
      ctx.fillStyle = "#151C2C";
      ctx.fillRect(0, 0, width, height);
      ctx.restore();
    },
  };

  function limitesY(lista, x) {
    let bajo = Infinity;
    let alto = -Infinity;
    for (const s of lista) {
      for (const p of s.puntos) {
        if (x && (p.longitud_onda_micras < x[0] || p.longitud_onda_micras > x[1])) continue;
        bajo = Math.min(bajo, p.flujo_mjy - p.error_mjy);
        alto = Math.max(alto, p.flujo_mjy + p.error_mjy);
      }
    }
    if (!Number.isFinite(bajo)) return null;
    const margen = (alto - bajo) * 0.08 || 0.1;
    return [bajo - margen, alto + margen];
  }

  function pintarGrafico(lista) {
    const lienzo = $("cmp-grafico");
    if (!lienzo) return;
    if (typeof Chart === "undefined") {
      estado("Chart.js no se cargó: no se puede dibujar el gráfico.");
      return;
    }
    const datasets = lista.map((s) => ({
      label: `${s.estilo.etiqueta}: ${s.nombre}`,
      data: s.puntos.map((p) => ({ x: p.longitud_onda_micras, y: p.flujo_mjy, e: p.error_mjy, det: p.detector })),
      borderColor: s.estilo.color,
      backgroundColor: s.estilo.color,
      borderDash: s.estilo.dash,
      borderWidth: 1.6,
      pointStyle: s.estilo.punto,
      pointRadius: 3.2,
      pointHoverRadius: 5,
      showLine: true,
      tension: 0,
    }));
    if (est.modo === "plantillas" && lista[0]) {
      const resumen = L.resumenPlantillas(lista[0], est.plantillas);
      const rango = [est.x ? est.x[0] : L.LAMBDA_MIN, est.x ? est.x[1] : L.LAMBDA_MAX];
      resumen.ajustes.forEach((a, i) => {
        const pl = (est.plantillas || []).find((x) => x.tipo === a.tipo);
        const curva = L.curvaEscalada(pl, a.escala, rango[0], rango[1]);
        if (!curva.length) return;
        const mejor = resumen.mejor && resumen.mejor.tipo === a.tipo;
        const estilo = ESTILO_PLANTILLA[i % ESTILO_PLANTILLA.length];
        datasets.push({
          label: `Plantilla: ${L.etiquetaPlantilla(a.tipo, est.plantillas)}${a.origen_plantilla === "bibliografia" ? "" : " (sintética)"}`,
          data: curva.map((p) => ({ x: p.x, y: p.y, e: 0 })),
          borderColor: estilo.color, backgroundColor: estilo.color, borderDash: estilo.dash,
          borderWidth: mejor ? 2.6 : 1.1, pointRadius: 0, pointHoverRadius: 0, showLine: true, tension: 0, esPlantilla: true,
        });
      });
    }
    const yl = limitesY(lista, est.x);
    const unidad = est.modo === "normalizado" ? "flujo normalizado (adimensional)" : "flujo (mJy)";
    const opciones = {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      parsing: false,
      plugins: {
        legend: {
          display: true,
          labels: { color: "#E6EAF2", usePointStyle: true, boxWidth: 8, font: { size: 11 } },
        },
        tooltip: {
          callbacks: {
            title: (items) => `λ = ${coma(items[0].parsed.x, 3)} µm`,
            label: (item) => {
              const p = item.raw;
              if (item.dataset.esPlantilla) return `${item.dataset.label}: ${coma(p.y, 4)} mJy (escalada)`;
              const u = est.modo === "normalizado" ? "" : " mJy";
              return `${item.dataset.label}: ${coma(p.y, 4)} ± ${coma(p.e, 4)}${u}` + (p.det ? ` · detector ${p.det}` : "");
            },
          },
        },
      },
      scales: {
        x: {
          type: "linear",
          min: est.x ? est.x[0] : L.LAMBDA_MIN,
          max: est.x ? est.x[1] : L.LAMBDA_MAX,
          title: { display: true, text: "longitud de onda (µm)", color: "#8b95a7" },
          ticks: { color: "#8b95a7", callback: (v) => coma(v, 1) },
          grid: { color: "rgba(29,42,68,0.6)" },
        },
        y: {
          min: yl ? yl[0] : undefined,
          max: yl ? yl[1] : undefined,
          title: { display: true, text: unidad, color: "#8b95a7" },
          ticks: { color: "#8b95a7" },
          grid: { color: "rgba(29,42,68,0.6)" },
        },
      },
    };
    if (est.grafico) {
      est.grafico.data.datasets = datasets;
      est.grafico.options = { ...est.grafico.options, ...opciones };
      est.grafico.update("none");
    } else {
      est.grafico = new Chart(lienzo, { type: "scatter", data: { datasets }, options: opciones, plugins: [pluginBarras, pluginFondo] });
    }
  }

  // ----------------------------------------------------------------- paneles
  function tarjeta(s) {
    const clase = s.origen === "real" ? "real" : s.origen === "sintetico" ? "sintetico" : "desconocido";
    const lam = s.puntos;
    const avisos = L.avisosDe(s).map((t) => `<li>${t}</li>`).join("");
    return `
      <div class="cmp-tarjeta" style="border-top-color:${s.estilo.color}">
        <h3>${s.estilo.etiqueta} · ${s.nombre}</h3>
        <p class="cmp-meta">${s.id_objeto} · ${s.puntos.length} puntos válidos ·
          ${coma(lam[0].longitud_onda_micras, 2)}–${coma(lam[lam.length - 1].longitud_onda_micras, 2)} µm
          ${s.agrupacion ? `· agrupación por ${s.agrupacion}` : ""}</p>
        <p><span class="insignia ${clase}">${L.etiquetaOrigen(s.origen)}</span></p>
        ${avisos ? `<ul class="cmp-avisos">${avisos}</ul>` : ""}
      </div>`;
  }

  function pintarPlantillas(lista) {
    const caja = $("cmp-compatibilidad");
    const metodo = $("cmp-metodo");
    $("cmp-tarjetas").innerHTML = lista.map(tarjeta).join("");
    metodo.textContent = "Objeto frente a plantilla: evalúa compatibilidad con un modelo de referencia. No identifica el objeto " +
      "ni equivale a compararlo con otro objeto observado. Las curvas se dibujan multiplicadas por la escala del ajuste de m6.";
    if (!lista.length) { caja.className = "cmp-compat"; caja.innerHTML = ""; return; }
    const r = L.resumenPlantillas(lista[0], est.plantillas);
    const filas = r.ajustes.map((a) => `<tr${r.mejor && r.mejor.tipo === a.tipo ? ' class="mejor"' : ""}>
        <td>${L.etiquetaPlantilla(a.tipo, est.plantillas)}</td><td>${coma(a.chi2_reducido, 2)}</td>
        <td>${a.grados_libertad}</td><td>${a.n_puntos === undefined ? "—" : a.n_puntos}</td>
        <td>${a.origen_plantilla === "bibliografia" ? "bibliografía" : "sintética"}</td></tr>`).join("");
    const avisos = L.avisosDe(lista[0]).map((x) => `<li>${x}</li>`).join("");
    caja.className = `cmp-compat ${r.nivel === "compatible" ? "ok" : "aviso"}`;
    caja.innerHTML = `<b>${r.texto}</b>` +
      (filas ? `<table class="cmp-tabla"><thead><tr><th>Plantilla</th><th>χ² reducido</th><th>Grados de libertad</th><th>Puntos</th><th>Origen</th></tr></thead><tbody>${filas}</tbody></table>` +
        `<p class="cmp-nota">χ² diagonal con una escala libre; no modela correlaciones entre canales ni errores sistemáticos.</p>` : "") +
      (avisos ? `<ul>${avisos}</ul>` : "") +
      (est.plantillas ? "" : "<p class=\"cmp-nota\">plantillas.json no está publicado: no se dibujan las curvas.</p>");
  }

  function pintarPaneles(lista, avisosSerie) {
    if (est.modo === "plantillas") { pintarPlantillas(lista); return; }
    $("cmp-tarjetas").innerHTML = lista.map(tarjeta).join("");

    const caja = $("cmp-compatibilidad");
    const metodo = $("cmp-metodo");
    const mensajes = [...avisosSerie];
    let estadoCompat = "ok";
    let comun = null;
    if (lista.length === 2) {
      const c = L.evaluarCompatibilidad(lista[0], lista[1], est.modo);
      estadoCompat = c.estado;
      comun = c.rangoComun;
      mensajes.push(...c.mensajes);
    } else if (lista.length === 1) {
      mensajes.push("Elige un segundo objeto para compararlos.");
    }
    if (avisosSerie.length && estadoCompat === "ok") estadoCompat = "aviso";
    const titulo = { ok: "Compatibles", aviso: "Comparables con cautela", incompatible: "No comparables" }[estadoCompat];
    caja.className = `cmp-compat ${estadoCompat}`;
    caja.innerHTML =
      lista.length === 2
        ? `<b>${titulo}.</b> ${comun ? `Intervalo común: ${coma(comun[0], 2)}–${coma(comun[1], 2)} µm. ` : ""}` +
          `Unidades: ${est.modo === "flujo" ? "mJy" : "adimensional"}.` +
          (mensajes.length ? `<ul>${mensajes.map((m) => `<li>${m}</li>`).join("")}</ul>` : "")
        : mensajes.length
        ? `<ul>${mensajes.map((m) => `<li>${m}</li>`).join("")}</ul>`
        : "";

    metodo.textContent =
      est.modo === "normalizado"
        ? "Normalización: " +
          lista.map((s) => `${s.estilo.etiqueta}: ${s.metodo}`).join(" · ") +
          ". La incertidumbre del factor no se propaga."
        : "Flujo medido en mJy, sin reescalar: solo se compara directamente si la calibración es compatible.";
  }

  function refrescar() {
    if (!est.cargado) return;
    const { lista, avisos } = series();
    $("cmp-lambda-caja").hidden = est.modo !== "normalizado";
    $("cmp-b").disabled = est.modo === "plantillas"; // en este modo solo se evalúa A
    const aviso = $("cmp-aviso-conceptual");
    if (aviso) {
      aviso.innerHTML = est.modo === "plantillas"
        ? "Aquí se evalúa <b>un objeto frente a plantillas de referencia</b>. Indica qué modelo reproduce mejor la forma del " +
          "espectro entre los evaluados; no identifica el objeto ni demuestra su composición."
        : "Aquí se comparan <b>dos espectros observados</b> entre sí. No es una clasificación ni una comparación con " +
          "plantillas: una curva parecida no prueba que dos objetos sean del mismo tipo.";
    }
    for (const m of ["flujo", "normalizado", "plantillas"]) {
      const b = $(`cmp-modo-${m}`);
      if (b) b.classList.toggle("activo", est.modo === m);
    }
    if (!est.objetos.length) {
      estado("No hay objetos con espectro válido en los campos publicados.");
      $("cmp-tarjetas").innerHTML = "";
      return;
    }
    estado("");
    pintarGrafico(lista);
    pintarPaneles(lista, avisos);
  }

  // ------------------------------------------------------------------- zoom
  function zoom(factor, centro) {
    const actual = est.x || [L.LAMBDA_MIN, L.LAMBDA_MAX];
    const c = centro === undefined ? (actual[0] + actual[1]) / 2 : centro;
    let bajo = c - (c - actual[0]) * factor;
    let alto = c + (actual[1] - c) * factor;
    bajo = Math.max(L.LAMBDA_MIN, bajo);
    alto = Math.min(L.LAMBDA_MAX, alto);
    const ancho = alto - bajo;
    if (ancho < 0.1) return; // no se acerca más: SPHEREx no resuelve menos
    est.x = ancho >= L.LAMBDA_MAX - L.LAMBDA_MIN - 1e-9 ? null : [bajo, alto];
    refrescar();
  }

  // ---------------------------------------------------------------- descargas
  function descargar(nombre, blob) {
    const url = URL.createObjectURL(blob);
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = nombre;
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function descargarCsv() {
    const { lista } = series();
    if (!lista.length) return;
    descargar("huella-x-espectros.csv", new Blob(["﻿" + L.aCsv(lista, est.modo)], { type: "text/csv;charset=utf-8" }));
  }

  function descargarPng() {
    if (!est.grafico) return;
    const enlace = document.createElement("a");
    enlace.href = est.grafico.toBase64Image("image/png", 1);
    enlace.download = "huella-x-espectros.png";
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
  }

  // ------------------------------------------------------------------- inicio
  function iniciar() {
    if (!$("panel-comparar") || !L) return;
    $("cmp-a").addEventListener("change", (e) => { est.a = e.target.value || null; refrescar(); });
    $("cmp-b").addEventListener("change", (e) => { est.b = e.target.value || null; refrescar(); });
    $("cmp-modo-flujo").addEventListener("click", () => { est.modo = "flujo"; refrescar(); });
    $("cmp-modo-normalizado").addEventListener("click", () => { est.modo = "normalizado"; refrescar(); });
    $("cmp-modo-plantillas").addEventListener("click", () => { est.modo = "plantillas"; refrescar(); });
    $("cmp-lambda").addEventListener("input", (e) => {
      const v = parseFloat(e.target.value);
      if (Number.isFinite(v) && v >= L.LAMBDA_MIN && v <= L.LAMBDA_MAX) { est.lambda0 = v; refrescar(); }
    });
    $("cmp-zoom-mas").addEventListener("click", () => zoom(0.6));
    $("cmp-zoom-menos").addEventListener("click", () => zoom(1 / 0.6));
    $("cmp-zoom-reset").addEventListener("click", () => { est.x = null; refrescar(); });
    $("cmp-csv").addEventListener("click", descargarCsv);
    $("cmp-png").addEventListener("click", descargarPng);
    $("cmp-grafico").addEventListener("wheel", (e) => {
      if (!est.grafico) return;
      e.preventDefault();
      const x = est.grafico.scales.x.getValueForPixel(e.offsetX);
      zoom(e.deltaY < 0 ? 0.8 : 1.25, x);
    }, { passive: false });
    HX.alAbrirPestana.push((nombre) => { if (nombre === "comparar") cargarTodo(); });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
