<!--
  ARCHIVO: contratos/imagenes_png.md
  ROL: Fija tamaño, contraste, orientación de las imágenes de la web.
  LEE: Nada.
  PRODUCE: La regla que cumplen productor con consumidores.
  VERIFICACION: Descrita en el último apartado de este archivo.
-->
# Contrato: imágenes PNG de la web

| Dato | Valor |
|---|---|
| Productor | `m2_alineacion/exportacion_png.py` |
| Consumidores | `m7_publicacion` (las copia), `m9_sitio` (las muestra) |
| Ruta | `datos/m2_alineacion/<campo>/`, copiadas a `datos/m7_publicacion/<campo>/` |
| En git | No: `datos/` no entra en el repositorio. |

## Forma obligatoria

- Tres archivos con nombres fijos: `epoca_a.png`, `epoca_b.png`, `diferencia.png`.
- 600 x 600 píxeles cada uno. Menos de 1 MB cada uno.
- `epoca_a.png` y `epoca_b.png` usan los mismos límites de contraste, calculados sobre la época A.
- `diferencia.png` es B menos A con un mapa de dos tonos: un tono para lo que aparece, otro para lo que desaparece.
- Orientación: norte arriba, este a la izquierda. La fila 0 de la rejilla alineada queda en la parte inferior del PNG.
- Conversión de rejilla a PNG: `x_png = x * 600 / ancho`, `y_png = 600 - y * 600 / alto`, con `ancho` y `alto` de `meta.json`.

## Verificación

Leer el tamaño de cada PNG: 600 x 600. Alternar `epoca_a.png` con `epoca_b.png`: las estrellas fijas no saltan.
