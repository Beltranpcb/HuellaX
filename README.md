# HuellaX · MoveScope × AstroNova

**English** | [Español](README.es.md)

**A candidate-first SPHEREx motion laboratory, with a clean public envelope and an explicit upstream.**

HuellaX combines:

- **MoveScope**, the primary live system: multi-epoch SPHEREx cutouts, SQL catalogues, source detection, motion/variability modelling, Gaia/2MASS/WISE identification, arbitrary-field coverage, batch runs and audit exports.
- **AstroNova / HUELLA X**, the NASA Space Apps Challenge 2026 prototype, preserved under [`astro/`](astro/) as a clearly labelled legacy demo and offline pipeline.
- A bilingual entry page, this English README and the Spanish [`README.es.md`](README.es.md).

> **Candidate rule.** A candidate is not a discovery. Two epochs do not establish a new object.
> A catalogue non-match is `no_match`, not a new planet. AstroNova's synthetic demo is not
> observational evidence.

---

## 1. Repository shape

This public repository is deliberately split into an **English/Spanish envelope** and a
**primary source submodule**:

```text
HuellaX/
├── index.html              bilingual entry page (English default, Spanish switch)
├── README.md               this file
├── README.es.md            Spanish README
├── INTEGRATION.md          integration architecture and upstream mapping
├── start.sh / stop.sh      entry points for the submodule launcher
├── scripts/                documentation and no-CJK checks
├── docs/integration/       functional-test report and screenshots
├── astro/                  AstroNova legacy (upstream, Spanish UI)
└── system/                 git submodule: primary MoveScope implementation
```

`system/` points to
[`tonyelos/huella-x-simu`](https://github.com/tonyelos/huella-x-simu), the primary
implementation. Its internal layout is owned by that upstream repository; this envelope
does not duplicate it. `astro/` is the AstroNova upstream preserved at the analysed
commit.

### Why a submodule?

The primary project contains a large, actively developed Python/SQLite stack. Keeping it
as a submodule:

- gives the public envelope a small, reviewable, English/Spanish-only surface;
- keeps the primary source and its history in one place;
- avoids copying 100+ MB of runtime data and generated caches into this repository;
- makes the boundary between **primary runtime** and **legacy AstroNova** explicit.

Clone with submodules:

```bash
git clone --recurse-submodules https://github.com/Beltranpcb/HuellaX.git
cd HuellaX
```

If the submodule is missing:

```bash
git submodule update --init --recursive
```

---

## 2. Quick start

```bash
# from the repository root
./start.sh
```

The wrapper locates the primary launcher inside `system/` and starts the core SQL-first stack (DB, MoveScope, Sky View). B/C and the static cover are separate optional services; see below.

| Service | Default port | Role |
|---|---:|---|
| Database API | 8797 | SQLite catalog, epochs, coverage |
| MoveScope app | 8790 | analysis, candidates, batch, tracks |
| Sky View | 8830 | region/time selection and one MoveScope handoff |
| Gaia catalog B | 8799 | separate SQLite catalogue service |
| AnyField C | 8798 | arbitrary-field coverage/discovery |
| Entry | 8840 | bilingual public entry page (optional; `./scripts/serve_cover.sh`) |

Open:

- entry: <http://127.0.0.1:8840/>
- MoveScope: <http://127.0.0.1:8790/>
- Sky View: <http://127.0.0.1:8830/>

Stop with:

```bash
./stop.sh
```

The wrapper is intentionally minimal. The authoritative launcher, runbook and
tests live in the `system/` submodule.

---

## 3. Data: SQL first

The primary data path is SQL:

- `system/` ships the SQLite catalog metadata and the separate Gaia/2MASS/WISE star
  catalogue used by service B;
- the app queries the database API for targets, epochs and coverage;
- catalog identification is a multi-catalogue positional match with a Gaia primary and
  0.5 arcsec de-duplication;
- arbitrary coordinates go through the coverage service and the SQL catalog;
- local JSON is an explicit offline fallback for preset targets, never a second source
  of truth.

The legacy AstroNova pipeline writes JSON/PNG under `astro/datos/`; that data is
**synthetic/demo** unless a real run is separately documented. It is not wired into the
primary SQL path.

### Candidate status vocabulary

`known`, `ambiguous`, `no_match`, `insufficient`, `unavailable`, `conflict`.

- `known` means a catalogue association within the tested tolerance.
- `ambiguous` means more than one plausible association.
- `no_match` means no catalogue match in the tested set; it does **not** mean new.
- `insufficient` means the data cannot support the question.
- `unavailable` means a required service/catalogue was unavailable.

---

## 4. Main features

- Multi-epoch SPHEREx cutout retrieval and common-WCS photometry.
- Motion vs variability model family with BIC, uncertainty and readiness levels.
- Gaia DR3 plus 2MASS/WISE derived crossmatches, with `known` / `ambiguous` /
  `no_match` semantics.
- A/C source batch identification, unified candidate directory and track view.
- Cascade/residual view and tracklets on the same canvas as the analysis.
- Arbitrary-field coverage/discovery service.
- CSV/JSON audit exports with provenance.
- Sky View: region/time selection, timeline, playback and one MoveScope handoff.

### Inside Sky View

- **SkyBoT** — live IMCCE cone search for known solar-system objects, with an explicit external-service fallback.
- **Bands** — a real 102-band instrument plan with molecular windows; it explicitly is not a measured spectrum.
- **3D context** — the actual Sky View globe and selection, plus a clearly labelled legacy 3D link.

The modules share the Sky View visual system and never turn a catalogue non-match into a discovery.
- Bilingual entry page and UI language selector (English default, Spanish complete).

The app intentionally does **not** claim a discovery, a confirmed planet, or a
composition derived from synthetic templates.

---

## 5. Validation

The integration was exercised locally with the primary runtime:

| Check | Result |
|---|---|
| App test suite | **298 tests OK** |
| Sky View smoke | **65 PASS / 0 FAIL / 0 WARN** |
| Public-envelope docs/CJK checks | **48 docs checks + no-CJK gate** |
| Acceptance T1 | **45 PASS / 0 FAIL / 1 WARN** |
| Drift checker T6 | **0 ERROR** |
| Integrated launcher | **6/6 services healthy** |
| Candidate functional test | Barnard `REAL`, 4 epochs, `L`, catalogue prior |

The full local evidence is in
[`docs/integration/FUNCTIONAL-TEST.md`](docs/integration/FUNCTIONAL-TEST.md).

---

## 6. AstroNova legacy boundary

[`astro/`](astro/) preserves the AstroNova / HUELLA X upstream:

- upstream: <https://github.com/Beltranpcb/AstroNova>
- analysed commit: `1253925ab13419b5d44db323548784c939a93a6e`
- event: NASA Space Apps Challenge 2026, Planet X and SPHEREx.

At merge time the upstream had **no LICENSE file**. The owner confirmed that the code
may be included in HuellaX as open code. It is preserved with attribution and is **not
relicensed** under the Apache License 2.0 that covers the original MoveScope work. Its
static demo fields are synthetic and must not be presented as observations or validation
evidence. See [`astro/UPSTREAM.md`](astro/UPSTREAM.md) and
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

NASA does not endorse this project or any commercial product or service.

---

## 7. Known limits

- The primary source lives in the submodule; this envelope alone is not the full runtime.
- AstroNova's UI remains Spanish legacy with a bilingual banner.
- The primary app still exposes some backend audit fields in their original form; the UI
  localises the user-facing labels.
- Real TAP ingestion can be blocked by upstream timeouts; the project does not fabricate
  a successful ingest.
- Catalogue non-matches are not discoveries.
- The public envelope contains no Chinese text; the upstream submodule is governed by
  its own repository.

---

## 8. Documentation

| Document | Purpose |
|---|---|
| [`README.es.md`](README.es.md) | Spanish README |
| [`INTEGRATION.md`](INTEGRATION.md) | architecture, mapping, SQL flow, ownership |
| [`docs/integration/FUNCTIONAL-TEST.md`](docs/integration/FUNCTIONAL-TEST.md) | local E2E results |
| [`NOTICE`](NOTICE) | licensing and upstream boundary |
| [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) | third-party data/software |
| [`REFERENCES.md`](REFERENCES.md) | citation list |
| [`index.html`](index.html) | bilingual cover |

## 9. License

The original MoveScope/HuellaX work is Apache-2.0; see [`LICENSE`](LICENSE).
AstroNova is included by owner permission, is not relicensed, and remains attributed.
Third-party data and software are not covered by the Apache license.
