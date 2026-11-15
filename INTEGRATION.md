# HuellaX Integration — AstroNova m1–m9 → MoveScope + SQL

> **Status:** integration documentation, `feat/cover-docs`, based on `develop`
> at `5675dbb`.
> **Upstream analyzed:** AstroNova / HUELLA X
> `1253925ab13419b5d44db323548784c939a93a6e`.
> **Scope:** explain how the upstream modules map onto the live HuellaX
> runtime, which ideas were borrowed, and which mechanisms were deliberately
> rejected. This document does not modify `系统/` or `astro/` source code.
>
> **One-line boundary:** SQL is the primary data source; AstroNova static data
> is legacy/demo; every result is a candidate, not a discovery.

---

## 1. Why integrate at all

AstroNova/HUELLA X is a strong **design** artifact: it has clear module
boundaries, JSON Schema contracts, a careful candidate narrative, a readable
static site and a complete offline pipeline specification. It is not a
validated real-data identification system: its shipped fields are synthetic,
its real-data run was blocked, its Gaia work was pending, and it had no license
at analysis time.

MoveScope is the opposite profile: less polished public storytelling, but a
working pipeline on real SPHEREx epochs, a SQL catalog, a Gaia/2MASS/WISE
identity service, multi-epoch model selection, benchmark targets and explicit
provenance.

The integration therefore keeps:

- **MoveScope + SQL as the runtime** — real data, real services, real tests;
- **AstroNova as a preserved upstream** — static site, offline pipeline and
  contracts, useful as reference and as a legacy demo;
- **a shared honesty boundary** — candidates are not discoveries, synthetic
  data is not evidence, and unavailable is not “not found”.

It rejects the idea that the merged project needs a second static publishing
architecture or a second scientific pipeline.

---

## 2. Repository composition

```text
HuellaX/
├── index.html              bilingual cover (EN default, ES complete)
├── README.md               English primary README
├── README.es.md            complete Spanish README
├── README.zh-CN.md         legacy Chinese MoveScope README (historical)
├── INTEGRATION.md          this document
├── LICENSE / NOTICE        Apache-2.0 for original work
├── THIRD_PARTY_NOTICES.md  third-party inventory
├── REFERENCES.md           short citation list
├── CITATION.cff            machine-readable citation metadata
├── 系统/                    primary runtime
│   ├── app/                MoveScope app (8790)
│   ├── 数据库工具/          SQL catalog (8797) + catalog service B (8799)
│   ├── anyfield/           coverage/discovery service C (8798)
│   ├── 视图工具/            optional sky view (8830)
│   └── docs/               theory, implementation log, validation outputs
├── astro/                  legacy AstroNova/HUELLA X upstream
│   ├── modulos/m1–m7, m9   offline Python pipeline + static site
│   ├── contratos/          JSON Schema contracts and examples
│   ├── UPSTREAM.md         upstream SHA, permission and scope
│   └── README.md           upstream Spanish README
└── 项目主控/                control plane: launcher, acceptance, architecture
```

`astro/` is a preserved subtree. The integration does not rewrite its modules
and does not import its Python code into `系统/`.

---

## 3. Architecture mapping: AstroNova m1–m9

AstroNova numbers its modules m1–m7 and m9. **There is no m8 in the analyzed
upstream**; the numbering simply skips it. The table below maps every existing
module to the HuellaX runtime and states what actually happened to it.

| Upstream | Upstream responsibility | HuellaX counterpart | Integration verdict |
|---|---|---|---|
| **m1_adquisicion** | IRSA TAP/S3 listing, A/B/template epoch selection, FITS cutout download | SQL catalog ingest (`系统/数据库工具/`) + C discovery/fetch (`系统/anyfield/`, 8798) | **Replaced.** The runtime gets epochs from SQL and fetches allowlisted cutouts through C. Upstream selection logic is reference only. |
| **m2_alineacion** | Zodiacal subtraction, reprojection to a common pixel grid, PNG export, field metadata | MoveScope `系统/app/core/wcs.py`, `data.py`, `pipeline.reproject_to_common`, server-side rendering | **Replaced.** Independent implementation; no upstream code copied. |
| **m3_deteccion** | DAOStarFinder detection, stationary/orphan separation, A/B pair proposals | MoveScope `系统/app/core/photometry.py` + `pipeline.py`: FLAGS mask, matched filter, PSF/bloom centroid, reference-star calibration, source association | **Replaced.** Stronger primary path; not a port of m3. |
| **m4_movimiento** | Two-epoch angular velocity, uncertainty, 2σ/5σ classes | MoveScope `系统/app/core/motion.py` M0–M4 + BIC, readiness L0–L3; `tracks.py` D0–D5 | **Replaced.** Multi-epoch, model-based, with explicit readiness and caveats. |
| **m5_identificacion** | JPL `sb_ident` / MPChecker, 15″ positional match, cached responses | B catalog service (`系统/数据库工具/catalog_server.py`, 8799): Gaia DR3 + field-level 2MASS/WISE; MoveScope `/api/identify` and `/api/identify/batch` | **Adapted, different scope.** HuellaX identifies stars/brown dwarfs/galaxies via Gaia/2MASS/WISE, not only solar-system bodies. The SkyBoT idea is borrowed; it is not integrated. |
| **m6_huella_espectral** | Planck temperature, synthetic template χ², molecular-band states | No spectral classification in the primary runtime | **Not adopted as evidence.** The state vocabulary is reserved for a future explanatory UI; no spectral claim is made today. |
| **m7_publicacion** | Union of candidates, static JSON/PNG publication, catalog index | SQL exports + v1 HTTP APIs + CSV/JSON audit export | **Not adopted as primary architecture.** Contract discipline is borrowed; static publication is not the runtime. |
| **m8** | — | — | **Absent upstream.** No module to map. |
| **m9_sitio** | Static web explorer, SkyBoT query, charts, 3D spectrum | MoveScope UI (8790) + optional Sky View (8830); legacy site kept at `astro/modulos/m9_sitio/` | **Preserved as legacy.** UI ideas only; no code copied into `系统/app/web/`. |

### 3.1 What “replaced” means here

“Replaced” does **not** mean “the upstream implementation was ported”. It
means the capability exists in the primary runtime with different code, a
different data source and stronger data semantics.

| Capability | Upstream approach | Primary approach |
|---|---|---|
| Epoch truth | Files under `datos/`, generated by a batch pipeline | SQLite `target_epochs`/`frames`, served by `/api/v1/epochs` |
| Time baseline | Two epochs (A/B) plus a template | 1–8+ curated epochs; readiness L0–L3; optional `t0/t1` window |
| Motion decision | Velocity + 2σ/5σ thresholds | M0–M4 model family, BIC selection, 3σ/readiness gates |
| Identity | JPL/MPC small bodies only | Gaia/2MASS/WISE stars and galaxies; solar-system cross-check idea from SkyBoT |
| Provenance | `origen` field in static JSON | `REAL/HYBRID/SIM/SAMPLE`, `fallback_reason`, quality flags, `discovery_claim: false` |
| Delivery | Pre-generated JSON/PNG, static site | Live HTTP APIs, SQL exports, CSV/JSON audit attachments |
| Validation | Synthetic module tests | 291 app tests, SQL contract tests, benchmark targets, injection-recovery |

### 3.2 Module-by-module notes

#### m1 — acquisition

Upstream value: it correctly recognizes that SPHEREx is not indexed by SIA and
moves to TAP `spherex.obscore`, with an S3 header-listing fallback. It also
defines A/B/template roles and selection constraints (same detector, 0.5–72 h,
template >120 days).

What HuellaX does instead:

- SQL catalog is the epoch index: `releases`, `weeks`, `observations`, `frames`,
  `target_epochs`, `cutouts`, `blobs`;
- C (`8798`) discovers arbitrary fields from the weekly index and S3 Range
  headers, and fetches only allowlisted cutouts;
- the app resolves epochs through the v1 contract, not through `datos/`.

Retained as reference: the idea of an S3 header fallback and explicit epoch
roles. Not retained: a file-only acquisition pipeline as the runtime.

#### m2 — alignment

Upstream value: explicit common-grid reprojection, zodiacal subtraction,
metadata output and PNG export.

What HuellaX does instead:

- `系统/app/core/wcs.py` implements the gnomonic projection, SIP handling and
  wavelength lookup needed by the app;
- `pipeline.reproject_to_common` builds a common grid for stack/difference and
  layer products;
- `server.py` renders PNGs on demand with bounded allocation.

Status: alignment capability present, independent implementation. No upstream
code used. Zodiacal subtraction is not a separate named step in the primary
pipeline; the background/noise model handles the local background, and the
provenance fields record what was actually applied. The upstream's `meta.json`
idea is reflected in the app's own metadata and provenance, not copied as a
file contract.

#### m3 — detection

Upstream value: a transparent, testable detection chain (background,
DAOStarFinder, 5σ, FWHM, FLAGS masking, orphan pairing).

What HuellaX does instead:

- `photometry.py`: sigma-clipped background/noise, FLAGS mask, matched filter,
  peak finding, PSF/bloom centroid, aperture photometry;
- `pipeline.py`: detection, quality flags, source deduplication, reference-star
  calibration and cross-epoch matching;
- saturation is flagged, not hidden (`SATURATED_SOURCE`).

Status: stronger primary path for SPHEREx's 6.15″ pixels. The upstream's
detector assumptions are not reused.

#### m4 — motion

Upstream value: cautious language, uncertainty propagation, explicit
stationary/candidate states.

What HuellaX does instead:

- model family M0 stationary, M1 variable, M2 linear proper motion, M3
  parallax, M4 proper motion + acceleration;
- BIC-based model choice, 3σ/readiness gates, evidence and falsifier;
- separate track candidates D0–D5 with explicit caveats for four-epoch
  ambiguity;
- catalog-prior motion only as a labelled prior, never as a measured proper
  motion.

Status: replaced. The upstream's two-epoch classification is not sufficient for
the primary product and is explicitly rejected (see §7).

#### m5 — identification

Upstream value: live ephemeris check for known solar-system bodies, cached
responses, a clear “not identified” wording.

What HuellaX does instead:

- B (`8799`) serves Gaia DR3 field caches and field-level 2MASS/WISE
  crossmatches;
- the app exposes single and batch identification, with `known`, `ambiguous`,
  `uncatalogued_candidate`, `insufficient_data` and `catalog_unavailable`;
- batch results can be exported for audit without writing catalog tables.

Gap retained from upstream as an idea: **SkyBoT**. A live IMCCE query would
add a “known asteroid/planet/comet at this position and time” cross-check. It
is not integrated, and would need a geocentric-position caveat (see §6.3).

#### m6 — spectral fingerprint

Upstream value: a restrained candidate vocabulary and a template/χ² display
that says “most compatible among those evaluated” rather than “this is a
comet”.

What HuellaX does instead:

- no spectral classification, no Planck fit and no molecular detection in the
  primary runtime;
- the app's current strengths are motion, variability and catalog identity;
- the upstream spectral states are kept as a **future UI vocabulary**, not as
  a scientific result.

Status: not adopted as evidence. See §6.4 for the exact states borrowed and
§7 for why synthetic templates cannot be used as validation.

#### m7 — publication

Upstream value: one publishable directory, schema validation, candidate union,
catalog index, “what data actually exists” flags.

What HuellaX does instead:

- SQL exports (`/api/export/...`), v1 APIs and audit attachments;
- no static publication directory as the runtime;
- export compatibility is reconciled with `check_compat.py`.

Borrowed: schema discipline, provenance flags, “data available?” UX.
Rejected: static JSON as the primary architecture.

#### m8 — absent

The analyzed upstream has no `m8_*` directory or contract. Nothing is mapped.
Any future renumbering must be checked against the upstream tree rather than
assumed.

#### m9 — site

Upstream value: the strongest part of the project. Blink/curtain/difference,
click-to-coordinates, candidate card, provenance labels, SkyBoT, spectrum
comparison, 3D spectrum, keyboard/accessibility care, honest empty/error text.

What HuellaX does instead:

- MoveScope (8790) is the product entry: Browse, Cascade-residual, Tracks,
  identify, audit export;
- Sky View (8830) is optional context with a single handoff URL;
- the upstream site is preserved at `astro/modulos/m9_sitio/index.html` as a
  legacy demo, not as a second product entry.

Borrowed: interaction and wording principles. Rejected: a no-backend static
site as the primary delivery. No JS/CSS was copied into `系统/app/web/`.

---

## 4. SQL data flow

### 4.1 Runtime path

```text
IRSA / S3 weekly products
        │
        │  T4 header harvest, CLI ingest, IRSA Gator imports, static cutouts
        ▼
系统/数据库工具/
  var/catalog.sqlite          metadata: releases, weeks, observations,
                              blobs, frames, frame_releases, targets,
                              target_epochs, cutouts, fields_snapshot,
                              ingest_runs, meta
  var/blobs/                  immutable headers and cutout products
        │
        │  GET /api/v1/epochs?ra&dec&fov
        │  GET /api/v1/coverage?ra&dec
        │  GET /api/v1/targets
        ▼
系统/app/core/epoch_source.py
  resolve (ra, dec, fov) → EpochRef[] + coverage
  validate key/obsid/mjd/detector/sep_deg; drop malformed entries
  dedupe (obsid, detector); sort (mjd, detector)
        │
        ▼
系统/app/core/data.py  build_dataset()
  → fetch slices (cache / IRSA) → Epoch objects
        │
        ▼
系统/app/core/pipeline.py
  photometry → calibration → association → motion
        │
        ▼
MoveScope UI (8790) · /api/analyze · audit CSV/JSON
```

### 4.2 What SQL owns

SQL is the **primary data source** for:

- target coordinates and curated target epochs;
- frames and exposure metadata;
- coverage and readiness-at-coverage (`coverage_level` C0–C3);
- cutout indexes and content-addressed blobs;
- release/week processing versions;
- ingestion runs and provenance.

It does **not** own:

- photometry;
- relative astrometric calibration;
- model selection or motion class;
- readiness L0–L3 (analysis readiness is MoveScope's);
- public wording, evidence or falsifiers.

The split is deliberate: `coverage_level` answers “how often was this sky
observed”; `analysis_readiness` answers “how many detections support a motion
claim”. They are different numbers and must not be conflated.

### 4.3 App fallback semantics

The primary path is SQL. Two explicit fallbacks exist and must stay visible:

1. **Preset target + offline**: MoveScope may load
   `系统/app/data/epoch_catalog.json` for the seven curated targets when SQL is
   unavailable. The response carries `source=local_json` and a named fallback.
2. **Custom coordinate within 0.05° of a preset**: the app may reuse the preset
   path if a local epoch catalog entry exists. The response marks
   `source=local_json_matched` and `matched_target_id`.

For arbitrary coordinates there is no local-JSON fallback. Zero local epochs
produce an explicit `NO_LOCAL_COVERAGE` and a SIM/unavailable state, never a
fabricated real measurement. DB failure produces `DB_UNAVAILABLE`, not
“baseline too short”.

The DB URL is `SPHEREX_DB_URL` (default `http://127.0.0.1:8797`).

### 4.4 Identity and coverage services

```text
app /api/identify          → B 8799  (star_catalog.sqlite, read-only)
app /api/sources, /field   → C 8798  (catalog read-only + anyfield.sqlite sidecar)
```

- **B** owns Gaia DR3 field caches and field-level 2MASS/WISE crossmatches.
  It answers “is this position known?” and returns candidates with status and
  quality. It does not classify motion.
- **C** owns true header footprints, arbitrary-field discovery, allowlisted
  S3/IRSA fetch and its own sidecar. A failed fetch is `UPSTREAM_UNAVAILABLE`;
  an incomplete index is `INDEX_INCOMPLETE`; neither is “no coverage”.
- **Neither B nor C writes the production SQL catalog.**
- `start_all.sh` starts DB, app and view only. B and C are optional services
  and must be started explicitly.

### 4.5 Failure vocabulary

| Situation | Must be reported as | Must not be reported as |
|---|---|---|
| DB unreachable | `DB_UNAVAILABLE` | “baseline too short” |
| No local epochs for a custom coordinate | `NO_LOCAL_COVERAGE` + explicit SIM | real measurement |
| Catalog service down | `catalog_unavailable` | “no match” |
| Catalog query returns zero | `uncatalogued_candidate` | “new object” |
| Fetch failed | `FETCH_FAILED` / `UPSTREAM_UNAVAILABLE` | “no coverage” |
| Partial 2MASS/WISE field cache | partial / unavailable | global survey |
| Synthetic data | `SIM` with a visible note | `REAL` |

---

## 5. Module ownership and branches

The integration is organized as independent workstreams on top of `develop`
(`5675dbb`). Ownership here means **which tree owns which contract**, not
personal ownership.

| Branch / workstream | Owns | Contract boundary | Status in this repo |
|---|---|---|---|
| `develop` | Integration baseline | Merge target for all feature branches | base `5675dbb` |
| `feat/app-i18n` | `系统/app/` UI strings and analysis UX | `/api` v1, result schema, provenance fields | parallel workstream |
| `feat/view-i18n` | `系统/视图工具/` | Handoff URL `ra/dec/fov/t0/t1/from=view`; no analysis | parallel workstream |
| `feat/sql-launcher` | `系统/数据库工具/`, `项目主控/启动/` | SQL schema, `/api/v1/*`, ports/health | parallel workstream |
| `feat/astro-legacy` | `astro/` packaging and legacy demo | Upstream tree preserved; no code import | parallel workstream |
| `feat/cover-docs` | Root `index.html`, `README.md`, `README.es.md`, `INTEGRATION.md`, notices | Documentation only; no runtime code | this workstream |

### 5.1 Ownership boundaries

| Plane | Owner | May write | May read |
|---|---|---|---|
| L1 data | `系统/数据库工具/` | `catalog.sqlite`, `blobs`, `star_catalog.sqlite` (B-side) | IRSA/S3, static fixtures |
| L2 measurement | `系统/app/core/` | analysis results, caches under `系统/app/data` | SQL v1, B, C |
| L3 experience | `系统/app/web/`, `系统/视图工具/` | UI state, URL state | app APIs, analysis results |
| L4 control | `项目主控/` | launcher state, reports, snapshots | all services, read-only |
| Legacy | `astro/` | generated demo data under `astro/datos/` (gitignored) | its own contracts |

Hard rules:

- `系统/app` never writes the production catalog DB.
- `系统/数据库工具` never performs photometry or motion classification.
- `系统/视图工具` never measures; it sends context and one handoff URL.
- `astro/` modules never import `系统/` code, and `系统/` never imports
  `astro/` code.
- Root docs never become a second source of runtime truth.

### 5.2 Branching and commits

- Feature branches start from `develop` and merge back by review.
- The target repository currently has **no push permission**; commits are
  local only. This document and the cover commit do not change that.
- `feat/cover-docs` contains documentation and static cover assets only.
- The legacy subtree keeps its upstream SHA and `astro/UPSTREAM.md`; do not
  rewrite history to make it look like first-party code.

---

## 6. Upstream attribution and licensing

### 6.1 Facts

| Item | Value |
|---|---|
| Upstream repository | <https://github.com/Beltranpcb/AstroNova> |
| Product name | HUELLA X |
| Analyzed commit | `1253925ab13419b5d44db323548784c939a93a6e` |
| Event | NASA Space Apps Challenge 2026 — Planet X and SPHEREx |
| Upstream state at analysis | Static web + offline Python pipeline; shipped demo fields synthetic; real-data validation pending; Gaia pending |
| License in upstream | None found (`LICENSE` / `COPYING` absent) |
| Inclusion basis | Owner confirmed the code may be included in HuellaX as open code |
| Our treatment | Preserved and attributed; **not** relicensed under Apache-2.0 |

### 6.2 What is preserved

- The complete `astro/` source tree: modules, contracts, examples, docs,
  Spanish README and architecture document.
- `astro/UPSTREAM.md`, which records the upstream path, SHA, event and owner
  permission.
- The original demo generator
  `astro/modulos/m9_sitio/ejemplos/generar_datos.py`, which produces synthetic
  demo fields.
- The static site at `astro/modulos/m9_sitio/index.html`.

### 6.3 What this means for reuse

- The source is included by permission, not under an OSI license found in the
  upstream. Do not describe `astro/` as Apache-2.0.
- Our Apache-2.0 covers original HuellaX code and documentation, not the
  upstream subtree.
- `THIRD_PARTY_NOTICES.md` and `NOTICE` carry the short attribution note.
- Before any public redistribution or relicensing, legal review is advisable;
  the owner permission is recorded but the upstream license status is unusual.

NASA Space Apps 2026 note: AstroNova was created for the NASA Space Apps
Challenge 2026 “Planet X and SPHEREx” challenge. Inclusion of the upstream does
not imply NASA endorsement, and no result in this repository confirms Planet X.

---

## 7. Borrowed ideas

These are **ideas**, not copied code. Each item states what was borrowed and
what HuellaX does with it today.

### 7.1 UI and interaction

Borrowed:

- blink / curtain / difference comparison as a way to make multi-epoch change
  legible;
- a candidate card that separates “what was measured” from “what is inferred”;
- provenance and “data available?” chips (`real` / `synthetic` / pending);
- explicit empty, partial and degraded states instead of silent fallbacks;
- accessible labels, keyboard reachability, non-color-only encodings and
  reduced-motion care;
- a 3D spectrum and template-comparison presentation as science communication.

Applied in HuellaX:

- MoveScope already has Browse (blink/stack/difference), Cascade-residual and
  Tracks;
- evidence, falsifier, readiness and provenance are first-class fields;
- the bilingual cover uses the same honesty framing: SQL primary, legacy demo,
  candidate-not-discovery;
- the 3D spectrum/comparator ideas are noted for future explanatory UI, not
  implemented as scientific claims.

Not borrowed: the static-site-only architecture, CDN-first delivery, or the
upstream visual identity.

### 7.2 Contracts and provenance

Borrowed:

- one JSON Schema per cross-module artifact;
- golden examples next to contracts;
- `origen`-style provenance on every published object;
- a status vocabulary that distinguishes “no match”, “ambiguous”,
  “insufficient” and “unavailable”;
- module boundaries that can be tested in isolation.

Applied in HuellaX:

- B/API result schemas and `schema_version` checks;
- `REAL/HYBRID/SIM/SAMPLE` provenance and `fallback_reason` in analysis
  results;
- catalog status vocabulary (`known_star`, `ambiguous`,
  `uncatalogued_candidate`, `insufficient_data`, `catalog_unavailable`);
- SQL export compatibility checks (`check_compat.py`);
- audit CSV/JSON that preserves provenance.

Not borrowed: using a static publication directory as the primary contract
transport.

### 7.3 SkyBoT

Upstream value:

- a live IMCCE SkyBoT query from the browser, using the epoch A date, returning
  separation, ephemeris error, tolerance and a verdict;
- a clear “not identified in the consulted catalogs” message, never Planet X;
- an explicit geocentric approximation caveat.

HuellaX status:

- **idea borrowed, not integrated**;
- it would complement B's Gaia/2MASS/WISE identity with a solar-system
  ephemeris check;
- a future integration must pass the SPHEREx position (not only a geocentric
  observer), handle network failure explicitly, and never turn “no match” into
  “new object”;
- until then, B's star/galaxy identity and the app's `uncatalogued_candidate`
  status remain the only identity path.

### 7.4 Spectral states

Upstream vocabulary:

```text
sin_rasgo · compatible · candidata · detectada · datos_insuficientes
```

Borrowed as a **UX vocabulary** for future explanatory panels:

- it distinguishes “no feature”, “compatible”, “candidate”, “detected” and
  “insufficient data”;
- it requires degrees of freedom, errors, resolution and alternative
  explanations;
- it says “most compatible among those evaluated”, not “this is a comet”.

HuellaX status:

- no spectral classification is implemented in the primary runtime;
- upstream templates are synthetic, and the real-observation validation was
  pending;
- therefore the states are not used as evidence and must not be shown as a
  scientific detection until a real, validated spectral pipeline exists.

### 7.5 Science communication

Borrowed:

- “what we measured / what we infer / what would falsify it” structure;
- explicit uncertainty and limitation text;
- candidate-level language, including in exports;
- a visible distinction between “same classification” and “similar spectrum”.

Applied in HuellaX:

- public text, evidence, falsifier and readiness in analysis results;
- benchmark reports that preserve failures and data-limited outcomes;
- README/cover language that does not upgrade candidates.

---

## 8. Explicitly not adopted

| Upstream mechanism | Why it is not adopted |
|---|---|
| **Static web + pre-generated JSON as the primary architecture** | HuellaX has chosen a live SQL/service runtime. Reverting to static publication would lose runtime data consistency, arbitrary-coordinate lookup and auditability. |
| **Synthetic demo data as scientific evidence** | The demo fields (`slipher`, `atlas`, `luhman`) are illustrative. HuellaX requires real provenance and explicit SIM/HYBRID labels. |
| **Two-epoch-only motion conclusions** | A/B velocity with 2σ/5σ thresholds cannot separate motion from variability, artifacts or chance alignment. HuellaX uses multi-epoch models and readiness gates. |
| **No Gaia / no stellar identity** | JPL/MPC identifies solar-system small bodies, not the stars, brown dwarfs and galaxies that dominate SPHEREx fields. HuellaX uses Gaia/2MASS/WISE through B. |
| **Direct code copy** | The upstream had no license at analysis time. Inclusion is by owner permission; the runtime does not copy upstream code. |
| **Molecular “detected” as confirmation** | The upstream templates and molecular states were validated on synthetic spectra; real-observation validation was pending. HuellaX does not present them as detections. |
| **15″ match tolerance as a primary identity rule** | At 6.15″/pixel this is ~2.4 px and too permissive for a confident identity. HuellaX uses catalog-specific quality, RUWE/PM checks and explicit ambiguity. |
| **No-backend browser-only operation** | A static site cannot provide catalog caches, batch identification, audit exports or runtime coverage. HuellaX keeps a service plane. |

Also not adopted as claims:

- “Planet X confirmed”;
- “new star” / “new planet” from a catalog miss;
- “real data” for a synthetic or hybrid run;
- “no coverage” from a failed fetch;
- “known” from an ambiguous multi-catalog match.

---

## 9. Verification

### 9.1 Static checks (no build)

```bash
cd <repo root>
python3 scripts/check_docs.py
```

The checker validates:

- UTF-8 decoding of the cover and documentation files;
- local HTML and Markdown links resolve to existing files;
- `README.md` carries the `English | Español` switch and links the Spanish
  README; `README.es.md` carries the reverse switch;
- `README.zh-CN.md` is linked only as legacy;
- `index.html` has complete `en`/`es` i18n key coverage and supports
  `?lang=en|es` + `localStorage`;
- required statements are present: SQL primary, AstroNova legacy/demo,
  candidate-not-discovery.

### 9.2 Service checks (manual)

```bash
curl -s http://127.0.0.1:8797/api/health
curl -s http://127.0.0.1:8790/api/health
curl -s http://127.0.0.1:8798/api/v1/health
curl -s http://127.0.0.1:8799/api/v1/health
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8830/
```

Expected: DB/app 200 with `ok=true`; C/B health JSON; view 200. Ports are
production defaults and must not be silently changed.

### 9.3 Data checks

```bash
curl -s 'http://127.0.0.1:8797/api/v1/epochs?ra=269.452077&dec=4.693365&fov=0.5'
curl -s 'http://127.0.0.1:8797/api/v1/coverage?ra=269.452077&dec=4.693365'
curl -s -X POST http://127.0.0.1:8790/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"ra":269.452077,"dec":4.693365,"fov":0.5,"mode":"auto"}'
```

The analysis response must retain `data.provenance`, `fallback_reason`,
`result.readiness` and `discovery_claim: false`. A DB outage must produce
`DB_UNAVAILABLE`, not a false “baseline too short”.

### 9.4 Legacy demo check

```bash
cd astro
python3 modulos/m9_sitio/ejemplos/generar_datos.py
cd ..
python3 -m http.server 8840
# open http://127.0.0.1:8840/astro/modulos/m9_sitio/index.html
```

The page must show its synthetic/demo warning. It must not be cited as
validation evidence.

---

## 10. Open issues and follow-ups

1. **Legacy demo data is not committed.** `astro/datos/` is gitignored and
   contains only `LEEME.md`. The site requires `generar_datos.py` and works
   only over HTTP. This is intentional (no generated data in git) but easy to
   misread.
2. **B and C are not started by `start_all.sh`.** The launcher starts DB, app
   and view. Catalog identity and coverage degrade explicitly until B/C are
   started; document this in demos.
3. **Spectral pipeline is absent.** m6 is not adopted as evidence. Any future
   spectral UI must use real templates/validation and keep the borrowed state
   vocabulary explicitly provisional.
4. **SkyBoT is not integrated.** It remains a candidate enhancement for
   solar-system identity; geocentric approximations and network failures must
   be explicit.
5. **Preset-target offline fallback can obscure SQL primacy.** The app can read
   `epoch_catalog.json` for the seven preset targets. This is deliberate for
   offline demos, but docs and UI must continue to label the source. Arbitrary
   coordinates always go through SQL.
6. **Upstream licensing is permission-based.** `astro/` has no upstream
   license. Attribution is preserved; legal review is advisable before public
   redistribution. Do not relicense it under Apache-2.0.
7. **Push is not authorized.** The integration target has no push permission
   in this environment. Commits are local; do not push.
8. **`README.zh-CN.md` is legacy and stale.** It describes MoveScope before the
   AstroNova integration. It is intentionally retained and labelled legacy;
   it is not the primary Chinese entry point.
9. **External services are dependencies.** IRSA, S3, Gaia TAP, SIMBAD and
   SkyBoT can be unavailable or rate-limited. The system must degrade
   explicitly, never silently fabricate.
10. **I18n scope is documentation-only.** The cover and READMEs are bilingual,
    but the MoveScope UI remains Chinese at this commit. The integration adds
    English docs, not a translated app.

---

## 11. References

- AstroNova upstream: <https://github.com/Beltranpcb/AstroNova>
- Upstream analysis in this repo:
  [`项目主控/参考/AstroNova-DEEP.md`](项目主控/参考/AstroNova-DEEP.md)
- Upstream boundary: [`astro/UPSTREAM.md`](astro/UPSTREAM.md)
- SQL catalog docs: [`系统/数据库工具/README.md`](系统/数据库工具/README.md),
  [`系统/数据库工具/docs/API.md`](系统/数据库工具/docs/API.md),
  [`系统/数据库工具/docs/CATALOG.md`](系统/数据库工具/docs/CATALOG.md)
- Architecture contract:
  [`项目主控/02_架构设计与集成契约.md`](项目主控/02_架构设计与集成契约.md)
- Launcher: [`项目主控/启动/README.md`](项目主控/启动/README.md)
- C service: [`系统/anyfield/README.md`](系统/anyfield/README.md)
- View: [`系统/视图工具/README.md`](系统/视图工具/README.md)
- NASA Space Apps 2026 challenge:
  <https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/>
