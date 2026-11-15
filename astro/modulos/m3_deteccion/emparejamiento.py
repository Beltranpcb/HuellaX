# ============================================================================
# ARCHIVO: modulos/m3_deteccion/emparejamiento.py
# MODULO: m3_deteccion (Lote B)
# ROL: Separa las fuentes estacionarias de las fuentes huérfanas.
# LEE: detecciones.json.
# PRODUCE: datos/m3_deteccion/<campo>/situaciones.json (intermedio interno).
# FUNCIONAMIENTO PREVISTO:
#   Recibe de deteccion_fuentes.py: detecciones.json.
#   1. Emparejar por posición en la rejilla común entre A, B, plantilla  ->  coincidencias
#   2. Marcar estacionaria toda fuente fija en las tres imágenes  ->  fuentes estacionarias
#   3. Marcar huérfana toda fuente sin coincidencia  ->  situaciones.json
#   Entrega a propuesta_parejas.py: situaciones.json.
# VERIFICACION: Toda fuente recibe una situacion; ninguna fuente presente a menos de 1 píxel en las tres imágenes queda como huérfana.
# USO: python -m modulos.m3_deteccion.emparejamiento <campo>
# ============================================================================
import json
import sys
from pathlib import Path

import numpy as np

EPOCAS = ("epoca_a", "epoca_b", "plantilla")
TOLERANCIA_PIXELES = 1.0  # las tres imágenes comparten la rejilla de la época A (contrato alineados_fits)


def emparejar_imagenes(origen, destino, tolerancia=TOLERANCIA_PIXELES):
    """Para cada fuente de `origen`, la fuente de `destino` más cercana a menos de `tolerancia` píxeles.

    Devuelve un dict id_fuente_origen -> id_fuente_destino (o None). Cada fuente de destino
    se asigna como mucho una vez: gana la pareja más cercana.
    """
    resultado = {f["id_fuente"]: None for f in origen}
    if not origen or not destino:
        return resultado
    xo = np.array([[f["x"], f["y"]] for f in origen])
    xd = np.array([[f["x"], f["y"]] for f in destino])
    distancias = np.hypot(xo[:, None, 0] - xd[None, :, 0], xo[:, None, 1] - xd[None, :, 1])
    candidatas = sorted(((distancias[i, j], i, j) for i in range(len(origen)) for j in range(len(destino))
                         if distancias[i, j] <= tolerancia))
    usadas_origen, usadas_destino = set(), set()
    for _, i, j in candidatas:
        if i in usadas_origen or j in usadas_destino:
            continue
        resultado[origen[i]["id_fuente"]] = destino[j]["id_fuente"]
        usadas_origen.add(i)
        usadas_destino.add(j)
    return resultado


def clasificar(detecciones, tolerancia=TOLERANCIA_PIXELES):
    """Asigna a cada detección su situación. Devuelve la lista de fuentes con `situacion` y `coincidencias`.

    - descartada: la fuente toca píxeles marcados en FLAGS.
    - estacionaria: tiene una coincidencia a menos de `tolerancia` píxeles en otra imagen.
    - huerfana: no coincide con ninguna otra imagen.
    """
    por_epoca = {e: [d for d in detecciones if d["epoca"] == e and not d.get("toca_mascara")] for e in EPOCAS}
    coincidencias = {d["id_fuente"]: {e: None for e in EPOCAS} for d in detecciones}
    for e1 in EPOCAS:
        for e2 in EPOCAS:
            if e1 == e2:
                continue
            for ido, idd in emparejar_imagenes(por_epoca[e1], por_epoca[e2], tolerancia).items():
                coincidencias[ido][e2] = idd
    fuentes = []
    for d in detecciones:
        c = coincidencias[d["id_fuente"]]
        c[d["epoca"]] = d["id_fuente"]
        if d.get("toca_mascara"):
            situacion = "descartada"
        elif any(c[e] for e in EPOCAS if e != d["epoca"]):
            situacion = "estacionaria"
        else:
            situacion = "huerfana"
        fuente = {k: v for k, v in d.items() if k != "toca_mascara"}
        fuente["situacion"] = situacion
        fuente["coincidencias"] = c
        fuentes.append(fuente)
    return fuentes


def emparejar_campo(campo, raiz_datos="datos"):
    """Lee detecciones.json del campo y escribe situaciones.json. Devuelve su ruta."""
    directorio = Path(raiz_datos) / "m3_deteccion" / campo
    datos = json.loads((directorio / "detecciones.json").read_text(encoding="utf-8"))
    fuentes = clasificar(datos["detecciones"])
    ruta = directorio / "situaciones.json"
    ruta.write_text(json.dumps({"campo": campo, "fuentes": fuentes}, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m3_deteccion.emparejamiento <campo>")
    ruta_escrita = emparejar_campo(sys.argv[1])
    fuentes_escritas = json.loads(ruta_escrita.read_text(encoding="utf-8"))["fuentes"]
    recuento = {s: sum(f["situacion"] == s for f in fuentes_escritas) for s in ("estacionaria", "huerfana", "descartada")}
    print("%s: %s" % (ruta_escrita, recuento))
