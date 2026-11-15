<!--
  ARCHIVO: modulos/m2_alineacion/LEEME.md
  ROL: Describe el módulo junto a su comando de verificación.
  LEE: Nada.
  PRODUCE: La ficha que consulta quien desarrolla o revisa el módulo.
  VERIFICACION: Cada archivo citado aquí existe en el directorio del módulo.
-->

# m2_alineacion

**Lote A** · 6 horas estimadas · capa 1 del grafo

Poner las tres imágenes de un campo en la misma rejilla de píxeles.

## Entradas

- datos/m1_adquisicion/&lt;campo&gt;/seleccion.json
- datos/m1_adquisicion/&lt;campo&gt;/recortes/*.fits

## Salidas

- datos/m2_alineacion/&lt;campo&gt;/epoca_a.fits, epoca_b.fits, plantilla.fits (contrato alineados_fits)
- datos/m2_alineacion/&lt;campo&gt;/meta.json (contrato meta)
- datos/m2_alineacion/&lt;campo&gt;/epoca_a.png, epoca_b.png, diferencia.png (contrato imagenes_png)

## Depende de

`m1_adquisicion` (solo a través de sus archivos de datos).

## Archivos

| Archivo | Responsabilidad única |
|---|---|
| `LEEME.md` | Describe el módulo junto a su comando de verificación. |
| `resta_zodiacal.py` | Resta la luz zodiacal de cada recorte crudo. |
| `reproyeccion.py` | Reproyecta cada imagen sobre la rejilla de la época A. |
| `metadatos_campo.py` | Escribe meta.json con los datos del campo alineado. |
| `exportacion_png.py` | Exporta las imágenes PNG que la web muestra. |
| `pruebas/prueba_alineacion.py` | Comprueba la alineación sobre imágenes sintéticas con estrellas desplazadas. |
| `esquemas/meta.schema.json` | Copia del contrato `contratos/meta.schema.json` para verificar el módulo suelto. |
| `pytest.ini` | Declara el nombrado en español de las pruebas cuando el módulo se ejecuta suelto. |

## Orden de ejecución

```bash
python -m modulos.m2_alineacion.resta_zodiacal <campo>
python -m modulos.m2_alineacion.reproyeccion <campo>
python -m modulos.m2_alineacion.metadatos_campo <campo>
python -m modulos.m2_alineacion.exportacion_png <campo>
```

## Verificación en aislamiento

```bash
python -m pytest modulos/m2_alineacion/pruebas -q
```

Criterio de aceptación: el comando termina con código 0 solo si se cumple todo lo siguiente.

1. Con dos imágenes sintéticas de cinco estrellas cuyo WCS difiere en un desplazamiento conocido, los centroides coinciden tras alinear con un error máximo de 0,2 píxeles.
2. La extensión FLAGS alineada solo contiene valores enteros presentes en la original.
3. Los tres PNG miden 600 x 600 píxeles.
4. El meta.json generado valida contra contratos/meta.schema.json.

La verificación no ejecuta ningún otro módulo: usa datos sintéticos o los ejemplos de `contratos/ejemplos/`.

## Nota

Las tres imágenes deben venir del mismo detector para que el brillo sea comparable. FLAGS nunca se interpola porque contiene enteros.

## Estado

Implementado. El comando de verificación pasa sobre imágenes sintéticas (cinco estrellas fijas con el WCS desplazado una fracción de píxel, más un objeto móvil). La reproyección usa `astropy.wcs` con `scipy.ndimage.map_coordinates` en lugar de la biblioteca `reproject`, que no está en `requirements.txt`. Pendiente de probar sobre un recorte real de SPHEREx: en especial que la extensión `ZODI` exista con ese nombre y que el WCS de `IMAGE` sea celeste 2D.
