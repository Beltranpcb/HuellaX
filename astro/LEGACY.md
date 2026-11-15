# Legacy module: AstroNova / HUELLA X

**Status: legacy / reference. This is not the primary HuellaX product.**

`astro/` preserves the AstroNova / HUELLA X upstream inside HuellaX as a
clearly labelled legacy module. It is a static demo plus an offline Python
pipeline. The primary HuellaX product is **MoveScope + SQL** under
[`system/`](../system/), documented by the [repository cover](../README.md).
This module is not the primary SQL runtime and is not the supported
science/data path.

## Provenance and attribution

| Item | Value |
|---|---|
| Upstream repository | [Beltranpcb/AstroNova](https://github.com/Beltranpcb/AstroNova) |
| Analyzed commit | `1253925ab13419b5d44db323548784c939a93a6e` |
| Origin | AstroNova team, NASA Space Apps Challenge 2026, SPHEREx / Planet X challenge |
| Original language | Spanish (demo UI, documentation, comments and field names) |
| Integration | copied to `astro/`; upstream paths, source and Spanish UI are preserved |
| Ownership | the HuellaX team's own earlier project, same GitHub account |

Attribution: the design, Spanish copy, demo data and pipeline come from the
AstroNova / HUELLA X team, which is the same team behind HuellaX. We merged our
two projects to combine their features; HuellaX keeps AstroNova's original
paths, source and UI.

## NASA Space Apps note

AstroNova / HUELLA X was built for the NASA Space Apps Challenge 2026
(SPHEREx / Planet X challenge). This note records event participation only.
NASA does not endorse this project, and no NASA affiliation is claimed.

## Data warning

- The demo fields and examples are **synthetic**. They do not represent the
  real sky and are not a validated scientific result.
- Validation with real SPHEREx data and with Gaia is **pending**.
- This demo makes no discovery or Planet X claim. An object without a catalog
  match is an “unidentified candidate”, never a new object.
- Do not use this module as the primary data source or as a basis for
  scientific conclusions.

## Primary product

The primary HuellaX product is **MoveScope + SQL** under [`system/`](../system/):

- [Repository cover](../README.md) and [MoveScope app](http://127.0.0.1:8790/).
- This legacy module must not be presented as the primary runtime or as the
  primary data source.

## Licensing

AstroNova is our own work and is part of this repository, so it is covered by
the repository-level Apache-2.0 [LICENSE](../LICENSE) and [NOTICE](../NOTICE).
Third-party data and media remain subject to their own terms; see the `astro/`
README and the repository-level notices.

## Preservation

- The legacy UI is not translated wholesale: Spanish is the original language.
- The upstream source is not removed.
- The bilingual notice in `modulos/m9_sitio/index.html` is an integration
  wrapper, not a rewrite of the upstream UI.

## Related documents

- [UPSTREAM.md](UPSTREAM.md): provenance and preservation.
- [README.md](README.md): original Spanish README.
- [LEGACY.es.md](LEGACY.es.md): Spanish version of this notice.
- [Static demo](modulos/m9_sitio/index.html).
