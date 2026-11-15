# ============================================================================
# ARCHIVO: modulos/m2_alineacion/reproyeccion.py
# MODULO: m2_alineacion (Lote A)
# ROL: Reproyecta cada imagen sobre la rejilla de la época A.
# LEE: Recortes sin zodiacal.
# PRODUCE: epoca_a.fits, epoca_b.fits, plantilla.fits en datos/m2_alineacion/<campo>/.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de resta_zodiacal.py: recortes sin zodiacal.
#   1. Leer el WCS de la época A  ->  rejilla de referencia
#   2. Interpolar IMAGE, VARIANCE  ->  matrices alineadas
#   3. Reproyectar FLAGS por vecino más cercano  ->  máscara alineada
#   4. Guardar los tres archivos  ->  FITS alineados
# VERIFICACION: Los tres FITS comparten forma de matriz con WCS idéntico; cumplen contratos/alineados_fits.md.
# USO: python -m modulos.m2_alineacion.reproyeccion <campo>
# NOTA: Mismo algoritmo que reproject_interp para imágenes celestes 2D, sin esa dependencia:
#       cada píxel de la rejilla de A se lleva al cielo con el WCS de A y de ahí al píxel de
#       la otra imagen con su WCS; allí se interpola (bilineal para IMAGE y VARIANCE, vecino
#       más cercano para FLAGS). Un píxel que cae fuera de la otra imagen vale NaN (0 en FLAGS).
# ============================================================================
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from scipy.ndimage import map_coordinates

PAPELES = ("epoca_a", "epoca_b", "plantilla")
CLAVES_PRIMARIA = ("MJD-OBS", "DETECTOR", "IDEXPO", "PAPEL")


def wcs_celeste(cabecera):
    return WCS(cabecera).celestial


def coordenadas_en_origen(wcs_destino, forma_destino, wcs_origen):
    """Para cada píxel de la rejilla de destino, su posición (fila, columna) en la imagen de origen."""
    filas, columnas = np.indices(forma_destino, dtype=float)
    ra, dec = wcs_destino.pixel_to_world_values(columnas, filas)
    x_origen, y_origen = wcs_origen.world_to_pixel_values(ra, dec)
    return np.array([y_origen, x_origen])


def reproyectar_matriz(datos, coordenadas, vecino_mas_cercano=False):
    """Interpola `datos` en las coordenadas pedidas. Fuera de la imagen: NaN (o 0 con vecino más cercano)."""
    if vecino_mas_cercano:
        resultado = map_coordinates(np.asarray(datos, dtype=float), coordenadas, order=0, mode="constant", cval=0.0)
        return np.rint(resultado).astype(np.asarray(datos).dtype if np.issubdtype(np.asarray(datos).dtype, np.integer) else np.int32)
    return map_coordinates(np.asarray(datos, dtype=float), coordenadas, order=1, mode="constant", cval=np.nan)


def alinear_sobre(hdul_referencia, hdul_imagen):
    """Devuelve (IMAGE, VARIANCE, FLAGS) de `hdul_imagen` sobre la rejilla de `hdul_referencia`."""
    wcs_a = wcs_celeste(hdul_referencia["IMAGE"].header)
    forma = hdul_referencia["IMAGE"].data.shape
    if hdul_imagen is hdul_referencia:
        return (np.asarray(hdul_imagen["IMAGE"].data, dtype=float), np.asarray(hdul_imagen["VARIANCE"].data, dtype=float),
                np.asarray(hdul_imagen["FLAGS"].data).astype(np.int32))
    coordenadas = coordenadas_en_origen(wcs_a, forma, wcs_celeste(hdul_imagen["IMAGE"].header))
    return (reproyectar_matriz(hdul_imagen["IMAGE"].data, coordenadas),
            reproyectar_matriz(hdul_imagen["VARIANCE"].data, coordenadas),
            reproyectar_matriz(hdul_imagen["FLAGS"].data, coordenadas, vecino_mas_cercano=True).astype(np.int32))


def construir_alineado(hdul_referencia, hdul_imagen):
    """HDUList alineado: primaria con la identidad de la exposición; IMAGE, VARIANCE, FLAGS con el WCS de A."""
    imagen, varianza, flags = alinear_sobre(hdul_referencia, hdul_imagen)
    cabecera_wcs = wcs_celeste(hdul_referencia["IMAGE"].header).to_header()
    primaria = fits.PrimaryHDU()
    for clave in CLAVES_PRIMARIA:
        if clave in hdul_imagen[0].header:
            primaria.header[clave] = (hdul_imagen[0].header[clave], hdul_imagen[0].header.comments[clave])
    primaria.header["HISTORY"] = "m2_alineacion/reproyeccion: rejilla de la epoca A"
    hdu_imagen = fits.ImageHDU(imagen, cabecera_wcs.copy(), name="IMAGE")
    hdu_imagen.header["BUNIT"] = "MJy/sr"
    hdu_varianza = fits.ImageHDU(varianza, cabecera_wcs.copy(), name="VARIANCE")
    hdu_varianza.header["BUNIT"] = "(MJy/sr)**2"
    hdu_flags = fits.ImageHDU(flags, cabecera_wcs.copy(), name="FLAGS")
    return fits.HDUList([primaria, hdu_imagen, hdu_varianza, hdu_flags])


def alinear_campo(campo, raiz_datos="datos"):
    """Lee sin_zodiacal/<papel>.fits y escribe <papel>.fits alineados en datos/m2_alineacion/<campo>/."""
    directorio = Path(raiz_datos) / "m2_alineacion" / campo
    abiertos = {p: fits.open(directorio / "sin_zodiacal" / (p + ".fits")) for p in PAPELES}
    rutas = {}
    try:
        for papel in PAPELES:
            rutas[papel] = directorio / (papel + ".fits")
            construir_alineado(abiertos["epoca_a"], abiertos[papel]).writeto(rutas[papel], overwrite=True)
    finally:
        for h in abiertos.values():
            h.close()
    return rutas


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m2_alineacion.reproyeccion <campo>")
    for papel_, ruta_ in alinear_campo(sys.argv[1]).items():
        with fits.open(ruta_) as h:
            datos_ = h["IMAGE"].data
            print("%s: %s  %dx%d, %.1f%% sin cobertura" % (papel_, ruta_, datos_.shape[1], datos_.shape[0],
                                                           100.0 * np.isnan(datos_).mean()))
