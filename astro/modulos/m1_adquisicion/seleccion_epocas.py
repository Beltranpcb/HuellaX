# ============================================================================
# ARCHIVO: modulos/m1_adquisicion/seleccion_epocas.py
# MODULO: m1_adquisicion (Lote A)
# ROL: Elige qué exposiciones cumplen cada papel del contrato de selección.
# LEE: listado_exposiciones.json.
# PRODUCE: datos/m1_adquisicion/<campo>/seleccion.json.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de consulta_sia.py: listado_exposiciones.json.
#   1. Agrupar por detector  ->  grupos por detector
#   2. Elegir época A, época B separadas horas o días  ->  pareja A-B
#   3. Elegir la plantilla de la otra pasada  ->  trío del mismo detector
#   4. Añadir la serie espectral de todos los detectores  ->  seleccion.json
#   Entrega a descarga_recortes.py, m2, m6: seleccion.json.
# VERIFICACION: El archivo valida contra contratos/seleccion.schema.json con un único epoca_a, un único epoca_b, una única plantilla.
# ESTADO: Esqueleto sin código. Este archivo solo documenta el trabajo pendiente.
# ============================================================================
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from modulos.m1_adquisicion.consulta_sia import DIR_DATOS

# Criterios de aceptación del módulo (LEEME.md)
SEPARACION_MIN_H = 0.5      # época A y B: al menos media hora
SEPARACION_MAX_H = 72.0     # ... y como mucho 72 horas
PLANTILLA_MIN_DIAS = 120.0  # la plantilla dista más de 120 días de A (y de B)

# Preferencias dentro de lo permitido (valores iniciales por calibrar)
SEPARACION_OBJETIVO_H = 6.0       # un asteroide a ~30"/h recorre ~29 px en 6 h y sigue en el campo
PLANTILLA_OBJETIVO_DIAS = 180.0   # "la otra pasada": unos seis meses
MARGEN_SERIE_H = 12.0             # la serie espectral abarca de A-margen a B+margen


class SeleccionImposible(ValueError):
    """Ningún detector tiene una pareja A-B y una plantilla que cumplan los criterios."""


def _dias(horas: float) -> float:
    return horas / 24.0


def _mejor_plantilla(exposiciones: list[dict], a: dict, b: dict) -> dict | None:
    """La exposición más cercana a 180 días de A, que diste más de 120 días de A y de B."""
    mejor, mejor_puntuacion = None, None
    for p in exposiciones:
        d_a = abs(p["t_min"] - a["t_min"])
        d_b = abs(p["t_min"] - b["t_min"])
        if d_a <= PLANTILLA_MIN_DIAS or d_b <= PLANTILLA_MIN_DIAS:
            continue
        puntuacion = abs(d_a - PLANTILLA_OBJETIVO_DIAS)
        if mejor_puntuacion is None or puntuacion < mejor_puntuacion:
            mejor, mejor_puntuacion = p, puntuacion
    return mejor


def elegir_trio(exposiciones: list[dict]) -> tuple[dict, dict, dict]:
    """Devuelve (época A, época B, plantilla).

    A y B son siempre del mismo detector. La plantilla se busca primero en ese
    detector; si esa pasada no tiene ninguna exposición a más de 120 días —lo
    habitual en DR1, donde un campo se visita una vez cada seis meses y no
    siempre con el mismo detector— se acepta la de otro detector. La plantilla
    solo sirve para identificar las estrellas fijas, así que sirve igual; quien
    lea `seleccion.json` puede verlo comparando el campo `detector` de cada
    exposición.
    """
    por_detector: dict[int, list[dict]] = defaultdict(list)
    for e in exposiciones:
        por_detector[e["detector"]].append(e)

    candidatos = []
    for detector, lista in por_detector.items():
        lista.sort(key=lambda e: e["t_min"])
        otros = [e for e in exposiciones if e["detector"] != detector]
        for i, a in enumerate(lista):
            for b in lista[i + 1:]:
                separacion_h = (b["t_min"] - a["t_min"]) * 24.0
                if separacion_h > SEPARACION_MAX_H:
                    break  # la lista está ordenada: el resto queda aún más lejos
                if separacion_h < SEPARACION_MIN_H:
                    continue
                plantilla = _mejor_plantilla(lista, a, b) or _mejor_plantilla(otros, a, b)
                if plantilla is None:
                    continue
                puntuacion = (
                    abs(separacion_h - SEPARACION_OBJETIVO_H),
                    abs(abs(plantilla["t_min"] - a["t_min"]) - PLANTILLA_OBJETIVO_DIAS),
                    detector,
                    a["t_min"],
                )
                candidatos.append((puntuacion, a, b, plantilla))

    if not candidatos:
        raise SeleccionImposible(_diagnostico(por_detector))
    _, a, b, plantilla = min(candidatos, key=lambda c: c[0])
    return a, b, plantilla


def _diagnostico(por_detector: dict[int, list[dict]]) -> str:
    """Explica por qué no hay trío, detector a detector, para decidir si hay que cambiar de campo."""
    lineas = [
        "Ningún detector tiene una pareja A-B "
        f"({SEPARACION_MIN_H} a {SEPARACION_MAX_H} h)"
        f" con una plantilla a más de {PLANTILLA_MIN_DIAS:.0f} días de A y de B"
        " (la plantilla puede ser de otro detector)."
    ]
    for detector in sorted(por_detector):
        tiempos = sorted(e["t_min"] for e in por_detector[detector])
        lineas.append(
            f"  detector {detector}: {len(tiempos)} exposiciones, "
            f"MJD {tiempos[0]:.2f} a {tiempos[-1]:.2f} (abarcan {tiempos[-1] - tiempos[0]:.1f} días)"
        )
    return "\n".join(lineas)


def _sin_parametros_de_recorte(url: str) -> str:
    """Quita `center` y `size` de la URL, y conserva el resto de la consulta.

    Las exposiciones de SPHEREx son DataLink (`.../links/spherex?ID=...`): si se
    borrara la consulta entera, la exposición dejaría de identificarse.
    """
    partes = urlsplit(url)
    consulta = [
        (clave, valor)
        for clave, valor in parse_qsl(partes.query, keep_blank_values=True)
        if clave.lower() not in {"center", "size"}
    ]
    return urlunsplit((partes.scheme, partes.netloc, partes.path, urlencode(consulta), ""))


def _entrada(exposicion: dict, papel: str) -> dict:
    return {
        "id_exposicion": exposicion["identificador"],
        "papel": papel,
        "mjd": exposicion["t_min"],
        "detector": exposicion["detector"],
        "coleccion": exposicion["coleccion"],
        "url_acceso": _sin_parametros_de_recorte(exposicion["access_url"]),
        "archivo_recorte": f"{exposicion['identificador']}.fits",
    }


def seleccionar(listado: dict) -> dict:
    """listado_exposiciones.json -> seleccion.json (contrato seleccion). No usa la red."""
    exposiciones = listado["exposiciones"]
    a, b, plantilla = elegir_trio(exposiciones)

    elegidas = {a["identificador"], b["identificador"], plantilla["identificador"]}
    inicio = a["t_min"] - _dias(MARGEN_SERIE_H)
    fin = b["t_min"] + _dias(MARGEN_SERIE_H)
    serie = sorted(
        (e for e in exposiciones if e["identificador"] not in elegidas and inicio <= e["t_min"] <= fin),
        key=lambda e: (e["t_min"], e["detector"]),
    )

    return {
        "version_contrato": "1",
        "campo": listado["campo"],
        "nombre": listado["nombre"],
        "centro": listado["centro"],
        "radio_grados": listado["radio_grados"],
        "exposiciones": (
            [_entrada(a, "epoca_a"), _entrada(b, "epoca_b"), _entrada(plantilla, "plantilla")]
            + [_entrada(e, "serie_espectral") for e in serie]
        ),
    }


def escribir_seleccion(seleccion: dict, dir_datos: Path = DIR_DATOS) -> Path:
    destino = dir_datos / seleccion["campo"] / "seleccion.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(seleccion, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return destino


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Elige época A, época B, plantilla y serie espectral de un campo.")
    parser.add_argument("campo", help="identificador del campo")
    args = parser.parse_args(argv)
    ruta = DIR_DATOS / args.campo / "listado_exposiciones.json"
    if not ruta.exists():
        print(f"ERROR: falta {ruta}. Ejecuta antes consulta_sia.", file=sys.stderr)
        return 1
    with open(ruta, encoding="utf-8") as f:
        listado = json.load(f)
    try:
        seleccion = seleccionar(listado)
    except SeleccionImposible as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    destino = escribir_seleccion(seleccion)
    a, b, t = seleccion["exposiciones"][:3]
    print(
        f"detector {a['detector']}: A={a['id_exposicion']}, B a {(b['mjd'] - a['mjd']) * 24:.1f} h, "
        f"plantilla a {abs(t['mjd'] - a['mjd']):.0f} d; "
        f"{len(seleccion['exposiciones']) - 3} de serie espectral -> {destino}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
