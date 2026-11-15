/* ============================================================================
   ARCHIVO: modulos/m9_sitio/identificar.js
   MODULO: m9_sitio (Lote D)
   ROL: Pestaña «Identificar»: imagen del campo con zoom, clic -> píxel -> RA/DEC
        con el WCS publicado, detección marcada más cercana con su identificación
        de m5 y consulta en vivo de efemérides de cuerpos menores (SkyBoT, IMCCE)
        para la fecha de la época A.
   LEE: HX.estado (meta con wcs, candidatos), HX.fotogramas.a (visor.js) y, a petición,
        el servicio SkyBoT. Lógica en identificar_logica.js.
   PRODUCE: El contenido de #panel-identificar.
   VERIFICACION: Un clic muestra píxel, RA/DEC y época; sin wcs avisa y no inventa
                 coordenadas; la consulta muestra cargando, error, vacío o coincidencias.
   NOTA: Las estrellas (Gaia DR3) no se consultan desde el navegador: los archivos de
         la ESA y del CDS no permiten peticiones de otra web (CORS). Queda pendiente
         precalcularlas en m5.
   ========================================================================== */
(function () {
  "use strict";

  const HX = (window.HX = window.HX || {});
  const I = window.HXIdentificar;
  const L = I ? I.LADO_LIENZO : 600;

  const est = { zoom: 1, ox: 0, oy: 0, sel: null, arrastre: null, consulta: 0 };
  const $ = (id) => document.getElementById(id);
  const coma = (n, d) => Number(n).toFixed(d).replace(".", ",");
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  // ------------------------------------------------------------------ dibujo
  function dibujar() {
    const lienzo = $("id-lienzo");
    if (!lienzo) return;
    const g = lienzo.getContext("2d");
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.fillStyle = "#0b0f1a";
    g.fillRect(0, 0, L, L);
    const { meta, candidatos } = HX.estado;
    if (!meta) return;
    g.setTransform(est.zoom, 0, 0, est.zoom, est.ox, est.oy);
    const fondo = HX.fotogramas && HX.fotogramas.a;
    if (fondo) g.drawImage(fondo, 0, 0, L, L);
    for (const c of candidatos) {
      if (!c.posicion_a || c.estado === "artefacto_descartado") continue;
      const p = I.pixelALienzo(meta, c.posicion_a.x, c.posicion_a.y);
      g.strokeStyle = c.estado === "conocido" ? "#4ade80" : "#ffb347";
      g.lineWidth = 1.5 / est.zoom;
      g.beginPath();
      g.arc(p.cx, p.cy, 9 / est.zoom, 0, 2 * Math.PI);
      g.stroke();
      g.fillStyle = g.strokeStyle;
      g.font = `${11 / est.zoom}px sans-serif`;
      g.fillText(c.id_candidato, p.cx + 11 / est.zoom, p.cy - 8 / est.zoom);
    }
    if (est.sel) {
      const p = I.pixelALienzo(meta, est.sel.x, est.sel.y);
      g.strokeStyle = "#7DD3FC";
      g.lineWidth = 1.5 / est.zoom;
      const r = 6 / est.zoom;
      g.beginPath();
      g.moveTo(p.cx - 2.2 * r, p.cy); g.lineTo(p.cx - r, p.cy);
      g.moveTo(p.cx + r, p.cy); g.lineTo(p.cx + 2.2 * r, p.cy);
      g.moveTo(p.cx, p.cy - 2.2 * r); g.lineTo(p.cx, p.cy - r);
      g.moveTo(p.cx, p.cy + r); g.lineTo(p.cx, p.cy + 2.2 * r);
      g.stroke();
    }
  }

  function aLienzo(evento) {
    const caja = $("id-lienzo").getBoundingClientRect();
    const x = ((evento.clientX - caja.left) / caja.width) * L;
    const y = ((evento.clientY - caja.top) / caja.height) * L;
    return { cx: (x - est.ox) / est.zoom, cy: (y - est.oy) / est.zoom, x, y };
  }

  function zoom(factor, cx = L / 2, cy = L / 2) {
    const nuevo = Math.min(8, Math.max(1, est.zoom * factor));
    est.ox = cx - ((cx - est.ox) / est.zoom) * nuevo;
    est.oy = cy - ((cy - est.oy) / est.zoom) * nuevo;
    est.zoom = nuevo;
    limitar();
    dibujar();
  }

  function limitar() {
    est.ox = Math.min(0, Math.max(L - L * est.zoom, est.ox));
    est.oy = Math.min(0, Math.max(L - L * est.zoom, est.oy));
  }

  // ------------------------------------------------------------------ panel
  function pintarCabecera() {
    const { meta } = HX.estado;
    const sel = $("id-campo");
    sel.innerHTML = "";
    for (const c of HX.estado.indice) sel.add(new Option(c.nombre, c.campo));
    sel.value = HX.estado.campo || "";
    const real = HX.estado.imagenes && HX.estado.imagenes.a;
    $("id-imagen-nota").textContent = !meta ? "" : real
      ? `Época A de SPHEREx (${meta.epocas.epoca_a.id_exposicion}).`
      : "Imagen sintética de demostración: el fondo no es una observación; las marcas son las detecciones publicadas.";
    $("id-sin-wcs").hidden = !meta || I.tieneWcs(meta);
  }

  function filas(pares) {
    return `<dl class="cat-dl">${pares.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join("")}</dl>`;
  }

  function pintarSeleccion() {
    const caja = $("id-fuente");
    const { meta } = HX.estado;
    if (!est.sel) {
      caja.innerHTML = `<p class="vacio">Haz clic en una fuente de la imagen o en una detección marcada.</p>`;
      $("id-consulta").hidden = true;
      $("id-resultados").innerHTML = "";
      return;
    }
    const pares = [["Píxel (base 0)", `x = ${coma(est.sel.x, 1)}, y = ${coma(est.sel.y, 1)}`]];
    if (!I.tieneWcs(meta)) {
      caja.innerHTML = filas(pares) +
        `<p class="aviso-conceptual">Este campo no publica WCS: no se pueden calcular coordenadas celestes y no se inventan.</p>`;
      $("id-consulta").hidden = true;
      return;
    }
    const s = est.sel.cielo;
    pares.push(["RA, DEC (ICRS)", `${coma(s.ra_grados, 5)}°, ${coma(s.dec_grados, 5)}°<br><span class="cmp-meta">${I.sexagesimal(s.ra_grados, true)} · ${I.sexagesimal(s.dec_grados, false)}</span>`]);
    pares.push(["Época A (UTC)", `${I.mjdAIso(meta.epocas.epoca_a.mjd)} <span class="cmp-meta">MJD ${coma(meta.epocas.epoca_a.mjd, 5)}</span>`]);
    pares.push(["Incertidumbre del clic", `± ${coma(meta.escala_segarc_por_pixel / 2, 2)}″ (medio píxel)`]);
    let deteccion = "";
    const d = est.sel.deteccion;
    if (d) {
      const sep = I.separacionSegarc(s.ra_grados, s.dec_grados, d.posicion_a.ra_grados, d.posicion_a.dec_grados);
      const ident = d.estado === "conocido"
        ? `Identificada por m5 como <b>${esc(d.nombre_objeto)}</b> a ${coma(d.distancia_catalogo_segarc, 2)}″ de la posición predicha para la época A` +
          (meta.origen === "sintetico" ? " (identificación de demostración)." : ".")
        : d.estado === "sin_identificar"
          ? "Objeto no identificado en los catálogos consultados por m5 (JPL sb_ident, MPChecker). No equivale a un descubrimiento."
          : "Pareja descartada como artefacto.";
      deteccion = `<div class="id-deteccion"><h4>Detección de HUELLA X · ${esc(d.id_candidato)}</h4>
        <p class="cmp-meta">Posición de la época A a ${coma(sep, 1)}″ del clic.</p><p>${ident}</p>
        <div class="cat-acciones">
          <button id="id-ver-movimiento">Analizar movimiento en el explorador</button>
          ${HX.abrirComparacion ? `<button id="id-ver-catalogo">Ver en el catálogo</button>` : ""}
        </div></div>`;
    }
    caja.innerHTML = filas(pares) + deteccion;
    $("id-consulta").hidden = false;
    if ($("id-ver-movimiento")) $("id-ver-movimiento").addEventListener("click", () => HX.verEnExplorador(HX.estado.campo, d.id_candidato));
    if ($("id-ver-catalogo")) $("id-ver-catalogo").addEventListener("click", () => { HX.mostrarPestana("catalogo"); });
  }

  // ------------------------------------------------------------------ SkyBoT
  async function consultar() {
    const { meta } = HX.estado;
    if (!est.sel || !I.tieneWcs(meta)) return;
    const caja = $("id-resultados");
    const yo = ++est.consulta;
    const { ra_grados: ra, dec_grados: dec } = est.sel.cielo;
    const mjd = meta.epocas.epoca_a.mjd;
    caja.innerHTML = `<p class="vacio" role="status">Consultando SkyBoT (IMCCE) para ${I.mjdAIso(mjd)}…</p>`;
    let datos;
    try {
      const control = new AbortController();
      const reloj = setTimeout(() => control.abort(), 20000);
      const r = await fetch(I.urlSkybot(ra, dec, mjd), { signal: control.signal });
      clearTimeout(reloj);
      if (r.status === 204) datos = [];
      else if (!r.ok) throw new Error(`HTTP ${r.status}`);
      else datos = await r.json();
    } catch (error) {
      if (yo !== est.consulta) return;
      caja.innerHTML = `<p class="cmp-compat incompatible">Error de red o del servicio externo (${esc(error.message || error)}).
        No se ha podido consultar SkyBoT; la posición y la detección siguen siendo válidas. Prueba de nuevo más tarde.</p>`;
      return;
    }
    if (yo !== est.consulta) return; // llegó una consulta más reciente
    const lista = I.leerSkybot(datos, ra, dec);
    const r = I.clasificar(lista, meta.escala_segarc_por_pixel);
    const clase = { coincidencia_compatible: "ok", coincidencia_ambigua: "aviso", sin_coincidencia_concluyente: "aviso" }[r.veredicto];
    const tabla = lista.length ? `<div class="tabla-scroll"><table class="cmp-tabla">
        <thead><tr><th>Objeto</th><th>Clase (SkyBoT)</th><th>RA, DEC predichas</th><th>Separación</th><th>Error efeméride</th><th>Tolerancia</th><th></th></tr></thead>
        <tbody>${r.coincidencias.map((c) => `<tr${c.dentro ? ' class="mejor"' : ""}>
          <td>${c.enlace ? `<a href="${esc(c.enlace)}" target="_blank" rel="noopener">${esc(c.nombre)}</a>` : esc(c.nombre)}</td>
          <td>${esc(c.clase_skybot || "—")}</td>
          <td>${coma(c.ra_grados, 5)}°, ${coma(c.dec_grados, 5)}°</td>
          <td>${coma(c.separacion_segarc, 1)}″</td>
          <td>${c.incertidumbre_segarc === null ? "—" : coma(c.incertidumbre_segarc, 2) + "″"}</td>
          <td>${coma(c.tolerancia_segarc, 1)}″</td>
          <td>${c.dentro ? "dentro" : "fuera"}</td></tr>`).join("")}</tbody></table></div>` : "";
    const demo = meta.origen === "sintetico"
      ? `<p class="aviso-conceptual">Datos de demostración: las posiciones de este campo son inventadas y SkyBoT consulta el
          cielo real en esa fecha, así que lo normal es que no encuentre los objetos de la demo.</p>` : "";
    caja.innerHTML = `${demo}
      <div class="cmp-compat ${clase}"><b>${esc(I.VEREDICTO[r.veredicto])}.</b>
        ${lista.length ? `${lista.length} cuerpo${lista.length === 1 ? "" : "s"} menor${lista.length === 1 ? "" : "es"} conocido${lista.length === 1 ? "" : "s"} a menos de ${I.RADIO_BUSQUEDA_SEGARC}″.` : `Ningún cuerpo menor conocido a menos de ${I.RADIO_BUSQUEDA_SEGARC}″ en esa fecha.`}
        ${r.veredicto === "sin_coincidencia_concluyente" ? " No se le asigna ninguna identidad por aproximación." : ""}
        ${r.veredicto === "coincidencia_ambigua" ? " Inspecciona las filas dentro de la tolerancia: no se elige una." : ""}</div>
      ${tabla}
      <p class="cmp-nota">Fuente: SkyBoT (IMCCE, ssp.imcce.fr), efemérides de asteroides, planetas y cometas para JD ${coma(I.mjdAJd(mjd), 5)}
        (época A, MJD de la cabecera tomado como UTC), observador geocéntrico (código 500): SPHEREx orbita a ~700 km, lo que
        para un objeto cercano a la Tierra puede mover la posición unos segundos de arco. Criterio: ${esc(r.criterio)}.
        Un objeto que no está en estas efemérides no es por ello un objeto nuevo.</p>`;
  }

  // ------------------------------------------------------------------ inicio
  function seleccionar(evento) {
    const { meta, candidatos } = HX.estado;
    if (!meta) return;
    const p = aLienzo(evento);
    const pixel = I.lienzoAPixel(meta, p.cx, p.cy);
    // 10 px de pantalla alrededor de la marca, pasados a píxeles de la rejilla; nunca menos de RADIO_SNAP_PIXELES.
    const radio = Math.max(I.RADIO_SNAP_PIXELES, (10 / est.zoom) * (meta.tamano_pixeles.ancho / L));
    const deteccion = I.deteccionCercana(candidatos.filter((c) => c.estado !== "artefacto_descartado"), pixel.x, pixel.y, radio);
    const x = deteccion ? deteccion.posicion_a.x : pixel.x;
    const y = deteccion ? deteccion.posicion_a.y : pixel.y;
    est.sel = { x, y, deteccion, cielo: I.tieneWcs(meta) ? I.pixelACielo(meta.wcs, x, y) : null };
    est.consulta++; // invalida respuestas pendientes de la selección anterior
    $("id-resultados").innerHTML = "";
    pintarSeleccion();
    dibujar();
  }

  function iniciar() {
    if (!$("panel-identificar") || !I) return;
    const lienzo = $("id-lienzo");
    lienzo.addEventListener("pointerdown", (e) => { est.arrastre = { x: e.clientX, y: e.clientY, ox: est.ox, oy: est.oy, movido: false }; });
    lienzo.addEventListener("pointermove", (e) => {
      if (!est.arrastre || est.zoom === 1) return;
      const caja = lienzo.getBoundingClientRect();
      const dx = ((e.clientX - est.arrastre.x) / caja.width) * L;
      const dy = ((e.clientY - est.arrastre.y) / caja.height) * L;
      if (Math.hypot(dx, dy) > 3) est.arrastre.movido = true;
      est.ox = est.arrastre.ox + dx;
      est.oy = est.arrastre.oy + dy;
      limitar();
      dibujar();
    });
    lienzo.addEventListener("pointerup", (e) => {
      const movido = est.arrastre && est.arrastre.movido;
      est.arrastre = null;
      if (!movido) seleccionar(e);
    });
    lienzo.addEventListener("wheel", (e) => {
      e.preventDefault();
      const p = aLienzo(e);
      zoom(e.deltaY < 0 ? 1.25 : 0.8, p.x, p.y);
    }, { passive: false });
    $("id-zoom-mas").addEventListener("click", () => zoom(1.5));
    $("id-zoom-menos").addEventListener("click", () => zoom(1 / 1.5));
    $("id-zoom-reset").addEventListener("click", () => { est.zoom = 1; est.ox = 0; est.oy = 0; dibujar(); });
    $("id-campo").addEventListener("change", (e) => HX.cargarCampo(e.target.value));
    $("id-consultar").addEventListener("click", consultar);
    HX.alCambiarCampo.push(() => {
      est.sel = null; est.zoom = 1; est.ox = 0; est.oy = 0; est.consulta++;
      pintarCabecera(); pintarSeleccion(); dibujar();
    });
    HX.alAbrirPestana.push((nombre) => { if (nombre === "identificar") { pintarCabecera(); pintarSeleccion(); dibujar(); } });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
