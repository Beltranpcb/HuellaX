/* ============================================================================
   ARCHIVO: modulos/m9_sitio/espectro3d.js
   MODULO: m9_sitio (Lote D)
   ROL: Dibuja en 3D las huellas espectrales de un campo publicado.
   LEE: datos/m7_publicacion/campos.json, <campo>/espectros.json y candidatos.json.
   PRODUCE: Una escena WebGL con un listón por candidata; la cámara orbita.
   FUNCIONAMIENTO PREVISTO:
     No inventa continuidad entre objetos: cada espectro es un listón en su plano.
     La superficie de unión es opcional y se avisa de que es una ayuda visual.
   VERIFICACION: Abre sin errores, muestra un listón por espectro y el eje de longitudes.
   USO: servir el repositorio por HTTP y abrir espectro3d.html?campo=<campo>.
   ========================================================================== */
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const BASE = "../../datos/m7_publicacion/";
const contenedor = document.getElementById("escena");
const aviso = document.getElementById("aviso3d");
const etiquetaCampo = document.getElementById("campo3d");
const botonConectar = document.getElementById("btn-conectar");
const botonReiniciar = document.getElementById("btn-reiniciar");

const COLORES = [0xffb347, 0x6fd3ff, 0xb08cff, 0x6fe3a8, 0xff8a8a, 0xffe066];

function mostrarAviso(texto) {
  aviso.textContent = texto;
  aviso.hidden = false;
}

async function leerJSON(ruta) {
  const respuesta = await fetch(ruta);
  if (!respuesta.ok) throw new Error(`${ruta}: ${respuesta.status}`);
  return respuesta.json();
}

function textoEnSprite(texto, color) {
  const lienzo = document.createElement("canvas");
  const ctx = lienzo.getContext("2d");
  const fuente = "600 28px 'Segoe UI', system-ui, sans-serif";
  ctx.font = fuente;
  lienzo.width = Math.ceil(ctx.measureText(texto).width) + 24;
  lienzo.height = 44;
  const c2 = lienzo.getContext("2d");
  c2.font = fuente;
  c2.fillStyle = "rgba(11,15,26,.75)";
  c2.fillRect(0, 0, lienzo.width, lienzo.height);
  c2.fillStyle = color;
  c2.textBaseline = "middle";
  c2.fillText(texto, 12, lienzo.height / 2);
  const textura = new THREE.CanvasTexture(lienzo);
  textura.anisotropy = 4;
  const material = new THREE.SpriteMaterial({ map: textura, transparent: true, depthWrite: false });
  const sprite = new THREE.Sprite(material);
  const escala = 0.0032;
  sprite.scale.set(lienzo.width * escala, lienzo.height * escala, 1);
  sprite.center.set(0, 0.5);   // crece hacia la derecha desde donde se coloca
  return sprite;
}

function main(datos) {
  const { campo, espectros, candidatos } = datos;
  etiquetaCampo.textContent = `Campo ${campo} · ${espectros.length} huella(s)`;

  if (!espectros.length) {
    mostrarAviso("Este campo no tiene huellas espectrales publicadas.");
    return;
  }

  const escena = new THREE.Scene();
  escena.background = new THREE.Color(0x0b0f1a);
  escena.fog = new THREE.Fog(0x0b0f1a, 6, 18);

  const camara = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  camara.position.set(4.9, 3.1, 6.6);

  const renderizador = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderizador.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  contenedor.appendChild(renderizador.domElement);

  const controles = new OrbitControls(camara, renderizador.domElement);
  controles.enableDamping = true;
  controles.dampingFactor = 0.08;
  controles.minDistance = 2.5;
  controles.maxDistance = 16;

  // Todo lo dibujado cuelga de un grupo raíz: así se puede girar entero en
  // pantallas verticales, donde un gráfico tan ancho no cabe de otra forma.
  const raiz = new THREE.Group();
  escena.add(raiz);

  escena.add(new THREE.AmbientLight(0xffffff, 0.9));
  const luz = new THREE.DirectionalLight(0xffffff, 0.8);
  luz.position.set(3, 6, 4);
  escena.add(luz);

  // --- ejes ---------------------------------------------------------------
  const largo = 4.4;
  const altura = 2.4;
  const fondo = -1.6;

  const ejes = new THREE.Group();
  const materialEje = new THREE.LineBasicMaterial({ color: 0x2c3648 });
  const puntos = [
    [new THREE.Vector3(-largo, fondo, 0), new THREE.Vector3(largo, fondo, 0)],   // λ
    [new THREE.Vector3(-largo, fondo, 0), new THREE.Vector3(-largo, fondo + altura, 0)], // flujo
    [new THREE.Vector3(-largo, fondo, -2.2), new THREE.Vector3(-largo, fondo, 2.2)],     // candidatas
  ];
  for (const [a, b] of puntos) {
    ejes.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([a, b]), materialEje));
  }
  raiz.add(ejes);

  const textoLambda = textoEnSprite("longitud de onda (µm)", "#8b93a7");
  textoLambda.position.set(0, fondo - 0.42, 0);
  raiz.add(textoLambda);

  const textoFlujo = textoEnSprite("flujo (mJy, normalizado)", "#8b93a7");
  textoFlujo.position.set(-largo - 0.55, fondo + altura / 2, 0);
  raiz.add(textoFlujo);

  // marcas de longitud de onda sobre el eje
  const marcas = new THREE.Group();
  for (const micras of [1, 2, 3, 4, 5]) {
    const x = -largo + ((micras - 0.75) / (5.0 - 0.75)) * 2 * largo;
    marcas.add(new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(x, fondo, 0), new THREE.Vector3(x, fondo - 0.12, 0),
      ]),
      new THREE.LineBasicMaterial({ color: 0x3a475e })
    ));
    const cifra = textoEnSprite(`${micras}`, "#7b869c");
    cifra.scale.multiplyScalar(0.75);
    cifra.center.set(0.5, 1);
    cifra.position.set(x, fondo - 0.16, 0);
    marcas.add(cifra);
  }
  raiz.add(marcas);

  // --- escalas ------------------------------------------------------------
  const todas = espectros.flatMap((e) => e.puntos);
  // El eje es SIEMPRE 0,75–5,0 µm, el rango del contrato. Si se ajustara a los
  // datos del campo, una huella real de dos puntos entre 4,69 y 4,74 µm se
  // estiraría por toda la gráfica y parecería cubrir todo el infrarrojo.
  const lambdaMin = 0.75;
  const lambdaMax = 5.0;
  const lambdaDatos = [
    Math.min(...todas.map((p) => p.longitud_onda_micras)),
    Math.max(...todas.map((p) => p.longitud_onda_micras)),
  ];
  // Se normaliza cada huella por su propio máximo: los objetos tienen brillos
  // muy distintos y si no, las débiles desaparecen.
  let flujoMaximo = 0;
  const normalizadas = espectros.map((e) => {
    const maximo = Math.max(...e.puntos.map((p) => p.flujo_mjy));
    flujoMaximo = Math.max(flujoMaximo, maximo);
    return e.puntos.map((p) => ({
      x: -largo + ((p.longitud_onda_micras - lambdaMin) / (lambdaMax - lambdaMin)) * 2 * largo,
      y: fondo + (p.flujo_mjy / maximo) * altura,
      flujo: p.flujo_mjy,
      error: p.error_mjy / maximo,
      lambda: p.longitud_onda_micras,
    }));
  });

  const separacion = espectros.length > 1 ? 3.6 / (espectros.length - 1) : 0;
  const desplazamientos = espectros.map((_, i) => (i - (espectros.length - 1) / 2) * separacion);

  // --- un listón por candidata -------------------------------------------
  const grupoListones = new THREE.Group();
  raiz.add(grupoListones);

  normalizadas.forEach((puntos_, i) => {
    const color = COLORES[i % COLORES.length];
    const z = desplazamientos[i];
    const espectro = espectros[i];
    const candidato = candidatos.find((c) => c.id_candidato === espectro.id_pareja);

    // línea del espectro
    const geometria = new THREE.BufferGeometry().setFromPoints(
      puntos_.map((p) => new THREE.Vector3(p.x, p.y, z))
    );
    grupoListones.add(new THREE.Line(geometria, new THREE.LineBasicMaterial({ color, linewidth: 2 })));

    // error: banda de ±1 sigma
    if (puntos_[0].error !== undefined) {
      const formaError = new THREE.Shape();
      formaError.moveTo(puntos_[0].x, 0);
      for (const p of puntos_) formaError.lineTo(p.x, p.y + p.error - fondo);
      for (let k = puntos_.length - 1; k >= 0; k--) {
        const p = puntos_[k];
        formaError.lineTo(p.x, p.y - p.error - fondo);
      }
      formaError.closePath();
      const banda = new THREE.Mesh(
        new THREE.ShapeGeometry(formaError),
        new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.10, side: THREE.DoubleSide, depthWrite: false })
      );
      banda.position.set(0, fondo, z);
      grupoListones.add(banda);
    }

    // puntos medidos: con una huella de dos puntos, la curva es casi un punto
    const esfera = new THREE.SphereGeometry(0.045, 12, 12);
    const materialPunto = new THREE.MeshBasicMaterial({ color });
    for (const p of puntos_) {
      const marca = new THREE.Mesh(esfera, materialPunto);
      marca.position.set(p.x, p.y, z);
      grupoListones.add(marca);
    }

    // etiqueta junto al primer punto, no en el borde del eje
    const nombre = candidato ? (candidato.nombre_objeto || "candidato") : espectro.id_pareja;
    const etiqueta = textoEnSprite(`${espectro.id_pareja} · ${nombre}`, `#${color.toString(16).padStart(6, "0")}`);
    etiqueta.position.set(puntos_[0].x, puntos_[0].y + 0.28, z);
    grupoListones.add(etiqueta);
  });

  // --- superficie opcional entre listones --------------------------------
  let superficie = null;
  if (espectros.length > 1) {
    const filas = normalizadas.length;
    const columnas = normalizadas[0].length;
    const vertices = new Float32Array(filas * columnas * 3);
    let k = 0;
    normalizadas.forEach((puntos_, i) => {
      for (const p of puntos_) {
        vertices[k++] = p.x;
        vertices[k++] = p.y;
        vertices[k++] = desplazamientos[i];
      }
    });
    const indices = [];
    for (let i = 0; i < filas - 1; i++) {
      for (let j = 0; j < columnas - 1; j++) {
        const a = i * columnas + j;
        const b = a + 1;
        const c = a + columnas;
        const d = c + 1;
        indices.push(a, c, b, b, c, d);
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(vertices, 3));
    geo.setIndex(indices);
    geo.computeVertexNormals();
    superficie = new THREE.Mesh(
      geo,
      new THREE.MeshBasicMaterial({ color: 0x4a7bd6, transparent: true, opacity: 0.13, side: THREE.DoubleSide, wireframe: true })
    );
    superficie.visible = false;
    raiz.add(superficie);
  }

  if (!superficie) {
    botonConectar.disabled = true;
    botonConectar.title = "Hace falta más de una huella para unirlas";
  }

  botonConectar.addEventListener("click", () => {
    if (!superficie) return;
    superficie.visible = !superficie.visible;
    botonConectar.classList.toggle("activo", superficie.visible);
    botonConectar.textContent = superficie.visible ? "Ocultar unión" : "Unir listones";
  });

  botonReiniciar.addEventListener("click", () => {
    controles.target.set(0, fondo + altura * 0.45, 0);
    camara.position.copy(controles.target).add(new THREE.Vector3(4.9, 3.1, 6.6));
    encuadrar();
  });
  controles.target.set(0, fondo + altura * 0.45, 0);
  controles.update();

  // En vertical el campo de visión horizontal se estrecha: la cámara se aleja
  // para que los listones sigan entrando, sin perder el giro que eligió el usuario.
  const DISTANCIA_BASE = 8.6;

  function encuadrar() {
    // Un gráfico de 9 unidades de ancho no cabe en un móvil en vertical: se
    // mantiene la vista de escritorio y se pide girar el dispositivo.
    const vertical = camara.aspect < 0.8;
    raiz.rotation.z = 0;
    const avisoGiro = document.getElementById("aviso-giro");
    if (avisoGiro) avisoGiro.hidden = !vertical;
    const distancia = vertical ? 13.5 : DISTANCIA_BASE;
    const direccion = camara.position.clone().sub(controles.target);
    if (direccion.lengthSq() === 0) direccion.set(4.9, 3.1, 6.6).sub(new THREE.Vector3(0, -0.52, 0));
    direccion.normalize().multiplyScalar(distancia);
    camara.position.copy(controles.target).add(direccion);
    controles.update();
  }

  function ajustar() {
    const ancho = contenedor.clientWidth;
    const alto = contenedor.clientHeight;
    if (!ancho || !alto) return;
    camara.aspect = ancho / alto;
    camara.updateProjectionMatrix();
    renderizador.setSize(ancho, alto);   // actualiza también el tamaño CSS
    encuadrar();
  }
  ajustar();
  window.addEventListener("resize", ajustar);

  function animar() {
    requestAnimationFrame(animar);
    controles.update();
    renderizador.render(escena, camara);
  }
  animar();

  window.HX3D = {
    escena, camara, renderizador,
    espectros: espectros.length,
    puntos: normalizadas.map((p) => p.length),
    lambda: lambdaDatos,
    eje: [lambdaMin, lambdaMax],
    superficieVisible: () => !!(superficie && superficie.visible),
  };
}

async function arrancar() {
  try {
    const indice = await leerJSON(`${BASE}campos.json`);
    const pedido = new URLSearchParams(location.search).get("campo");
    const campos = indice.campos.filter((c) => c.numero_candidatos > 0);
    const elegido = campos.find((c) => c.campo === pedido) || campos[0];
    if (!elegido) {
      mostrarAviso("No hay campos publicados.");
      return;
    }
    const [espectrosDoc, candidatosDoc] = await Promise.all([
      leerJSON(`${BASE}${elegido.campo}/espectros.json`),
      leerJSON(`${BASE}${elegido.campo}/candidatos.json`),
    ]);
    main({
      campo: elegido.campo,
      espectros: espectrosDoc.espectros,
      candidatos: candidatosDoc.candidatos,
    });
  } catch (error) {
    mostrarAviso(`No se pudo cargar el campo: ${error.message}`);
    console.error(error);
  }
}

arrancar();
