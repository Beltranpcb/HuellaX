<!--
  ARCHIVO: modulos/m5_identificacion/LEEME.md
  ROL: Describe el módulo junto a su comando de verificación.
  LEE: Nada.
  PRODUCE: La ficha que consulta quien desarrolla o revisa el módulo.
  VERIFICACION: Cada archivo citado aquí existe en el directorio del módulo.
-->

# m5_identificacion

**Lote B** · 6 horas estimadas · capa 4 del grafo

Decir si cada pareja en movimiento corresponde a un objeto ya catalogado.

## Entradas

- datos/m3_deteccion/&lt;campo&gt;/fuentes.json
- datos/m4_movimiento/&lt;campo&gt;/movimiento.json
- API sb_ident de JPL, con MPChecker del Minor Planet Center como alternativa

## Salidas

- datos/m5_identificacion/&lt;campo&gt;/identificacion.json (contrato identificacion)
- datos/m5_identificacion/cache/ (respuestas guardadas; van a git)

## Depende de

`m3_deteccion`, `m4_movimiento` (solo a través de sus archivos de datos).

## Archivos

| Archivo | Responsabilidad única |
|---|---|
| `LEEME.md` | Describe el módulo junto a su comando de verificación. |
| `consulta_catalogos.py` | Obtiene la respuesta del catálogo de cuerpos menores para cada pareja en movimiento. |
| `cruce_posicional.py` | Decide el estado de catálogo de cada pareja. |
| `pruebas/prueba_identificacion.py` | Comprueba el cruce con una caché sintética sin usar la red. |
| `esquemas/identificacion.schema.json` | Copia del contrato `contratos/identificacion.schema.json` para verificar el módulo suelto. |
| `ejemplos/campo_ejemplo/fuentes.json`, `movimiento.json`, `identificacion.json` | Copias de `contratos/ejemplos/campo_ejemplo/` para verificar el módulo suelto. |
| `pytest.ini` | Declara el nombrado en español de las pruebas cuando el módulo se ejecuta suelto. |

## Orden de ejecución

```bash
python -m modulos.m5_identificacion.consulta_catalogos <campo>
python -m modulos.m5_identificacion.cruce_posicional <campo>
```

## Verificación en aislamiento

```bash
python -m pytest modulos/m5_identificacion/pruebas -q
```

Criterio de aceptación: el comando termina con código 0 solo si se cumple todo lo siguiente.

1. Con una caché sintética, un objeto predicho a 5 segundos de arco da estado conocido.
2. Un objeto predicho a 30 segundos de arco da estado sin_identificar.
3. Una pareja no_concluyente sin coincidencia da estado artefacto_descartado.
4. La prueba termina sin abrir ninguna conexión de red.
5. El identificacion.json generado valida contra contratos/identificacion.schema.json.

La verificación no ejecuta ningún otro módulo: usa datos sintéticos o los ejemplos de `contratos/ejemplos/`.

## Nota

La tolerancia de 15 segundos de arco cubre el desplazamiento por la órbita de SPHEREx. Las respuestas de datos/m5_identificacion/cache/ van a git para que la demo no dependa de la red.

## Estado

Implementado. El comando de verificación pasa sin red, con fragmentos reales de las respuestas de los dos servicios. `consulta_catalogos.py` pregunta a MPChecker y a JPL sb_ident (dos pasos) y guarda las dos respuestas; `cruce_posicional.py` toma la coincidencia más cercana de cualquiera de los dos. Rellenar la caché cuesta unos 2 minutos por pareja por la lentitud de JPL: hacerlo con antelación.
