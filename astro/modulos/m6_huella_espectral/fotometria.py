# ============================================================================
# ARCHIVO: modulos/m6_huella_espectral/fotometria.py
# MODULO: m6_huella_espectral (Lote C)
# ROL: Mide el flujo del objeto en cada exposición de la serie espectral.
# LEE: posiciones_previstas.json; recortes FITS crudos.
# PRODUCE: datos/m6_huella_espectral/<campo>/espectro_medido.json (intermedio interno).
# FUNCIONAMIENTO PREVISTO:
#   Recibe de trayectoria.py: posiciones_previstas.json.
#   1. Restar ZODI de IMAGE en cada recorte  ->  imagen sin zodiacal
#   2. Leer la longitud de onda del píxel en WCS-WAVE  ->  longitud de onda en micras
#   3. Ajustar la PSF en la posición prevista  ->  flujo con error
#   4. Promediar por detector cuando la señal/ruido es baja  ->  espectro_medido.json
#   Entrega a comparacion_plantillas.py, ajuste_planck.py, escritura_espectros.py: espectro_medido.json.
# VERIFICACION: Cada punto tiene longitud de onda entre 0,75 y 5,0 micras, flujo, error positivo, fecha MJD.
# USO: python -m modulos.m6_huella_espectral.fotometria <campo>
# NOTA: La PSF se modela como una gaussiana de 2 píxeles de anchura a media altura, con el centro
#       libre hasta 1,5 píxeles alrededor de la posición prevista y un fondo constante; el error
#       sale de la matriz de covarianza del ajuste pesado con VARIANCE. Cuando la mediana de la
#       señal/ruido de los puntos baja de 5, se promedian por detector (6 puntos anchos en vez de
#       102 bandas) y el espectro se marca con agrupacion = detector.
# ============================================================================
import json
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_area
from scipy.optimize import curve_fit

ANCHURA_PIXELES = 2.0
SIGMA_PIXELES = ANCHURA_PIXELES / 2.355
SEMILADO_VENTANA = 4           # ventana de 9 x 9 píxeles alrededor de la posición prevista
DESPLAZAMIENTO_MAXIMO = 1.5    # píxeles que el centro puede alejarse de la posición prevista
MINIMO_PIXELES_VALIDOS = 12
SNR_MINIMA_POR_BANDA = 5.0     # por debajo (mediana), se promedia por detector
LONGITUD_ONDA_MIN, LONGITUD_ONDA_MAX = 0.75, 5.0
BIT_SOURCE = 21                # bit informativo de FLAGS que no invalida el píxel


def modelo(xy, amplitud, x0, y0, fondo):
    x, y = xy
    return (amplitud * np.exp(-((x - x0) ** 2 + (y - y0) ** 2) / (2 * SIGMA_PIXELES ** 2)) + fondo).ravel()


def mascara_de_flags(flags, cabecera=None):
    bit = int(cabecera["MP_SOURCE"]) if cabecera is not None and "MP_SOURCE" in cabecera else BIT_SOURCE
    return (np.asarray(flags).astype(np.int64) & ~(1 << bit)) != 0


def _onda_densa(datos, x, y):
    onda = np.asarray(datos, dtype=float)
    return float(onda[int(round(y)), int(round(x))])


def _onda_dispersa(hdul, datos, x, y):
    """Longitud de onda de un píxel leída de la rejilla dispersa de SPHEREx.

    `WCS-WAVE` no es una imagen: trae una rejilla de nodos (X, Y) y en cada nodo
    un par (longitud de onda, incertidumbre). Las coordenadas X e Y están en el
    marco del detector completo (2040×2040), no en el del recorte: el desplazamiento
    se recupera de CRPIX1W, que el servicio de recortes deja negativo.
    """
    from scipy.interpolate import RegularGridInterpolator

    xs = np.asarray(datos["X"][0], dtype=float)
    ys = np.asarray(datos["Y"][0], dtype=float)
    valores = np.asarray(datos["VALUES"][0], dtype=float)[:, :, 0]  # (len(ys), len(xs))

    cabecera = hdul["IMAGE"].header
    desplazamiento_x = -float(cabecera.get("CRPIX1W", 0.0))
    desplazamiento_y = -float(cabecera.get("CRPIX2W", 0.0))
    px, py = x + desplazamiento_x, y + desplazamiento_y

    # Fuera de la rejilla se toma el nodo más cercano: el borde del detector.
    px = float(np.clip(px, xs.min(), xs.max()))
    py = float(np.clip(py, ys.min(), ys.max()))

    interpolador = RegularGridInterpolator((ys, xs), valores, method="linear")
    return float(interpolador((py, px)))


def longitud_de_onda(hdul, x, y):
    if "WCS-WAVE" not in hdul:
        raise ValueError("el recorte no tiene extensión WCS-WAVE (contrato recortes_fits)")
    datos = hdul["WCS-WAVE"].data
    if datos is None:
        raise ValueError("la extensión WCS-WAVE está vacía")
    if datos.dtype.names is None:
        return _onda_densa(datos, x, y)
    return _onda_dispersa(hdul, datos, x, y)


def medir_en_recorte(hdul, ra_grados, dec_grados):
    """Flujo del objeto en la posición prevista. Devuelve un dict o None si no se puede medir."""
    wcs = WCS(hdul["IMAGE"].header).celestial
    x, y = (float(v) for v in wcs.world_to_pixel_values(ra_grados, dec_grados))
    imagen = np.asarray(hdul["IMAGE"].data, dtype=float) - np.asarray(hdul["ZODI"].data, dtype=float)
    alto, ancho = imagen.shape
    if not (SEMILADO_VENTANA <= x < ancho - SEMILADO_VENTANA and SEMILADO_VENTANA <= y < alto - SEMILADO_VENTANA):
        return None
    varianza = np.asarray(hdul["VARIANCE"].data, dtype=float)
    mascara = mascara_de_flags(hdul["FLAGS"].data, hdul["FLAGS"].header)

    f0, c0 = int(round(y)) - SEMILADO_VENTANA, int(round(x)) - SEMILADO_VENTANA
    corte = (slice(f0, f0 + 2 * SEMILADO_VENTANA + 1), slice(c0, c0 + 2 * SEMILADO_VENTANA + 1))
    valores, var, mal = imagen[corte], varianza[corte], mascara[corte]
    validos = np.isfinite(valores) & np.isfinite(var) & (var > 0) & ~mal
    if validos.sum() < MINIMO_PIXELES_VALIDOS:
        return None
    filas, columnas = np.indices(valores.shape)
    xx, yy = (columnas + c0)[validos].astype(float), (filas + f0)[validos].astype(float)
    datos, sigmas = valores[validos], np.sqrt(var[validos])
    fondo0 = float(np.median(datos))
    p0 = (float(datos.max() - fondo0), x, y, fondo0)
    limites = ([-np.inf, x - DESPLAZAMIENTO_MAXIMO, y - DESPLAZAMIENTO_MAXIMO, -np.inf],
               [np.inf, x + DESPLAZAMIENTO_MAXIMO, y + DESPLAZAMIENTO_MAXIMO, np.inf])
    try:
        popt, pcov = curve_fit(modelo, (xx, yy), datos, p0=p0, sigma=sigmas, absolute_sigma=True, bounds=limites)
    except (RuntimeError, ValueError):
        return None
    amplitud, error_amplitud = popt[0], float(np.sqrt(pcov[0, 0]))
    if not np.isfinite(error_amplitud) or error_amplitud <= 0:
        return None
    a_mjy = 2 * np.pi * SIGMA_PIXELES ** 2 * float(proj_plane_pixel_area(wcs)) * (np.pi / 180.0) ** 2 * 1e9
    onda = longitud_de_onda(hdul, x, y)
    if not (LONGITUD_ONDA_MIN <= onda <= LONGITUD_ONDA_MAX):
        return None
    return {"longitud_onda_micras": round(onda, 4), "flujo_mjy": round(amplitud * a_mjy, 5),
            "error_mjy": round(error_amplitud * a_mjy, 5), "senal_ruido": round(amplitud / error_amplitud, 2),
            "x": round(popt[1], 3), "y": round(popt[2], 3)}


def medir_objeto(objeto, directorio_recortes):
    """Un punto por exposición útil del objeto, ordenados por fecha."""
    puntos = []
    for e in objeto["exposiciones"]:
        with fits.open(Path(directorio_recortes) / e["archivo_recorte"]) as hdul:
            medida = medir_en_recorte(hdul, e["ra_grados"], e["dec_grados"])
        if medida is None:
            continue
        puntos.append({**medida, "mjd": e["mjd"], "detector": int(e["detector"]), "id_exposicion": e["id_exposicion"]})
    puntos.sort(key=lambda p: p["mjd"])
    return puntos


def promediar_por_detector(puntos):
    """Media pesada por 1/error² de los puntos de cada detector; un punto por detector, ordenados por fecha."""
    resultado = []
    for detector in sorted({p["detector"] for p in puntos}):
        grupo = [p for p in puntos if p["detector"] == detector]
        pesos = np.array([1.0 / p["error_mjy"] ** 2 for p in grupo])
        flujo = float(np.sum(pesos * [p["flujo_mjy"] for p in grupo]) / pesos.sum())
        error = float(1.0 / np.sqrt(pesos.sum()))
        resultado.append({"longitud_onda_micras": round(float(np.sum(pesos * [p["longitud_onda_micras"] for p in grupo]) / pesos.sum()), 4),
                          "flujo_mjy": round(flujo, 5), "error_mjy": round(error, 5), "senal_ruido": round(flujo / error, 2),
                          "mjd": round(float(np.mean([p["mjd"] for p in grupo])), 6), "detector": detector,
                          "exposiciones_promediadas": len(grupo)})
    resultado.sort(key=lambda p: p["mjd"])
    return resultado


def espectro_de(objeto, directorio_recortes):
    """Espectro medido de un objeto, con la agrupación decidida por la señal/ruido."""
    puntos = medir_objeto(objeto, directorio_recortes)
    agrupacion = "banda"
    if puntos and float(np.median([p["senal_ruido"] for p in puntos])) < SNR_MINIMA_POR_BANDA:
        puntos, agrupacion = promediar_por_detector(puntos), "detector"
    return {"id_pareja": objeto["id_pareja"], "agrupacion": agrupacion, "puntos": puntos}


def medir_campo(campo, raiz_datos="datos"):
    """Lee posiciones_previstas.json (m6) y los recortes crudos (m1); escribe espectro_medido.json."""
    raiz = Path(raiz_datos)
    directorio = raiz / "m6_huella_espectral" / campo
    previstas = json.loads((directorio / "posiciones_previstas.json").read_text(encoding="utf-8"))
    recortes = raiz / "m1_adquisicion" / campo / "recortes"
    espectros = [espectro_de(objeto, recortes) for objeto in previstas["objetos"]]
    ruta = directorio / "espectro_medido.json"
    ruta.write_text(json.dumps({"campo": campo, "espectros": espectros}, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m6_huella_espectral.fotometria <campo>")
    ruta_escrita = medir_campo(sys.argv[1])
    for espectro_ in json.loads(ruta_escrita.read_text(encoding="utf-8"))["espectros"]:
        print("%s: %d puntos, agrupacion %s" % (espectro_["id_pareja"], len(espectro_["puntos"]), espectro_["agrupacion"]))
    print(ruta_escrita)
