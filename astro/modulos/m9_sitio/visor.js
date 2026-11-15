/* ============================================================================
   ARCHIVO: modulos/m9_sitio/visor.js
   MODULO: m9_sitio (Lote D)
   ROL: Dibuja las dos épocas en el lienzo según el modo elegido y aplica
        zoom y arrastre.
   LEE: HX.estado.imagenes (epoca_a.png, epoca_b.png) o, si faltan, los
        candidatos para sintetizar dos fotogramas; HX.estado.meta.epocas.
   PRODUCE: El lienzo pintado, las fechas y el tiempo transcurrido; expone
            HX.redibujar y HX.centrarEn.
   VERIFICACION: Los tres modos cambian la imagen; la rueda hace zoom y el
                 arrastre desplaza; Centrar devuelve zoom 1.
   ========================================================================== */
(function () {
  "use strict";

  const HX = (window.HX = window.HX || {});
  const ANCHO = 600;
  const ALTO = 600;
  const INTERVALO_PARPADEO = 450;
  const ZOOM_MIN = 1;
  const ZOOM_MAX = 8;
  const RADIO_CLIC = 22;

  let lienzo = null;
  let ctx = null;
  let cortinaEl = null;
  let fotogramaA = null;
  let fotogramaB = null;
  let fotogramaD = null;
  let ultimoParpadeo = 0;
  let arrastrando = false;
  let movido = false;
  let inicioArrastre = null;

  // ------------------------------------------------------------------ utiles --

  function mulberry32(semilla) {
    return function () {
      semilla |= 0;
      semilla = (semilla + 0x6d2b79f5) | 0;
      let t = Math.imul(semilla ^ (semilla >>> 15), 1 | semilla);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function hashTexto(txt) {
    let h = 2166136261;
    for (let i = 0; i < txt.length; i++) {
      h ^= txt.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }

  const limitar = (v, min, max) => Math.min(max, Math.max(min, v));

  function fechaDesdeMjd(mjd) {
    return new Date((mjd + 2400000.5 - 2440587.5) * 86400000);
  }

  function formatearFecha(fecha, conHora) {
    const opciones = { year: "numeric", month: "short", day: "numeric" };
    if (conHora) {
      opciones.hour = "2-digit";
      opciones.minute = "2-digit";
    }
    return fecha.toLocaleString("es-ES", opciones);
  }

  // --------------------------------------------------------- fotogramas demo --

  /**
   * Sustituto de epoca_a.png / epoca_b.png mientras el pipeline no los genera.
   * Estrellas fijas con la misma semilla en las dos épocas; solo se mueven los
   * candidatos. La coordenada y del contrato tiene el origen abajo: aquí se
   * invierte para dibujar en el lienzo.
   */
  function sintetizar(epoca) {
    const c = document.createElement("canvas");
    c.width = ANCHO;
    c.height = ALTO;
    const g = c.getContext("2d");
    const { meta, candidatos } = HX.estado;

    g.fillStyle = "#0b0f1a";
    g.fillRect(0, 0, ANCHO, ALTO);

    const rnd = mulberry32(hashTexto(meta.campo));
    for (let i = 0; i < 520; i++) {
      const x = rnd() * ANCHO;
      const y = rnd() * ALTO;
      const mag = Math.pow(rnd(), 3.2);
      const radio = 0.35 + mag * 1.9;
      const alfa = 0.18 + mag * 0.82;
      const grad = g.createRadialGradient(x, y, 0, x, y, radio * 2.6);
      grad.addColorStop(0, `rgba(230,234,242,${alfa})`);
      grad.addColorStop(1, "rgba(0,0,0,0)");
      g.fillStyle = grad;
      g.beginPath();
      g.arc(x, y, radio * 2.6, 0, Math.PI * 2);
      g.fill();
    }

    for (const cand of candidatos) {
      const pos = epoca === "a" ? cand.posicion_a : cand.posicion_b;
      if (!pos) continue;
      const px = pos.x;
      const py = ALTO - pos.y; // contrato: origen abajo
      const grad = g.createRadialGradient(px, py, 0, px, py, 16);
      grad.addColorStop(0, "rgba(255,255,255,0.98)");
      grad.addColorStop(0.3, "rgba(210,230,255,0.5)");
      grad.addColorStop(1, "rgba(120,160,255,0)");
      g.fillStyle = grad;
      g.beginPath();
      g.arc(px, py, 16, 0, Math.PI * 2);
      g.fill();
    }

    const rndRuido = mulberry32(hashTexto(meta.campo + epoca));
    for (let i = 0; i < 14; i++) {
      g.fillStyle = `rgba(255,255,255,${0.25 + rndRuido() * 0.4})`;
      g.beginPath();
      g.arc(rndRuido() * ANCHO, rndRuido() * ALTO, 0.8 + rndRuido() * 1.6, 0, Math.PI * 2);
      g.fill();
    }
    return c;
  }

  function diferencia(a, b) {
    const c = document.createElement("canvas");
    c.width = ANCHO;
    c.height = ALTO;
    const g = c.getContext("2d");
    const da = a.getContext("2d").getImageData(0, 0, ANCHO, ALTO);
    const db = b.getContext("2d").getImageData(0, 0, ANCHO, ALTO);
    const salida = g.createImageData(ANCHO, ALTO);

    for (let i = 0; i < da.data.length; i += 4) {
      const lumA = (da.data[i] * 0.299 + da.data[i + 1] * 0.587 + da.data[i + 2] * 0.114) / 255;
      const lumB = (db.data[i] * 0.299 + db.data[i + 1] * 0.587 + db.data[i + 2] * 0.114) / 255;
      const d = lumB - lumA;
      if (d > 0.045) {
        const f = Math.min(1, d * 4.5);
        salida.data[i] = 74 * f;
        salida.data[i + 1] = 222 * f;
        salida.data[i + 2] = 128 * f;
      } else if (d < -0.045) {
        const f = Math.min(1, -d * 4.5);
        salida.data[i] = 248 * f;
        salida.data[i + 1] = 113 * f;
        salida.data[i + 2] = 113 * f;
      } else {
        salida.data[i] = 11;
        salida.data[i + 1] = 15;
        salida.data[i + 2] = 26;
      }
      salida.data[i + 3] = 255;
    }
    g.putImageData(salida, 0, 0);
    return c;
  }

  /** Acepta un HTMLImageElement o un canvas y devuelve algo dibujable. */
  function comoCanvas(origen) {
    if (!origen) return null;
    if (origen instanceof HTMLCanvasElement) return origen;
    const c = document.createElement("canvas");
    c.width = ANCHO;
    c.height = ALTO;
    c.getContext("2d").drawImage(origen, 0, 0, ANCHO, ALTO);
    return c;
  }

  function prepararFotogramas() {
    const { imagenes, meta, candidatos } = HX.estado;
    if (!meta) return;

    fotogramaA = imagenes.a
      ? comoCanvas(imagenes.a)
      : sintetizar("a");
    fotogramaB = imagenes.b
      ? comoCanvas(imagenes.b)
      : sintetizar("b");
    fotogramaD = diferencia(fotogramaA, fotogramaB);

    // Aviso visible cuando las imágenes no vienen del pipeline.
    const aviso = document.getElementById("aviso-sintesis");
    if (aviso) aviso.hidden = Boolean(imagenes.a && imagenes.b);
    HX.fotogramas = { a: fotogramaA, b: fotogramaB, d: fotogramaD };
  }

  // ------------------------------------------------------------------ dibujo --

  function dibujar() {
    if (!ctx) return;
    const e = HX.estado;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = "#0b0f1a";
    ctx.fillRect(0, 0, ANCHO, ALTO);
    if (!fotogramaA) return;

    const base = e.modo === "diferencia" ? fotogramaD : e.epoca === "a" ? fotogramaA : fotogramaB;
    ctx.setTransform(e.zoom, 0, 0, e.zoom, e.offsetX, e.offsetY);

    if (e.modo === "cortina") {
      ctx.drawImage(fotogramaA, 0, 0);
      const corte = limitar(e.cortina, 0, 1) * ANCHO;
      ctx.save();
      ctx.beginPath();
      ctx.rect(0, 0, corte, ALTO);
      ctx.clip();
      ctx.drawImage(fotogramaB, 0, 0);
      ctx.restore();
      ctx.strokeStyle = "rgba(255,179,71,0.9)";
      ctx.lineWidth = 1.5 / e.zoom;
      ctx.beginPath();
      ctx.moveTo(corte, 0);
      ctx.lineTo(corte, ALTO);
      ctx.stroke();
    } else {
      ctx.drawImage(base, 0, 0);
    }

    if (typeof HX.dibujarSuperposicion === "function") {
      HX.dibujarSuperposicion(ctx, e);
    }

    ctx.setTransform(1, 0, 0, 1, 0, 0);

    if (cortinaEl) {
      const visible = e.modo === "cortina";
      cortinaEl.classList.toggle("visible", visible);
      if (visible) {
        const caja = lienzo.getBoundingClientRect();
        const x = limitar(e.cortina, 0, 1) * ANCHO * e.zoom + e.offsetX;
        cortinaEl.style.left = (x / ANCHO) * caja.width + "px";
      }
    }
  }

  // ------------------------------------------------------------ interacción --

  function aCoordenadasImagen(evento) {
    const caja = lienzo.getBoundingClientRect();
    const x = ((evento.clientX - caja.left) / caja.width) * ANCHO;
    const y = ((evento.clientY - caja.top) / caja.height) * ALTO;
    return {
      x: (x - HX.estado.offsetX) / HX.estado.zoom,
      y: (y - HX.estado.offsetY) / HX.estado.zoom,
    };
  }

  function candidatoCercano(punto) {
    let mejor = null;
    let mejorDist = RADIO_CLIC;
    for (const cand of HX.estado.candidatos) {
      const pos = cand.posicion_a;
      if (!pos) continue;
      const d = Math.hypot(pos.x - punto.x, (ALTO - pos.y) - punto.y);
      if (d < mejorDist) {
        mejorDist = d;
        mejor = cand;
      }
    }
    return mejor;
  }

  function limitarDesplazamiento() {
    const e = HX.estado;
    e.offsetX = limitar(e.offsetX, ANCHO - ANCHO * e.zoom, 0);
    e.offsetY = limitar(e.offsetY, ALTO - ALTO * e.zoom, 0);
  }

  HX.centrarEn = function (cand) {
    if (!cand || !cand.posicion_a) return;
    const e = HX.estado;
    e.zoom = Math.max(e.zoom, 2.4);
    e.offsetX = ANCHO / 2 - cand.posicion_a.x * e.zoom;
    e.offsetY = ALTO / 2 - (ALTO - cand.posicion_a.y) * e.zoom;
    limitarDesplazamiento();
    dibujar();
  };

  HX.redibujar = dibujar;

  HX.reconstruirFotogramas = function () {
    prepararFotogramas();
    dibujar();
  };

  function pintarFechas() {
    const meta = HX.estado.meta;
    if (!meta) return;
    const mjdA = meta.epocas.epoca_a.mjd;
    const mjdB = meta.epocas.epoca_b.mjd;
    const horas = meta.horas_entre_a_b;
    const conHora = horas < 24;

    document.getElementById("fecha-a").textContent = formatearFecha(fechaDesdeMjd(mjdA), conHora);
    document.getElementById("fecha-b").textContent = formatearFecha(fechaDesdeMjd(mjdB), conHora);
    document.getElementById("transcurrido").textContent =
      (horas < 24 ? horas.toFixed(1) : (horas / 24).toFixed(1)).replace(".", ",") +
      (horas < 24 ? " h" : " días");
  }

  function cambiarModo(modo) {
    HX.estado.modo = modo;
    for (const nombre of ["parpadeo", "cortina", "diferencia"]) {
      const boton = document.getElementById(`modo-${nombre}`);
      if (boton) boton.classList.toggle("activo", nombre === modo);
    }
    // Pausa solo tiene sentido con el parpadeo: en los otros dos modos la
    // imagen es estática y el botón no haría nada.
    const reproducir = document.getElementById("btn-reproducir");
    if (reproducir) {
      const aplica = modo === "parpadeo";
      reproducir.hidden = !aplica;
      reproducir.disabled = !aplica;
      if (aplica) reproducir.textContent = HX.estado.reproduciendo ? "Pausa" : "Reproducir";
    }
    dibujar();
  }

  function bucle(t) {
    requestAnimationFrame(bucle);
    const e = HX.estado;
    if (e.modo !== "parpadeo" || !e.reproduciendo) return;
    if (t - ultimoParpadeo < INTERVALO_PARPADEO) return;
    ultimoParpadeo = t;
    e.epoca = e.epoca === "a" ? "b" : "a";
    dibujar();
  }

  function conectar() {
    lienzo.addEventListener(
      "wheel",
      (ev) => {
        ev.preventDefault();
        const caja = lienzo.getBoundingClientRect();
        const cx = ((ev.clientX - caja.left) / caja.width) * ANCHO;
        const cy = ((ev.clientY - caja.top) / caja.height) * ALTO;
        const factor = ev.deltaY < 0 ? 1.14 : 1 / 1.14;
        const nz = limitar(HX.estado.zoom * factor, ZOOM_MIN, ZOOM_MAX);
        const razon = nz / HX.estado.zoom;
        HX.estado.offsetX = cx - (cx - HX.estado.offsetX) * razon;
        HX.estado.offsetY = cy - (cy - HX.estado.offsetY) * razon;
        HX.estado.zoom = nz;
        dibujar();
      },
      { passive: false }
    );

    lienzo.addEventListener("pointerdown", (ev) => {
      lienzo.setPointerCapture(ev.pointerId);
      arrastrando = true;
      movido = false;
      inicioArrastre = {
        x: ev.clientX,
        y: ev.clientY,
        offsetX: HX.estado.offsetX,
        offsetY: HX.estado.offsetY,
      };
      lienzo.classList.add("arrastrando");
    });

    lienzo.addEventListener("pointermove", (ev) => {
      if (!arrastrando || !inicioArrastre) return;
      const dx = ev.clientX - inicioArrastre.x;
      const dy = ev.clientY - inicioArrastre.y;
      if (Math.abs(dx) + Math.abs(dy) > 4) movido = true;

      if (HX.estado.modo === "cortina") {
        const caja = lienzo.getBoundingClientRect();
        HX.estado.cortina = limitar((ev.clientX - caja.left) / caja.width, 0.02, 0.98);
      } else {
        const caja = lienzo.getBoundingClientRect();
        const escala = ANCHO / caja.width;
        HX.estado.offsetX = inicioArrastre.offsetX + dx * escala;
        HX.estado.offsetY = inicioArrastre.offsetY + dy * escala;
        limitarDesplazamiento();
      }
      dibujar();
    });

    const soltar = (ev) => {
      if (!arrastrando) return;
      arrastrando = false;
      lienzo.classList.remove("arrastrando");
      if (!movido) {
        const cand = candidatoCercano(aCoordenadasImagen(ev));
        if (cand) HX.seleccionar(cand.id_candidato, false);
      }
      inicioArrastre = null;
    };
    lienzo.addEventListener("pointerup", soltar);
    lienzo.addEventListener("pointercancel", soltar);
  }

  function iniciar() {
    lienzo = document.getElementById("lienzo");
    if (!lienzo) return;
    ctx = lienzo.getContext("2d");
    cortinaEl = document.getElementById("cortina");

    for (const nombre of ["parpadeo", "cortina", "diferencia"]) {
      const boton = document.getElementById("modo-" + nombre);
      if (boton) boton.addEventListener("click", () => cambiarModo(nombre));
    }

    const botonReproducir = document.getElementById("btn-reproducir");
    if (botonReproducir) {
      botonReproducir.addEventListener("click", () => {
        HX.estado.reproduciendo = !HX.estado.reproduciendo;
        botonReproducir.textContent = HX.estado.reproduciendo ? "Pausa" : "Reproducir";
      });
    }

    const botonCentrar = document.getElementById("btn-reset");
    if (botonCentrar) {
      botonCentrar.addEventListener("click", () => {
        HX.estado.zoom = 1;
        HX.estado.offsetX = 0;
        HX.estado.offsetY = 0;
        dibujar();
      });
    }

    conectar();
    requestAnimationFrame(bucle);
  }

  HX.alCambiarCampo.push(() => {
    pintarFechas();
    prepararFotogramas();
    dibujar();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
