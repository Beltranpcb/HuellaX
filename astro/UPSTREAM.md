# AstroNova / HUELLA X upstream

This directory preserves the AstroNova / HUELLA X upstream for the HuellaX
integration.

- Upstream: https://github.com/Beltranpcb/AstroNova
- Analyzed commit: 1253925ab13419b5d44db323548784c939a93a6e
- Status at merge time: NASA Space Apps 2026 challenge prototype; static web +
  offline Python pipeline; demo fields are synthetic; real-data validation was
  pending.
- The owner confirmed this code may be included in HuellaX as open code.
- Keep upstream path, attribution and the NASA Space Apps 2026 event note in
  the repository history. Do not remove this file when adapting the legacy UI.

The primary HuellaX runtime (MoveScope + SQL catalog services) lives in
`系统/`; AstroNova is kept as a functional upstream/reference, not as the
primary data source.
