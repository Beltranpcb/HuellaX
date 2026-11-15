/* ============================================================================
   ARCHIVO: modulos/m9_sitio/carga_datos.js
   MODULO: m9_sitio (Lote D)
   ROL: Lee los archivos publicados por m7_publicacion y los deja en HX.estado.
   LEE: datos/m7_publicacion/campos.json y <campo>/{meta,candidatos,espectros}.json;
        opcionalmente epoca_a.png, epoca_b.png y diferencia.png del mismo campo.
   PRODUCE: HX.estado (indice, campo, meta, candidatos, espectros, imagenes).
   VERIFICACION: Tras cargar un campo, HX.estado.candidatos tiene al menos una
                 entrada y HX.estado.meta.campo coincide con el campo pedido.
   ========================================================================== */
(function () {
  "use strict";

  const HX = (window.HX = window.HX || {});

  // La web puede servirse desde la raíz del repositorio o desde su propio
  // directorio; se prueba cada ruta hasta que una responde.
  const BASES_DATOS = [
    "../../datos/m7_publicacion",
    "datos/m7_publicacion",
    "../datos/m7_publicacion",
  ];

  let baseConfirmada = null;

  async function leerJson(url) {
    const respuesta = await fetch(url, { cache: "no-store" });
    if (!respuesta.ok) throw new Error(`${respuesta.status} ${url}`);
    return respuesta.json();
  }

  async function resolverBase() {
    if (baseConfirmada) return baseConfirmada;
    for (const base of BASES_DATOS) {
      try {
        await leerJson(`${base}/campos.json`);
        baseConfirmada = base;
        return base;
      } catch (error) {
        /* se prueba la siguiente */
      }
    }
    throw new Error("No se encontró datos/m7_publicacion/campos.json");
  }

  /** Carga un PNG y devuelve la imagen, o null si el pipeline aún no lo generó. */
  function cargarImagen(url) {
    return new Promise((resolver) => {
      const img = new Image();
      img.onload = () => resolver(img);
      img.onerror = () => resolver(null);
      img.src = url;
    });
  }

  /** Lee un JSON publicado (ruta relativa a datos/m7_publicacion). Solo lectura. */
  HX.leerDatos = async function (rutaRelativa) {
    const base = await resolverBase();
    return leerJson(`${base}/${rutaRelativa}`);
  };

  HX.cargarIndice = async function () {
    const base = await resolverBase();
    const documento = await leerJson(`${base}/campos.json`);
    HX.estado.indice = documento.campos || [];
    return HX.estado.indice;
  };

  HX.cargarCampo = async function (id) {
    const base = await resolverBase();
    const dir = `${base}/${id}`;

    const [meta, candidatos, espectros] = await Promise.all([
      leerJson(`${dir}/meta.json`),
      leerJson(`${dir}/candidatos.json`),
      leerJson(`${dir}/espectros.json`),
    ]);

    const [imagenA, imagenB] = await Promise.all([
      cargarImagen(`${dir}/${meta.imagenes.epoca_a}`),
      cargarImagen(`${dir}/${meta.imagenes.epoca_b}`),
    ]);

    HX.estado.campo = id;
    HX.estado.meta = meta;
    HX.estado.candidatos = candidatos.candidatos || [];
    HX.estado.espectros = espectros.espectros || [];
    HX.estado.imagenes = { a: imagenA, b: imagenB, d: null };
    HX.estado.seleccionado = null;
    HX.estado.zoom = 1;
    HX.estado.offsetX = 0;
    HX.estado.offsetY = 0;
    HX.estado.epoca = "a";

    HX.avisarCampo();
    if (typeof HX.redibujar === "function") HX.redibujar();
    return HX.estado;
  };

  // Arranca cuando todos los archivos ya se han registrado (evento load).
  window.addEventListener("load", async () => {
    try {
      const indice = await HX.cargarIndice();
      if (typeof HX.pintarSelectores === "function") HX.pintarSelectores();
      if (indice.length) await HX.cargarCampo(indice[0].campo);
    } catch (error) {
      console.error(error);
      const aviso = document.getElementById("ficha-contenido");
      if (aviso) {
        aviso.innerHTML =
          '<p class="vacio">No se pudieron cargar los datos publicados ' +
          "(datos/m7_publicacion). Sirve la web con un servidor local.</p>";
      }
    }
  });
})();
