<!--
  ARCHIVO: modulos/m9_sitio/LEEME.md
  ROL: Describe el módulo junto a su comando de verificación.
  LEE: Nada.
  PRODUCE: La ficha que consulta quien desarrolla o revisa el módulo.
  VERIFICACION: Cada archivo citado aquí existe en el directorio del módulo.
-->

# m9_sitio

**Lote D** · 18 h estimadas · capa 6 del grafo

Mostrar al público qué se mueve en cada campo, con la naturaleza de cada objeto.

## Entradas

- `datos/m7_publicacion/campos.json`
- `datos/m7_publicacion/<campo>/{meta,candidatos,espectros}.json`
- Opcionalmente `datos/m7_publicacion/<campo>/{epoca_a,epoca_b,diferencia}.png`
- Opcionalmente `datos/m7_publicacion/plantillas.json` (curvas de referencia)
- Opcionalmente `datos/m7_publicacion/catalogo.json` (catálogo navegable, de `m7_publicacion/indice_catalogo.py`)
- Aladin Lite y Chart.js, cargados por CDN
- `contratos/guia_visual.md` (variables de color)

## Salidas

- La web pública servida desde `modulos/m9_sitio/index.html`

## Depende de

`m7_publicacion` (solo a través de sus archivos de datos). Ningún módulo importa
el código de otro.

## Archivos

| Archivo | Responsabilidad única |
|---|---|
| `LEEME.md` | Describe el módulo junto a su comando de verificación. |
| `index.html` | Define la portada, el visor, la ficha y la tabla. |
| `estilo.css` | Aplica la guía visual con diseño adaptable a móvil. |
| `estado_seleccion.js` | Mantiene el estado compartido y avisa de la selección. |
| `carga_datos.js` | Lee los archivos publicados por m7_publicacion. |
| `selector_campo.js` | Dibuja la lista de campos disponibles. |
| `espectro3d.html` | Página aparte con las huellas espectrales del campo en 3D. |
| `espectro3d.js` | Escena WebGL (three.js): un listón por candidata, ejes y unión opcional. |
| `visor.js` | Dibuja las dos épocas en el lienzo según el modo elegido. |
| `superposicion.js` | Dibuja sobre el visor la trayectoria de cada candidato. |
| `tabla.js` | Muestra la tabla ordenable de candidatos y exporta CSV. |
| `ficha.js` | Muestra la ficha del candidato y el mapa del cielo. |
| `espectro.js` | Dibuja la huella espectral del candidato seleccionado. |
| `analisis.js` | Alterna entre explorador y «Análisis de objetos» y gestiona sus pestañas. |
| `comparador_logica.js` | Lógica pura del comparador: objetos con espectro válido, normalización y compatibilidad. |
| `comparador.js` | Dibuja el comparador de espectros (selectores, gráfico con incertidumbres, avisos, CSV y PNG). |
| `catalogo_logica.js` | Lógica pura del catálogo: búsqueda, filtros y textos de cada objeto. |
| `catalogo.js` | Dibuja el catálogo navegable, la ficha del objeto y sus dos listas de relacionados. |
| `composicion_logica.js` | Lógica pura de «Composición espectral»: cuándo se muestra, orden y textos. |
| `composicion.js` | Dibuja «Composición espectral» en la ficha del explorador y en la del catálogo. |
| `identificar_logica.js` | Lógica pura de «Identificar»: proyección TAN, lienzo <-> píxel, detección cercana y lectura de SkyBoT. |
| `identificar.js` | Pestaña «Identificar»: clic en la imagen, coordenadas, detección marcada y efemérides de SkyBoT. |
| `ejemplos/generar_datos.py` | Genera datos de demostración conformes a los contratos. |
| `pruebas/lista_visual.md` | Comprobaciones manuales de la web. |

## Cómo se ejecuta

```bash
# 1. Servir el repositorio desde la raíz (no abrir con file://)
python3 -m http.server 8765

# 2. Abrir en el navegador
#    http://127.0.0.1:8765/modulos/m9_sitio/index.html
```

La web busca los datos en `datos/m7_publicacion/` probando tres rutas relativas,
de modo que funciona tanto servida desde la raíz como desde su propio directorio.

## Análisis de objetos

La cabecera tiene dos secciones: **Explorador** y **Análisis de objetos**. Esta última
tiene tres pestañas:

- **Catálogo** (la primera): los objetos detectados en los campos publicados, con búsqueda,
  filtros por clase, identificación y espectro. Cada objeto declara qué datos existen de verdad
  (imagen, trayectoria, espectro real, de demostración, de origen no declarado o pendiente). La
  ficha muestra la clasificación con su fuente, el espectro si existe y **dos listas separadas**:
  «Misma clasificación» (clase catalogada) y «Espectros más similares» (χ² reducido entre formas
  calculado por m7). «Comparar» abre el comparador con los dos objetos; «Ver en el explorador»
  abre el campo con el candidato seleccionado. Los artefactos descartados no entran.

- **Comparar espectros**: compara dos espectros observados. Solo se listan objetos con
  al menos dos puntos válidos; se puede ver el flujo medido (mJy) o normalizado
  (método y longitud de onda visibles), hacer zoom y descargar CSV o PNG. Avisa si el
  intervalo común es estrecho, la resolución difiere o el origen de los datos no coincide.
  No clasifica nada.
- **Plantillas (objeto A)**: el objeto frente a las plantillas de `plantillas.json`, dibujadas
  con la escala del ajuste de m6, y la tabla de χ² reducido con grados de libertad, puntos y
  origen. Se redacta como «más compatible con la plantilla X entre las evaluadas»; si m6 dejó
  el tipo indeterminado, la web no elige ninguna.
- **Identificar**: clic en la imagen del campo (zoom y arrastre). El píxel se convierte en RA/DEC con
  `meta.wcs` (proyección TAN, comprobada contra astropy); sin WCS se avisa y no se inventan coordenadas.
  Un clic cerca de una detección marcada la selecciona y muestra su identificación de m5. «Consultar
  efemérides» pregunta en vivo a SkyBoT (IMCCE) qué asteroides, planetas o cometas conocidos estaban allí
  en la fecha de la época A, con separación, error de la efeméride, tolerancia y veredicto (compatible,
  ambigua o sin coincidencia concluyente). Gaia DR3 queda pendiente: sus archivos no admiten CORS.

Los datos de demostración llevan `origen: "sintetico"` y la web lo muestra en cada objeto.

## Composición espectral

Las fichas del explorador y del catálogo muestran «Composición espectral» solo si el espectro es
utilizable y `espectros.json` trae `composicion` (m6, `identificacion_molecular.py`). Se ve el
espectro medido con sus errores, las ventanas de referencia como franjas (teóricas, no medidas)
y una tarjeta por molécula con su estado escrito (detectada, candidata, compatible, sin rasgo o
datos insuficientes), la significancia S en sigmas, la explicación del criterio, las otras
explicaciones posibles, las advertencias y la referencia de la banda. La web no calcula nada.

## Datos de demostración

Mientras el pipeline no produce datos reales:

```bash
python modulos/m9_sitio/ejemplos/generar_datos.py
python -m modulos.m6_huella_espectral.identificacion_molecular --anotar datos/m7_publicacion  # composición (m6)
python -m modulos.m7_publicacion.indice_catalogo     # catálogo navegable sobre esos datos
```

Escribe en `datos/m7_publicacion/` tres campos (`slipher`, `atlas`, `luhman`) con
la misma forma que produce `m7_publicacion`. Los valores son ilustrativos.

## Verificación

```bash
# Los datos de demostración cumplen los contratos
check-jsonschema --schemafile contratos/campos.schema.json datos/m7_publicacion/campos.json

# La web arranca sin errores de recursos
python3 -m http.server 8765 &
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8765/modulos/m9_sitio/index.html
```

Pruebas de lógica:

```bash
node --test modulos/m9_sitio/pruebas/prueba_sitio.js modulos/m9_sitio/pruebas/prueba_comparador.js modulos/m9_sitio/pruebas/prueba_catalogo.js modulos/m9_sitio/pruebas/prueba_composicion.js
```

Comprobaciones manuales: `pruebas/lista_visual.md`.

## Límites conocidos

- **Los PNG no existen todavía.** Si falta `epoca_a.png`, el visor sintetiza dos
  fotogramas con los candidatos para que la interfaz sea demostrable. Cuando el
  pipeline entregue los PNG, se usan automáticamente y la síntesis no se ejecuta.
- **El campo `luhman` usa valores ilustrativos.** El movimiento propio real de
  una enana marrón (2,75 ″/año) no es detectable entre dos épocas de SPHEREx:
  en 6 meses supone 1,4 ″, una quinta parte de un píxel. El campo se conserva
  para mostrar la huella espectral, no como ejemplo de detección por movimiento.
- **El mapa del cielo depende de un servicio externo.** Si el servidor HiPS no
  responde en 2,5 s, la ficha dibuja un mapa de respaldo con la rejilla y la
  posición.
