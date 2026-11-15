<!--
  ARCHIVO: contratos/recortes_fits.md
  ROL: Fija las extensiones que debe traer cada recorte crudo.
  LEE: Nada.
  PRODUCE: La regla que cumplen productor con consumidores.
  VERIFICACION: Descrita en el último apartado de este archivo.
-->
# Contrato: recortes FITS crudos

| Dato | Valor |
|---|---|
| Productor | `m1_adquisicion/descarga_recortes.py` |
| Consumidores | `m2_alineacion`, `m6_huella_espectral` |
| Ruta | `datos/m1_adquisicion/<campo>/recortes/<id_exposicion>.fits` |
| En git | No. `.gitignore` excluye todo `*.fits`. |

## Forma obligatoria

- Un archivo por cada exposición de `seleccion.json`, con el nombre de su `archivo_recorte`.
- Recorte de imagen espectral de nivel 2 de SPHEREx, pedido con `center` y `size` al servicio de recortes de IRSA.
- Escala nativa de 6,15 segundos de arco por píxel.
- Extensiones presentes, con estos nombres:

| Extensión | Contenido | Unidad |
|---|---|---|
| `IMAGE` | Brillo superficial | MJy/sr |
| `FLAGS` | Máscara de píxeles, valores enteros | sin unidad |
| `VARIANCE` | Varianza de `IMAGE` | (MJy/sr)² |
| `ZODI` | Modelo de luz zodiacal | MJy/sr |
| `PSF` | Función de dispersión de punto | sin unidad |
| `WCS-WAVE` | Longitud de onda de cada píxel | micras |

Los nombres exactos se confirmaron contra la cabecera de los primeros recortes
reales (2026-11-14):

| Extensión del contrato | Nombre real en el recorte | Observación |
|---|---|---|
| `PSF` | **`EPSF`** | `m1` acepta los dos nombres (`ALIAS_EXTENSIONES`). |
| `WCS-WAVE` | `WCS-WAVE` | Tabla `WAVE-TAB` dispersa, no una imagen (ver abajo). |

### Formato real de `WCS-WAVE`

No es una imagen con un valor por píxel: es una tabla con una rejilla de nodos.

```
X       9 valores   coordenadas de columna en el marco del detector (1…2040)
Y      14 valores   coordenadas de fila en el marco del detector (1…2040)
VALUES 14 × 9 × 2   (longitud de onda µm, incertidumbre µm) en cada nodo
```

El recorte se sitúa en el detector completo con `CRPIX1W` / `CRPIX2W`, que el
servicio de recortes deja negativos: `píxel_detector = píxel_recorte − CRPIX1W`.
`m6_huella_espectral` interpola la longitud de onda a partir de esa rejilla.

## Verificación

Abrir cada archivo con `astropy.io.fits` y comprobar que la lista de extensiones contiene las seis de la tabla.
