# Third-party notices

This project is a candidate-first SPHEREx analysis tool. The following data,
software and media are used with attribution. They are not relicensed under the
Apache License 2.0 that covers the original HuellaX / MoveScope work.

## 1. SPHEREx data

- SPHEREx level-2 spectral images (QR3 / DR1) are from NASA/IPAC IRSA.
- IRSA: <https://irsa.ipac.caltech.edu/Missions/spherex.html>
- NASA data are publicly available; NASA does not endorse this project.
- AstroNova's static demo fields are synthetic and are not observations.

## 2. Catalogues

- Gaia DR3: ESA / Gaia Data Processing and Analysis Consortium.
- 2MASS: NASA/IPAC; derived crossmatch subsets in the primary catalogue service.
- AllWISE / WISE: NASA/JPL-Caltech; derived crossmatch subsets in the primary service.
- SIMBAD: CDS, Strasbourg; used for names and object metadata.
- JPL Small-Body Database / sb_ident and MPChecker: used by the legacy AstroNova
  module for solar-system identification.

The derived 2MASS/WISE tables are Gaia-crossmatch subsets, not complete all-sky
catalogues. Catalogue non-matches are `no_match`, not discoveries.

## 3. Software

- three.js r160: MIT License; notice preserved in the primary submodule.
- Python, Astropy and related dependencies: their respective licenses.
- AstroNova / HUELLA X upstream: preserved with attribution; no LICENSE file at
  merge time; owner confirmed inclusion; not relicensed under Apache-2.0.

## 4. Media

- Earth imagery: NASA Visible Earth / Blue Marble and NASA Earth Observatory
  night lights, via three.js example textures (MIT); NASA media guidelines apply.
  Exact files and code-provenance notes: [`assets/ATTRIBUTION.md`](assets/ATTRIBUTION.md).
- Screenshots and diagrams in this repository are project documentation.

## 5. NASA Space Apps Challenge

- Event: NASA Space Apps Challenge 2026, Planet X and SPHEREx.
- Legal terms: <https://www.spaceappschallenge.org/legal/>
- NASA does not endorse this project or any commercial product or service.

## 6. Upstream boundary

`astro/` is a legacy reference. Its static demo is synthetic; its real-data/Gaia
validation was pending at merge time. The primary runtime is `system/` and uses
SQL, not the AstroNova static JSON.
