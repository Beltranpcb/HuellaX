/* ============================================================================
   ARCHIVO: modulos/m9_sitio/selector_campo.js
   MODULO: m9_sitio (Lote D)
   ROL: Dibuja la lista de campos publicados y cambia de campo al pulsar.
   LEE: HX.estado.indice y HX.estado.campo.
   PRODUCE: Los botones de #selector-campos y #portada-campos; al pulsar,
            llama a HX.cargarCampo().
   VERIFICACION: Con tres campos en el índice aparecen tres botones en cada
                 contenedor y el activo lleva la clase "activo".
   ========================================================================== */
(function () {
  "use strict";

  const HX = (window.HX = window.HX || {});

  function boton(campo, alPulsar) {
    const elemento = document.createElement("button");
    elemento.textContent = campo.nombre;
    elemento.dataset.campo = campo.campo;
    elemento.title = `${campo.numero_candidatos} candidatos`;
    if (campo.campo === HX.estado.campo) elemento.classList.add("activo");
    elemento.addEventListener("click", alPulsar);
    return elemento;
  }

  HX.pintarSelectores = function () {
    const barra = document.getElementById("selector-campos");
    if (barra) {
      barra.innerHTML = "";
      for (const campo of HX.estado.indice) {
        barra.appendChild(
          boton(campo, () => HX.cargarCampo(campo.campo))
        );
      }
    }

    const portada = document.getElementById("portada-campos");
    if (portada) {
      portada.innerHTML = "";
      for (const campo of HX.estado.indice) {
        portada.appendChild(
          boton(campo, async () => {
            if (HX.abrirApp) HX.abrirApp();
            await HX.cargarCampo(campo.campo);
          })
        );
      }
    }
  };

  // Al cambiar de campo, refresca la clase "activo" de los botones.
  HX.alCambiarCampo.push(() => HX.pintarSelectores());
})();
