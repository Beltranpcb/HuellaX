<!--
  ARCHIVO: modulos/m1_adquisicion/LEEME.md
  ROL: Describe el módulo junto a su comando de verificación.
  LEE: Nada.
  PRODUCE: La ficha que consulta quien desarrolla o revisa el módulo.
  VERIFICACION: Cada archivo citado aquí existe en el directorio del módulo.
-->

# m1_adquisicion

**Lote A** · 6 horas estimadas · capa 0 del grafo

Obtener del archivo IRSA los recortes FITS de cada campo objetivo.

## Entradas

- Servicio SIA2 de IRSA (colecciones spherex_qr3, spherex_dr1, spherex_dr1_deep)
- Servicio de recortes de IRSA

## Salidas

- datos/m1_adquisicion/&lt;campo&gt;/seleccion.json (contrato seleccion)
- datos/m1_adquisicion/&lt;campo&gt;/recortes/*.fits (contrato recortes_fits)

## Depende de

Ningún otro módulo.

## Archivos

| Archivo | Responsabilidad única |
|---|---|
| `LEEME.md` | Describe el módulo junto a su comando de verificación. |
| `campos_objetivo.json` | Declara los campos del cielo que el pipeline debe procesar. |
| `consulta_sia.py` | Lista las exposiciones de SPHEREx que cubren un campo objetivo (TAP de IRSA; respaldo: listado guardado y luego S3). |
| `indice_s3.py` | Lista las exposiciones sin TAP: lee las cabeceras de los FITS en la copia pública de AWS S3 y comprueba la cobertura con su WCS. |
| `seleccion_epocas.py` | Elige qué exposiciones cumplen cada papel del contrato de selección. |
| `descarga_recortes.py` | Descarga el recorte FITS de cada exposición seleccionada. |
| `pruebas/prueba_adquisicion.py` | Comprueba la selección de épocas sobre un listado sintético sin usar la red. |

## Orden de ejecución

```bash
python -m modulos.m1_adquisicion.consulta_sia <campo>
python -m modulos.m1_adquisicion.seleccion_epocas <campo>
python -m modulos.m1_adquisicion.descarga_recortes <campo>
```

## Verificación en aislamiento

```bash
python -m pytest modulos/m1_adquisicion/pruebas -q
```

Criterio de aceptación: el comando termina con código 0 solo si se cumple todo lo siguiente.

1. El seleccion.json generado desde un listado sintético valida contra contratos/seleccion.schema.json.
2. Las exposiciones con papel epoca_a, epoca_b, plantilla comparten el mismo detector.
3. La época A dista de la época B entre 0,5 y 72 horas.
4. La plantilla dista más de 120 días de la época A.
5. La prueba termina sin abrir ninguna conexión de red.

La verificación no ejecuta ningún otro módulo: usa datos sintéticos o los ejemplos de `contratos/ejemplos/`.

## Nota

Primera tarea de la hora 0: rellenar campos_objetivo.json; comprobar con la columna t_min que cada campo tiene dos exposiciones del mismo detector separadas horas o días.

## Estado

Esqueleto sin código: el comando de verificación falla hasta que el lote implemente el módulo.
