/* ============================================================================
   ARCHIVO: modulos/m9_sitio/tabla.js
   MODULO: m9_sitio (Lote D)
   ROL: Pinta la tabla ordenable de candidatos y descarga la vista en CSV.
   LEE: HX.estado.candidatos (candidatos.json de m7_publicacion).
   PRODUCE: Filas de #cuerpo-tabla; al pulsar una fila llama a HX.seleccionar().
   VERIFICACION: Ordenar por velocidad da el mismo orden que ordenar los datos
                 a mano; el filtro deja solo las filas del estado elegido.
   ========================================================================== */
(function () {
  "use strict";

  const HX = (window.HX = window.HX || {});

  const ETIQUETA_ESTADO = {
    conocido: "Conocida",
    sin_identificar: "Sin identificar",
    artefacto_descartado: "Artefacto",
  };

  const estado = {
    orden: { clave: "significancia", sentido: "desc" },
    filtro: "todas",
  };

  let cuerpo = null;

  const numero = (valor, decimales) =>
    valor === null || valor === undefined || Number.isNaN(valor)
      ? "—"
      : valor.toFixed(decimales).replace(".", ",");

  function filas() {
    const todos = HX.estado.candidatos || [];
    if (estado.filtro === "todas") return todos.slice();
    return todos.filter((c) => c.estado === estado.filtro);
  }

  function comparar(a, b, clave) {
    let va = a[clave];
    let vb = b[clave];
    if (va === null || va === undefined) va = -Infinity;
    if (vb === null || vb === undefined) vb = -Infinity;
    return typeof va === "string" || typeof vb === "string"
      ? String(va).localeCompare(String(vb), "es")
      : va - vb;
  }

  function nombreDe(cand) {
    if (cand.nombre_objeto) return cand.nombre_objeto;
    return cand.estado === "artefacto_descartado" ? "<i>descartado</i>" : "<i>sin identificar</i>";
  }

  function pintar() {
    if (!cuerpo) return;
    const lista = filas().sort((a, b) => {
      const r = comparar(a, b, estado.orden.clave);
      return estado.orden.sentido === "asc" ? r : -r;
    });

    if (!lista.length) {
      // Un campo sin candidatas no es un filtro vacío: el pipeline no encontró
      // parejas, casi siempre porque las épocas están demasiado separadas.
      const sinNada = (HX.estado.candidatos || []).length === 0;
      const mensaje = sinNada
        ? "Este campo no tiene candidatas: el pipeline no encontró parejas entre las dos épocas."
        : "Sin candidatos para este filtro.";
      cuerpo.innerHTML =
        '<tr><td colspan="7" style="color:var(--texto_secundario)">' + mensaje + "</td></tr>";
      return;
    }

    cuerpo.innerHTML = lista
      .map((c) => {
        const activo = c.id_candidato === HX.estado.seleccionado ? " class=\"seleccionada\"" : "";
        const etiqueta = ETIQUETA_ESTADO[c.estado] || c.estado;
        return `
          <tr data-id="${c.id_candidato}"${activo}>
            <td class="num">${c.id_candidato}</td>
            <td>${nombreDe(c)}</td>
            <td class="num">${numero(c.separacion_segarc, 1)}″</td>
            <td class="num">${numero(c.velocidad_segarc_por_hora, 2)} ± ${numero(c.incertidumbre_velocidad, 2)} ″/h</td>
            <td class="num">${numero(c.significancia, 1)} σ</td>
            <td><span class="etiqueta ${c.estado}">${etiqueta}</span></td>
            <td style="color:var(--texto_secundario);font-size:.78rem">${c.nombre_objeto || "—"}</td>
          </tr>`;
      })
      .join("");

    for (const fila of cuerpo.querySelectorAll("tr[data-id]")) {
      fila.addEventListener("click", () => HX.seleccionar(fila.dataset.id, true));
    }
    marcarFlecha();
  }

  function marcarFlecha() {
    for (const th of document.querySelectorAll("#tabla-candidatos th[data-orden]")) {
      const flecha = th.querySelector(".flecha");
      if (!flecha) continue;
      flecha.textContent =
        th.dataset.orden === estado.orden.clave
          ? estado.orden.sentido === "asc" ? "▲" : "▼"
          : "";
    }
  }

  function resaltar(cand) {
    if (!cuerpo) return;
    const id = cand ? cand.id_candidato : null;
    for (const fila of cuerpo.querySelectorAll("tr[data-id]")) {
      fila.classList.toggle("seleccionada", fila.dataset.id === id);
    }
  }

  function exportarCsv() {
    const cabecera = [
      "id_candidato", "estado", "nombre_objeto", "clase_movimiento",
      "separacion_segarc", "velocidad_segarc_por_hora", "incertidumbre_velocidad",
      "significancia", "tipo", "temperatura_k",
    ];
    const lineas = filas().map((c) =>
      cabecera.map((k) => `"${String(c[k] ?? "").replace(/"/g, '""')}"`).join(",")
    );
    const texto = [cabecera.join(","), ...lineas].join("\n");
    const blob = new Blob(["\ufeff" + texto], { type: "text/csv;charset=utf-8" });
    const enlace = document.createElement("a");
    enlace.href = URL.createObjectURL(blob);
    enlace.download = `huella-x-${HX.estado.campo || "candidatos"}.csv`;
    enlace.click();
    URL.revokeObjectURL(enlace.href);
  }

  function iniciar() {
    cuerpo = document.getElementById("cuerpo-tabla");
    if (!cuerpo) return;

    for (const th of document.querySelectorAll("#tabla-candidatos th[data-orden]")) {
      th.addEventListener("click", () => {
        const clave = th.dataset.orden;
        if (estado.orden.clave === clave) {
          estado.orden.sentido = estado.orden.sentido === "asc" ? "desc" : "asc";
        } else {
          estado.orden.clave = clave;
          estado.orden.sentido = "asc";
        }
        pintar();
      });
    }

    for (const boton of document.querySelectorAll("#filtros button")) {
      boton.addEventListener("click", () => {
        estado.filtro = boton.dataset.filtro;
        for (const otro of document.querySelectorAll("#filtros button")) {
          otro.classList.toggle("activo", otro === boton);
        }
        pintar();
      });
    }

    const botonCsv = document.getElementById("btn-csv");
    if (botonCsv) botonCsv.addEventListener("click", exportarCsv);

    pintar();
  }

  HX.alCambiarCampo.push(pintar);
  HX.alSeleccionar.push(resaltar);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
