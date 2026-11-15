# Earth visual attribution

## Source confirmed by the project owner

The Earth visual reference for the entry page is **God's Eye View** by Bilawal
Sidhu:

- Repository: <https://github.com/bilawalsidhu/gods-eye-view>
- Project site: <https://maptheworld.ai/>
- License: MIT for the source code
  <https://github.com/bilawalsidhu/gods-eye-view/blob/main/LICENSE>
- Copyright (c) 2026 Bilawal Sidhu

The entry page does **not** copy the God's Eye View Earth mesh, Cesium/Google
Maps integration, shaders or camera code. Its orbit/Earth drawing is original
Canvas 2D code written for HuellaX. God's Eye View is credited as the source of
the real-Earth visual reference and as design inspiration.

## Texture files

| File | Role | Provenance note |
|---|---|---|
| `assets/earth.jpg` | Earth day/atmosphere texture | Project-owner-confirmed Earth visual source: God's Eye View |
| `assets/earth-lights.png` | Earth night-lights texture | Project-owner-confirmed Earth visual source: God's Eye View |

God's Eye View's MIT grant covers its **source code only**. Its README states
that third-party data and imagery (including Google Maps and other providers)
remain under their own terms and are not relicensed by MIT. Therefore this file
does not relicense the Earth imagery under Apache-2.0, MIT or any other project
license; the imagery remains subject to its original provider terms.

Before public commercial redistribution, confirm the terms of the exact image
files with the provider. NASA does not endorse this project.

## Code provenance

- Entry-page orbital/Earth drawing: original Canvas 2D code in `index.html`.
- No God's Eye View source code is copied into this repository.
- The primary Sky View application uses its own three.js globe code and its own
  texture copy in the `system/` submodule.
