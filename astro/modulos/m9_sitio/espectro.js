/* ============================================================================
   ARCHIVO: modulos/m9_sitio/espectro.js
   MODULO: m9_sitio (Lote D)
   ROL: Dibuja la huella espectral del candidato seleccionado.
   LEE: HX.estado.espectros (espectros.json de m7_publicacion) y el candidato
        activo; la librería Chart.js viene por CDN.
   PRODUCE: El gráfico de #grafico-espectro y su nota explicativa.
   VERIFICACION: Al cambiar de candidato con espectro, la curva cambia; un
                 candidato con tiene_espectro falso muestra la nota de vacío.
   ========================================================================== */
(function () {
  "use strict";

  const HX = (window.HX = window.HX || {});

  const ETIQUETA_TIPO = {
    asteroide_rocoso: "asteroide rocoso (tipo S)",
    asteroide_oscuro: "asteroide primitivo (tipo C)",
    cometa: "cometa",
    enana_marron: "enana marrón",
    indeterminado: "sin determinar",
  };

  let grafico = null;

  const puntos = (espectro) =>
    espectro.puntos.map((p) => ({ x: p.longitud_onda_micras, y: p.flujo_mjy }));

  function nota(texto) {
    const elemento = document.getElementById("ficha-espectro-nota");
    if (elemento) elemento.textContent = texto;
  }

  function pintar(cand) {
    const lienzo = document.getElementById("grafico-espectro");
    if (!lienzo) return;

    if (!cand) {
      nota("");
      return;
    }

    const espectro = HX.espectroDe(cand.id_candidato);
    if (!espectro) {
      nota("Sin huella espectral para este candidato (pareja descartada o sin cobertura).");
      if (grafico) {
        grafico.destroy();
        grafico = null;
      }
      return;
    }

    nota(
      `Huella espectral ${espectro.puntos[0].longitud_onda_micras}–` +
      `${espectro.puntos[espectro.puntos.length - 1].longitud_onda_micras} µm · ` +
      `${ETIQUETA_TIPO[espectro.tipo] || espectro.tipo}` +
      (espectro.temperatura_k
        ? ` · ${espectro.temperatura_k} K · pico de Wien ${espectro.pico_wien_micras} µm`
        : "")
    );

    if (typeof Chart === "undefined") {
      nota("Chart.js no se cargó: no se puede dibujar el espectro.");
      return;
    }

    if (grafico) {
      grafico.data.datasets[0].data = puntos(espectro);
      grafico.update("none");
      return;
    }

    grafico = new Chart(lienzo, {
      type: "line",
      data: {
        datasets: [{
          data: puntos(espectro),
          borderColor: "#ffb347",
          backgroundColor: "rgba(255,179,71,0.16)",
          borderWidth: 1.8,
          pointRadius: 0,
          fill: true,
          tension: 0.25,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        parsing: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: (items) => `${items[0].parsed.x.toFixed(2).replace(".", ",")} µm`,
              label: (item) => `${item.parsed.y} mJy`,
            },
          },
        },
        scales: {
          x: {
            type: "linear",
            min: 0.75,
            max: 5,
            title: { display: true, text: "longitud de onda (µm)", color: "#8b95a7", font: { size: 10 } },
            ticks: {
              color: "#8b95a7",
              maxTicksLimit: 6,
              font: { size: 9 },
              callback: (v) => Number(v).toFixed(1).replace(".", ","),
            },
            grid: { color: "rgba(29,42,68,0.6)" },
          },
          y: {
            title: { display: true, text: "flujo (mJy)", color: "#8b95a7", font: { size: 10 } },
            ticks: { color: "#8b95a7", maxTicksLimit: 4, font: { size: 9 } },
            grid: { color: "rgba(29,42,68,0.6)" },
          },
        },
      },
    });
  }

  function iniciar() {
    if (!document.getElementById("grafico-espectro")) return;
    HX.alSeleccionar.push(pintar);
    HX.alCambiarCampo.push(() => {
      if (grafico) {
        grafico.destroy();
        grafico = null;
      }
      nota("");
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
