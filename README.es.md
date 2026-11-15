# HuellaX · MoveScope × AstroNova

[English](README.md) | **Español**

**Un laboratorio de movimiento SPHEREx centrado en candidatos, con una envoltura pública limpia y un upstream explícito.**

HuellaX combina:

- **MoveScope**, el sistema primario en vivo: recortes SPHEREx multiépoca, catálogos SQL, detección de fuentes, modelado de movimiento/variabilidad, identificación Gaia/2MASS/WISE, cobertura de campo arbitrario, lotes y exportaciones auditables.
- **AstroNova / HUELLA X**, el prototipo de NASA Space Apps Challenge 2026, conservado en [`astro/`](astro/) como demo legacy y pipeline offline claramente etiquetado.
- Una portada bilingüe, este README en español y el README principal en [`README.md`](README.md).

> **Regla de candidato.** Un candidato no es un descubrimiento. Dos épocas no demuestran un objeto nuevo.
> Un `no_match` de catálogo no es un planeta nuevo. La demo sintética de AstroNova no es evidencia observacional.

---

## 1. Forma del repositorio

Este repositorio público separa una **envoltura inglés/español** del **submódulo de código primario**:

```text
HuellaX/
├── index.html              portada bilingüe (inglés por defecto, selector español)
├── README.md               README principal en inglés
├── README.es.md            este archivo
├── INTEGRATION.md          arquitectura de integración y mapeo del upstream
├── start.sh / stop.sh      entrada al lanzador del submódulo
├── scripts/                comprobaciones de documentación y de ausencia de CJK
├── docs/integration/       informe de prueba funcional y capturas
├── astro/                  AstroNova legacy (upstream, UI en español)
└── system/                 submódulo git: implementación primaria MoveScope
```

`system/` apunta a
[`tonyelos/huella-x-simu`](https://github.com/tonyelos/huella-x-simu), la implementación
primaria. Su estructura interna pertenece a ese repositorio; esta envoltura no la
duplica. `astro/` es el upstream de AstroNova en el commit analizado.

### Por qué un submódulo

El proyecto primario contiene un stack Python/SQLite grande y en desarrollo activo.
Mantenerlo como submódulo:

- deja una superficie pública pequeña, revisable y solo en inglés/español;
- conserva el código y la historia del proyecto primario en un único lugar;
- evita copiar más de 100 MB de datos de ejecución y cachés generadas;
- hace explícita la frontera entre **runtime primario** y **AstroNova legacy**.

Clonar con submódulos:

```bash
git clone --recurse-submodules https://github.com/Beltranpcb/HuellaX.git
cd HuellaX
```

Si falta el submódulo:

```bash
git submodule update --init --recursive
```

---

## 2. Inicio rápido

```bash
# desde la raíz del repositorio
./start.sh
```

El wrapper localiza el lanzador primario dentro de `system/` y arranca el stack SQL-first:

| Servicio | Puerto por defecto | Función |
|---|---:|---|
| API de base de datos | 8797 | catálogo SQLite, épocas, cobertura |
| App MoveScope | 8790 | análisis, candidatos, lotes, trayectorias |
| Sky View | 8830 | selección de región/tiempo y un único handoff a MoveScope |
| Catálogo Gaia B | 8799 | servicio de catálogo SQLite separado |
| AnyField C | 8798 | cobertura/descubrimiento de campo arbitrario |
| Portada | 8840 | landing pública bilingüe |

Abrir:

- portada: <http://127.0.0.1:8840/>
- MoveScope: <http://127.0.0.1:8790/>
- Sky View: <http://127.0.0.1:8830/>

Detener:

```bash
./stop.sh
```

El wrapper es mínimo. El lanzador autoritativo, el runbook y las pruebas viven en el
submódulo `system/`.

---

## 3. Datos: SQL primero

La ruta primaria es SQL:

- `system/` incluye el catálogo SQLite de metadatos y el catálogo separado Gaia/2MASS/WISE que usa el servicio B;
- la app consulta la API de base de datos para objetivos, épocas y cobertura;
- la identificación es un cruce posicional multicatálogo con Gaia como primario y deduplicación de 0,5 arcsec;
- las coordenadas arbitrarias pasan por el servicio de cobertura y el catálogo SQL;
- el JSON local es un respaldo offline explícito para objetivos predefinidos, nunca una segunda fuente de verdad.

El pipeline legacy de AstroNova escribe JSON/PNG en `astro/datos/`; esos datos son
**sintéticos/demo** salvo que se documente una ejecución real. No está conectado a la
ruta SQL primaria.

### Vocabulario de estado

`known`, `ambiguous`, `no_match`, `insufficient`, `unavailable`, `conflict`.

- `known`: asociación de catálogo dentro de la tolerancia probada.
- `ambiguous`: más de una asociación plausible.
- `no_match`: ninguna asociación en el conjunto probado; **no** significa nuevo.
- `insufficient`: los datos no permiten responder.
- `unavailable`: un servicio/catálogo requerido no estaba disponible.

---

## 4. Funciones principales

- Recuperación de recortes SPHEREx multiépoca y fotometría en WCS común.
- Familia de modelos movimiento/variabilidad con BIC, incertidumbre y niveles de preparación.
- Gaia DR3 más cruces derivados 2MASS/WISE, con semántica `known` / `ambiguous` / `no_match`.
- Identificación por lotes de fuentes A/C, directorio unificado de candidatos y vista de trayectorias.
- Vista cascada/residuales y tracklets en el mismo lienzo que el análisis.
- Servicio de cobertura/descubrimiento de campo arbitrario.
- Exportaciones CSV/JSON con procedencia.
- Sky View: región/tiempo, línea temporal, reproducción y un único handoff a MoveScope.
- Portada bilingüe y selector de idioma en la UI (inglés por defecto, español completo).

La app no afirma un descubrimiento, un planeta confirmado ni una composición derivada de
plantillas sintéticas.

---

## 5. Validación

La integración se probó localmente con el runtime primario:

| Comprobación | Resultado |
|---|---|
| Suite de la app | **298 tests OK** |
| Smoke de Sky View | **65 PASS / 0 FAIL / 0 WARN** |
| Comprobaciones de la envoltura | **48 docs checks + puerta no-CJK** |
| Aceptación T1 | **45 PASS / 0 FAIL / 1 WARN** |
| Comprobador de deriva T6 | **0 ERROR** |
| Lanzador integrado | **6/6 servicios sanos** |
| Prueba funcional de candidato | Barnard `REAL`, 4 épocas, `L`, prior de catálogo |

La evidencia local completa está en
[`docs/integration/FUNCTIONAL-TEST.md`](docs/integration/FUNCTIONAL-TEST.md).

---

## 6. Frontera legacy de AstroNova

[`astro/`](astro/) conserva el upstream AstroNova / HUELLA X:

- upstream: <https://github.com/Beltranpcb/AstroNova>
- commit analizado: `1253925ab13419b5d44db323548784c939a93a6e`
- evento: NASA Space Apps Challenge 2026, Planet X and SPHEREx.

En el momento de la integración el upstream **no tenía LICENSE**. El propietario
confirmó que el código puede incluirse en HuellaX como código abierto. Se conserva con
atribución y **no** se relicencia bajo Apache License 2.0, que cubre el trabajo original
MoveScope. Sus campos de demo estáticos son sintéticos y no deben presentarse como
observaciones o evidencia de validación. Ver [`astro/UPSTREAM.md`](astro/UPSTREAM.md) y
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

NASA no respalda este proyecto ni ningún producto o servicio comercial.

---

## 7. Límites conocidos

- El código primario vive en el submódulo; esta envoltura por sí sola no es el runtime completo.
- La UI de AstroNova sigue siendo legacy en español, con un banner bilingüe.
- La app primaria aún expone algunos campos de auditoría del backend en su forma original; la UI localiza las etiquetas visibles.
- La ingesta TAP real puede bloquearse por timeouts del upstream; el proyecto no fabrica una ingesta exitosa.
- Los `no_match` de catálogo no son descubrimientos.
- La envoltura pública no contiene texto en chino; el submódulo se rige por su propio repositorio.

---

## 8. Documentación

| Documento | Función |
|---|---|
| [`README.md`](README.md) | README principal en inglés |
| [`INTEGRATION.md`](INTEGRATION.md) | arquitectura, mapeo, flujo SQL, propiedad |
| [`docs/integration/FUNCTIONAL-TEST.md`](docs/integration/FUNCTIONAL-TEST.md) | resultados E2E locales |
| [`NOTICE`](NOTICE) | licencia y frontera del upstream |
| [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) | datos/software de terceros |
| [`REFERENCES.md`](REFERENCES.md) | lista de citas |
| [`index.html`](index.html) | portada bilingüe |

## 9. Licencia

El trabajo original MoveScope/HuellaX es Apache-2.0; ver [`LICENSE`](LICENSE).
AstroNova se incluye con permiso del propietario, no se relicencia y mantiene su
atribución. Los datos y el software de terceros no están cubiertos por la licencia
Apache.
