<!--
  ARCHIVO: modulos/m6_huella_espectral/LEEME.md
  ROL: Describe el módulo junto a su comando de verificación.
  LEE: Nada.
  PRODUCE: La ficha que consulta quien desarrolla o revisa el módulo.
  VERIFICACION: Cada archivo citado aquí existe en el directorio del módulo.
-->

# m6_huella_espectral

**Lote C** · 10 horas estimadas · capa 4 del grafo

Construir el espectro infrarrojo de cada objeto en movimiento para estimar su naturaleza.

## Entradas

- datos/m1_adquisicion/&lt;campo&gt;/seleccion.json
- datos/m1_adquisicion/&lt;campo&gt;/recortes/*.fits
- datos/m3_deteccion/&lt;campo&gt;/fuentes.json
- datos/m4_movimiento/&lt;campo&gt;/movimiento.json

## Salidas

- datos/m6_huella_espectral/&lt;campo&gt;/espectros.json (contrato espectros)

## Depende de

`m1_adquisicion`, `m3_deteccion`, `m4_movimiento` (solo a través de sus archivos de datos).

## Archivos

| Archivo | Responsabilidad única |
|---|---|
| `LEEME.md` | Describe el módulo junto a su comando de verificación. |
| `trayectoria.py` | Predice dónde está el objeto en el instante de cada exposición. |
| `fotometria.py` | Mide el flujo del objeto en cada exposición de la serie espectral. |
| `plantillas.json` | Contiene los espectros de referencia de los cuatro tipos de objeto. |
| `comparacion_plantillas.py` | Asigna al espectro medido el tipo de la plantilla más parecida. |
| `ajuste_planck.py` | Estima la temperatura del objeto ajustando la ley de Planck. |
| `identificacion_molecular.py` | Evalúa banda por banda rasgos de H2O, CH4, CO2, CO y NH3 con estados sin_rasgo, compatible, candidata, detectada o datos_insuficientes. |
| `escritura_espectros.py` | Reúne medida, tipo, temperatura en el archivo del contrato. |
| `pruebas/prueba_huella_espectral.py` | Comprueba el ajuste espectral sobre espectros sintéticos. |
| `esquemas/espectros.schema.json` | Copia del contrato `contratos/espectros.schema.json` para verificar el módulo suelto. |
| `ejemplos/campo_ejemplo/seleccion.json`, `fuentes.json`, `movimiento.json`, `espectros.json` | Copias de `contratos/ejemplos/campo_ejemplo/` para verificar el módulo suelto. |
| `pytest.ini` | Declara el nombrado en español de las pruebas cuando el módulo se ejecuta suelto. |

## Orden de ejecución

```bash
python -m modulos.m6_huella_espectral.trayectoria <campo>
python -m modulos.m6_huella_espectral.fotometria <campo>
python -m modulos.m6_huella_espectral.comparacion_plantillas <campo>
python -m modulos.m6_huella_espectral.ajuste_planck <campo>
python -m modulos.m6_huella_espectral.identificacion_molecular <campo>
python -m modulos.m6_huella_espectral.escritura_espectros <campo>
```

## Verificación en aislamiento

```bash
python -m pytest modulos/m6_huella_espectral/pruebas -q
```

Criterio de aceptación: el comando termina con código 0 solo si se cumple todo lo siguiente.

1. Un cuerpo negro sintético de 300 K se recupera con una temperatura entre 270 y 330 K.
2. Un espectro sintético con un pico de emisión en 4,26 micras recibe el tipo cometa.
3. Un espectro de ruido puro recibe el tipo indeterminado.
4. El espectros.json generado valida contra contratos/espectros.schema.json.

La verificación no ejecuta ningún otro módulo: usa datos sintéticos o los ejemplos de `contratos/ejemplos/`.

## Nota

Si el espectro de un objeto móvil sale ruidoso se publica con agrupacion igual a detector (6 puntos), dicho con transparencia en la web.

## Estado

Implementado. Los cinco comandos de arriba se ejecutan en orden y la verificación
pasa con `python -m pytest modulos/m6_huella_espectral/pruebas -q`.

Las curvas de `plantillas.json` son sintéticas: reproducen los rasgos de la
especificación (silicatos, hidratación, hielo de agua, CO₂, CO, metano), no son
espectros de referencia medidos. Sirven para comparar formas y deben sustituirse
por curvas de bibliografía antes de publicar.

## Composición molecular (identificacion_molecular.py)

Una ventana por molécula dentro de 0,75-5 µm (H2O 2,85-3,15; CH4 3,20-3,45; CO2 4,20-4,33;
CO 4,55-4,75; NH3 2,17-2,27), orientativa y con su referencia. El continuo es local: un polinomio
de grado 2 con los 6 puntos más cercanos a cada lado que no caen en ninguna banda (hasta 0,8 µm;
si una banda vecina tapa el flanco, se salta). Un continuo global confunde la curvatura térmica
con un rasgo. El rasgo es la media pesada de F - C dentro de la banda,
con el error del continuo sumado entero (está correlacionado entre puntos). La métrica es la
significancia S en sigmas, con un grado de libertad.

| Estado | Regla |
|---|---|
| `datos_insuficientes` | Espectro promediado por detector, menos de 8 puntos, sin continuo a los dos lados de la banda o menos de 2 puntos dentro. |
| `sin_rasgo` | abs(S) < 2: no confirma ni descarta la molécula. |
| `compatible` | 2 ≤ abs(S) < 3. |
| `candidata` | 3 ≤ abs(S) < 5, o abs(S) ≥ 5 sin cumplir todo lo de abajo. |
| `detectada` | abs(S) ≥ 5 también con una recta y 3 puntos a cada lado, ≥ 3 puntos, banda de ≥ 2 elementos de resolución, sentido esperado para el tipo (emisión en cometas para H2O, CO2 y CO; absorción en el resto) y ninguna alternativa física para ese tipo. |

Alternativas consideradas: minerales hidratados (OH) para H2O en asteroides, hidrocarburos C-H para
CH4 en cometas, la banda de CH4 a 2,3 µm para NH3. Con tipo indeterminado nada pasa de candidata.
La resolución es la nominal de SPHEREx (R ≈ 41 hasta 2,4 µm, 35 hasta 3,8, 110 hasta 4,4 y 130 hasta 5).
No se interpola para ganar resolución.

Calibración con espectros sintéticos sin rasgos (continuo lineal, térmico y de luz reflejada; 80 a 120
puntos; tres tipos de objeto): S tiene desviación típica 0,95-1,1, como debe, y **ningún** espectro da
`detectada`. Con cinco bandas evaluadas a 3 sigmas, alrededor del 1-3 % de los espectros sin rasgos
muestra una `candidata` por azar: por eso `candidata` no es una detección.

Límite conocido: el CO (4,55-4,75 µm) necesita 6 puntos libres entre 4,80 y 5,0 µm para su continuo;
con el muestreo nominal suele quedar en `datos_insuficientes`. No se relaja el requisito porque con 4
puntos por flanco aparecen candidatas falsas en el 10 % de los espectros.

Datos de demostración: `--anotar` añade la composición a un `espectros.json` ya publicado
(`python -m modulos.m6_huella_espectral.identificacion_molecular --anotar datos/m7_publicacion`). En el
pipeline real la composición llega por `escritura_espectros.py`.

La validación con observaciones reales está pendiente.
