/* ============================================================================
   ARCHIVO: modulos/m9_sitio/superposicion.js
   MODULO: m9_sitio (Lote D)
   ROL: Dibuja sobre el visor la posición de cada candidato y su trayectoria A→B.
   LEE: HX.estado.candidatos (posicion_a, posicion_b) y HX.estado.seleccionado.
   PRODUCE: Los trazos sobre el lienzo; no guarda estado propio.
   VERIFICACION: Con zoom 1 cada candidato muestra un círculo en A y una flecha
                 hacia B; el seleccionado se dibuja con doble anillo.
   ========================================================================== */
(function () {
  "use strict";

  const HX = (window.HX = window.HX || {});
  const ALTO = 600;

  const COLOR = {
    conocido: "#4ade80",
    sin_identificar: "#ffb347",
    artefacto_descartado: "#8b95a7",
  };

  function colorDe(cand) {
    return COLOR[cand.estado] || "#8b95a7";
  }

  function flecha(g, ax, ay, bx, by, color, zoom) {
    const ang = Math.atan2(by - ay, bx - ax);
    const largo = 7 / zoom;
    g.fillStyle = color;
    g.beginPath();
    g.moveTo(bx, by);
    g.lineTo(bx - largo * Math.cos(ang - 0.4), by - largo * Math.sin(ang - 0.4));
    g.lineTo(bx - largo * Math.cos(ang + 0.4), by - largo * Math.sin(ang + 0.4));
    g.closePath();
    g.fill();
  }

  HX.dibujarSuperposicion = function (g, estado) {
    for (const cand of estado.candidatos) {
      const a = cand.posicion_a;
      const b = cand.posicion_b;
      if (!a || !b) continue;

      // El contrato sitúa el origen de `y` abajo; el lienzo lo tiene arriba.
      const ax = a.x;
      const ay = ALTO - a.y;
      const bx = b.x;
      const by = ALTO - b.y;

      const seleccionado = cand.id_candidato === estado.seleccionado;
      const color = colorDe(cand);

      if (Math.hypot(bx - ax, by - ay) > 3) {
        g.strokeStyle = color;
        g.globalAlpha = seleccionado ? 1 : 0.55;
        g.lineWidth = (seleccionado ? 2.2 : 1.2) / estado.zoom;
        g.beginPath();
        g.moveTo(ax, ay);
        g.lineTo(bx, by);
        g.stroke();
        flecha(g, ax, ay, bx, by, color, estado.zoom);
        g.globalAlpha = 1;
      }

      g.strokeStyle = color;
      g.lineWidth = (seleccionado ? 2.6 : 1.6) / estado.zoom;
      g.beginPath();
      g.arc(ax, ay, (seleccionado ? 18 : 13) / estado.zoom, 0, Math.PI * 2);
      g.stroke();

      if (seleccionado) {
        g.strokeStyle = "rgba(230,234,242,0.85)";
        g.lineWidth = 1 / estado.zoom;
        g.beginPath();
        g.arc(ax, ay, 24 / estado.zoom, 0, Math.PI * 2);
        g.stroke();
      }

      g.fillStyle = color;
      g.font = `600 ${11 / estado.zoom}px ui-monospace, monospace`;
      g.globalAlpha = seleccionado ? 1 : 0.8;
      g.fillText(cand.id_candidato, ax + 20 / estado.zoom, ay - 16 / estado.zoom);
      g.globalAlpha = 1;
    }
  };
})();
