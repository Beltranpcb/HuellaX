# Earth texture attribution

The entry page uses two image textures for the animated Earth:

| File | Subject | Source |
|---|---|---|
| `assets/earth.jpg` | Earth day/atmosphere texture | NASA Visible Earth / Blue Marble, imported from the three.js example planet textures |
| `assets/earth-lights.png` | Earth night-lights texture | NASA Earth Observatory night-lights imagery, imported from the same three.js example set |

Reference sources:

- NASA Visible Earth, Blue Marble collection:
  <https://visibleearth.nasa.gov/collection/1484/blue-marble>
- NASA Earth Observatory, night lights:
  <https://earthobservatory.nasa.gov/features/NightLights>
- three.js example assets and MIT license:
  <https://threejs.org/examples/textures/planets/earth_atmos_2048.jpg>
  <https://threejs.org/examples/textures/planets/earth_lights_2048.png>
  <https://github.com/mrdoob/three.js/blob/dev/LICENSE>

## Code provenance

The entry-page orbital drawing in `index.html` is original Canvas 2D code written
for HuellaX. No three.js Earth mesh, shader, or orbital-camera code is copied into
this page. The textures are used only as image sources inside a clipped 2D canvas.

The primary Sky View application separately uses its own three.js globe code and
its own copy of these textures. That application is maintained in the `system/`
submodule and keeps its own notices.

## Terms

NASA imagery is generally not copyrighted, but NASA media guidelines apply. NASA
does not endorse this project or any commercial product or service. three.js is
distributed under the MIT License; the texture files are attributed here rather
than relicensed under the Apache License 2.0 that covers the original
MoveScope/HuellaX work.
