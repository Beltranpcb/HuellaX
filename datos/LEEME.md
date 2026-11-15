<!--
  ARCHIVO: datos/LEEME.md
  ROL: Describe el directorio de datos generados. Nada de aquí entra en git.
  LEE: Nada.
  PRODUCE: La regla de propiedad de cada subdirectorio.
  VERIFICACION: Cada subdirectorio existente pertenece a un módulo de la tabla.
-->

# datos/

Este directorio lo escribe el pipeline. Nadie lo edita a mano. Hoy solo contiene este archivo: cada módulo crea su subdirectorio al ejecutarse.

Regla de propiedad: **cada módulo escribe únicamente en `datos/<su_modulo>/`** y lee de los subdirectorios de los módulos de los que depende.

| Subdirectorio | Lo escribe | Contenido | En git |
|---|---|---|---|
| `datos/m1_adquisicion/<campo>/` | m1_adquisicion | `seleccion.json`, `listado_exposiciones.json`, `recortes/*.fits` | No |
| `datos/m2_alineacion/<campo>/` | m2_alineacion | `epoca_a.fits`, `epoca_b.fits`, `plantilla.fits`, `meta.json`, tres PNG, `sin_zodiacal/` | No |
| `datos/m3_deteccion/<campo>/` | m3_deteccion | `fuentes.json`, `detecciones.json`, `situaciones.json` | No |
| `datos/m4_movimiento/<campo>/` | m4_movimiento | `movimiento.json`, `cinematica.json`, `significancia.json` | No |
| `datos/m5_identificacion/<campo>/` | m5_identificacion | `identificacion.json` | No |
| `datos/m5_identificacion/cache/` | m5_identificacion | Respuestas guardadas de JPL o del Minor Planet Center | No |
| `datos/m6_huella_espectral/<campo>/` | m6_huella_espectral | `espectros.json` con sus cuatro intermedios | No |
| `datos/m7_publicacion/` | m7_publicacion | `campos.json`; por campo: `candidatos.json`, `meta.json`, `espectros.json`, tres PNG | No |

`datos/m7_publicacion/` es lo único que lee la web. Cada archivo publicado pesa menos de 1 MB.

**Nada de este directorio entra en git.** Son salidas del pipeline, no fuente: se
regeneran ejecutando los módulos. Para tener datos de demostración sin red,
`modulos/m9_sitio/ejemplos/generar_datos.py` escribe tres campos sintéticos en
`datos/m7_publicacion/`.
