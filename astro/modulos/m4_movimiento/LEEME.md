<!--
  ARCHIVO: modulos/m4_movimiento/LEEME.md
  ROL: Describe el módulo junto a su comando de verificación.
  LEE: Nada.
  PRODUCE: La ficha que consulta quien desarrolla o revisa el módulo.
  VERIFICACION: Cada archivo citado aquí existe en el directorio del módulo.
-->

# m4_movimiento

**Lote C** · 4 horas estimadas · capa 3 del grafo

Medir cuánto se mueve cada pareja propuesta, con su incertidumbre.

## Entradas

- datos/m3_deteccion/&lt;campo&gt;/fuentes.json

## Salidas

- datos/m4_movimiento/&lt;campo&gt;/movimiento.json (contrato movimiento)

## Depende de

`m3_deteccion` (solo a través de sus archivos de datos).

## Archivos

| Archivo | Responsabilidad única |
|---|---|
| `LEEME.md` | Describe el módulo junto a su comando de verificación. |
| `cinematica.py` | Calcula la velocidad angular de cada pareja propuesta. |
| `incertidumbre.py` | Propaga la incertidumbre de posición hasta la velocidad. |
| `clasificacion.py` | Asigna a cada pareja su clase de movimiento. |
| `pruebas/prueba_movimiento.py` | Comprueba las medidas de movimiento sobre el ejemplo del contrato. |
| `esquemas/movimiento.schema.json` | Copia del contrato `contratos/movimiento.schema.json` para verificar el módulo suelto. |
| `ejemplos/campo_ejemplo/fuentes.json`, `movimiento.json` | Copias de `contratos/ejemplos/campo_ejemplo/` para verificar el módulo suelto. |
| `pytest.ini` | Declara el nombrado en español de las pruebas cuando el módulo se ejecuta suelto. |

## Orden de ejecución

```bash
python -m modulos.m4_movimiento.cinematica <campo>
python -m modulos.m4_movimiento.incertidumbre <campo>
python -m modulos.m4_movimiento.clasificacion <campo>
```

## Verificación en aislamiento

```bash
python -m pytest modulos/m4_movimiento/pruebas -q
```

Criterio de aceptación: el comando termina con código 0 solo si se cumple todo lo siguiente.

1. Con contratos/ejemplos/campo_ejemplo/fuentes.json, la velocidad de cada pareja difiere menos de un 1 % de la del ejemplo movimiento.json.
2. Una pareja con posiciones idénticas recibe la clase estacionaria.
3. La clase de cada pareja del ejemplo coincide con la del ejemplo movimiento.json.
4. El movimiento.json generado valida contra contratos/movimiento.schema.json.

La verificación no ejecuta ningún otro módulo: usa datos sintéticos o los ejemplos de `contratos/ejemplos/`.

## Nota

Los umbrales de significancia (2 y 5) son valores iniciales. Cambiarlos exige actualizar contratos/movimiento.schema.json en un PR propio.

## Estado

Implementado. El comando de verificación pasa sobre el ejemplo del contrato: reproduce valor a valor el `movimiento.json` de ejemplo. Los umbrales de clase (2 y 5 sigmas) son valores iniciales por calibrar con datos reales.
