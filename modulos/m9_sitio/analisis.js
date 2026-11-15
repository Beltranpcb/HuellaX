/* ============================================================================
   ARCHIVO: modulos/m9_sitio/analisis.js
   MODULO: m9_sitio (Lote D)
   ROL: Gestiona la sección «Análisis de objetos»: el cambio entre el explorador
        y el análisis, y las pestañas Catálogo, Identificar y Comparar espectros.
   LEE: Nada.
   PRODUCE: HX.mostrarVista(nombre), HX.mostrarPestana(nombre) y HX.verEnExplorador(); avisa a
            HX.alAbrirPestana[] cuando se abre una pestaña.
   VERIFICACION: Pulsar «Análisis de objetos» oculta el visor y la tabla y
                 muestra las pestañas; «Explorador» los devuelve.
   ========================================================================== */
(function () {
  "use strict";

  const HX = (window.HX = window.HX || {});
  HX.alAbrirPestana = [];

  const VISTAS = ["explorador", "analisis"];
  const PESTANAS = ["catalogo", "identificar", "comparar"];

  function mostrarVista(nombre) {
    if (!VISTAS.includes(nombre)) return;
    const explorador = nombre === "explorador";
    for (const id of ["vista-explorador", "vista-tabla"]) {
      const el = document.getElementById(id);
      if (el) el.hidden = !explorador;
    }
    const selector = document.getElementById("selector-campos");
    if (selector) selector.hidden = !explorador; // los campos solo importan en el explorador
    const analisis = document.getElementById("vista-analisis");
    if (analisis) analisis.hidden = explorador;
    for (const v of VISTAS) {
      const boton = document.getElementById(`nav-${v}`);
      if (!boton) continue;
      boton.classList.toggle("activo", v === nombre);
      boton.setAttribute("aria-current", v === nombre ? "page" : "false");
    }
    if (!explorador) mostrarPestana(HX.pestanaActual || "catalogo");
  }

  function mostrarPestana(nombre) {
    if (!PESTANAS.includes(nombre)) return;
    HX.pestanaActual = nombre;
    for (const p of PESTANAS) {
      const boton = document.getElementById(`pestana-${p}`);
      const panel = document.getElementById(`panel-${p}`);
      if (boton) {
        boton.classList.toggle("activo", p === nombre);
        boton.setAttribute("aria-selected", p === nombre ? "true" : "false");
      }
      if (panel) panel.hidden = p !== nombre;
    }
    for (const f of HX.alAbrirPestana) f(nombre);
  }

  HX.mostrarVista = mostrarVista;

  /** Abre el explorador con el campo cargado y el candidato seleccionado. */
  HX.verEnExplorador = async function (campo, idCandidato) {
    mostrarVista("explorador");
    if (HX.estado.campo !== campo) await HX.cargarCampo(campo);
    HX.seleccionar(idCandidato, true);
  };
  HX.mostrarPestana = mostrarPestana;

  function iniciar() {
    for (const v of VISTAS) {
      const boton = document.getElementById(`nav-${v}`);
      if (boton) boton.addEventListener("click", () => mostrarVista(v));
    }
    for (const p of PESTANAS) {
      const boton = document.getElementById(`pestana-${p}`);
      if (boton) boton.addEventListener("click", () => mostrarPestana(p));
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
