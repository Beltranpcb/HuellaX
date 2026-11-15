<!--
  ARCHIVO: docs/analisis_de_objetos.md
  ROL: Balance de la ampliación «Análisis de objetos» pedida en la especificación
       «HUELLA X · Especificación web con composición molecular» (PDF del equipo, no
       versionado): qué se hizo, cómo se ejecuta, qué es real, qué es demostración y
       qué queda pendiente.
  ESTADO: develop, 2026-11-14.
-->

# Análisis de objetos: balance

La web tiene una sección **Análisis de objetos** con tres pestañas (Catálogo, Identificar,
Comparar espectros) y las fichas incluyen **Composición espectral**. La interfaz separa
detección, identificación por catálogo, comparación entre objetos, comparación con plantillas
y composición molecular: son operaciones distintas y así se presentan.

## Cómo se ejecuta

```bash
# Datos de demostración (sin red): campos sintéticos, composición de m6 y catálogo de m7
python modulos/m9_sitio/ejemplos/generar_datos.py
python -m modulos.m6_huella_espectral.identificacion_molecular --anotar datos/m7_publicacion
python -m modulos.m7_publicacion.indice_catalogo

# Datos reales: el pipeline completo, que ya incluye identificación molecular y catálogo
python -m herramientas.actualizar_publicacion --forzar

# Servir la raíz del repositorio y abrir la web
python -m http.server 8765
#   http://127.0.0.1:8765/modulos/m9_sitio/index.html  ->  «Análisis de objetos»

# Pruebas
python -m pytest -q                              # 162: m1 a m7 y la de extremo a extremo
node --test modulos/m9_sitio/pruebas/prueba_*.js  # 55: lógica de la web
```

## Qué es real, qué es demostración y qué falta

| Pieza | Estado | Detalle |
|---|---|---|
| Clic -> RA/DEC | **Real** | `meta.wcs` lo escribe m2 desde el FITS alineado; la proyección TAN de la web coincide con astropy a menos de 1 mas (5 casos: rotado, polo, RA = 0, hemisferio sur). |
| Efemérides de cuerpos menores | **Real, en vivo** | SkyBoT (IMCCE) desde el navegador, con la fecha de la época A. Probado con 2014 RR73: «coincidencia compatible» a 1,0″. |
| Identificación de las detecciones | Real cuando lo es el pipeline | La de m5 (JPL sb_ident, MPChecker) para la fecha de la época A. |
| Estrellas y galaxias (Gaia DR3) | **Pendiente** | El archivo de la ESA no admite CORS; el CDS estaba caído e IRSA daba 502 el 2026-11-14. Hay que precalcularlo en m5 (Python no necesita CORS). |
| Comparador de espectros | Real cuando lo es el pipeline | Lee `espectros.json`; cada objeto muestra su origen (real, demostración, no declarado). |
| Plantillas de referencia | **Sintéticas** | `plantillas.json` se declara `origen_plantilla: sintetica`. El χ² y el tipo solo tienen valor científico con curvas de bibliografía. |
| Composición molecular | Método real, validación **pendiente** | Calibrado con espectros sintéticos (S con desviación típica 0,95-1,1; ninguna detección falsa en 270 espectros sin rasgos). Falta validarlo con observaciones reales. |
| Catálogo navegable | Real cuando lo es el pipeline | Solo objetos detectados en los campos publicados. No hay Vesta, Ceres ni Halley porque el proyecto no tiene sus datos. |
| Datos de la web hoy | **Demostración** | Los tres campos (`slipher`, `atlas`, `luhman`) son sintéticos y lo dicen. El TAP de IRSA devolvía 502 el 2026-11-14; m1 tiene ahora un respaldo que lista las exposiciones leyendo las cabeceras de los FITS en la copia pública de AWS S3 (`indice_s3.py`), y el servicio de recortes de IRSA sí responde. |

## Criterios de aceptación de la especificación

| Criterio | Estado |
|---|---|
| Abrir una imagen compatible y seleccionar una fuente | Hecho (clic libre o sobre una detección marcada; zoom y arrastre). |
| Píxel -> RA/DEC con WCS y época de observación | Hecho; sin WCS se avisa y no se inventan coordenadas. |
| Búsqueda de móviles con fecha/hora y servicio adecuado | Hecho (SkyBoT, JD de la época A, observador geocéntrico avisado). |
| Resultados con fuente, separación y procedencia | Hecho, con error de la efeméride, tolerancia y criterio escrito. |
| Sin coincidencia: no identificado, nunca Planeta X | Hecho («Objeto no identificado en los catálogos consultados»). |
| El selector espectral solo incluye espectros válidos | Hecho (al menos dos puntos válidos); cuenta los excluidos. |
| Dos espectros con ejes, unidades, leyenda e incertidumbres | Hecho; las curvas se distinguen por estilo, no solo por color. |
| Flujo medido o normalizado, indicando el método | Hecho (λ de normalización y método visibles). |
| Plantillas separadas de la comparación A–B | Hecho (modo propio, texto propio, B desactivado). |
| Métricas con grados de libertad y advertencias | Hecho (χ² reducido, N - 1, puntos, avisos de m6). |
| Consume el contrato real sin romper m3/m4/m6 | Hecho: todos los campos nuevos son opcionales y `version_contrato` sigue en «1». |
| Informa de errores, falta de datos y calidad insuficiente | Hecho (carga, red, sin WCS, sin espectro, incompatibles, datos insuficientes). |
| Catálogo con nombre, designación, clase y datos disponibles | Hecho; la clase cita su fuente. |
| «Misma clasificación» y «Espectros más similares» separados | Hecho; la similitud la calcula m7 con métrica, intervalo y normalización. |
| Composición solo con espectro utilizable | Hecho. |
| Cada molécula con estado explícito y criterio | Hecho (sin rasgo, compatible, candidata, detectada, datos insuficientes). |
| Resolución de SPHEREx en la comparación y solapamientos | Hecho (R nominal por detector; banda sin resolver no pasa de candidata; alternativas físicas). |
| Ninguna detección por coincidencia aproximada | Hecho («detectada» exige cinco condiciones a la vez). |
| Pruebas de detecciones, falsos positivos y ambigüedades | Hecho, con datos sintéticos etiquetados. |
| Validación con observaciones reales | **Pendiente** (sin datos reales procesados todavía). |
| Objetos de prueba previstos (Barnard, Epsilon Indi B, WISE 0855, RW Aur, R Dra) | **Pendiente**: no hay sus FITS en el repositorio. |

## Contratos

Todas las ampliaciones son compatibles: campos opcionales, `version_contrato` igual a «1». Nuevos
contratos: `plantillas.schema.json` y `catalogo.schema.json`. Detalle en [contratos/LEEME.md](../contratos/LEEME.md).

## Archivos

| Módulo | Nuevos | Modificados |
|---|---|---|
| contratos | `catalogo.schema.json`, `plantillas.schema.json`, sus ejemplos | `meta`, `identificacion`, `espectros`, `candidatos` (campos opcionales), `LEEME.md` |
| m2 | — | `metadatos_campo.py` (publica `wcs` y `origen`) |
| m6 | `identificacion_molecular.py` | `comparacion_plantillas.py` (grados de libertad, avisos), `ajuste_planck.py` (aviso de cuerpo negro), `escritura_espectros.py` (calidad, composición, plantillas publicadas), `plantillas.json` (origen) |
| m7 | `indice_catalogo.py` | `copia_publicable.py` (plantillas), `control_publicacion.py` (valida plantillas y catálogo) |
| m9 | `analisis.js`, `catalogo*.js`, `comparador*.js`, `composicion*.js`, `identificar*.js`, cuatro pruebas y `wcs_referencia.json` | `index.html`, `estilo.css`, `carga_datos.js`, `ejemplos/generar_datos.py` |
| herramientas | `pruebas/prueba_extremo_a_extremo.py` | `actualizar_publicacion.py` (pasos nuevos; UTF-8 en Windows) |

## Decisiones que quedan para el equipo

1. **Gaia DR3 en m5**: precalcular un cone search por detección contra el archivo de la ESA y
   guardarlo en `identificacion.coincidencias` (el contrato ya lo admite).
2. **Plantillas de bibliografía**: sustituir las cuatro curvas sintéticas y rellenar `referencia`.
3. **Datos reales**: `actualizar_publicacion --forzar` ya no depende del TAP de IRSA (respaldo por S3). La primera exploración de una semana tarda minutos (lee ~2000 cabeceras); después queda en caché en `datos/m1_adquisicion/indice_s3/`.
4. **CO junto a 5 µm**: con el muestreo nominal suele quedar en «datos insuficientes»; no se relajó
   el continuo porque con menos puntos aparecían candidatas falsas en el 10 % de los espectros.
5. **SkyBoT es geocéntrico**: para objetos muy cercanos convendría pasar la posición de SPHEREx.
