# ============================================================================
# ARCHIVO: modulos/m3_deteccion/deteccion_fuentes.py
# MODULO: m3_deteccion (Lote B)
# ROL: Detecta las fuentes puntuales de cada imagen alineada.
# LEE: epoca_a.fits, epoca_b.fits, plantilla.fits.
# PRODUCE: datos/m3_deteccion/<campo>/detecciones.json (intermedio interno).
# FUNCIONAMIENTO PREVISTO:
#   Recibe de m2_alineacion: FITS alineados.
#   1. Enmascarar los píxeles marcados en FLAGS  ->  imagen enmascarada
#   2. Estimar el fondo local  ->  imagen sin fondo
#   3. Buscar picos sobre 5 veces el ruido  ->  posiciones x, y
#   4. Calcular señal/ruido con VARIANCE  ->  detecciones.json
#   Entrega a emparejamiento.py: detecciones.json.
# VERIFICACION: Cada detección tiene señal/ruido mayor o igual que 5; su incertidumbre de posición nunca baja de 0,5 segundos de arco.
# USO: python -m modulos.m3_deteccion.deteccion_fuentes <campo>
# ============================================================================
import json
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_area
from photutils.background import Background2D
from photutils.detection import DAOStarFinder

EPOCAS = {"epoca_a": "a", "epoca_b": "b", "plantilla": "t"}  # imagen -> prefijo de id_fuente
UMBRAL_SIGMAS = 5.0
ANCHURA_PIXELES = 2.0  # anchura a media altura de una fuente puntual de SPHEREx
RADIO_APERTURA_PIXELES = 1.5 * ANCHURA_PIXELES
RADIO_MASCARA_PIXELES = 2.0
INCERTIDUMBRE_MINIMA_SEGARC = 0.5
# Bits de FLAGS que describen el píxel sin invalidarlo. SOURCE marca los píxeles
# de fuentes conocidas: enmascararlo borraría justo lo que buscamos.
BITS_INFORMATIVOS = {"SOURCE": 21}


def mascara_de_flags(flags, cabecera=None):
    """Devuelve True en los píxeles que no se deben usar.

    El número de cada bit informativo se lee de la cabecera (claves MP_<NOMBRE>)
    si está; si no, se usa el valor por defecto de BITS_INFORMATIVOS.
    """
    flags = np.asarray(flags).astype(np.int64)
    ignorados = 0
    for nombre, bit in BITS_INFORMATIVOS.items():
        if cabecera is not None and ("MP_" + nombre) in cabecera:
            bit = int(cabecera["MP_" + nombre])
        ignorados |= 1 << bit
    return (flags & ~ignorados) != 0


def restar_fondo(imagen, mascara):
    """Devuelve (imagen sin fondo, mapa de ruido del fondo)."""
    lado = max(8, min(imagen.shape) // 4)
    fondo = Background2D(imagen, lado, mask=mascara, filter_size=3, exclude_percentile=50.0)
    return imagen - fondo.background, fondo.background_rms


def buscar_picos(sin_fondo, ruido, mascara):
    """Devuelve una lista de (x, y) de los picos sobre UMBRAL_SIGMAS veces el ruido."""
    umbral = UMBRAL_SIGMAS * float(np.nanmedian(ruido))
    buscador = DAOStarFinder(threshold=umbral, fwhm=ANCHURA_PIXELES)
    tabla = buscador(np.where(mascara, 0.0, sin_fondo), mask=mascara)
    if tabla is None or len(tabla) == 0:
        return []
    col_x = "x_centroid" if "x_centroid" in tabla.colnames else "xcentroid"
    col_y = "y_centroid" if "y_centroid" in tabla.colnames else "ycentroid"
    return [(float(x), float(y)) for x, y in zip(tabla[col_x], tabla[col_y])]


def medir_fuente(x, y, sin_fondo, varianza, mascara, wcs):
    """Mide una fuente en una apertura circular. Devuelve None si no se puede medir."""
    filas, columnas = np.indices(sin_fondo.shape)
    distancia = np.hypot(columnas - x, filas - y)
    apertura = (distancia <= RADIO_APERTURA_PIXELES) & ~mascara
    if not apertura.any():
        return None
    suma = float(sin_fondo[apertura].sum())
    ruido = float(np.sqrt(varianza[apertura].sum()))
    if not np.isfinite(suma) or not np.isfinite(ruido) or ruido <= 0:
        return None
    senal_ruido = suma / ruido

    area_grados2 = float(proj_plane_pixel_area(wcs))  # el WCS celeste trabaja en grados
    area_sr = area_grados2 * (np.pi / 180.0) ** 2
    escala_segarc = float(np.sqrt(area_grados2)) * 3600.0
    ra, dec = wcs.pixel_to_world_values(x, y)
    incertidumbre = ANCHURA_PIXELES * escala_segarc / (2.355 * senal_ruido) if senal_ruido > 0 else np.inf
    return {
        "ra_grados": round(float(ra), 7),
        "dec_grados": round(float(dec), 7),
        "x": round(x, 3),
        "y": round(y, 3),
        "flujo_mjy": round(suma * area_sr * 1e9, 5),  # MJy/sr por píxel -> mJy
        "senal_ruido": round(senal_ruido, 2),
        "incertidumbre_posicion_segarc": round(max(INCERTIDUMBRE_MINIMA_SEGARC, incertidumbre), 3),
        "toca_mascara": bool((mascara & (distancia <= RADIO_MASCARA_PIXELES)).any()),
    }


def detectar_en_imagen(imagen, varianza, flags, wcs, cabecera_flags=None):
    """Detecta las fuentes de una imagen alineada. Devuelve una lista de dicts, la más brillante primero."""
    imagen = np.asarray(imagen, dtype=float)
    varianza = np.asarray(varianza, dtype=float)
    mascara = mascara_de_flags(flags, cabecera_flags) | ~np.isfinite(imagen) | ~np.isfinite(varianza)
    relleno = np.where(mascara, 0.0, imagen)
    sin_fondo, ruido = restar_fondo(relleno, mascara)
    varianza = np.where(np.isfinite(varianza) & (varianza > 0), varianza, ruido ** 2)

    fuentes = []
    for x, y in buscar_picos(sin_fondo, ruido, mascara):
        medida = medir_fuente(x, y, sin_fondo, varianza, mascara, wcs)
        if medida is not None and medida["senal_ruido"] >= UMBRAL_SIGMAS:
            fuentes.append(medida)
    fuentes.sort(key=lambda f: -f["flujo_mjy"])
    return fuentes


def detectar_archivo(ruta_fits, epoca):
    """Detecta las fuentes de un FITS alineado (extensiones IMAGE, VARIANCE, FLAGS)."""
    with fits.open(ruta_fits) as hdus:
        fuentes = detectar_en_imagen(
            hdus["IMAGE"].data, hdus["VARIANCE"].data, hdus["FLAGS"].data,
            WCS(hdus["IMAGE"].header), hdus["FLAGS"].header)
    prefijo = EPOCAS[epoca]
    return [{"id_fuente": "%s%03d" % (prefijo, i), "epoca": epoca, **f} for i, f in enumerate(fuentes, 1)]


def detectar_campo(campo, raiz_datos="datos"):
    """Lee los tres FITS alineados del campo y escribe detecciones.json. Devuelve su ruta."""
    entrada = Path(raiz_datos) / "m2_alineacion" / campo
    salida = Path(raiz_datos) / "m3_deteccion" / campo
    detecciones = []
    for epoca in EPOCAS:
        detecciones += detectar_archivo(entrada / (epoca + ".fits"), epoca)
    salida.mkdir(parents=True, exist_ok=True)
    ruta = salida / "detecciones.json"
    ruta.write_text(json.dumps({"campo": campo, "detecciones": detecciones}, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return ruta


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m3_deteccion.deteccion_fuentes <campo>")
    ruta_escrita = detectar_campo(sys.argv[1])
    total = len(json.loads(ruta_escrita.read_text(encoding="utf-8"))["detecciones"])
    print("%s: %d detecciones" % (ruta_escrita, total))
