<!--
  ARCHIVO: contratos/LEEME.md
  ROL: Describe la capa de contratos con sus reglas de cambio.
  LEE: Nada.
  PRODUCE: El índice de contratos que consultan los cuatro lotes.
  VERIFICACION: Cada contrato de la tabla existe en este directorio; cada esquema tiene su ejemplo.
-->

# contratos/

Los módulos de HUELLA X no se importan entre sí: se comunican por archivos de datos. Este directorio fija la forma de cada uno de esos archivos. No contiene lógica.

## Índice

| Contrato | Dato | Productor | Consumidores | Ruta real del dato |
|---|---|---|---|---|
| `contratos/seleccion.schema.json` | seleccion.json | m1 | m2, m6 | `datos/m1_adquisicion/<campo>/seleccion.json` |
| `contratos/recortes_fits.md` | recortes FITS crudos | m1 | m2, m6 | `datos/m1_adquisicion/<campo>/recortes/*.fits` |
| `contratos/alineados_fits.md` | FITS alineados | m2 | m3 | `datos/m2_alineacion/<campo>/epoca_a.fits, epoca_b.fits, plantilla.fits` |
| `contratos/meta.schema.json` | meta.json | m2 | m3, m7, m9 | `datos/m2_alineacion/<campo>/meta.json` |
| `contratos/imagenes_png.md` | tres PNG | m2 | m7, m9 | `datos/m2_alineacion/<campo>/epoca_a.png, epoca_b.png, diferencia.png` |
| `contratos/fuentes.schema.json` | fuentes.json | m3 | m4, m5, m6, m7 | `datos/m3_deteccion/<campo>/fuentes.json` |
| `contratos/movimiento.schema.json` | movimiento.json | m4 | m5, m6, m7 | `datos/m4_movimiento/<campo>/movimiento.json` |
| `contratos/identificacion.schema.json` | identificacion.json | m5 | m7 | `datos/m5_identificacion/<campo>/identificacion.json` |
| `contratos/espectros.schema.json` | espectros.json | m6 | m7, m9 | `datos/m6_huella_espectral/<campo>/espectros.json` |
| `contratos/candidatos.schema.json` | candidatos.json | m7 | m9 | `datos/m7_publicacion/<campo>/candidatos.json` |
| `contratos/campos.schema.json` | campos.json | m7 | m9 | `datos/m7_publicacion/campos.json` |
| `contratos/plantillas.schema.json` | plantillas.json | m6 (`publicar_plantillas`) | m7, m9 | `datos/m6_huella_espectral/plantillas.json` |
| `contratos/catalogo.schema.json` | catalogo.json | m7 (propuesto: `indice_catalogo.py`) | m9 | `datos/m7_publicacion/catalogo.json` |
| `contratos/guia_visual.md` | variables de estilo | equipo | m8, m9 | `copiadas a mano en cada estilo.css` |

Los archivos intermedios internos de un módulo (por ejemplo `detecciones.json` dentro de m3) no tienen contrato: ningún otro módulo los lee.

## Convenciones comunes

- Coordenadas: ICRS, en grados decimales (`ra_grados`, `dec_grados`).
- Fechas: MJD, en días (`mjd`).
- Ángulos pequeños: segundos de arco (sufijo `_segarc`).
- Píxeles `x`, `y`: rejilla alineada de la época A, base 0, origen en la esquina inferior izquierda.
- Identificadores: `campo` en minúsculas con guion bajo; `id_pareja` con la forma `p001`; `id_fuente` con la forma `a001`, `b001`, `t001` según la imagen (época A, época B, plantilla).
- Todo JSON lleva `version_contrato` igual a `"1"`.
- Todo JSON admite un campo `_comentario` que ningún consumidor lee.
- Nombres de campo en español, sin acentos, sin espacios.

## Ejemplos

`contratos/ejemplos/` contiene un ejemplo escrito a mano de cada contrato JSON. Los ocho ejemplos describen el mismo campo ficticio (`campo_ejemplo`) con dos parejas, así que son coherentes entre sí: `candidatos.json` es exactamente la unión de los otros. Sus valores son inventados, sin valor científico.

Sirven para que cada lote trabaje sin esperar a los demás: un módulo se prueba leyendo los ejemplos de sus entradas.

Los contratos binarios (FITS, PNG) no tienen ejemplo en git: las pruebas de m2, m3, m6 crean imágenes sintéticas en memoria.

## Verificación

```bash
check-jsonschema --schemafile contratos/seleccion.schema.json contratos/ejemplos/campo_ejemplo/seleccion.json
check-jsonschema --schemafile contratos/meta.schema.json contratos/ejemplos/campo_ejemplo/meta.json
check-jsonschema --schemafile contratos/fuentes.schema.json contratos/ejemplos/campo_ejemplo/fuentes.json
check-jsonschema --schemafile contratos/movimiento.schema.json contratos/ejemplos/campo_ejemplo/movimiento.json
check-jsonschema --schemafile contratos/identificacion.schema.json contratos/ejemplos/campo_ejemplo/identificacion.json
check-jsonschema --schemafile contratos/espectros.schema.json contratos/ejemplos/campo_ejemplo/espectros.json
check-jsonschema --schemafile contratos/candidatos.schema.json contratos/ejemplos/campo_ejemplo/candidatos.json
check-jsonschema --schemafile contratos/campos.schema.json contratos/ejemplos/campos.json
check-jsonschema --schemafile contratos/catalogo.schema.json contratos/ejemplos/catalogo.json
check-jsonschema --schemafile contratos/plantillas.schema.json contratos/ejemplos/plantillas.json
```

Criterio de aceptación: los diez comandos terminan con código 0.

## Regla de cambio

Un contrato solo cambia en un pull request propio, que actualiza a la vez el esquema con su ejemplo, avisado a los cuatro lotes. Un cambio incompatible sube `version_contrato`.

## Ampliación compatible (análisis de objetos)

Todos los campos nuevos son **opcionales**: ninguno entra en `required`, así que los datos anteriores siguen validando y `version_contrato` se mantiene en `"1"`.

| Contrato | Campos nuevos | Para qué |
|---|---|---|
| `meta` | `origen`, `wcs` | Marcar datos reales o sintéticos; convertir un clic en RA/DEC sin inventar coordenadas. |
| `identificacion` | `clase_objeto`, `veredicto`, `mjd_consulta`, `coincidencias`; `catalogo` admite `gaia_dr3` | Varias coincidencias ordenadas, ambigüedad y «sin coincidencia concluyente». |
| `espectros` | `origen`, `advertencias`, `calidad`, `composicion`; en `ajustes_plantilla`: `grados_libertad`, `n_puntos`, `escala`, `origen_plantilla`, `referencia_plantilla` | Chi² con grados de libertad, avisos de interpretación y composición molecular (compatible, candidata, detectada, datos insuficientes). |
| `candidatos` | `clase_objeto`, `veredicto_identificacion`, `origen_espectro`, `advertencias`, `tiene_composicion` | Lo que la web necesita sin releer otros archivos. |
| `plantillas` (nuevo) | `plantillas[]` con curva normalizada, `origen_plantilla` y `referencia` | Dibujar las plantillas sobre el espectro y declarar si son sintéticas. |
| `catalogo` (nuevo) | `objetos[]` con clasificación, datos disponibles y `relacionados` | Catálogo navegable; «misma clasificación» y «espectros similares» son listas distintas. |

Los ejemplos de `meta`, `espectros` y `catalogo` ya usan los campos nuevos. Los de `identificacion` y `candidatos` se actualizan cuando m5 y m7 los produzcan, porque sus pruebas comparan la salida con el ejemplo.
