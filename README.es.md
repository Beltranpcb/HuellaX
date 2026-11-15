# HuellaX · MoveScope × AstroNova

**Un laboratorio de movimiento con SPHEREx, unificado y centrado en candidatos.**

HuellaX combina **MoveScope**, nuestro sistema vivo de análisis de imágenes
multiépoca de SPHEREx, con **AstroNova / HUELLA X**, el prototipo de NASA Space
Apps Challenge 2026 conservado como demo estática legacy y pipeline offline.
El sistema vivo está en `系统/`; la referencia upstream está en `astro/`.

[English](README.md) | **Español**

> Idioma legacy: [中文](README.zh-CN.md) es el README histórico en chino, solo
> de MoveScope. Se conserva por continuidad y **no** es el punto de entrada
> principal de este repositorio unificado.
>
> Portada bilingüe: [`index.html`](index.html) (inglés por defecto, español
> completo, `?lang=en|es`).

> **Jerarquía de datos — leer primero.**
> **SQL es la fuente de datos principal**: el catálogo SQLite y el almacén de
> blobs en el puerto `8797` poseen los objetivos, las épocas, la cobertura y
> los índices de recortes. Los JSON estáticos de AstroNova en `astro/` son
> **datos legacy/demostración**, útiles como referencia de interfaz y de
> contratos, pero nunca como evidencia de un resultado científico.
>
> **Cada resultado es un candidato, no un descubrimiento.** Este repositorio no
> afirma una nueva estrella, un nuevo planeta ni una confirmación del Planeta X.
> El producto declara explícitamente `discovery_claim: false`.

![Interfaz de MoveScope](系统/docs/img/ui-main.png)

*Datos reales: Epsilon Indi B, ocho épocas de SPHEREx en una línea base de 361
días. El recuadro de trayectoria muestra el desplazamiento medido de 4,41″.*

---

## 1. Qué es este repositorio

| Capa | Ruta | Rol |
|---|---|---|
| **Runtime principal** | `系统/` | App MoveScope, catálogo SQL, servicio de catálogo B, servicio de cobertura C y vista 3D opcional |
| **Upstream legacy** | `astro/` | Sitio estático y pipeline Python offline de AstroNova/HUELLA X, preservados en un commit upstream analizado |
| **Plano de control** | `项目主控/` | Lanzador, informes de aceptación, decisiones de arquitectura y análisis de referencia |
| **Documentación de integración** | raíz | `index.html`, este README, [`README.es.md`](README.es.md), [`INTEGRATION.md`](INTEGRATION.md) |

### Puntos de entrada

| Destino | URL | Notas |
|---|---|---|
| **App MoveScope** | <http://127.0.0.1:8790/> | Interfaz de análisis viva; iniciar con el lanzador |
| **Vista del cielo** | <http://127.0.0.1:8830/> | Contexto opcional de cielo/globo con three.js |
| **AstroNova legacy** | [`astro/modulos/m9_sitio/index.html`](astro/modulos/m9_sitio/index.html) | Demo estática; requiere datos de demo sintéticos y un servidor HTTP |
| **GitHub — principal** | <https://github.com/tonyelos/huella-x-simu> | Repositorio fuente de MoveScope |
| **GitHub — destino de integración** | <https://github.com/Beltranpcb/HuellaX> | Repositorio de integración HuellaX |
| **AstroNova upstream** | <https://github.com/Beltranpcb/AstroNova> | Prototipo original de NASA Space Apps 2026 |

### Qué no es

- No es un motor de descubrimientos. “Sin coincidencia en catálogo” significa
  “candidato sin catalogar”, nunca “objeto nuevo”.
- No es una confirmación del Planeta X. Las asociaciones de dos o cuatro épocas
  no pueden establecer un nuevo cuerpo del sistema solar.
- No afirma que los datos de demo de AstroNova sean reales. Sus campos
  publicados son sintéticos y no se usan como evidencia de validación.
- No es una copia del código de AstroNova. El upstream no tenía licencia en el
  momento del análisis; se incluye con permiso del propietario y no se
  relicencia bajo nuestra Apache-2.0. Ver [`astro/UPSTREAM.md`](astro/UPSTREAM.md)
  e [`INTEGRATION.md`](INTEGRATION.md).

---

## 2. Qué hace MoveScope

MoveScope toma una posición del cielo, recupera varias imágenes espectrales de
nivel 2 de SPHEREx, mide la posición y el flujo de un objetivo (y de los objetos
que lo rodean), ajusta una familia de modelos físicamente motivada y publica una
**huella de movimiento**, una clasificación, confianza, evidencia falsable y los
límites de lo que los datos pueden sostener.

Para un objetivo informa una de estas clases de movimiento:

| Clase | Significado | Interpretación típica |
|---|---|---|
| **L** | Movimiento propio lineal | Estrella cercana / enana marrón con μ medible |
| **V** | Variable | Posición estable, flujo cambiante (estrella variable, AGN) |
| **A** | Acelerado / curvado | Objeto del sistema solar o candidato a órbita binaria |
| **S** | Estacionario | Estrella de fondo / galaxia; da un límite superior de movimiento a 3σ |
| **U** | Indeterminado | La madurez o la calidad de datos no alcanza; no adivina |

Cada resultado incluye:

- **readiness** L0–L3 (1 / 2 / 3–5 / ≥6 épocas con una línea base ≥6 meses);
- **selección de modelo** entre M0 estacionario, M1 variable, M2 movimiento
  propio lineal, M3 paralaje, M4 movimiento propio + aceleración;
- **cadena de evidencia** y **falsador**;
- **procedencia** REAL / HYBRID / SIM / SAMPLE; los datos simulados nunca se
  presentan como reales;
- un límite explícito `discovery_claim: false`.

La herramienta habla deliberadamente de candidatos y evidencia. “Sin
coincidencia en catálogo” significa “candidato sin catalogar”, nunca “nueva
estrella” o “nuevo planeta”.

> El diseño precede al código. Lee primero la nota teórica:
> [`系统/docs/01_理论设计编排.md`](系统/docs/01_理论设计编排.md).
> Los detalles de implementación, los valores medidos y las discrepancias
> conocidas están en
> [`系统/docs/02_实现与实测记录.md`](系统/docs/02_实现与实测记录.md).

---

## 3. Estado actual

La suite de pruebas del lado de la app tiene actualmente **291 pruebas**:

```bash
PY=/Users/yiao/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3
cd 系统/app
$PY -m unittest discover -s tests
# Ran 291 tests ... OK
```

Capacidades recientes:

- modos del lienzo principal: **Browse / Cascade-residual / Tracks**;
- filtrado por ventana temporal `t0/t1` para el análisis y los productos de capa;
- identificación por lotes de fuentes A y C;
- exportación de auditoría CSV/JSON, incluido CSV con candidatos expandidos;
- consumo por lotes de catálogos Gaia + 2MASS + WISE con deduplicación
  posicional de 0,5″;
- anotación de movimiento con prior de catálogo (caso Barnard de línea base
  corta);
- directorio de auditoría unificado A + C + Tracks;
- inspección de candidatos A/C/Track sin escribir en la base de datos de
  catálogo.

Los cinco objetivos oficiales del benchmark en la caché actual se resuelven así:

| Objetivo | Esperado | Resultado de la app | Notas |
|---|---|---|---|
| Barnard's Star | L | **L (prior de catálogo)** | SPHEREx no midió el movimiento de forma independiente; se usó el prior de PM de Gaia |
| Epsilon Indi B | L + O | **L**, identidad ambigua | RUWE alto; no se fuerza una identidad de catálogo única |
| WISE 0855 | L | **U** | limitado por datos; no se fuerza L |
| RW Aurigae | V | **V** | variabilidad de flujo, posición estable |
| R Draconis | V | **V** | variabilidad de flujo, posición estable |

Resultado: **4 PASS + 1 DATA_LIMITED**. El benchmark puede fallar o quedar
limitado por datos a propósito; la herramienta no ajusta las etiquetas a la
respuesta esperada.

---

## 4. Inicio rápido

### Requisitos

- Python 3.12 con NumPy y Pillow (el runtime incluido funciona sin configuración);
- un navegador con soporte de Canvas;
- para la vista WebGL opcional: WebGL2;
- los puertos son solo locales por defecto.

### Un solo comando (DB + app + vista)

```bash
cd /path/to/HuellaX          # repository root
项目主控/启动/start_all.sh
# abrir http://127.0.0.1:8790/
```

El lanzador inicia **DB → app → vista**, hace comprobaciones de salud y se niega
a reemplazar en silencio servicios que ya están corriendo. **No** inicia el
servicio de catálogo B (`8799`) ni el servicio de cobertura C (`8798`);
inícialos por separado cuando hagan falta. Ver
[`项目主控/启动/README.md`](项目主控/启动/README.md).

En un checkout nuevo sin `系统/数据库工具/var/catalog.sqlite`, inicializa
primero el catálogo SQL; el lanzador se detiene con un error explícito en lugar
de crear una base vacía. Ver
[`系统/数据库工具/README.md`](系统/数据库工具/README.md) §2.

### Inicio manual

```bash
PY=/Users/yiao/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3

# 1) app principal
$PY 系统/app/server.py --port 8790

# 2) catálogo SQL + servicio de blobs
cd 系统/数据库工具
$PY cli.py serve --port 8797
```

Servicios complementarios opcionales:

```bash
# B: servicio de catálogo / identificación (8799)
cd 系统/数据库工具
$PY tools/import_gaia.py --rebuild --offline   # bootstrap/fixture offline
$PY catalog_server.py --port 8799

# C: cobertura local / descubrimiento / descarga (8798)
cd 系统/anyfield
./start.sh 8798

# Vista: selector de cielo/Tierra con three.js (8830)
cd 系统/视图工具
./start.sh 8830
```

La página principal es <http://127.0.0.1:8790/>. Si B o C no están corriendo,
la app degrada de forma explícita; no inventa resultados de catálogo ni de
cobertura.

### Puertos

| Servicio | Puerto | ¿Lo inicia `start_all.sh`? | Datos que posee |
|---|---:|---|---|
| App MoveScope | **8790** | sí | Resultados de análisis, evidencia, readiness |
| API del catálogo SQL | **8797** | sí | Objetivos, épocas, cobertura, frames, recortes, blobs |
| Vista del cielo | **8830** | sí | Solo contexto de cielo |
| Servicio de catálogo B | **8799** | opcional | Caché por campo de Gaia, cruces 2MASS/WISE |
| Servicio de cobertura C | **8798** | opcional | Huellas de cabeceras, sidecar, trabajos de descarga |
| Portada / legacy estático | cualquier puerto estático | no | Datos de demo generados |

Los valores de producción nunca cambian en silencio. Para pruebas aisladas de
la cadena de arranque, el lanzador acepta puertos sandbox explícitos; ver su
README.

### Portada y demo legacy

La portada bilingüe es HTML/CSS/JS sin build. Sirve la raíz del repositorio por
HTTP (el sitio legacy usa `fetch` y no funcionará desde `file://`):

```bash
cd /path/to/HuellaX          # repository root
python3 -m http.server 8840
# portada: http://127.0.0.1:8840/index.html
# legacy:  http://127.0.0.1:8840/astro/modulos/m9_sitio/index.html
```

El sitio estático legacy lee `astro/datos/m7_publicacion/`, que está en
`.gitignore`. Genera primero sus campos de demostración **sintéticos**:

```bash
cd astro
python3 modulos/m9_sitio/ejemplos/generar_datos.py
```

Esto escribe JSON/PNG de demo para los campos `slipher`, `atlas` y `luhman`.
Son sintéticos, están claramente etiquetados y no deben presentarse como
observaciones.

### URLs básicas

```text
http://127.0.0.1:8790/                                      # modo Browse
http://127.0.0.1:8790/?target=barnard                      # preset
http://127.0.0.1:8790/?ra=269.452077&dec=4.693365&fov=0.2  # coordenadas personalizadas
http://127.0.0.1:8790/?target=barnard&mode=cascade          # superposición en el lienzo principal
http://127.0.0.1:8790/?target=barnard&mode=tracks
http://127.0.0.1:8790/?ra=269.452077&dec=4.693365&fov=0.5&t0=60890&t1=60950&from=view
```

`mode` es el modo del lienzo (`browse`, `cascade`, `tracks`), no el modo de
datos. El modo de datos se elige en el panel izquierdo (`auto`, `real`,
`synthetic`, `sample`). `/cascade` y `/tracks` siguen disponibles como tablas
de diagnóstico detalladas; la página principal no redirige a ellas al cambiar
de modo.

---

## 5. Arquitectura

```text
                         ┌─────────────────────────────┐
                         │ Vista (opcional, 8830)      │
                         │ selector de cielo / Tierra  │
                         │ ra / dec / fov / t0 / t1    │
                         └──────────────┬──────────────┘
                                        │ una URL de handoff
                                        ▼
┌──────────────────────────────────────────────────────────────────┐
│ App MoveScope (8790)                                             │
│                                                                  │
│  Interfaz de navegador (sin build)                               │
│    Browse  ── análisis, selección de fuentes, lock, identify     │
│    Cascade ── superposición L1 / enmascarado / residual          │
│    Tracks  ── líneas/nodos de tracklets y niveles D0–D4          │
│                                                                  │
│  /api/analyze   → build_dataset → pipeline → resultado           │
│  /api/cascade   → L1 / máscara / residual por época              │
│  /api/tracks    → tracklets → D0–D4                              │
│  /api/identify  → coincidencia en catálogo B (fuente única)      │
│  /api/identify/batch → coincidencia por lotes B (fuentes A/C)    │
│  /api/identify/batch/export → adjunto CSV/JSON                   │
└───────────────┬───────────────────────┬──────────────────────────┘
                │                       │
                ▼                       ▼
┌───────────────────────────┐   ┌──────────────────────────────────┐
│ Catálogo SQL (8797)       │   │ Servicio de catálogo B (8799)    │
│ metadatos SQLite + Blob   │   │ Gaia DR3 + 2MASS/WISE por campo  │
│ índice de épocas/cobertura│   │ match simple/lote, TAP opcional  │
│ fuente de datos primaria  │   │ sin clasificación científica     │
└───────────────┬───────────┘   └──────────────────────────────────┘
                │ cobertura / descubrimiento opcional
                ▼
┌───────────────────────────┐
│ Servicio de cobertura C   │
│ (8798)                    │
│ huellas de cabeceras,     │
│ descubrimiento, descarga  │
│ S3/IRSA                   │
└───────────────────────────┘
```

La app principal no tiene paso de build: los recursos estáticos de `web/` se
sirven directamente. El pipeline de análisis es Python puro + NumPy + Pillow;
no requiere Astropy/SciPy/FastAPI para la ruta central.

### 5.1 Flujo de datos SQL

```text
Productos semanales de IRSA / S3
        │
        ▼
系统/数据库工具/  (ingesta, recolección, importación)
        │  releases · weeks · observations · frames · targets
        │  target_epochs · cutouts · blobs · fields_snapshot · ingest_runs
        ▼
var/catalog.sqlite  +  var/blobs/          ← única verdad de épocas/cobertura
        │
        │  GET /api/v1/epochs?ra&dec&fov
        │  GET /api/v1/coverage?ra&dec
        ▼
App MoveScope (8790)
  build_dataset → descarga de recortes → fotometría → asociación
  → M0–M4 + BIC → readiness → evidencia / falsador / procedencia
        │
        ▼
Interfaz · /api/analyze · auditoría CSV/JSON
```

Propiedades clave:

- SQL posee **lo que se observó**: coordenadas de objetivos, frames, metadatos
  de exposición, épocas curadas, índices de recortes, cobertura y procedencia.
- MoveScope posee **lo que significa**: fotometría, calibración astrométrica
  relativa, asociación, selección de modelo, readiness y redacción pública.
- B posee **candidatos de identidad** de Gaia/2MASS/WISE. No hace clasificación
  científica y nunca convierte una coincidencia en descubrimiento.
- C posee **cobertura y descubrimiento de campos arbitrarios**, y escribe solo
  su propio sidecar. Una descarga fallida se informa como no disponible, no
  como “sin cobertura”.
- Las exportaciones son vistas materializadas, no una segunda verdad.
  `check_compat.py` concilia los JSON exportados con los consumidores app/view.

Para objetivos predefinidos, MoveScope puede funcionar desde el
`epoch_catalog.json` local para mantener la demo operativa offline. Ese
respaldo es explícito. Para coordenadas arbitrarias, la app resuelve épocas
reales mediante el contrato v1 de la DB; cero épocas locales producen un estado
SIM/no disponible explícito, nunca una medición real fabricada. La variable de
entorno es `SPHEREX_DB_URL` (por defecto `http://127.0.0.1:8797`).

### 5.2 Pipeline de análisis

```text
Imagen FITS / nivel 2
  → fondo + máscara FLAGS + modelo de ruido
  → detección con filtro adaptado
  → centroide PSF / bloom + fotometría de apertura
  → calibración astrométrica relativa con estrellas de referencia
  → asociación de posiciones de fuentes entre épocas
  → ajuste de la familia M0/M1/M2/M3/M4
  → elección por BIC + umbrales 3σ / readiness
  → resultado, evidencia, falsador, procedencia
```

Módulos clave de implementación:

- `系统/app/core/photometry.py` — máscara, filtro adaptado, centroide, fotometría;
- `系统/app/core/motion.py` — familia de modelos, BIC, huella de movimiento;
- `系统/app/core/pipeline.py` — detección → calibración → asociación → inferencia;
- `系统/app/core/epoch_source.py` — resolvedor DB v1, cobertura y respaldo explícito;
- `系统/app/core/catalog.py` — cliente de catálogo B, mapeo de estados,
  deduplicación posicional multi-catálogo e ingesta opcional;
- `系统/app/core/catalog_prior.py` — prior genérico de PM de Gaia para un
  resultado S de línea base corta poco significativo;
- `系统/app/core/tracks.py` — tracklets entre épocas y niveles de candidato D0–D4.

### 5.3 Ventana temporal

`/api/analyze`, `/api/cascade` y `/api/tracks` aceptan `t0` / `t1` (también
`mjd_min` / `mjd_max`). El filtro se aplica después de
`data_layer.build_dataset`:

- 0 épocas → HTTP 200 con un resultado de ventana vacía explícito, nunca una
  medición fabricada;
- 1 época → resultado normal de una época; los tracks se marcan `insufficient`;
- sin `t0/t1` → comportamiento anterior sin cambios.

La respuesta incluye `time_filter: {t0,t1,requested,kept,filtered}` y la
interfaz muestra “from view / time window / kept N of M”.

---

## 6. Modos principales de la interfaz

### Browse

El comportamiento original: parpadeo multiépoca, apilado, diferencia,
trayectoria del objetivo, tabla de fuentes A, lock/identify, readiness y
evidencia del modelo.

### Cascade / residual

Para cada época:

- **L1**: detección a 6σ, como máximo 80 objetos por época;
- **masked**: las posiciones L1, máscara de 2 px, motivo `already_detected`;
- **residual**: re-detección a 5σ tras enmascarar la mediana local, como máximo
  80 candidatos por época, excluyendo duplicados a menos de 2 px de L1.

El lienzo principal superpone L1 como puntos cian sólidos, lo enmascarado como
cruces grises y los residuales como círculos ámbar huecos. Hay conmutadores de
capa y recuentos por frame. Al hacer clic en un nodo residual se bloquea y se
llama a `/api/identify`; no se vuelve a ejecutar todo el análisis. Los
candidatos residuales **no son objetos nuevos**, explícitamente.

Página de diagnóstico detallada: [`/cascade`](系统/app/web/cascade.html).

### Tracks

Los nodos L1 + residuales se asocian entre épocas (vecino más cercano voraz,
puerta de 3 px, se permite un hueco de una época, sin reutilizar nodos). Los
modelos de track son `stationary / linear / curved / variable / transient`, y
los niveles de candidato son:

- D0 artefacto;
- D1 catálogo conocido;
- D2 no implementado;
- D3 movimiento desconocido;
- D4 estacionario desconocido;
- D5 fuera de alcance (manual/seguimiento).

El lienzo principal dibuja líneas y nodos de track; al hacer clic en un nodo se
salta a su época y se invoca `/api/identify`. Los candidatos de track **no son
objetos nuevos**; cuatro épocas hacen que la asociación sea intrínsecamente
ambigua y cada track carga esa advertencia.

Página de diagnóstico detallada: [`/tracks`](系统/app/web/tracks.html).

### Identificación por lotes A / C

- Tabla A: `sources` del análisis, paginadas/por lotes de 200 por petición;
- Tabla C: filas de `/api/sources`, por lotes de 200 por petición;
- cada fuente se envía a `/api/identify/batch`;
- estados: known / ambiguous / no_match (`uncatalogued_candidate`) /
  insufficient / catalog unavailable / unknown;
- las notas de lote A y C muestran recuentos y los catálogos solicitados;
- los resultados por lotes se pueden exportar para auditoría sin cambiar la
  tabla.

### Directorio unificado de candidatos

A + C + Tracks se fusionan en una única tabla de auditoría de solo lectura:

- las filas A/C se deduplican por `(mjd, round(ra,6), round(dec,6))`;
- filas A/C en la misma posición fusionan `origins` en `A;C`;
- las identidades en conflicto se convierten en `conflict`, nunca se resuelven
  en silencio;
- un track es una fila; los nodos del track **no** cuentan como fuentes nuevas;
- recuentos: rows / unique_sources / tracks / known / ambiguous / no_match /
  insufficient / unknown / conflict;
- exportación CSV y JSON; la interfaz muestra las primeras 80 filas y los
  recuentos sobre el conjunto completo.

---

## 7. Identificación en catálogo y reglas multi-catálogo

### Vocabulario de estados

| Estado | Significado |
|---|---|
| `known_star` | Un único candidato de catálogo con calidad astrométrica aceptable |
| `ambiguous` | Varios candidatos físicos, o un conflicto de calidad/RUWE/PM |
| `uncatalogued_candidate` | La consulta tuvo éxito con cero candidatos; **no** es “objeto nuevo” |
| `insufficient_data` | Información insuficiente; p. ej. un único candidato a más de 6,15″ |
| `catalog_unavailable` | Servicio/cobertura de catálogo no disponible; **no** es “sin coincidencia” |

Un único candidato a más de **6,15″** (un píxel de SPHEREx) del objetivo se
rechaza como alineación accidental y se devuelve como `insufficient_data` con
motivo `CATALOG_OFFSET_TOO_LARGE`.

### Movimiento con prior de catálogo

Para un resultado `class="S"` de línea base corta, la app puede aplicar un prior
genérico de catálogo cuando:

- hay un PM de Gaia único/ambiguo;
- el PM de catálogo es significativo y > 1000 mas/año;
- el PM medido y el de catálogo coinciden dentro de 3σ.

Entonces la clase pasa a `L` con:

- `catalog_motion.basis = "catalog_prior"`;
- `quality += CATALOG_PRIOR_MOTION, MEASUREMENT_NOT_SIGNIFICANT`;
- confianza ≤ 0,6;
- texto explícito: “SPHEREx no lo midió de forma independiente; se usó el prior
  de PM de Gaia; no es un descubrimiento”.

Se conservan la μ medida, su error, `moving=false` y la significancia original.
El prior nunca se escribe como movimiento propio medido.

### Lote multi-catálogo

Las peticiones por lotes A/C usan:

```json
{"catalogs": ["gaia", "2mass", "wise"]}
```

2MASS/WISE tienen **cachés reales de campo de IRSA Gator para los 7 campos
predefinidos** (2MASS 8.674; WISE 23.774), además de versiones derivadas
legacy. No son sondeos globales; las consultas fuera de los 7 campos siguen no
disponibles. El cliente:

- agrupa candidatos de distintos catálogos dentro de **2,0″**;
- prefiere Gaia como candidato principal, luego 2MASS y luego WISE;
- conserva las filas de otros catálogos en `crossmatches`;
- no fusiona dos posiciones distintas; dos grupos físicos siguen siendo
  ambiguos;
- no trata varias filas de catálogo de una misma fuente física como varias
  fuentes.

Un fallo de B sigue siendo `catalog_unavailable`; versiones antiguas de B
pueden recurrir a Gaia con un marcador explícito `catalog_fallback="gaia"`.

---

## 8. Resumen de la API

| Método | Ruta | Propósito |
|---|---|---|
| `POST` | `/api/analyze` | análisis completo de movimiento; acepta target/ra/dec/fov/mode/t0/t1 |
| `GET` | `/api/targets` | objetivos predefinidos |
| `GET` | `/api/health` | salud de la app |
| `GET` | `/api/sources` | proxy de la lista de fuentes C |
| `GET` | `/api/field` | handshake de cobertura C |
| `GET` | `/api/cascade` | L1 / enmascarado / residual por época |
| `GET` | `/api/tracks` | tracklets entre épocas y D0–D4 |
| `POST` | `/api/identify` | identificación de una fuente en catálogo |
| `POST` | `/api/identify/batch` | identificación por lotes (≤200 fuentes) |
| `POST` | `/api/identify/batch/export` | adjunto de auditoría CSV/JSON |

Ejemplos:

```bash
curl -X POST http://127.0.0.1:8790/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"target_id":"barnard","fov":0.2,"mode":"auto"}'

curl 'http://127.0.0.1:8790/api/cascade?target_id=barnard&fov=0.2'
curl 'http://127.0.0.1:8790/api/tracks?target_id=barnard&fov=0.2'

curl -X POST http://127.0.0.1:8790/api/identify \
  -H 'Content-Type: application/json' \
  -d '{"ra":269.452077,"dec":4.693365,"mjd":60916.656,"sigma_arcsec":0.5}'
```

Los endpoints por lotes están explícitamente limitados a 200 fuentes por
petición. El endpoint de exportación divide entradas de tamaño A (215 → 200 +
15) y devuelve un adjunto CSV/JSON; el JSON contiene `sources`, `results` y
`byId`, y el CSV expande los candidatos físicos en filas de candidatos.

La ingesta automática de catálogo está **desactivada por defecto**:

```bash
export CATALOG_AUTO_INGEST=1
export MOVESCOPE_CATALOG_INGEST_TIMEOUT=60
```

Cuando se activa, una coincidencia parcial o sin campo en caché puede llamar
una vez a B `POST /api/v1/catalog/ingest` y reintentar una vez. Las escrituras
de ingesta son del lado de B; la app no escribe la DB de producción. La
disponibilidad de TAP sigue siendo una dependencia upstream.

Endpoints del catálogo SQL usados por el runtime:

```text
GET http://127.0.0.1:8797/api/v1/health
GET http://127.0.0.1:8797/api/v1/epochs?ra=...&dec=...&fov=...
GET http://127.0.0.1:8797/api/v1/coverage?ra=...&dec=...
GET http://127.0.0.1:8797/api/v1/targets
```

---

## 9. Modos de datos

| Modo | Fuente | Propósito | Insignia |
|---|---|---|---|
| REAL | Recortes de nivel 2 de SPHEREx multiépoca desde IRSA/caché estática | Observaciones reales | verde |
| HYBRID | Fondo/PSF/ruido reales de una época + objetivo inyectado | Cuando las épocas reales no alcanzan | ámbar |
| SIM | Serie temporal sintética a partir de PSF/fondo/ruido reales | Validación de algoritmos / enseñanza | azul |
| SAMPLE | Dos recortes offline empaquetados de campos distintos | Solo análisis/renderizado | gris |

La ruta de datos no requiere TAP/SIA/DataLink para los campos predefinidos
conocidos: usa el índice semanal de apuntamientos en S3, cabeceras HTTP Range y
recortes estáticos. La cobertura de coordenadas arbitrarias sigue dependiendo
del índice local de DB/C y se informa como `NO_LOCAL_COVERAGE` o
`DB_UNAVAILABLE` cuando falta.

---

## 10. Validación y pruebas

### Pruebas de la app

```bash
PY=/Users/yiao/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3
cd 系统/app
$PY -m unittest discover -s tests -v
# Ran 291 tests ... OK
```

La cobertura incluye: modos sample/real, validación de FOV, caché y LRU,
conflictos de coordenadas de objetivos, contratos de esquema, mapeo de estados
de catálogo, movimiento con prior de catálogo, filtros temporales, modos del
lienzo principal, capas cascade, tracklets, identificación por lotes A/C,
candidatos/exportación y deduplicación del directorio unificado.

### Pruebas del catálogo SQL

```bash
cd 系统/数据库工具
$PY -m unittest discover -s tests -v
```

El proyecto de catálogo mantiene sus propias pruebas de contrato y
comprobaciones de compatibilidad:

```bash
$PY tools/check_compat.py --root ..
```

### Informes de benchmark y validación

- [`项目主控/验收/官方案例基准_report.md`](项目主控/验收/官方案例基准_report.md)
- [`项目主控/验收/官方案例基准_fullcache.md`](项目主控/验收/官方案例基准_fullcache.md)
- [`项目主控/验收/星表识别覆盖率.md`](项目主控/验收/星表识别覆盖率.md)
- [`项目主控/验收/GUI链路测试.md`](项目主控/验收/GUI链路测试.md)
- [`系统/docs/validation_report.json`](系统/docs/validation_report.json)
- [`系统/docs/motion_vs_variability.json`](系统/docs/motion_vs_variability.json)

Resultados representativos de validación:

- inyección-recuperación: 5 objetivos oficiales × 8 semillas aleatorias =
  40/40 correctos;
- contraejemplos: RW Aur y R Dra se clasifican como V en todas las semillas; la
  pendiente de posición es compatible con cero;
- Epsilon Indi B: 8 épocas reales, línea base de 361 días, μ ≈ 4,71 ± 0,55″/año,
  PA ≈ 129,6° (los valores de SIMBAD son cercanos);
- Barnard: la μ de SPHEREx de línea base corta no es significativa; se informa
  como L con un prior explícito de PM de Gaia, no como una detección medida por
  SPHEREx;
- WISE 0855: U limitado por datos; sin clasificación forzada.

Los recuentos de lotes A/C y del directorio dependen de los datos y los imprime
la interfaz; el registro E2E en `系统/docs/02_实现与实测记录.md` es la fuente
autoritativa para la caché actual.

### Comprobaciones estáticas de integración

La integración de portada/documentación añade un verificador sin dependencias:

```bash
python3 scripts/check_docs.py
```

Verifica la decodificación UTF-8, los enlaces locales de HTML/Markdown, el
cambio de idioma del README, la cobertura de claves i18n en `index.html` y las
afirmaciones mínimas obligatorias (SQL principal, demo legacy, candidato no
descubrimiento). No compila ni ejecuta los servicios.

---

## 11. Estructura del repositorio

```text
index.html                 portada bilingüe (EN por defecto / ES completo)
README.md                  este archivo en inglés (principal)
README.es.md               README completo en español
README.zh-CN.md            README chino legacy de MoveScope (histórico)
INTEGRATION.md             mapeo AstroNova → HuellaX, flujo SQL, atribución
LICENSE / NOTICE           Apache-2.0 para el trabajo original
THIRD_PARTY_NOTICES.md     inventario completo de terceros
REFERENCES.md              lista breve de citas para la entrega
CITATION.cff               metadatos de citación legibles por máquina
scripts/check_docs.py      comprobaciones estáticas sin dependencias (enlaces, UTF-8, i18n)

系统/
  app/                     app principal MoveScope (servidor + core + web)
    server.py              API HTTP, interfaz estática, renderizado de imágenes
    core/                  FITS, WCS, fotometría, movimiento, pipeline, catálogo,
                           epoch_source, tracks, prior de catálogo, utilidades
    web/                   interfaz sin build y páginas de diagnóstico
    tests/                 pruebas unitarias/de integración de la app
  docs/
    01_理论设计编排.md       base teórica (leer primero)
    02_实现与实测记录.md     implementación, medidas, discrepancias
    validation_report.json  inyección-recuperación
  anyfield/                servicio C de cobertura/descubrimiento/descarga
  数据库工具/               catálogo SQL + servicio de catálogo B
  视图工具/                 vista opcional de cielo/Tierra con three.js
  tools/                   utilidades de índice semanal/búsqueda de épocas/validación
  参考 资料/               referencias y notas de terceros

astro/
  README.md                README upstream de AstroNova/HUELLA X (español)
  ARQUITECTURA.md          arquitectura y contratos de módulos upstream
  UPSTREAM.md              SHA upstream, permiso y límite de alcance
  modulos/m1–m7, m9        pipeline offline + sitio estático
  contratos/               contratos JSON Schema y ejemplos

项目主控/
  架构/                    notas de arquitectura y evolución
  验收/                    informes de benchmark/aceptación
  启动/                    lanzador de arranque/parada
  参考/AstroNova-DEEP.md   análisis profundo upstream (solo lectura)
  README.md                notas de control del proyecto
```

Documentos clave:

- [Diseño teórico](系统/docs/01_理论设计编排.md)
- [Implementación y registro medido](系统/docs/02_实现与实测记录.md)
- [Contrato de arquitectura](项目主控/02_架构设计与集成契约.md)
- [Guía del lanzador](项目主控/启动/README.md)
- [Plan de refactor por modos](项目主控/架构/14_模式化重构计划.md)
- [Plan de ingesta de catálogo](项目主控/架构/17_数据接收接口与自动缓存.md)
- [Plan de identificación por lotes](项目主控/架构/18_批量星表识别.md)
- [Plan de auditoría y exportación](项目主控/架构/20_批量结果审计导出.md)
- [Plan de directorio unificado de candidatos](项目主控/架构/22_统一候选目录.md)
- [Análisis profundo de AstroNova](项目主控/参考/AstroNova-DEEP.md)
- [Mapa de integración](INTEGRATION.md)

---

## 12. Configuración y entorno

| Variable | Valor por defecto | Propósito |
|---|---|---|
| `SPHEREX_DB_URL` | `http://127.0.0.1:8797` | Override del endpoint v1 del catálogo SQL |
| `CATALOG_URL` / `MOVESCOPE_CATALOG_URL` | `http://127.0.0.1:8799` | URL base del catálogo B |
| `MOVESCOPE_CATALOG_TIMEOUT` | `2.5` s | Timeout de coincidencia B |
| `CATALOG_AUTO_INGEST` | desactivado | Permite una ingesta+reintento en parcial/sin campo en caché |
| `MOVESCOPE_CATALOG_INGEST_TIMEOUT` | `60` s | Timeout de ingesta B |
| `ANYFIELD_URL` | `http://127.0.0.1:8798` | URL base de cobertura C |
| `ANYFIELD_TIMEOUT` | `1.5` s | Timeout de cobertura C |

La app nunca cambia de puerto en silencio, y el lanzador se niega a reemplazar
un servicio vivo con un PID que no coincide.

---

## 13. Limitaciones y uso responsable

1. **No es un descubrimiento.** Cada estado de catálogo y cada track es un
   candidato. `discovery_claim` es falso; no se afirma “nuevo planeta/estrella”.
2. **Escala de píxel.** SPHEREx tiene unos 6,15″/píxel. Un movimiento por
   debajo de ~0,5″/año no se mide de forma fiable en una línea base corta; las
   estrellas de fondo y galaxias suelen quedar en `S` con un límite superior.
3. **Saturación.** Barnard's Star está saturada en algunos datos de SPHEREx;
   los errores del centroide bloom son grandes y se marcan explícitamente
   (`SATURATED_SOURCE`).
4. **Cobertura de catálogo.** B tiene solo 7 campos predefinidos; 2MASS/WISE son
   cachés reales de IRSA Gator para esos campos, no sondeos globales. Las
   versiones derivadas legacy se conservan pero marcadas como derivadas.
   `partial` y `catalog_unavailable` no son “no encontrado”.
5. **Ambigüedad de 4 épocas.** La asociación entre épocas con solo cuatro
   épocas está subdeterminada; D0–D4 son candidatos, no confirmación.
6. **Residuales.** Los residuales de cascade pueden contener alas de PSF,
   artefactos de borde y ruido. Un residual no es una fuente astrofísica nueva.
7. **TAP.** La ingesta TAP real se ha visto bloqueada por timeouts upstream en
   este entorno. La ingesta automática está desactivada por defecto; un éxito
   TAP simulado nunca se informa como real.
8. **Sin servicio de cielo completo.** La caché local de catálogo cubre un
   conjunto pequeño de campos predefinidos; los campos arbitrarios requieren
   una ruta explícita de ingesta DB/C.
9. **Los datos legacy no son evidencia.** Los campos de demo de AstroNova son
   sintéticos; sus asociaciones de dos épocas y plantillas espectrales
   sintéticas no validan ningún resultado de HuellaX.

---

## 14. Upstream legacy AstroNova

`astro/` conserva el proyecto upstream AstroNova / HUELLA X como referencia
funcional, no como runtime principal.

| Elemento | Valor |
|---|---|
| Repositorio | <https://github.com/Beltranpcb/AstroNova> |
| Commit analizado | `1253925ab13419b5d44db323548784c939a93a6e` |
| Evento | NASA Space Apps Challenge 2026 — Planet X and SPHEREx |
| Estado upstream al analizar | Web estática + pipeline Python offline; tres campos de demo sintéticos; validación con datos reales pendiente |
| Licencia original | Ninguna encontrada en el repositorio analizado |
| Inclusión | El propietario confirmó que el código puede incluirse en HuellaX como código abierto |
| Tratamiento de licencia | **No** se relicencia bajo Apache-2.0; se preserva la atribución; ver `astro/UPSTREAM.md` |

Qué conservamos:

- el árbol fuente upstream en `astro/`, incluidos su README en español, el
  documento de arquitectura, la documentación de módulos, los contratos JSON
  Schema y los ejemplos;
- la ruta del repositorio original, el SHA del commit y la nota del evento NASA
  Space Apps 2026;
- el sitio estático como demo legacy funcional;
- una declaración clara de que sus datos de demo son sintéticos.

Qué **no** hacemos:

- copiar código de AstroNova dentro del runtime `系统/`;
- usar sus datos de demo como evidencia científica;
- presentar sus asociaciones de dos épocas o sus tipos espectrales sintéticos
  como confirmación;
- eliminar la atribución upstream al adaptar la interfaz legacy.

Ver [`INTEGRATION.md`](INTEGRATION.md) para el mapeo módulo a módulo y la lista
explícita de ideas prestadas frente a mecanismos rechazados.

---

## 15. Citas y agradecimientos

Si usas este repositorio, cita el repositorio y los artículos originales de los
datos. El inventario completo de fuentes/licencias está en
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) y la lista breve para la
entrega en [`REFERENCES.md`](REFERENCES.md); los metadatos legibles por máquina
están en [`CITATION.cff`](CITATION.cff).

### Datos de misión

- **Imágenes espectrales de nivel 2 de SPHEREx (QR3/DR1)**, NASA/IPAC Infrared
  Science Archive (IRSA), <https://irsa.ipac.caltech.edu/Missions/spherex.html>.
  SPHEREx es una misión de NASA; consulta las páginas de la misión y la
  documentación de IRSA para los detalles de versión/entrega actuales.
- **NASA Space Apps Challenge 2026 — Planet X and SPHEREx**,
  <https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/>.

### Catálogos y resolución de nombres

- **Gaia DR3**: Gaia Collaboration et al. (2023), *A&A* 674, A1,
  <https://doi.org/10.1051/0004-6361/202243940>.
- **2MASS**: Skrutskie et al. (2006), *AJ* 131, 1163,
  <https://doi.org/10.1086/498708>.
- **WISE / AllWISE**: Wright et al. (2010), *AJ* 140, 1868,
  <https://doi.org/10.1088/0004-6256/140/6/1868>; Cutri et al. (2021),
  AllWISE Source Catalog, VizieR II/328.
- **SIMBAD**: Wenger et al. (2000), *A&AS* 143, 9,
  <https://doi.org/10.1051/aas:2000332>.
- Los campos derivados de 2MASS/WISE en B usan cruces de IRSA Gator con IDs de
  Gaia; las coordenadas/PM siguen basadas en Gaia y no sustituyen la astrometría
  original de los sondeos.

### Software y recursos

- **three.js r160** (MIT), <https://threejs.org/>; texto de licencia en
  `系统/视图工具/vendor/three.LICENSE`. La vista 3D opcional usa patrones de
  ejemplo de three.js (reescritos, no copiados en bloque).
- **Texturas de la Tierra**: NASA Visible Earth / Blue Marble,
  <https://visibleearth.nasa.gov/collection/1484/blue-marble>; distribuidas vía
  los ejemplos de three.js con términos MIT/NASA.
- **Runtime**: Python 3.12 (PSF-2.0), NumPy (BSD-3-Clause), Pillow (HPND).
- **AstroNova / HUELLA X** (upstream, commit analizado arriba): incluido con
  permiso del propietario para la integración HuellaX; no se encontró licencia
  original.
- Inspiración de interfaz/interacción: WiseView (Backyard Worlds: Planet 9),
  <http://byw.tools/wiseview>; el proyecto no reutiliza su código/datos.
- Inspiración de contratos/interfaz: AstroNova/HUELLA X; solo ideas, sin copia
  de código.

### Licencia

El código, la documentación, las figuras y las capturas originales están bajo
la **Apache License 2.0**; ver [`LICENSE`](LICENSE) y [`NOTICE`](NOTICE).
El material de terceros conserva su propia licencia; ver
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) y
[`REFERENCES.md`](REFERENCES.md). NASA no respalda este proyecto.

---

## 16. Contribución y reproducción

- Mantén los cambios revisables y añade pruebas para cambios de comportamiento.
- No escribas en la DB de catálogo de producción desde las pruebas de la app.
- No conviertas estados de catálogo parciales/no disponibles en “sin
  coincidencia”.
- No añadas lenguaje positivo de “nuevo planeta/nueva estrella” a la interfaz
  ni a las exportaciones.
- Conserva la atribución de AstroNova y el SHA upstream.
- Para validar, usa el lanzador y los campos en caché actuales; registra la
  procedencia y el comando exacto de prueba.

Reproducción mínima:

```bash
PY=python3
cd 系统/app
$PY -m unittest discover -s tests
$PY server.py --port 8790
# abrir http://127.0.0.1:8790/
```

Se aceptan issues con coordenadas reproducibles, procedencia de datos y estado
esperado/real.
