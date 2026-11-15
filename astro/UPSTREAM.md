# AstroNova / HUELLA X upstream

This directory preserves the AstroNova / HUELLA X upstream for the HuellaX
integration.

- Upstream: https://github.com/Beltranpcb/AstroNova
- Analyzed commit: 1253925ab13419b5d44db323548784c939a93a6e
- Origin: AstroNova team, NASA Space Apps Challenge 2026, SPHEREx / Planet X
  challenge. The original UI, documentation, comments and field names are in
  Spanish.
- NASA note: this records event participation only. NASA does not endorse this
  project, and no NASA affiliation is claimed.
- Status: legacy / reference; static web demo plus an offline Python pipeline.
  Demo fields and examples are synthetic; real SPHEREx-data and Gaia validation
  were still pending at merge time.
- Ownership: AstroNova is the HuellaX team's own earlier project, published
  under the same GitHub account. It was merged into HuellaX to combine its
  features with MoveScope and is covered by the repository's Apache-2.0 license.
- Attribution: design, Spanish copy, demo data and pipeline are from the
  AstroNova / HUELLA X team. Keep the original paths, source and this file.

The primary HuellaX runtime (MoveScope + SQL catalog services) lives in
`system/`; AstroNova is kept as a functional upstream/reference, not as the
primary data source or supported runtime. The bilingual legacy notice is at
the top of `modulos/m9_sitio/index.html`; the full notice is in
[LEGACY.md](LEGACY.md) and [LEGACY.es.md](LEGACY.es.md).
