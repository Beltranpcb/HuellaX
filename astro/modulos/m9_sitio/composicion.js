/* ============================================================================
   ARCHIVO: modulos/m9_sitio/composicion.js
   MODULO: m9_sitio (Lote D)
   ROL: Dibuja la sección «Composición espectral» de una ficha: el espectro medido
        con sus errores, las ventanas de referencia como franjas y una tarjeta por
        molécula con estado, métrica, explicación, alternativas y referencia.
   LEE: Un espectro de espectros.json con `composicion` (m6); lógica en composicion_logica.js.
   PRODUCE: HX.pintarComposicion(contenedor, espectro, origen); se usa en la ficha del
            explorador (#ficha-composicion) y en la del catálogo (#cat-composicion).
   VERIFICACION: Un candidato sin composición no muestra la sección; con ella, cada
                 molécula aparece con su estado escrito, no solo con un color.
   ========================================================================== */
(function () {
  "use strict";

  const HX = (window.HX = window.HX || {});
  const K = window.HXComposicion;
  const graficos = new WeakMap(); // contenedor -> gráfico de Chart.js

  const COLOR = {
    detectada: "rgba(74,222,128,0.20)",
    candidata: "rgba(255,179,71,0.18)",
    compatible: "rgba(125,211,252,0.14)",
    sin_rasgo: "rgba(139,149,167,0.10)",
    datos_insuficientes: "rgba(139,149,167,0.05)",
  };
  const ORIGEN = { real: "Datos reales de SPHEREx", sintetico: "Demostración (datos sintéticos)" };
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const coma = (n, d) => Number(n).toFixed(d).replace(".", ",");

  // Franjas de las ventanas de referencia, detrás del espectro, con la fórmula arriba.
  const pluginFranjas = {
    id: "franjasMoleculares",
    beforeDatasetsDraw(chart, _args, opciones) {
      const { ctx, chartArea, scales } = chart;
      ctx.save();
      for (const r of opciones.regiones || []) {
        const x0 = scales.x.getPixelForValue(r.bajo);
        const x1 = scales.x.getPixelForValue(r.alto);
        ctx.fillStyle = COLOR[r.estado] || COLOR.sin_rasgo;
        ctx.fillRect(x0, chartArea.top, x1 - x0, chartArea.bottom - chartArea.top);
        ctx.setLineDash([3, 3]);
        ctx.strokeStyle = "rgba(139,149,167,0.6)";
        ctx.strokeRect(x0, chartArea.top, x1 - x0, chartArea.bottom - chartArea.top);
        ctx.setLineDash([]);
        ctx.fillStyle = "#E6EAF2";
        ctx.font = "10px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(r.formula, (x0 + x1) / 2, chartArea.top + 11);
      }
      ctx.restore();
    },
  };

  const pluginErrores = {
    id: "erroresComposicion",
    afterDatasetsDraw(chart) {
      const { ctx, scales } = chart;
      ctx.save();
      ctx.strokeStyle = "rgba(255,179,71,0.7)";
      ctx.lineWidth = 1;
      for (const p of chart.data.datasets[0].data) {
        const x = scales.x.getPixelForValue(p.x);
        ctx.beginPath();
        ctx.moveTo(x, scales.y.getPixelForValue(p.y - p.e));
        ctx.lineTo(x, scales.y.getPixelForValue(p.y + p.e));
        ctx.stroke();
      }
      ctx.restore();
    },
  };

  function tarjeta(m) {
    const rasgo = K.textoRasgo(m);
    const alternativas = K.textoAlternativas(m);
    const avisos = m.advertencias && m.advertencias.length && window.HXComparador
      ? window.HXComparador.avisosDe({ advertencias: m.advertencias }) : [];
    return `
      <li class="mol mol-${m.estado}">
        <div class="mol-cab">
          <b>${esc(m.formula)}</b> <span class="cmp-meta">${esc(K.MOLECULA[m.molecula] || m.molecula)} · ${esc(K.textoBanda(m))}</span>
          <span class="mol-estado">${esc(K.ESTADO[m.estado] || m.estado)}</span>
        </div>
        <p class="mol-metrica">${esc(K.textoMetrica(m))}${rasgo ? " · " + rasgo : ""}</p>
        ${m.explicacion ? `<p>${esc(m.explicacion)}</p>` : ""}
        ${alternativas.length ? `<p class="cmp-meta">Otras explicaciones posibles: ${esc(alternativas.join(", "))}.</p>` : ""}
        ${avisos.length ? `<ul class="cmp-avisos">${avisos.map((a) => `<li>${esc(a)}</li>`).join("")}</ul>` : ""}
        ${m.referencia ? `<p class="mol-ref">Referencia de la banda: ${esc(m.referencia)}</p>` : ""}
      </li>`;
  }

  function dibujar(lienzo, espectro, contenedor) {
    if (typeof Chart === "undefined") return;
    const anterior = graficos.get(contenedor);
    if (anterior) anterior.destroy();
    const puntos = K.puntosUtiles(espectro);
    graficos.set(contenedor, new Chart(lienzo, {
      type: "scatter",
      data: { datasets: [{
        label: "Espectro medido (puntos ± error)",
        data: puntos.map((p) => ({ x: p.longitud_onda_micras, y: p.flujo_mjy, e: p.error_mjy })),
        borderColor: "#FFB347", backgroundColor: "#FFB347", pointRadius: 2, showLine: false,
      }] },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false, parsing: false,
        plugins: {
          franjasMoleculares: { regiones: K.regiones(espectro.composicion) },
          legend: { display: true, labels: { color: "#E6EAF2", boxWidth: 8, font: { size: 10 } } },
          tooltip: { callbacks: {
            title: (i) => `λ = ${coma(i[0].parsed.x, 3)} µm`,
            label: (i) => `${coma(i.raw.y, 4)} ± ${coma(i.raw.e, 4)} mJy (medido)` } },
        },
        scales: {
          x: { type: "linear", min: 0.75, max: 5, title: { display: true, text: "longitud de onda (µm)", color: "#8b95a7" }, ticks: { color: "#8b95a7" }, grid: { color: "rgba(29,42,68,0.6)" } },
          y: { title: { display: true, text: "flujo (mJy)", color: "#8b95a7" }, ticks: { color: "#8b95a7" }, grid: { color: "rgba(29,42,68,0.6)" } },
        },
      },
      plugins: [pluginFranjas, pluginErrores],
    }));
  }

  /** Pinta la sección en `contenedor`; la oculta si no hay espectro utilizable con composición. */
  HX.pintarComposicion = function (contenedor, espectro, origen) {
    if (!contenedor) return;
    const anterior = graficos.get(contenedor);
    if (!K.debeMostrarse(espectro)) {
      if (anterior) { anterior.destroy(); graficos.delete(contenedor); }
      contenedor.hidden = true;
      contenedor.innerHTML = "";
      return;
    }
    const c = espectro.composicion;
    const procedencia = ORIGEN[espectro.origen || origen] || "Origen de los datos no declarado";
    contenedor.hidden = false;
    contenedor.innerHTML = `
      <h4 class="composicion-titulo">Composición espectral</h4>
      <p class="aviso-conceptual">Busca rasgos en bandas de referencia. Una coincidencia aproximada de longitud
        de onda no prueba la composición: el estado dice cuánta evidencia hay.</p>
      <p class="composicion-resumen">${esc(K.resumen(c))}</p>
      <div class="composicion-grafico"><canvas aria-label="Espectro medido con las ventanas moleculares"></canvas></div>
      <p class="cmp-nota">Puntos: espectro medido. Franjas: ventanas de referencia de cada molécula (teóricas, no medidas),
        coloreadas por estado. El continuo que ajusta m6 no se publica.</p>
      <ul class="mol-lista">${K.ordenadas(c.moleculas).map(tarjeta).join("")}</ul>
      <p class="cmp-nota">Método ${esc(c.version_metodo)} · continuo: ${esc(c.continuo)} ·
        referencias: ${esc(c.origen_referencias === "bibliografia" ? "bibliografía" : c.origen_referencias || "no declaradas")} ·
        datos: ${esc(procedencia)}. Sin porcentajes de confianza: S es la significancia del rasgo en sigmas.</p>`;
    dibujar(contenedor.querySelector("canvas"), espectro, contenedor);
  };

  // Ficha del explorador.
  function iniciar() {
    const caja = document.getElementById("ficha-composicion");
    if (!caja || !K) return;
    HX.alSeleccionar.push((cand) => {
      const espectro = cand ? HX.espectroDe(cand.id_candidato) : null;
      HX.pintarComposicion(caja, espectro, HX.estado.meta && HX.estado.meta.origen);
    });
    HX.alCambiarCampo.push(() => HX.pintarComposicion(caja, null));
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
