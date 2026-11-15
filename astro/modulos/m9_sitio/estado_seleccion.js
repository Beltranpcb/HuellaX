/* ============================================================================
   ARCHIVO: modulos/m9_sitio/estado_seleccion.js
   MODULO: m9_sitio (Lote D)
   ROL: Guarda el estado compartido de la web (campo, candidato, modo, vista)
        y avisa a los demás archivos cuando cambia la selección o el campo.
   LEE: Nada.
   PRODUCE: window.HX: estado, alSeleccionar[], alCambiarCampo[], seleccionar().
   VERIFICACION: Al llamar a HX.seleccionar("p001") se ejecutan los suscriptores
                 de alSeleccionar con ese candidato y el estado lo refleja.
   ========================================================================== */
(function () {
  "use strict";

  const HX = (window.HX = window.HX || {});

  HX.estado = {
    indice: [],        // campos publicados
    campo: null,       // campo activo
    meta: null,        // meta.json del campo
    candidatos: [],    // candidatos.json
    espectros: [],     // espectros.json
    seleccionado: null,// id_candidato activo
    modo: "parpadeo",  // parpadeo | cortina | diferencia
    epoca: "a",        // época visible en modo parpadeo
    reproduciendo: true,
    cortina: 0.5,      // fracción 0..1
    zoom: 1,
    offsetX: 0,
    offsetY: 0,
    imagenes: { a: null, b: null, d: null }, // PNG reales; null = sintetizar
  };

  // Suscriptores: cada archivo empuja aquí su función de pintado.
  HX.alSeleccionar = [];
  HX.alCambiarCampo = [];

  HX.candidatoActual = function () {
    const id = HX.estado.seleccionado;
    return HX.estado.candidatos.find((c) => c.id_candidato === id) || null;
  };

  HX.espectroDe = function (idCandidato) {
    const lista = HX.estado.espectros || [];
    return lista.find((e) => e.id_pareja === idCandidato) || null;
  };

  HX.seleccionar = function (id, centrar) {
    HX.estado.seleccionado = id;
    const candidato = HX.candidatoActual();

    if (centrar && candidato && typeof HX.centrarEn === "function") {
      HX.centrarEn(candidato);
    }
    if (typeof HX.redibujar === "function") HX.redibujar();

    for (const aviso of HX.alSeleccionar) {
      try {
        aviso(candidato);
      } catch (error) {
        console.error("alSeleccionar:", error);
      }
    }
  };

  HX.avisarCampo = function () {
    for (const aviso of HX.alCambiarCampo) {
      try {
        aviso();
      } catch (error) {
        console.error("alCambiarCampo:", error);
      }
    }
  };
})();
