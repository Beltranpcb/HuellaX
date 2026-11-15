# ============================================================================
# ARCHIVO: modulos/m2_alineacion/resta_zodiacal.py
# MODULO: m2_alineacion (Lote A)
# ROL: Resta la luz zodiacal de cada recorte crudo.
# LEE: seleccion.json; recortes FITS crudos con papel epoca_a, epoca_b, plantilla.
# PRODUCE: datos/m2_alineacion/<campo>/sin_zodiacal/*.fits (intermedio interno).
# FUNCIONAMIENTO PREVISTO:
#   Recibe de m1_adquisicion: seleccion.json, recortes FITS crudos.
#   1. Abrir las extensiones IMAGE, ZODI  ->  dos matrices en MJy/sr
#   2. Calcular IMAGE menos ZODI  ->  imagen sin zodiacal
#   3. Guardar junto a VARIANCE, FLAGS  ->  recortes sin zodiacal
#   Entrega a reproyeccion.py: recortes sin zodiacal.
# VERIFICACION: La mediana de cada imagen resultante queda más cerca de cero que la mediana de IMAGE.
# USO: python -m modulos.m2_alineacion.resta_zodiacal <campo>
# NOTA: La fecha (MJD-OBS), el detector (DETECTOR) y el identificador (IDEXPO) se copian de
#       seleccion.json a la cabecera primaria, porque los nombres de esas claves en la
#       cabecera real de SPHEREx se confirman con el primer recorte real.
# ============================================================================
import json
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits

PAPELES = ("epoca_a", "epoca_b", "plantilla")


def exposiciones_por_papel(seleccion):
    """Las tres exposiciones que forman el campo, indexadas por papel. Falla si falta o sobra alguna."""
    por_papel = {}
    for e in seleccion["exposiciones"]:
        if e["papel"] in PAPELES:
            if e["papel"] in por_papel:
                raise ValueError("seleccion.json tiene más de una exposición con papel %s" % e["papel"])
            por_papel[e["papel"]] = e
    faltan = [p for p in PAPELES if p not in por_papel]
    if faltan:
        raise ValueError("seleccion.json no tiene exposición con papel: %s" % ", ".join(faltan))
    return por_papel


def restar_zodiacal(hdul):
    """IMAGE menos ZODI, en MJy/sr, como matriz de coma flotante."""
    if "ZODI" not in hdul:
        raise ValueError("el recorte no tiene extensión ZODI (contrato recortes_fits)")
    return np.asarray(hdul["IMAGE"].data, dtype=float) - np.asarray(hdul["ZODI"].data, dtype=float)


def construir_sin_zodiacal(hdul, exposicion):
    """HDUList con IMAGE (sin zodiacal), VARIANCE y FLAGS, más la identidad de la exposición en la primaria."""
    primaria = fits.PrimaryHDU()
    primaria.header["MJD-OBS"] = (float(exposicion["mjd"]), "MJD de la exposicion")
    primaria.header["DETECTOR"] = (int(exposicion["detector"]), "Detector SPHEREx (1 a 6)")
    primaria.header["IDEXPO"] = (str(exposicion["id_exposicion"]), "Id de la exposicion en IRSA")
    primaria.header["PAPEL"] = (exposicion["papel"], "epoca_a, epoca_b o plantilla")
    imagen = fits.ImageHDU(restar_zodiacal(hdul), hdul["IMAGE"].header.copy(), name="IMAGE")
    imagen.header["BUNIT"] = "MJy/sr"
    imagen.header["HISTORY"] = "m2_alineacion/resta_zodiacal: IMAGE - ZODI"
    varianza = fits.ImageHDU(np.asarray(hdul["VARIANCE"].data, dtype=float), hdul["VARIANCE"].header.copy(), name="VARIANCE")
    flags = fits.ImageHDU(np.asarray(hdul["FLAGS"].data), hdul["FLAGS"].header.copy(), name="FLAGS")
    return fits.HDUList([primaria, imagen, varianza, flags])


def restar_campo(campo, raiz_datos="datos"):
    """Lee seleccion.json y los recortes crudos del campo; escribe sin_zodiacal/<papel>.fits. Devuelve las rutas."""
    raiz = Path(raiz_datos)
    entrada = raiz / "m1_adquisicion" / campo
    seleccion = json.loads((entrada / "seleccion.json").read_text(encoding="utf-8"))
    salida = raiz / "m2_alineacion" / campo / "sin_zodiacal"
    salida.mkdir(parents=True, exist_ok=True)
    rutas = {}
    for papel, exposicion in exposiciones_por_papel(seleccion).items():
        with fits.open(entrada / "recortes" / exposicion["archivo_recorte"]) as hdul:
            resultado = construir_sin_zodiacal(hdul, exposicion)
        rutas[papel] = salida / (papel + ".fits")
        resultado.writeto(rutas[papel], overwrite=True)
    return rutas


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m2_alineacion.resta_zodiacal <campo>")
    for papel_, ruta_ in restar_campo(sys.argv[1]).items():
        with fits.open(ruta_) as h:
            print("%s: %s  mediana %.4f MJy/sr" % (papel_, ruta_, float(np.nanmedian(h["IMAGE"].data))))
