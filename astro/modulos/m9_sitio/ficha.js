/* ============================================================================
   ARCHIVO: modulos/m9_sitio/ficha.js
   MODULO: m9_sitio (Lote D)
   ROL: Muestra la ficha del candidato seleccionado y un mapa del cielo
        centrado en su posición.
   LEE: HX.estado.candidatos, HX.estado.meta y, para el mapa, Aladin Lite.
   PRODUCE: El contenido de #ficha-contenido y #mapa-aladin.
   VERIFICACION: Al seleccionar un candidato la ficha muestra su posición y su
                 clase; la nota de «candidato» está siempre visible.
   ========================================================================== */
(function () {
  "use strict";

  const HX = (window.HX = window.HX || {});

  const ETIQUETA_TIPO = {
    asteroide_rocoso: "Asteroide rocoso (tipo S)",
    asteroide_oscuro: "Asteroide primitivo (tipo C)",
    cometa: "Cometa (hielo + CO₂)",
    enana_marron: "Enana marrón (metano)",
    indeterminado: "Sin determinar",
  };

  let contenedor = null;
  let mapaAladin = null;
  let estructuraLista = false;
  let aladinListo = false;
  let hipsDisponible = null;

  const numero = (valor, decimales) =>
    valor === null || valor === undefined || Number.isNaN(valor)
      ? "—"
      : valor.toFixed(decimales).replace(".", ",");

  function estructura() {
    contenedor.innerHTML = `
      <div class="aviso-candidato">
        <b>candidato</b> — dos detecciones no demuestran un objeto nuevo.
        Esta ficha describe una pareja verificada contra catálogos, no un descubrimiento.
      </div>
      <h3 id="ficha-nombre">—</h3>
      <div class="subtitulo" id="ficha-subtitulo">—</div>
      <dl id="ficha-datos"></dl>
      <div id="mapa-aladin" aria-label="Mapa del cielo centrado en el candidato"></div>`;
    estructuraLista = true;
  }

  function vaciar() {
    contenedor.innerHTML =
      '<p class="vacio">Selecciona un candidato en el visor o en la tabla.</p>';
    estructuraLista = false;
    mapaAladin = null;
  }

  async function hipsResponde() {
    if (hipsDisponible !== null) return hipsDisponible;
    try {
      const control = new AbortController();
      const t = setTimeout(() => control.abort(), 2500);
      await fetch("https://alasky.unistra.fr/DSS/DSSColor/Norder3/Dir0/Npix0.jpg",
        { signal: control.signal, mode: "no-cors" });
      clearTimeout(t);
      hipsDisponible = true;
    } catch (error) {
      hipsDisponible = false;
    }
    return hipsDisponible;
  }

  function mapaRespaldo(div, ra, dec) {
    const ancho = Math.max(div.clientWidth || 320, 280);
    const alto = div.clientHeight || 190;
    const dpr = window.devicePixelRatio || 1;
    div.innerHTML = `<canvas width="${ancho * dpr}" height="${alto * dpr}"
        style="width:100%;height:100%;display:block"></canvas>
      <div class="nota-mapa">Mapa aproximado · servicio HiPS no disponible</div>`;

    const g = div.querySelector("canvas").getContext("2d");
    g.scale(dpr, dpr);
    g.fillStyle = "#0b0f1a";
    g.fillRect(0, 0, ancho, alto);
    g.strokeStyle = "rgba(255,179,71,0.14)";
    g.lineWidth = 1;
    for (let i = 1; i < 6; i++) {
      const x = (ancho / 6) * i;
      g.beginPath(); g.moveTo(x, 0); g.lineTo(x, alto); g.stroke();
      if (i < 4) {
        const y = (alto / 4) * i;
        g.beginPath(); g.moveTo(0, y); g.lineTo(ancho, y); g.stroke();
      }
    }
    g.strokeStyle = "rgba(139,149,167,0.4)";
    g.beginPath();
    g.moveTo(ancho / 2, alto / 2 - 14); g.lineTo(ancho / 2, alto / 2 + 14);
    g.moveTo(ancho / 2 - 14, alto / 2); g.lineTo(ancho / 2 + 14, alto / 2);
    g.stroke();
    g.fillStyle = "#ffb347";
    g.beginPath();
    g.arc(ancho / 2, alto / 2, 3.5, 0, Math.PI * 2);
    g.fill();
    g.fillStyle = "#8b95a7";
    g.font = "10px ui-monospace, monospace";
    g.fillText(`RA ${ra.toFixed(2)}°  Dec ${dec.toFixed(2)}°`.replace(/\./g, ","), ancho / 2 + 12, alto / 2 - 10);
  }

  async function mapa(ra, dec) {
    const div = document.getElementById("mapa-aladin");
    if (!div) return;

    if (!aladinListo || !window.A || !window.A.aladin || !(await hipsResponde())) {
      mapaRespaldo(div, ra, dec);
      return;
    }
    try {
      if (!mapaAladin) {
        div.innerHTML = "";
        mapaAladin = window.A.aladin(div, {
          target: `${ra} ${dec}`,
          fov: 0.06,
          survey: "P/DSS2/color",
          showCooGrid: false,
          showLayersControl: false,
          showGotoControl: false,
          showFrame: false,
        });
      } else {
        mapaAladin.gotoRaDec(ra, dec);
      }
    } catch (error) {
      console.warn("Aladin:", error);
      mapaRespaldo(div, ra, dec);
    }
  }

  function pintar(cand) {
    if (!cand) {
      vaciar();
      return;
    }
    if (!estructuraLista) estructura();

    const meta = HX.estado.meta || {};
    document.getElementById("ficha-nombre").textContent =
      cand.nombre_objeto || (cand.estado === "artefacto_descartado" ? "Artefacto descartado" : "Sin identificar");
    document.getElementById("ficha-subtitulo").textContent =
      `${meta.nombre || ""} · detector ${meta.detector} · ${numero(meta.escala_segarc_por_pixel, 2)}″/px`;

    const filas = [
      ["Posición A (RA, Dec)", `${numero(cand.posicion_a.ra_grados, 3)}°, ${numero(cand.posicion_a.dec_grados, 3)}°`],
      ["Separación", `${numero(cand.separacion_segarc, 1)}″`],
      ["Velocidad", `${numero(cand.velocidad_segarc_por_hora, 2)} ± ${numero(cand.incertidumbre_velocidad, 2)} ″/h`],
      ["Significancia", `${numero(cand.significancia, 1)} σ`],
      ["Clase", cand.clase_movimiento],
    ];
    if (cand.tipo) filas.push(["Tipo estimado", ETIQUETA_TIPO[cand.tipo] || cand.tipo]);
    if (cand.temperatura_k) filas.push(["Temperatura (Planck)", `${numero(cand.temperatura_k, 0)} K`]);
    if (cand.distancia_catalogo_segarc !== null && cand.distancia_catalogo_segarc !== undefined) {
      filas.push(["Distancia al catálogo", `${numero(cand.distancia_catalogo_segarc, 2)}″`]);
    }
    filas.push(["Estado", cand.estado]);

    document.getElementById("ficha-datos").innerHTML = filas
      .map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`)
      .join("");

    mapa(cand.posicion_a.ra_grados, cand.posicion_a.dec_grados);
  }

  function iniciar() {
    contenedor = document.getElementById("ficha-contenido");
    if (!contenedor) return;

    HX.alSeleccionar.push(pintar);
    HX.alCambiarCampo.push(() => {
      mapaAladin = null;
      vaciar();
    });

    window.addEventListener("aladin-listo", () => {
      aladinListo = true;
      const cand = HX.candidatoActual();
      if (cand) mapa(cand.posicion_a.ra_grados, cand.posicion_a.dec_grados);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
