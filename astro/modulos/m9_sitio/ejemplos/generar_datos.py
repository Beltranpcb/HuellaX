#!/usr/bin/env python3
"""Genera datos de demostración conformes a los contratos de m7_publicacion.

Escribe en `datos/m7_publicacion/` exactamente la forma que produce
`modulos/m7_publicacion/union_candidatos.py`, para que la web (m9_sitio) se
pueda construir y probar antes de que el pipeline tenga datos reales.

Uso:
    python modulos/m9_sitio/ejemplos/generar_datos.py [--salida datos/m7_publicacion]

Los valores son ilustrativos, no observaciones. Los espectros llevan las
absorciones y emisiones que distinguen cada tipo espectral.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

VERSION_CONTRATO = "1"

# Bandas de los seis detectores de SPHEREx, en micras.
BANDAS_DETECTOR = {
    1: (0.75, 1.09),
    2: (1.10, 1.62),
    3: (1.63, 2.41),
    4: (2.42, 3.82),
    5: (3.83, 4.41),
    6: (4.42, 5.00),
}

CAMPOS = [
    {
        "campo": "slipher",
        "nombre": "Asteroide (1766) Slipher",
        "centro": {"ra_grados": 45.176, "dec_grados": 12.342},
        "detector": 2,
        "mjd_a": 60990.31,
        "horas": 6.72,
        "plantilla_mjd": 60811.4,
        "candidatos": [
            {
                "id": "p001", "estado": "conocido", "nombre": "(1766) Slipher",
                "clase": "candidata", "tipo": "asteroide_rocoso", "temperatura": 272.0,
                "separacion": 222.93, "velocidad": 33.17, "incertidumbre": 1.10,
                "distancia_catalogo": 0.42, "xa": 298, "ya": 309, "xb": 331, "yb": 324,
            },
            {
                "id": "p002", "estado": "sin_identificar", "nombre": None,
                "clase": "candidata", "tipo": "asteroide_oscuro", "temperatura": 198.0,
                "separacion": 123.80, "velocidad": 18.42, "incertidumbre": 2.80,
                "distancia_catalogo": None, "xa": 452, "ya": 220, "xb": 470, "yb": 229,
            },
            {
                "id": "p003", "estado": "artefacto_descartado", "nombre": None,
                "clase": "no_concluyente", "tipo": None, "temperatura": None,
                "separacion": 6.15, "velocidad": 0.92, "incertidumbre": 1.90,
                "distancia_catalogo": None, "xa": 140, "ya": 130, "xb": 141, "yb": 130,
            },
        ],
    },
    {
        "campo": "atlas",
        "nombre": "Cometa 3I/ATLAS",
        "centro": {"ra_grados": 120.451, "dec_grados": -20.118},
        "detector": 5,
        "mjd_a": 60900.10,
        "horas": 4.32,
        "plantilla_mjd": 60720.5,
        "candidatos": [
            {
                "id": "p001", "estado": "conocido", "nombre": "3I/ATLAS",
                "clase": "candidata", "tipo": "cometa", "temperatura": 212.0,
                "separacion": 253.30, "velocidad": 58.63, "incertidumbre": 2.00,
                "distancia_catalogo": 0.31, "xa": 280, "ya": 290, "xb": 316, "yb": 270,
            },
            {
                "id": "p002", "estado": "sin_identificar", "nombre": None,
                "clase": "candidata", "tipo": "cometa", "temperatura": 240.0,
                "separacion": 74.10, "velocidad": 17.14, "incertidumbre": 3.10,
                "distancia_catalogo": None, "xa": 410, "ya": 410, "xb": 419, "yb": 402,
            },
            {
                "id": "p003", "estado": "sin_identificar", "nombre": None,
                "clase": "no_concluyente", "tipo": "indeterminado", "temperatura": None,
                "separacion": 22.20, "velocidad": 5.13, "incertidumbre": 2.40,
                "distancia_catalogo": None, "xa": 510, "ya": 160, "xb": 513, "yb": 162,
            },
        ],
    },
    {
        "campo": "luhman",
        "nombre": "Nana marrón Luhman 16",
        "centro": {"ra_grados": 162.315, "dec_grados": -53.321},
        "detector": 4,
        "mjd_a": 60950.20,
        "horas": 12.0,
        "plantilla_mjd": 60771.1,
        "candidatos": [
            {
                "id": "p001", "estado": "conocido", "nombre": "Luhman 16 A",
                "clase": "candidata", "tipo": "enana_marron", "temperatura": 1350.0,
                "separacion": 27.50, "velocidad": 2.29, "incertidumbre": 0.40,
                "distancia_catalogo": 0.18, "xa": 305, "ya": 300, "xb": 309, "yb": 298,
            },
            {
                "id": "p002", "estado": "sin_identificar", "nombre": None,
                "clase": "candidata", "tipo": "enana_marron", "temperatura": 950.0,
                "separacion": 19.40, "velocidad": 1.62, "incertidumbre": 0.90,
                "distancia_catalogo": None, "xa": 402, "ya": 245, "xb": 405, "yb": 244,
            },
            {
                "id": "p003", "estado": "artefacto_descartado", "nombre": None,
                "clase": "no_concluyente", "tipo": None, "temperatura": None,
                "separacion": 0.0, "velocidad": 0.0, "incertidumbre": 1.70,
                "distancia_catalogo": None, "xa": 215, "ya": 420, "xb": 215, "yb": 420,
            },
        ],
    },
]

PLANTILLAS = ["asteroide_rocoso", "asteroide_oscuro", "cometa", "enana_marron"]
# Clase catalogada de demostración, solo para objetos «conocidos» (en el pipeline real la da m5).
CLASE_DEMO = {"asteroide_rocoso": "asteroide", "asteroide_oscuro": "asteroide", "cometa": "cometa", "enana_marron": "enana_marron"}


def flujo(tipo: str, lam: float) -> float:
    """Flujo relativo de cada plantilla, con sus rasgos espectrales."""
    if tipo == "asteroide_rocoso":
        valor = 0.85 + 0.45 * (lam - 0.75)
        if 0.90 < lam < 1.05:
            valor *= 0.72          # silicatos
        if 1.90 < lam < 2.10:
            valor *= 0.80
    elif tipo == "asteroide_oscuro":
        valor = 0.62 + 0.04 * (lam - 0.75)
        if 2.90 < lam < 3.15:
            valor *= 0.82          # hidratación
    elif tipo == "cometa":
        valor = 0.55 + 0.10 * (lam - 0.75)
        if 2.70 < lam < 3.00:
            valor *= 1.25          # hielo de agua
        if 4.15 < lam < 4.35:
            valor *= 2.10          # CO2
        if 4.60 < lam < 4.75:
            valor *= 1.55          # CO
    elif tipo == "enana_marron":
        valor = 1.25 * math.exp(-0.35 * (lam - 0.75))
        if 3.20 < lam < 3.45:
            valor *= 0.42          # metano
    else:
        valor = 0.9
    return max(valor, 0.01)


def ajustar(plantilla: str, puntos: list[dict]) -> dict:
    """Ajuste por mínimos cuadrados de la plantilla (escala libre), como hace m6 con datos reales."""
    modelo = [flujo(plantilla, p["longitud_onda_micras"]) for p in puntos]
    pesos = [1.0 / p["error_mjy"] ** 2 for p in puntos]
    escala = sum(w * m * p["flujo_mjy"] for w, m, p in zip(pesos, modelo, puntos)) / sum(w * m * m for w, m in zip(pesos, modelo))
    chi2 = sum(((p["flujo_mjy"] - escala * m) / p["error_mjy"]) ** 2 for m, p in zip(modelo, puntos))
    gl = len(puntos) - 1
    return {
        "tipo": plantilla, "chi2_reducido": round(chi2 / gl, 3), "grados_libertad": gl, "n_puntos": len(puntos),
        "escala": round(escala, 5), "origen_plantilla": "sintetica", "referencia_plantilla": None,
    }


def plantillas_publicadas() -> dict:
    """plantillas.json de demostración: las mismas curvas que generan los espectros."""
    lam = [round(0.75 + i * (4.25 / 89), 4) for i in range(90)]
    etiquetas = {"asteroide_rocoso": "Roca con silicatos", "asteroide_oscuro": "Cuerpo primitivo oscuro",
                 "cometa": "Hielo y CO2", "enana_marron": "Enana marrón con metano"}
    return {
        "_comentario": "Plantillas de demostración (sintéticas). No son espectros de referencia medidos.",
        "version_contrato": VERSION_CONTRATO,
        "plantillas": [{"tipo": p, "etiqueta_publica": etiquetas[p], "origen_plantilla": "sintetica", "referencia": None,
                        "longitud_onda_micras": lam, "flujo_normalizado": [round(flujo(p, x), 4) for x in lam]}
                       for p in PLANTILLAS],
    }


def detector_de(lam: float) -> int:
    for numero, (bajo, alto) in BANDAS_DETECTOR.items():
        if bajo <= lam <= alto:
            return numero
    return 6


def espectro(cand: dict, mjd: float) -> dict | None:
    tipo = cand["tipo"]
    if tipo is None:
        return None

    puntos = []
    for i in range(60):
        lam = 0.75 + i * (4.25 / 59)
        base = flujo(tipo, lam)
        ruido = math.sin(i * 2.399) * 0.025  # ruido reproducible
        puntos.append({
            "longitud_onda_micras": round(lam, 4),
            "flujo_mjy": round(base * (1 + ruido), 4),
            "error_mjy": round(max(base * 0.06, 0.01), 4),
            "mjd": mjd,
            "detector": detector_de(lam),
        })

    temperaturas = cand["temperatura"]
    ajustes = [ajustar(plantilla, puntos) for plantilla in PLANTILLAS]

    return {
        "id_pareja": cand["id"],
        "origen": "sintetico",
        "advertencias": ["plantillas_sinteticas"],
        "agrupacion": "banda",
        "puntos": puntos,
        "tipo": tipo,
        "ajustes_plantilla": ajustes,
        "temperatura_k": temperaturas,
        "incertidumbre_temperatura_k": round(temperaturas * 0.08, 1) if temperaturas else None,
        "pico_wien_micras": round(2898.0 / temperaturas, 2) if temperaturas else None,
    }


def wcs_de(campo: dict, ancho: int, alto: int, escala: float) -> dict:
    """WCS TAN de demostración: centro del campo en el centro de la rejilla, norte arriba, este a la izquierda."""
    grados = escala / 3600.0
    return {"proyeccion": "TAN", "crval_ra_grados": campo["centro"]["ra_grados"],
            "crval_dec_grados": campo["centro"]["dec_grados"],
            "crpix_x": (ancho - 1) / 2.0, "crpix_y": (alto - 1) / 2.0, "cd": [[-grados, 0.0], [0.0, grados]]}


def cielo(wcs: dict, x: float, y: float) -> tuple[float, float]:
    """Proyección gnomónica inversa (la misma que usa la web), para que las posiciones casen con el WCS."""
    dx, dy = x - wcs["crpix_x"], y - wcs["crpix_y"]
    xi = math.radians(wcs["cd"][0][0] * dx + wcs["cd"][0][1] * dy)
    eta = math.radians(wcs["cd"][1][0] * dx + wcs["cd"][1][1] * dy)
    a0, d0 = math.radians(wcs["crval_ra_grados"]), math.radians(wcs["crval_dec_grados"])
    den = math.cos(d0) - eta * math.sin(d0)
    ra = a0 + math.atan2(xi, den)
    dec = math.atan2(math.sin(d0) + eta * math.cos(d0), math.hypot(xi, den))
    return round(math.degrees(ra) % 360.0, 6), round(math.degrees(dec), 6)


def construir(campo: dict) -> tuple[dict, dict, dict]:
    ancho = alto = 600
    escala = 6.15
    mjd_a = campo["mjd_a"]
    mjd_b = round(mjd_a + campo["horas"] / 24.0, 5)
    wcs = wcs_de(campo, ancho, alto, escala)

    meta = {
        "_comentario": "Datos de demostración generados por m9_sitio/ejemplos/generar_datos.py.",
        "version_contrato": VERSION_CONTRATO,
        "origen": "sintetico",
        "wcs": wcs,
        "campo": campo["campo"],
        "nombre": campo["nombre"],
        "centro": campo["centro"],
        "detector": campo["detector"],
        "escala_segarc_por_pixel": escala,
        "tamano_pixeles": {"ancho": ancho, "alto": alto},
        "epocas": {
            "epoca_a": {"id_exposicion": f"{campo['campo']}_A", "mjd": mjd_a},
            "epoca_b": {"id_exposicion": f"{campo['campo']}_B", "mjd": mjd_b},
            "plantilla": {
                "id_exposicion": f"{campo['campo']}_T",
                "mjd": campo["plantilla_mjd"],
            },
        },
        "horas_entre_a_b": campo["horas"],
        "imagenes": {
            "epoca_a": "epoca_a.png",
            "epoca_b": "epoca_b.png",
            "diferencia": "diferencia.png",
        },
    }

    candidatos = []
    espectros = []
    for cand in campo["candidatos"]:
        esp = espectro(cand, mjd_a)
        if esp:
            espectros.append(esp)

        candidatos.append({
            "id_candidato": cand["id"],
            "estado": cand["estado"],
            "nombre_objeto": cand["nombre"],
            "distancia_catalogo_segarc": cand["distancia_catalogo"],
            "clase_movimiento": cand["clase"],
            "posicion_a": {
                "ra_grados": cielo(wcs, cand["xa"], cand["ya"])[0],
                "dec_grados": cielo(wcs, cand["xa"], cand["ya"])[1],
                "x": cand["xa"],
                "y": cand["ya"],
                "mjd": mjd_a,
            },
            "posicion_b": {
                "ra_grados": cielo(wcs, cand["xb"], cand["yb"])[0],
                "dec_grados": cielo(wcs, cand["xb"], cand["yb"])[1],
                "x": cand["xb"],
                "y": cand["yb"],
                "mjd": mjd_b,
            },
            "separacion_segarc": cand["separacion"],
            "velocidad_segarc_por_hora": cand["velocidad"],
            "incertidumbre_velocidad": cand["incertidumbre"],
            "significancia": round(cand["velocidad"] / cand["incertidumbre"], 1),
            "tiene_espectro": esp is not None,
            "tipo": cand["tipo"],
            "temperatura_k": esp["temperatura_k"] if esp else None,
            "clase_objeto": CLASE_DEMO.get(cand["tipo"]) if cand["estado"] == "conocido" else None,
        })

    candidatos_doc = {
        "_comentario": "Cada entrada es una pareja A-B verificada contra catálogos, no un descubrimiento.",
        "version_contrato": VERSION_CONTRATO,
        "campo": campo["campo"],
        "candidatos": candidatos,
    }

    espectros_doc = {
        "_comentario": "Huella espectral de cada pareja medida.",
        "version_contrato": VERSION_CONTRATO,
        "campo": campo["campo"],
        "espectros": espectros,
    }

    return meta, candidatos_doc, espectros_doc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", default="datos/m7_publicacion",
                        help="directorio de publicación (por defecto datos/m7_publicacion)")
    args = parser.parse_args()

    raiz = Path(args.salida)
    raiz.mkdir(parents=True, exist_ok=True)

    indice = []
    for campo in CAMPOS:
        meta, candidatos, espectros = construir(campo)
        destino = raiz / campo["campo"]
        destino.mkdir(parents=True, exist_ok=True)
        for nombre, contenido in (
            ("meta.json", meta),
            ("candidatos.json", candidatos),
            ("espectros.json", espectros),
        ):
            (destino / nombre).write_text(
                json.dumps(contenido, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        indice.append({
            "campo": campo["campo"],
            "nombre": campo["nombre"],
            "ruta": campo["campo"],
            "numero_candidatos": len(candidatos["candidatos"]),
        })
        print(f"  {campo['campo']}: {len(candidatos['candidatos'])} candidatos, "
              f"{len(espectros['espectros'])} espectros")

    (raiz / "plantillas.json").write_text(
        json.dumps(plantillas_publicadas(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    campos_doc = {
        "_comentario": "Índice de los campos publicados.",
        "version_contrato": VERSION_CONTRATO,
        "campos": indice,
    }
    (raiz / "campos.json").write_text(
        json.dumps(campos_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"campos.json escrito en {raiz}/")


if __name__ == "__main__":
    main()
