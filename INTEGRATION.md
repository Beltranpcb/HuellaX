# HuellaX integration

**Status:** public envelope. The primary source is the `system/` git submodule; the
AstroNova upstream is preserved under `astro/`.

## 1. What is where

| Path | Role |
|---|---|
| `system/` | Primary MoveScope implementation: SQL catalog, app, services B/C, Sky View, tests. Submodule of `tonyelos/huella-x-simu`. |
| `astro/` | AstroNova / HUELLA X upstream, preserved at commit `1253925ab13419b5d44db323548784c939a93a6e`. Legacy/demo only. |
| `index.html` | Bilingual cover. English default, Spanish selector. |
| `start.sh`, `stop.sh` | Locate the primary launcher inside `system/` without duplicating it. |
| `docs/integration/` | Local functional-test report and screenshots. |

The envelope contains no primary source copy and no runtime database. This keeps the
public surface small and avoids duplicating the private/runtime data of the primary
repository.

## 2. Upstream mapping

| AstroNova | Primary HuellaX equivalent | Decision |
|---|---|---|
| `m1_adquisicion` | `system/` acquisition/S3/DB epochs | Not duplicated; primary is SQL-first |
| `m2_alineacion` | primary reprojection/common WCS | Not duplicated |
| `m3_deteccion` | primary source detection/quality | Not duplicated |
| `m4_movimiento` | primary multi-epoch BIC/model family | Primary is stronger; not replaced by two-epoch thresholds |
| `m5_identificacion` | Gaia/2MASS/WISE services B + D | Different catalogues; AstroNova lacks Gaia |
| `m6_huella_espectral` | no complete primary equivalent yet | Borrow the state/caveat vocabulary; do not treat synthetic templates as evidence |
| `m7_publicacion` | primary API/exports | Concept only; primary remains live SQL |
| `m9_sitio` | primary app + Sky View + cover | UI/interaction reference; static-only architecture rejected |

AstroNova's useful ideas:

- explicit data contracts and provenance;
- blink/curtain/difference viewing;
- click-to-WCS;
- SkyBoT / JPL / MPC as a supplementary solar-system channel;
- composition states such as `compatible`, `candidate`, `detected`, `insufficient`;
- candidate-first language.

Explicitly rejected:

- static pre-generated JSON as the primary architecture;
- synthetic demo data as evidence;
- two-epoch motion classification as the final model;
- treating a catalogue non-match as a discovery;
- using JPL/MPC as a substitute for stellar catalogues.

## 3. SQL-first flow

```text
SPHEREx cutouts / epochs
        |
        v
SQL catalog (8797)  <--- epochs, coverage, targets, provenance
        |
        +--> MoveScope app (8790) --> analysis / batch / tracks
        |
        +--> Sky View (8830) --> one handoff to MoveScope
        |
        +--> catalogue B (8799): Gaia + derived 2MASS/WISE
        |
        +--> AnyField C (8798): arbitrary-field coverage/discovery
```

Local JSON is an explicit offline fallback for preset targets, not a second source of
truth. AstroNova static JSON/PNG under `astro/datos/` is legacy/demo and is not connected
to the SQL path.

## 4. Services and defaults

| Service | Port |
|---|---:|
| DB API | 8797 |
| MoveScope | 8790 |
| Sky View | 8830 |
| Catalogue B | 8799 |
| AnyField C | 8798 |
| Cover | 8840 |

Run `./start.sh` from the envelope; stop with `./stop.sh`. The primary launcher remains
authoritative inside `system/`.

## 5. Ownership and attribution

- Primary MoveScope/HuellaX: `tonyelos/huella-x-simu`, Apache-2.0.
- AstroNova: `Beltranpcb/AstroNova`, the same team's earlier project under the same
  GitHub account. Merged into HuellaX to combine features; covered by the repository's
  Apache-2.0 license.
- NASA Space Apps Challenge 2026 context is retained in the documentation.
- NASA does not endorse this project.

## 6. Validation

See [`docs/integration/FUNCTIONAL-TEST.md`](docs/integration/FUNCTIONAL-TEST.md).
Local integration results: app 298 tests, Sky View 65 smoke checks, T1 45/0/1, T6 0 ERROR,
launcher 6/6 healthy.

## 7. No-Chinese gate

`python3 scripts/check_no_chinese.py` fails if any tracked public-envelope text file
contains CJK characters. The gate intentionally skips the `system/` submodule, whose
content is governed by its own upstream repository.
