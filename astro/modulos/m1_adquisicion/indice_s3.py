# ============================================================================
# ARCHIVO: modulos/m1_adquisicion/indice_s3.py
# MODULO: m1_adquisicion (Lote A)
# ROL: Lista las exposiciones de SPHEREx que cubren un campo sin usar el TAP de
#      IRSA: lee las cabeceras de los FITS de nivel 2 en la copia pública de
#      AWS S3 (bucket nasa-irsa-spherex) y comprueba con su WCS si cubren el campo.
# LEE: campos_objetivo.json; listados y cabeceras del bucket s3://nasa-irsa-spherex.
# PRODUCE: datos/m1_adquisicion/<campo>/listado_exposiciones.json (mismo formato que
#          consulta_sia.py) y una caché de cabeceras en datos/m1_adquisicion/indice_s3/.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de campos_objetivo.json: centro, radio del campo.
#   1. Predecir las semanas en que SPHEREx mira el campo (Sol a 90° en longitud eclíptica)
#   2. Listar los FITS de esas semanas en S3 (detectores 1-3, subexposición 1)
#   3. Leer solo la cabecera IMAGE de cada uno (petición Range, ~29 KB de 66 MB)
#   4. Quedarse con los que contienen el recorte; añadir su subexposición 2 y los
#      detectores gemelos (D1-D4, D2-D5, D3-D6 miran el mismo cielo)
#   5. Escribir listado_exposiciones.json con url_acceso del servicio de recortes de IRSA
#   Entrega a seleccion_epocas.py: listado_exposiciones.json.
# VERIFICACION: Para sphx_a encuentra 2025W48_2A_0120_1 en el detector 6; el listado pasa
#   por seleccion_epocas.py igual que el de TAP.
# USO: python -m modulos.m1_adquisicion.indice_s3 <campo> [--semanas 2025W48 2026W21] [--hilos 24]
# NOTA: Es la vía de respaldo cuando el TAP de IRSA no responde (502 el 2026-11-14). El
#   servicio de recortes de IRSA sí respondía, así que la descarga no cambia. Criterio de
#   cobertura: el cuadrado de semilado radio_grados alrededor del centro del campo cabe
#   entero en la imagen (con el WCS completo de la cabecera, SIP incluido). Es más amplio
#   que el de TAP (centro de la imagen a menos de radio_grados), que sigue siendo el primero.
# ============================================================================
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from modulos.m1_adquisicion.consulta_sia import DIR_DATOS, buscar_campo, construir_listado, escribir_listado

BUCKET = "https://nasa-irsa-spherex.s3.amazonaws.com/"
IBE = "https://irsa.ipac.caltech.edu/ibe/data/spherex/"
# Entregas que se exploran y la colección de IRSA a la que corresponden (qr2 queda superada por dr1).
ENTREGAS = {"qr3": "spherex_qr3", "dr1": "spherex_dr1"}
DIR_CACHE = DIR_DATOS / "indice_s3"
BYTES_CABECERA = 28800           # primaria + cabecera IMAGE caben en 10 bloques FITS
HILOS = 12                        # S3 frena las peticiones si se le exige más (medido: 64 hilos -> 3/s; 12 -> 16/s sostenidos)
MARGEN_SEMANAS = 1                # semanas a cada lado de la fecha predicha
PRIMER_DIA = datetime.date(2025, 4, 20)  # primeros datos de DR1 (2025W17)
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
PATRON = re.compile(r"level2_(?P<semana>\d{4}W\d{2}_\d[A-Z])_(?P<n>\d{4})_(?P<k>\d)D(?P<d>[1-6])_spx_.*\.fits$")
FIN_CABECERA = "END" + " " * 77
GEMELO = {1: 4, 2: 5, 3: 6}


# --- semanas -----------------------------------------------------------------

def semanas_probables(ra: float, dec: float, hasta: datetime.date | None = None,
                      margen: int = MARGEN_SEMANAS) -> list[str]:
    """Semanas ISO (p. ej. «2025W48») en que el Sol está a ±90° del campo en longitud eclíptica.

    SPHEREx barre círculos máximos a unos 90° del Sol: un punto del cielo se observa
    cuando la longitud eclíptica del Sol difiere en ±90° de la suya, dos veces al año.
    """
    import numpy as np
    from astropy.coordinates import GeocentricTrueEcliptic, SkyCoord, get_sun
    from astropy.time import Time
    import astropy.units as u

    hasta = hasta or datetime.date.today()
    lon = SkyCoord(ra * u.deg, dec * u.deg).transform_to(GeocentricTrueEcliptic()).lon.deg
    dias = [PRIMER_DIA + datetime.timedelta(days=i) for i in range((hasta - PRIMER_DIA).days + 1)]
    sol = get_sun(Time([d.isoformat() for d in dias])).transform_to(GeocentricTrueEcliptic()).lon.deg
    diferencia = (sol - lon + 540.0) % 360.0 - 180.0
    semanas: set[str] = set()
    for objetivo in (90.0, -90.0):
        distancia = np.abs((diferencia - objetivo + 180.0) % 360.0 - 180.0)
        for i in np.flatnonzero(distancia < 1.0):  # el Sol avanza ~1°/día: 1-2 días por paso
            for desplazamiento in range(-margen, margen + 1):
                dia = dias[i] + datetime.timedelta(weeks=desplazamiento)
                anio, semana, _ = dia.isocalendar()
                semanas.add(f"{anio}W{semana:02d}")
    return sorted(semanas)


# --- S3 ----------------------------------------------------------------------

def _url(clave: str) -> str:
    return BUCKET + urllib.parse.quote(clave)


def listar(prefijo: str, delimitador: bool = True) -> tuple[list[str], list[str]]:
    """(subcarpetas, claves) bajo `prefijo`, recorriendo todas las páginas del listado de S3."""
    carpetas, claves, testigo = [], [], None
    while True:
        consulta = {"list-type": "2", "max-keys": "1000", "prefix": prefijo}
        if delimitador:
            consulta["delimiter"] = "/"
        if testigo:
            consulta["continuation-token"] = testigo
        raiz = ET.fromstring(_obtener(BUCKET + "?" + urllib.parse.urlencode(consulta)))
        carpetas += [p.find(NS + "Prefix").text for p in raiz.iter(NS + "CommonPrefixes")]
        claves += [c.find(NS + "Key").text for c in raiz.iter(NS + "Contents")]
        siguiente = raiz.find(NS + "NextContinuationToken")
        if siguiente is None:
            return carpetas, claves
        testigo = siguiente.text


def _obtener(url: str, rango: int | None = None, reintentos: int = 4, timeout_s: float = 20.0) -> bytes:
    """GET con reintentos. Cuando S3 frena, deja las conexiones colgadas: por eso el timeout es corto."""
    cabeceras = {"Range": f"bytes=0-{rango - 1}"} if rango else {}
    for intento in range(reintentos):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=cabeceras), timeout=timeout_s).read()
        except Exception:  # red o S3 frenando: espera creciente y se reintenta
            if intento == reintentos - 1:
                raise
            time.sleep(2.0 * 2 ** intento)
    raise RuntimeError("inalcanzable")


def leer_cabecera_imagen(clave: str) -> str:
    """Texto de la cabecera de la extensión IMAGE (la segunda) del FITS en S3."""
    texto = _obtener(_url(clave), BYTES_CABECERA).decode("latin-1")
    return cabecera_imagen_de(texto)


def cabecera_imagen_de(texto: str) -> str:
    """Extrae la segunda cabecera de los primeros bloques de un FITS."""
    fin0 = texto.index(FIN_CABECERA)
    inicio = (fin0 // 2880 + 1) * 2880
    fin1 = texto.index(FIN_CABECERA, inicio)
    return texto[inicio:fin1 + 80]


# --- cobertura -----------------------------------------------------------------

def registro_de(clave: str, cabecera: str) -> dict:
    """Lo que se guarda de cada FITS: la clave, su exposición y la cabecera WCS."""
    from astropy.io import fits

    h = fits.Header.fromstring(cabecera)
    m = PATRON.search(clave)
    return {
        "clave": clave,
        "obsid": str(h.get("OBSID") or f"{m['semana']}_{m['n']}_{m['k']}"),
        "detector": int(h.get("DETECTOR") or m["d"]),
        "mjd": float(h.get("MJD-OBS") or h.get("MJD-AVG")),
        "cabecera": cabecera,
    }


def separacion_grados(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    """Distancia angular (haversine), en grados."""
    import math

    p1, p2 = math.radians(dec1), math.radians(dec2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(ra2 - ra1) / 2) ** 2
    return math.degrees(2 * math.asin(min(1.0, math.sqrt(h))))


TOLERANCIA_IDA_Y_VUELTA = 1.0 / 3600  # grados


def cubre(registro: dict, ra: float, dec: float, radio: float) -> bool:
    """Verdadero si el cuadrado de semilado `radio` alrededor de (ra, dec) cabe en la imagen.

    Dos defensas contra la inversión del WCS con SIP, que para puntos lejanos de la imagen
    puede divergir y devolver un píxel «dentro» que no corresponde a nada (pasó con datos
    reales: un recorte salió a 50° del campo): el centro de la imagen tiene que estar a
    menos de su semidiagonal más el radio, y el píxel hallado tiene que volver a (ra, dec).
    """
    import warnings

    import numpy as np
    from astropy.io import fits
    from astropy.wcs import WCS

    h = fits.Header.fromstring(registro["cabecera"])
    w = WCS(h).celestial
    ancho, alto = int(h["NAXIS1"]), int(h["NAXIS2"])
    escala = float(np.sqrt(abs(np.linalg.det(w.pixel_scale_matrix))))
    ra_c, dec_c = (float(v) for v in w.pixel_to_world_values((ancho - 1) / 2, (alto - 1) / 2))
    if separacion_grados(ra_c, dec_c, ra, dec) > escala * np.hypot(ancho, alto) / 2 + radio:
        return False
    margen = radio / escala
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            x, y = (float(v) for v in w.world_to_pixel_values(ra, dec))
            ra_v, dec_v = (float(v) for v in w.pixel_to_world_values(x, y))
    except Exception:  # el punto está detrás de la proyección
        return False
    if not (np.isfinite(x) and np.isfinite(y)) or separacion_grados(ra_v, dec_v, ra, dec) > TOLERANCIA_IDA_Y_VUELTA:
        return False
    return margen <= x <= ancho - 1 - margen and margen <= y <= alto - 1 - margen


def url_acceso(entrega: str, clave: str) -> str:
    """Ruta del mismo FITS en el archivo de IRSA, que acepta center y size (servicio de recortes)."""
    if not clave.startswith(f"{entrega}/"):
        raise ValueError(f"la clave {clave!r} no es de la entrega {entrega}")
    return IBE + clave  # s3://nasa-irsa-spherex/dr1/... = .../ibe/data/spherex/dr1/...


# --- exploración ---------------------------------------------------------------

def _cache(entrega: str, mitad: str) -> Path:
    return DIR_CACHE / f"{entrega}_{mitad}.json"


def _cargar_cache(ruta: Path) -> dict:
    if ruta.is_file():
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    return {"registros": {}}


def _guardar_cache(ruta: Path, cache: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def claves_de_mitad(entrega: str, mitad: str, listar_fn=listar) -> list[str]:
    """Todos los FITS de una media semana (todas las carpetas de proceso, todos los detectores)."""
    procesos, _ = listar_fn(f"{entrega}/level2/{mitad}/")
    claves: list[str] = []
    for proceso in procesos:
        for detector in range(1, 7):
            claves += listar_fn(f"{proceso}{detector}/", False)[1]
    # Si una exposición está en la carpeta normal y en la de reintento, vale la normal.
    por_exposicion: dict[tuple, str] = {}
    for clave in sorted(claves, key=lambda c: "_retry" in c):
        m = PATRON.search(clave)
        if m:
            por_exposicion.setdefault((m["n"], m["k"], m["d"]), clave)
    return sorted(por_exposicion.values())


def explorar_mitad(entrega: str, mitad: str, ra: float, dec: float, radio: float,
                   listar_fn=listar, leer_fn=leer_cabecera_imagen, hilos: int = HILOS,
                   aviso=lambda texto: None) -> list[dict]:
    """Registros de la media semana que cubren el campo. Lee solo lo que no está en la caché."""
    ruta = _cache(entrega, mitad)
    cache = _cargar_cache(ruta)
    if "claves" not in cache:
        cache["claves"] = claves_de_mitad(entrega, mitad, listar_fn)
    por_exposicion = {}
    for clave in cache["claves"]:
        m = PATRON.search(clave)
        por_exposicion[(m["n"], m["k"], int(m["d"]))] = clave

    def leer(claves: list[str]) -> None:
        pendientes = [c for c in claves if c not in cache["registros"]]
        if not pendientes:
            return
        aviso(f"  {entrega} {mitad}: {len(pendientes)} cabeceras")
        with ThreadPoolExecutor(hilos) as ex:
            for clave, texto in zip(pendientes, ex.map(_seguro(leer_fn), pendientes)):
                if texto is not None:
                    cache["registros"][clave] = registro_de(clave, texto)
        _guardar_cache(ruta, cache)

    # Primera pasada: subexposición 1 de los detectores 1-3 (los gemelos miran el mismo cielo).
    primeras = [c for (n, k, d), c in por_exposicion.items() if k == "1" and d in GEMELO]
    leer(primeras)
    aciertos = [cache["registros"][c] for c in primeras if c in cache["registros"]
                and cubre(cache["registros"][c], ra, dec, radio)]
    # Segunda pasada: todas las subexposiciones y detectores de las exposiciones que aciertan.
    numeros = {PATRON.search(r["clave"])["n"] for r in aciertos}
    detectores = {r["detector"] for r in aciertos}
    familia = {d for det in detectores for d in (det, GEMELO.get(det, det))}
    extra = [c for (n, k, d), c in por_exposicion.items() if n in numeros and d in familia]
    leer(extra)
    return [cache["registros"][c] for c in extra if c in cache["registros"]
            and cubre(cache["registros"][c], ra, dec, radio)]


def _seguro(leer_fn):
    def envuelto(clave):
        try:
            return leer_fn(clave)
        except Exception:  # un FITS ilegible no detiene la exploración
            return None
    return envuelto


def explorar_campo(campo: dict, semanas: list[str] | None = None, listar_fn=listar,
                   leer_fn=leer_cabecera_imagen, hilos: int = HILOS, aviso=None) -> dict:
    """Listado de exposiciones del campo con el formato de consulta_sia.construir_listado."""
    aviso = aviso or (lambda texto: print(texto, file=sys.stderr, flush=True))
    ra, dec, radio = campo["ra_grados"], campo["dec_grados"], campo["radio_grados"]
    semanas = semanas or semanas_probables(ra, dec)
    aviso(f"AVISO: explorando S3 en las semanas {', '.join(semanas)}")
    filas: dict[str, list[dict]] = {}
    for entrega, coleccion in ENTREGAS.items():
        mitades = [m for m in (p.rstrip("/").split("/")[-1] for p in listar_fn(f"{entrega}/level2/")[0])
                   if m[:7] in semanas]
        for mitad in mitades:
            for r in explorar_mitad(entrega, mitad, ra, dec, radio, listar_fn, leer_fn, hilos, aviso):
                filas.setdefault(coleccion, []).append({
                    "access_url": url_acceso(entrega, r["clave"]),
                    "t_min": r["mjd"],
                    "calib_level": 2,
                    "energy_bandpassname": f"SPHEREx-D{r['detector']}",
                    "identificador": f"{r['obsid']}_D{r['detector']}",
                })
    return construir_listado(campo, filas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lista las exposiciones de un campo leyendo las cabeceras en S3.")
    parser.add_argument("campo", help="identificador del campo en campos_objetivo.json")
    parser.add_argument("--semanas", nargs="*", help="semanas ISO, p. ej. 2025W48 (por defecto, las predichas)")
    parser.add_argument("--hilos", type=int, default=HILOS)
    args = parser.parse_args(argv)
    try:
        campo = buscar_campo(args.campo)
        listado = explorar_campo(campo, args.semanas, hilos=args.hilos)
    except (KeyError, ValueError, RuntimeError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if not listado["exposiciones"]:
        print("ERROR: ninguna exposición de esas semanas cubre el campo", file=sys.stderr)
        return 1
    destino = escribir_listado(listado)
    detectores = sorted({e["detector"] for e in listado["exposiciones"]})
    print(f"{len(listado['exposiciones'])} exposiciones (detectores {detectores}) desde S3 -> {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
