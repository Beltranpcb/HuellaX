<!--
  ARCHIVO: contratos/guia_visual.md
  ROL: Fija los colores con las tipografías comunes a las dos páginas.
  LEE: Nada.
  PRODUCE: La regla que cumplen productor con consumidores.
  VERIFICACION: Descrita en el último apartado de este archivo.
-->
# Contrato: guía visual

| Dato | Valor |
|---|---|
| Productor | El equipo, en la hora 0 |
| Consumidores | `m9_sitio/estilo.css` |
| Regla | Cada `estilo.css` copia estas variables. Ningún módulo enlaza la hoja de estilo de otro. |

## Variables obligatorias

| Variable CSS | Valor | Uso |
|---|---|---|
| `--fondo` | `#0B0F1A` | Fondo de página, azul casi negro |
| `--acento` | `#FFB347` | Botones con la X del logotipo, ámbar |
| `--acierto` | `#4ADE80` | Lo que aparece, verde menta |
| `--fallo` | `#F87171` | Lo que desaparece, coral |
| `--texto` | `#E6EAF2` | Texto principal |
| `--texto_secundario` | `#8B95A7` | Texto secundario |

## Tipografías

- Títulos con cifras: Space Grotesk.
- Texto: Inter.

## Reglas de aspecto

- Un solo color de acento.
- Márgenes iguales en todas las pantallas.
- Sin fondos de estrellas decorativos: la imagen real del cielo es la protagonista.
- El color nunca es la única señal: `--acierto` y `--fallo` van siempre acompañados de un icono o un texto.

## Verificación

Buscar las seis variables en cada `estilo.css`: los seis valores coinciden con esta tabla.
