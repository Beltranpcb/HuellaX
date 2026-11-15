# ============================================================================
# ARCHIVO: modulos/m2_alineacion/metadatos_campo.py
# MODULO: m2_alineacion (Lote A)
# ROL: Escribe meta.json con los datos del campo alineado.
# LEE: Cabeceras de los FITS alineados; seleccion.json.
# PRODUCE: datos/m2_alineacion/<campo>/meta.json.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de reproyeccion.py: FITS alineados.
#   1. Leer fechas MJD, detector, tamaño de las cabeceras  ->  datos de las épocas
#   2. Leer nombre, centro de seleccion.json  ->  identidad del campo
#   3. Calcular las horas entre A, B  ->  meta.json
#   4. Publicar el WCS (TAN, base 0) y el origen real si los FITS vienen de IRSA  ->  wcs, origen
# VERIFICACION: El archivo valida contra contratos/meta.schema.json; horas_entre_a_b coincide con la resta de las dos fechas MJD.
# USO: python -m modulos.m2_alineacion.metadatos_campo <campo>
# ============================================================================
import json
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_area

PAPELES = ("epoca_a", "epoca_b", "plantilla")
IMAGENES = {"epoca_a": "epoca_a.png", "epoca_b": "epoca_b.png", "diferencia": "diferencia.png"}


def escala_segarc_por_pixel(cabecera_imagen):
    """Lado de un píxel en segundos de arco, a partir del WCS celeste."""
    return float(np.sqrt(proj_plane_pixel_area(WCS(cabecera_imagen).celestial))) * 3600.0


def leer_cabeceras(ruta_fits):
    """(cabecera primaria, cabecera de IMAGE, forma de IMAGE) de un FITS alineado."""
    with fits.open(ruta_fits) as h:
        return h[0].header.copy(), h["IMAGE"].header.copy(), h["IMAGE"].data.shape


def wcs_publicable(cabecera_imagen):
    """WCS de la rejilla alineada en la forma del contrato (TAN, píxeles base 0); None si no es TAN.

    La web lo usa para convertir un clic en RA/DEC; si no hay WCS utilizable, la web no inventa coordenadas.
    """
    w = WCS(cabecera_imagen).celestial
    if not (w.wcs.ctype[0].endswith("-TAN") and w.wcs.ctype[1].endswith("-TAN")):
        return None
    cd = w.pixel_scale_matrix  # grados por píxel, incluye CDELT y PC
    return {"proyeccion": "TAN",
            "crval_ra_grados": float(w.wcs.crval[0]) % 360.0, "crval_dec_grados": float(w.wcs.crval[1]),
            "crpix_x": float(w.wcs.crpix[0]) - 1.0, "crpix_y": float(w.wcs.crpix[1]) - 1.0,
            "cd": [[float(cd[0, 0]), float(cd[0, 1])], [float(cd[1, 0]), float(cd[1, 1])]]}


def origen_de(seleccion):
    """real si todas las exposiciones se descargaron de IRSA; None (no declarado) en otro caso."""
    urls = [e.get("url_acceso", "") for e in seleccion.get("exposiciones", [])]
    return "real" if urls and all("irsa.ipac.caltech.edu" in u for u in urls) else None


def construir_meta(seleccion, cabeceras):
    """Monta meta.json según contratos/meta.schema.json. `cabeceras` = {papel: (primaria, imagen, forma)}."""
    detectores = {p: int(cabeceras[p][0]["DETECTOR"]) for p in PAPELES}
    if detectores["epoca_a"] != detectores["epoca_b"]:
        raise ValueError(
            "las épocas A y B deben ser del mismo detector (es lo que mide el "
            "movimiento); hay %s" % detectores
        )
    if detectores["plantilla"] != detectores["epoca_a"]:
        # DR1 no siempre tiene una visita lejana del mismo detector. La plantilla
        # solo sirve para identificar las estrellas fijas, así que se acepta la de
        # otro detector, avisando: cambia la banda, no la posición de las estrellas.
        print(
            "AVISO: la plantilla es del detector %d y las épocas del %d; "
            "se usa igualmente para restar estrellas fijas."
            % (detectores["plantilla"], detectores["epoca_a"]),
            file=sys.stderr,
        )
    formas = {cabeceras[p][2] for p in PAPELES}
    if len(formas) != 1:
        raise ValueError("los FITS alineados no comparten forma: %s" % formas)
    alto, ancho = cabeceras["epoca_a"][2]
    mjd = {p: float(cabeceras[p][0]["MJD-OBS"]) for p in PAPELES}
    horas = (mjd["epoca_b"] - mjd["epoca_a"]) * 24.0
    if horas <= 0:
        raise ValueError("la época B (MJD %s) debe ser posterior a la época A (MJD %s)" % (mjd["epoca_b"], mjd["epoca_a"]))
    meta = {
        "_comentario": "Generado por m2_alineacion. Rejilla de la época A; x, y con origen en la esquina inferior izquierda.",
        "version_contrato": "1",
        "campo": seleccion["campo"],
        "nombre": seleccion["nombre"],
        "centro": {"ra_grados": seleccion["centro"]["ra_grados"], "dec_grados": seleccion["centro"]["dec_grados"]},
        "detector": detectores["epoca_a"],
        "escala_segarc_por_pixel": round(escala_segarc_por_pixel(cabeceras["epoca_a"][1]), 4),
        "tamano_pixeles": {"ancho": int(ancho), "alto": int(alto)},
        "epocas": {p: {"id_exposicion": str(cabeceras[p][0]["IDEXPO"]), "mjd": mjd[p]} for p in PAPELES},
        "horas_entre_a_b": round(horas, 6),
        "imagenes": dict(IMAGENES),
    }
    wcs = wcs_publicable(cabeceras["epoca_a"][1])
    if wcs is not None:
        meta["wcs"] = wcs
    origen = origen_de(seleccion)
    if origen is not None:
        meta["origen"] = origen
    return meta


def escribir_meta(campo, raiz_datos="datos"):
    """Lee seleccion.json (m1) y los FITS alineados (m2); escribe meta.json. Devuelve su ruta."""
    raiz = Path(raiz_datos)
    seleccion = json.loads((raiz / "m1_adquisicion" / campo / "seleccion.json").read_text(encoding="utf-8"))
    directorio = raiz / "m2_alineacion" / campo
    cabeceras = {p: leer_cabeceras(directorio / (p + ".fits")) for p in PAPELES}
    ruta = directorio / "meta.json"
    ruta.write_text(json.dumps(construir_meta(seleccion, cabeceras), ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m2_alineacion.metadatos_campo <campo>")
    ruta_escrita = escribir_meta(sys.argv[1])
    meta_ = json.loads(ruta_escrita.read_text(encoding="utf-8"))
    print("%s: detector %d, %dx%d px, %.2f h entre A y B" % (ruta_escrita, meta_["detector"], meta_["tamano_pixeles"]["ancho"],
                                                           meta_["tamano_pixeles"]["alto"], meta_["horas_entre_a_b"]))
