/* ============================================================================
   ARCHIVO: modulos/m9_sitio/catalogo.js
   MODULO: m9_sitio (Lote D)
   ROL: Dibuja el catálogo navegable: lista con búsqueda y filtros, ficha del
        objeto, su espectro y dos listas separadas (misma clasificación y
        espectros más similares) que abren el comparador.
   LEE: datos/m7_publicacion/catalogo.json y, para el gráfico, el espectros.json
        del campo del objeto (vía HX.leerDatos). Lógica en catalogo_logica.js.
   PRODUCE: El contenido de #panel-catalogo.
   VERIFICACION: Buscar «slipher» deja una fila; al pulsarla se ve su ficha y el
                 botón «Comparar» de un similar abre el comparador con los dos.
   ========================================================================== */
(function () {
  "use strict";

  const HX = (window.HX = window.HX || {});
  const C = window.HXCatalogo;

  const est = { promesa: null, objetos: [], porId: new Map(), filtros: {}, actual: null, grafico: null };
  const $ = (id) => document.getElementById(id);
  const coma = (n, d) => Number(n).toFixed(d).replace(".", ",");
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function cargar() {
    if (!est.promesa) {
      est.promesa = (async () => {
        $("cat-estado").textContent = "Cargando catálogo…";
        try {
          const doc = await HX.leerDatos("catalogo.json");
          est.objetos = doc.objetos || [];
          est.porId = new Map(est.objetos.map((o) => [o.id_objeto, o]));
          $("cat-estado").textContent = "";
          pintarFiltros();
          pintarLista();
        } catch (error) {
          console.warn(error);
          $("cat-estado").textContent =
            "catalogo.json no está publicado: falta ejecutar indice_catalogo.py de m7 (ver el LEEME de m9).";
        }
      })();
    }
    return est.promesa;
  }

  // ------------------------------------------------------------------ lista
  function pintarFiltros() {
    const sel = $("cat-clase");
    sel.innerHTML = "";
    sel.add(new Option("Todas las clases", ""));
    for (const c of C.clasesPresentes(est.objetos)) sel.add(new Option(C.CLASE[c], c));
  }

  function insignias(o) {
    const d = o.datos;
    const clase = { real: "real", sintetico: "sintetico" }[d.espectro] || "desconocido";
    return `<span class="insignia ${d.imagen ? "real" : "desconocido"}">${d.imagen ? "Imagen" : "Sin imagen"}</span>
      <span class="insignia ${d.trayectoria ? "real" : "desconocido"}">${d.trayectoria ? "Trayectoria" : "Sin trayectoria"}</span>
      <span class="insignia ${clase}">${C.ESPECTRO[d.espectro]}</span>`;
  }

  function pintarLista() {
    const lista = C.filtrar(est.objetos, est.filtros);
    $("cat-cuenta").textContent = `${lista.length} de ${est.objetos.length} objetos`;
    const cuerpo = $("cat-cuerpo");
    if (!lista.length) {
      cuerpo.innerHTML = `<tr><td colspan="4" class="vacio">Ningún objeto cumple los filtros.</td></tr>`;
      return;
    }
    cuerpo.innerHTML = lista.map((o) => `
      <tr data-id="${esc(o.id_objeto)}" tabindex="0"${est.actual === o.id_objeto ? ' class="seleccionada"' : ""}>
        <td><b>${esc(o.nombre)}</b><br><span class="cmp-meta">${esc(o.id_objeto)}</span></td>
        <td>${o.designacion ? esc(o.designacion) : "—"}</td>
        <td>${esc(C.CLASE[o.clasificacion] || o.clasificacion)}<br><span class="cmp-meta">${esc(C.ESTADO[o.estado_identificacion])}</span></td>
        <td class="cat-datos">${insignias(o)}</td>
      </tr>`).join("");
  }

  // ------------------------------------------------------------------ ficha
  function filaRelacionado(o, extra, idBase) {
    const comparar = C.tieneEspectro(o) && C.tieneEspectro(est.porId.get(idBase))
      ? `<button data-comparar="${esc(o.id_objeto)}">Comparar</button>` : "";
    return `<li><button class="enlace" data-abrir="${esc(o.id_objeto)}">${esc(o.nombre)}</button>
      <span class="cmp-meta">${esc(o.id_objeto)}</span> ${extra || ""} ${comparar}</li>`;
  }

  function pintarFicha(id) {
    const o = est.porId.get(id);
    est.actual = id;
    pintarLista();
    const caja = $("cat-ficha");
    if (!o) {
      caja.innerHTML = `<p class="vacio">Selecciona un objeto del catálogo.</p>`;
      return;
    }
    const r = C.relacionados(o, est.porId);
    const tipo = C.textoTipoEspectral(o);
    const misma = o.clasificacion === "desconocida"
      ? `<p class="vacio">Sin clase catalogada: no se agrupa con otros objetos.</p>`
      : r.misma.length
      ? `<ul class="cat-rel">${r.misma.map((x) => filaRelacionado(x, "", id)).join("")}</ul>`
      : `<p class="vacio">No hay otros objetos de esta clase en los campos publicados.</p>`;
    const similares = !C.tieneEspectro(o)
      ? `<p class="vacio">Este objeto no tiene espectro: no se puede comparar su forma.</p>`
      : r.similares.length
      ? `<ul class="cat-rel">${r.similares.map((s) => filaRelacionado(s.objeto,
          `<span class="cat-metrica ${s.compatible ? "ok" : ""}">χ²ᵣ ${coma(s.valor, 2)} · ${coma(s.rango_comun_micras[0], 2)}–${coma(s.rango_comun_micras[1], 2)} µm · ${s.n_puntos} pts</span>`, id)).join("")}</ul>
         <p class="cmp-nota">Métrica: χ² reducido entre formas (${esc(r.similares[0].normalizacion)}). Menor es más parecido;
           ≤ ${C.UMBRAL_FORMA_COMPATIBLE} se marca en verde: diferencias del orden de los errores. Parecido de forma no es misma clase.</p>`
      : `<p class="vacio">No hay espectros con intervalo común suficiente para comparar.</p>`;

    caja.innerHTML = `
      <h3 class="cat-titulo">${esc(C.titulo(o))}</h3>
      ${o.estado_identificacion !== "conocido"
        ? `<p class="aviso-conceptual">Objeto no identificado en los catálogos consultados. No equivale a un descubrimiento.</p>` : ""}
      <dl class="cat-dl">
        <dt>Clasificación</dt><dd>${esc(C.textoClasificacion(o))}</dd>
        <dt>Identificación</dt><dd>${esc(C.ESTADO[o.estado_identificacion])}</dd>
        <dt>Datos</dt><dd>${insignias(o)}</dd>
        ${tipo ? `<dt>Tipo espectral (m6)</dt><dd>${esc(tipo)}</dd>` : ""}
      </dl>
      <div class="cat-acciones">
        <button id="cat-ver-explorador">Ver en el explorador</button>
        ${C.tieneEspectro(o) ? `<button id="cat-comparar">Abrir en el comparador</button>` : ""}
      </div>
      <div class="cat-grafico" ${C.tieneEspectro(o) ? "" : "hidden"}><canvas id="cat-grafico"></canvas></div>
      <p class="cmp-nota" id="cat-grafico-nota">${C.tieneEspectro(o) ? "" : esc(C.ESPECTRO[o.datos.espectro]) + ": no se dibuja ninguna curva."}</p>
      <div id="cat-composicion" class="composicion" hidden></div>
      <div class="cat-columnas">
        <section><h4>Misma clasificación</h4>${misma}</section>
        <section><h4>Espectros más similares</h4>${similares}</section>
      </div>`;

    $("cat-ver-explorador").addEventListener("click", () => HX.verEnExplorador(o.campo, o.id_candidato));
    if ($("cat-comparar")) $("cat-comparar").addEventListener("click", () => HX.abrirComparacion(o.id_objeto, null));
    if (C.tieneEspectro(o)) pintarEspectro(o);
  }

  async function pintarEspectro(o) {
    if (est.grafico) { est.grafico.destroy(); est.grafico = null; }
    if (typeof Chart === "undefined") { $("cat-grafico-nota").textContent = "Chart.js no se cargó."; return; }
    let espectro = null;
    try {
      const doc = await HX.leerDatos(`${o.campo}/espectros.json`);
      espectro = (doc.espectros || []).find((e) => e.id_pareja === o.id_candidato) || null;
    } catch (error) {
      console.warn(error);
    }
    if (est.actual !== o.id_objeto) return; // el usuario ya eligió otro
    const puntos = espectro ? window.HXComparador.puntosValidos(espectro) : [];
    if (!puntos.length) { $("cat-grafico-nota").textContent = "No se pudo leer el espectro del campo."; return; }
    if (HX.pintarComposicion) {
      const origen = { real: "real", sintetico: "sintetico" }[o.datos.espectro] || null;
      HX.pintarComposicion($("cat-composicion"), espectro, origen);
    }
    $("cat-grafico-nota").textContent =
      `${puntos.length} puntos medidos, ${coma(puntos[0].longitud_onda_micras, 2)}–${coma(puntos[puntos.length - 1].longitud_onda_micras, 2)} µm · ${C.ESPECTRO[o.datos.espectro]}.`;
    est.grafico = new Chart($("cat-grafico"), {
      type: "scatter",
      data: { datasets: [{ label: o.nombre, data: puntos.map((p) => ({ x: p.longitud_onda_micras, y: p.flujo_mjy, e: p.error_mjy })),
        borderColor: "#FFB347", backgroundColor: "#FFB347", pointRadius: 2.2, showLine: true, borderWidth: 1.4 }] },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false, parsing: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: {
          title: (i) => `λ = ${coma(i[0].parsed.x, 3)} µm`, label: (i) => `${coma(i.raw.y, 4)} ± ${coma(i.raw.e, 4)} mJy` } } },
        scales: {
          x: { type: "linear", min: 0.75, max: 5, title: { display: true, text: "longitud de onda (µm)", color: "#8b95a7" }, ticks: { color: "#8b95a7" }, grid: { color: "rgba(29,42,68,0.6)" } },
          y: { title: { display: true, text: "flujo (mJy)", color: "#8b95a7" }, ticks: { color: "#8b95a7" }, grid: { color: "rgba(29,42,68,0.6)" } },
        },
      },
    });
  }

  // ------------------------------------------------------------------ inicio
  function iniciar() {
    if (!$("panel-catalogo") || !C) return;
    $("cat-buscar").addEventListener("input", (e) => { est.filtros.texto = e.target.value; pintarLista(); });
    $("cat-clase").addEventListener("change", (e) => { est.filtros.clasificacion = e.target.value; pintarLista(); });
    $("cat-ident").addEventListener("change", (e) => { est.filtros.estado = e.target.value; pintarLista(); });
    $("cat-con-espectro").addEventListener("change", (e) => { est.filtros.soloConEspectro = e.target.checked; pintarLista(); });
    const abrirFila = (e) => {
      const fila = e.target.closest("tr[data-id]");
      if (fila) pintarFicha(fila.dataset.id);
    };
    $("cat-cuerpo").addEventListener("click", abrirFila);
    $("cat-cuerpo").addEventListener("keydown", (e) => { if (e.key === "Enter") abrirFila(e); });
    $("cat-ficha").addEventListener("click", (e) => {
      const abrir = e.target.closest("[data-abrir]");
      const comparar = e.target.closest("[data-comparar]");
      if (abrir) pintarFicha(abrir.dataset.abrir);
      if (comparar) HX.abrirComparacion(est.actual, comparar.dataset.comparar);
    });
    HX.alAbrirPestana.push((nombre) => { if (nombre === "catalogo") cargar(); });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
