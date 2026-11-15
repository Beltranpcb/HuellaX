<!--
  ARCHIVO: contratos/alineados_fits.md
  ROL: Fija la rejilla común de las tres imágenes alineadas.
  LEE: Nada.
  PRODUCE: La regla que cumplen productor con consumidores.
  VERIFICACION: Descrita en el último apartado de este archivo.
-->
# Contrato: FITS alineados

| Dato | Valor |
|---|---|
| Productor | `m2_alineacion/reproyeccion.py` |
| Consumidor | `m3_deteccion` |
| Ruta | `datos/m2_alineacion/<campo>/epoca_a.fits`, `epoca_b.fits`, `plantilla.fits` |
| En git | No. `.gitignore` excluye todo `*.fits`. |

## Forma obligatoria

- Tres archivos con nombres fijos: `epoca_a.fits`, `epoca_b.fits`, `plantilla.fits`.
- Los tres comparten la misma forma de matriz con el mismo WCS: la rejilla de la época A.
- Extensiones de cada archivo:

| Extensión | Contenido | Regla de reproyección |
|---|---|---|
| `IMAGE` | Brillo con la luz zodiacal ya restada, en MJy/sr | interpolada |
| `VARIANCE` | Varianza de `IMAGE` | interpolada |
| `FLAGS` | Máscara de píxeles | vecino más cercano, nunca interpolada |

- La cabecera primaria conserva la fecha de la exposición en MJD junto al número de detector.
- Un píxel sin cobertura tras reproyectar vale `NaN` en `IMAGE`.

## Verificación

Las tres matrices `IMAGE` tienen la misma forma. Una estrella fija ocupa el mismo píxel en los tres archivos con un error máximo de 0,2 píxeles.
