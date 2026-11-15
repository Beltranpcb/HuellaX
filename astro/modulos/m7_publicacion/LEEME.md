<!--
  ARCHIVO: modulos/m7_publicacion/LEEME.md
  ROL: Describe el módulo junto a su comando de verificación.
  LEE: Nada.
  PRODUCE: La ficha que consulta quien desarrolla o revisa el módulo.
  VERIFICACION: Cada archivo citado aquí existe en el directorio del módulo.
-->

# m7_publicacion

**Lote A** · 4 horas estimadas · capa 5 del grafo

Dejar en un único directorio los datos que la web lee.

## Entradas

- datos/m2_alineacion/&lt;campo&gt;/meta.json con sus tres PNG
- datos/m3_deteccion/&lt;campo&gt;/fuentes.json
- datos/m4_movimiento/&lt;campo&gt;/movimiento.json
- datos/m5_identificacion/&lt;campo&gt;/identificacion.json
- datos/m6_huella_espectral/&lt;campo&gt;/espectros.json

## Salidas

- datos/m7_publicacion/campos.json (contrato campos)
- datos/m7_publicacion/&lt;campo&gt;/candidatos.json (contrato candidatos)
- datos/m7_publicacion/&lt;campo&gt;/meta.json, espectros.json, epoca_a.png, epoca_b.png, diferencia.png (copias)

## Depende de

`m2_alineacion`, `m3_deteccion`, `m4_movimiento`, `m5_identificacion`, `m6_huella_espectral` (solo a través de sus archivos de datos).

## Archivos

| Archivo | Responsabilidad única |
|---|---|
| `LEEME.md` | Describe el módulo junto a su comando de verificación. |
| `union_candidatos.py` | Une los resultados de cada pareja en candidatos.json. |
| `copia_publicable.py` | Copia al directorio publicado los archivos que la web lee sin cambios. |
| `indice_campos.py` | Escribe campos.json con la lista de campos publicados. |
| `indice_catalogo.py` | Escribe catalogo.json: objetos publicados, datos disponibles, misma clasificación y espectros similares. |
| `control_publicacion.py` | Rechaza la publicación cuando un archivo incumple su contrato. |
| `pruebas/prueba_publicacion.py` | Comprueba la unión sobre los ejemplos de los contratos. |
| `pytest.ini` | Recoge las pruebas `prueba_*.py` sin depender de la raíz. |
| `esquemas/` | Copia de los cuatro contratos que valida el control. |
| `ejemplos/` | `campo_ejemplo`: los siete JSON de referencia. |

## Orden de ejecución

```bash
python -m modulos.m7_publicacion.union_candidatos <campo>
python -m modulos.m7_publicacion.copia_publicable <campo>
python -m modulos.m7_publicacion.indice_campos
python -m modulos.m7_publicacion.control_publicacion
```

## Verificación en aislamiento

```bash
python -m pytest modulos/m7_publicacion/pruebas -q
```

Criterio de aceptación: el comando termina con código 0 solo si se cumple todo lo siguiente.

1. El candidatos.json generado desde los ejemplos coincide valor a valor con modulos/m7_publicacion/ejemplos/campo_ejemplo/candidatos.json.
2. El campos.json generado desde los ejemplos coincide con modulos/m7_publicacion/ejemplos/campos.json.
3. Un JSON de entrada que incumple su esquema hace que control_publicacion termine con código distinto de cero.
4. Un archivo de 2 MB en el directorio publicado hace que control_publicacion termine con código distinto de cero.
5. Un PNG que no mide 600 x 600 hace que control_publicacion termine con código distinto de cero.
6. Publicar dos campos a la vez escribe las dos entradas en campos.json con su recuento correcto.
7. Un campo donde todas las parejas son estacionarias publica una lista vacía de candidatos y pasa el control.
8. Un meta.json o un candidatos.json incompleto hace que indice_campos falle con un mensaje que nombra el archivo y la clave que falta.

La verificación no ejecuta ningún otro módulo: usa datos sintéticos o los ejemplos de `modulos/m7_publicacion/ejemplos/`.

## Nota

Único módulo que escribe en datos/m7_publicacion/. Nadie edita ese directorio a mano.

## Estado

Implementado. Los cuatro comandos de arriba se ejecutan en ese orden y la
verificación pasa: 19 pruebas en verde con `python -m pytest
modulos/m7_publicacion/pruebas -q`. La unión solo necesita la biblioteca
estándar; `control_publicacion.py` usa `jsonschema` para leer los esquemas de
`esquemas/` (o `contratos/` si el árbol completo está presente) y lee la
cabecera de los PNG con `struct` para comprobar que miden 600 x 600,
sin depender de ninguna biblioteca de imagen.
