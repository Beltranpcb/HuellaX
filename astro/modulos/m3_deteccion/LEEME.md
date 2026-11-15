<!--
  ARCHIVO: modulos/m3_deteccion/LEEME.md
  ROL: Describe el módulo junto a su comando de verificación.
  LEE: Nada.
  PRODUCE: La ficha que consulta quien desarrolla o revisa el módulo.
  VERIFICACION: Cada archivo citado aquí existe en el directorio del módulo.
-->

# m3_deteccion

**Lote B** · 12 horas estimadas · capa 2 del grafo

Encontrar las fuentes que cambian de posición entre la época A y la época B.

## Entradas

- datos/m2_alineacion/&lt;campo&gt;/epoca_a.fits, epoca_b.fits, plantilla.fits
- datos/m2_alineacion/&lt;campo&gt;/meta.json

## Salidas

- datos/m3_deteccion/&lt;campo&gt;/fuentes.json (contrato fuentes)

## Depende de

`m2_alineacion` (solo a través de sus archivos de datos).

## Archivos

| Archivo | Responsabilidad única |
|---|---|
| `LEEME.md` | Describe el módulo junto a su comando de verificación. |
| `deteccion_fuentes.py` | Detecta las fuentes puntuales de cada imagen alineada. |
| `emparejamiento.py` | Separa las fuentes estacionarias de las fuentes huérfanas. |
| `propuesta_parejas.py` | Propone parejas A-B entre las fuentes huérfanas. |
| `pruebas/prueba_deteccion.py` | Comprueba la detección sobre imágenes de ruido con fuentes inyectadas. |
| `esquemas/fuentes.schema.json` | Copia del contrato `contratos/fuentes.schema.json` para verificar el módulo suelto. |
| `pytest.ini` | Declara el nombrado en español de las pruebas cuando el módulo se ejecuta suelto. |

## Orden de ejecución

```bash
python -m modulos.m3_deteccion.deteccion_fuentes <campo>
python -m modulos.m3_deteccion.emparejamiento <campo>
python -m modulos.m3_deteccion.propuesta_parejas <campo>
```

## Verificación en aislamiento

```bash
python -m pytest modulos/m3_deteccion/pruebas -q
```

Criterio de aceptación: el comando termina con código 0 solo si se cumple todo lo siguiente.

1. Una fuente falsa inyectada en una imagen de ruido se recupera con un error de posición máximo de 0,5 píxeles.
2. Las estrellas presentes en el mismo sitio de las tres imágenes salen con situacion igual a estacionaria.
3. Una única fuente desplazada entre A y B produce exactamente una pareja.
4. El fuentes.json generado valida contra contratos/fuentes.schema.json.

La verificación no ejecuta ningún otro módulo: usa datos sintéticos o los ejemplos de `contratos/ejemplos/`.

## Nota

Toda detección se trata como candidata a objeto móvil, nunca como asteroide confirmado. La velocidad admisible va de 0,05 a 150 segundos de arco por hora (un asteroide del cinturón principal recorre unos 75 ″/h). Además se exige señal/ruido de al menos 5 en las dos fuentes y que ninguna caiga a menos de 5 píxeles del borde del recorte.

## Estado

Implementado. El comando de verificación pasa sobre imágenes sintéticas. Pendiente de probar sobre un recorte real de SPHEREx: en especial el número del bit `SOURCE` de FLAGS (supuesto 21, leído de la cabecera `MP_SOURCE` si existe) y los umbrales iniciales (5 sigmas, 60 segundos de arco por hora, razón de brillo 2).
