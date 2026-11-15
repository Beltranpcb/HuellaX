# ============================================================================
# ARCHIVO: modulos/m1_adquisicion/consulta_sia.py
# MODULO: m1_adquisicion (Lote A)
# ROL: Lista las exposiciones de SPHEREx que cubren un campo objetivo.
# LEE: campos_objetivo.json; servicio TAP de IRSA (tabla spherex.obscore).
# PRODUCE: datos/m1_adquisicion/<campo>/listado_exposiciones.json (intermedio interno).
# FUNCIONAMIENTO PREVISTO:
#   Recibe de campos_objetivo.json: centro, radio del campo.
#   1. Consultar TAP en las colecciones de SPHEREx  ->  tabla de exposiciones
#   2. Ordenar por t_min  ->  listado_exposiciones.json
#   Entrega a seleccion_epocas.py: listado_exposiciones.json.
# VERIFICACION: El listado sale ordenado por t_min; cada fila tiene identificador, t_min, detector, access_url.
# NOTA: el servicio SIA del IRSA solo cubre wise/twomass/ptf y no indexa SPHEREx;
#       la vía que responde es TAP sobre spherex.obscore (ver issue #2). Si TAP no
#       responde (502 el 2026-11-14) y no hay listado guardado, se recurre a la copia
#       pública en AWS S3 leyendo cabeceras (indice_s3.py).
# ============================================================================
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parents[2]
RUTA_CAMPOS = Path(__file__).with_name("campos_objetivo.json")
DIR_DATOS = RAIZ / "datos" / "m1_adquisicion"

# El servicio SIA del IRSA no indexa SPHEREx (solo wise, twomass y ptf); la
# tabla ObsCore de SPHEREx se consulta por TAP.
URL_TAP = "https://irsa.ipac.caltech.edu/TAP/sync"
COLECCIONES = ("spherex_qr3", "spherex_dr1", "spherex_dr1_deep")

CLAVES_CAMPO = ("campo", "nombre", "ra_grados", "dec_grados", "radio_grados")
PATRON_CAMPO = re.compile(r"^[a-z0-9_]+$")


# --- campos objetivo -------------------------------------------------------

def validar_campo(entrada: dict) -> None:
    """Lanza ValueError si la entrada de campos_objetivo.json está mal formada."""
    faltan = [k for k in CLAVES_CAMPO if k not in entrada]
    if faltan:
        raise ValueError(f"Campo sin los datos {faltan}: {entrada!r}")
    if not PATRON_CAMPO.match(str(entrada["campo"])):
        raise ValueError(
            f"Identificador de campo no válido: {entrada['campo']!r} "
            "(solo minúsculas, cifras, guion bajo)"
        )
    if not 0 <= entrada["ra_grados"] <= 360:
        raise ValueError(f"ra_grados fuera de [0, 360] en {entrada['campo']}")
    if not -90 <= entrada["dec_grados"] <= 90:
        raise ValueError(f"dec_grados fuera de [-90, 90] en {entrada['campo']}")
    if not entrada["radio_grados"] > 0:
        raise ValueError(f"radio_grados debe ser positivo en {entrada['campo']}")


def cargar_campos(ruta: Path = RUTA_CAMPOS) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        campos = json.load(f)["campos"]
    for entrada in campos:
        validar_campo(entrada)
    return campos


def buscar_campo(identificador: str, campos: list[dict] | None = None) -> dict:
    campos = cargar_campos() if campos is None else campos
    for entrada in campos:
        if entrada["campo"] == identificador:
            return entrada
    conocidos = ", ".join(c["campo"] for c in campos) or "(ninguno: rellena campos_objetivo.json)"
    raise KeyError(f"El campo {identificador!r} no está en campos_objetivo.json. Campos: {conocidos}")


# --- normalización de filas SIA2 -------------------------------------------

def _escalar(valor):
    """Convierte valores de astropy (enmascarados, bytes, numpy) en tipos de Python."""
    import numpy as np

    if valor is None or np.ma.is_masked(valor):
        return None
    if isinstance(valor, bytes):
        return valor.decode("utf-8", errors="replace")
    if hasattr(valor, "item"):
        return valor.item()
    return valor


def detector_de_fila(nombre_banda, url: str) -> int | None:
    """Detector 1 a 6: primero por energy_bandpassname ('SPHEREx-D2'), si no por el nombre del archivo."""
    if nombre_banda:
        m = re.search(r"D([1-6])\s*$", str(nombre_banda))
        if m:
            return int(m.group(1))
    m = re.search(r"_2D([1-6])_", urlparse(url).path)
    return int(m.group(1)) if m else None


def identificador_de_url(url: str) -> str:
    """Nombre del FITS sin extensión, apto como nombre de archivo (patrón del contrato seleccion)."""
    nombre = Path(urlparse(url).path).stem
    return re.sub(r"[^A-Za-z0-9_.-]", "_", nombre)


def normalizar_fila(fila: dict, coleccion: str) -> dict | None:
    """Fila SIA2 -> fila del listado. Devuelve None si no es una imagen de nivel 2 utilizable."""
    url = _escalar(fila.get("access_url"))
    t_min = _escalar(fila.get("t_min"))
    if not url or t_min is None:
        return None
    nivel = _escalar(fila.get("calib_level"))
    if nivel is not None and int(nivel) != 2:
        return None
    detector = detector_de_fila(_escalar(fila.get("energy_bandpassname")), url)
    if detector is None:
        return None
    return {
        # Las filas de TAP ya traen un identificador propio (obs_id + detector);
        # las de SIA se deducen del nombre del archivo.
        "identificador": _escalar(fila.get("identificador")) or identificador_de_url(url),
        "t_min": float(t_min),
        "detector": detector,
        "access_url": url,
        "coleccion": coleccion,
    }


def construir_listado(campo: dict, filas_por_coleccion: dict[str, list[dict]]) -> dict:
    """Une las filas de todas las colecciones: sin duplicados y ordenadas por t_min. No usa la red."""
    vistas_url: set[str] = set()
    vistas_instante: set[tuple[int, float]] = set()
    exposiciones: list[dict] = []
    for coleccion in COLECCIONES:  # el orden de COLECCIONES decide qué copia se conserva
        for fila in filas_por_coleccion.get(coleccion, []):
            nueva = normalizar_fila(fila, coleccion)
            if nueva is None:
                continue
            instante = (nueva["detector"], round(nueva["t_min"], 6))
            if nueva["access_url"] in vistas_url or instante in vistas_instante:
                continue
            vistas_url.add(nueva["access_url"])
            vistas_instante.add(instante)
            exposiciones.append(nueva)
    exposiciones.sort(key=lambda e: (e["t_min"], e["detector"], e["identificador"]))
    return {
        "campo": campo["campo"],
        "nombre": campo["nombre"],
        "centro": {"ra_grados": campo["ra_grados"], "dec_grados": campo["dec_grados"]},
        "radio_grados": campo["radio_grados"],
        "exposiciones": exposiciones,
    }


# --- red -------------------------------------------------------------------

CONSULTA_TAP = (
    "SELECT obs_id, s_ra, s_dec, t_min, access_url, obs_collection "
    "FROM spherex.obscore "
    "WHERE obs_collection = '{coleccion}' "
    "AND 1=CONTAINS(POINT('ICRS', s_ra, s_dec), CIRCLE('ICRS', {ra}, {dec}, {radio}))"
)


def detector_de_datalink(url: str) -> int | None:
    """Detector a partir de la URL de DataLink (`.../D3`)."""
    m = re.search(r"/D([1-6])\s*$", str(url))
    return int(m.group(1)) if m else None


def fila_tap_a_sia(fila: dict) -> dict | None:
    """Fila de `spherex.obscore` -> forma que entiende `normalizar_fila`.

    No es una fila SIA de verdad: se rellenan los campos que la normalización
    necesita (`access_url`, `t_min`, `calib_level`, `energy_bandpassname`)
    para no duplicar la lógica de deduplicación y orden.
    """
    url = (fila.get("access_url") or "").strip()
    detector = detector_de_datalink(url)
    if not url or detector is None:
        return None
    try:
        t_min = float(fila["t_min"])
    except (KeyError, TypeError, ValueError):
        return None
    return {
        "access_url": url,
        "t_min": t_min,
        "calib_level": 2,
        "energy_bandpassname": f"SPHEREx-D{detector}",
        "identificador": f"{fila.get('obs_id', 'exposicion')}_D{detector}",
    }


def consultar_tap(ra: float, dec: float, radio: float, coleccion: str,
                  reintentos: int = 2, espera_s: float = 2.0, timeout_s: float = 30.0) -> list[dict]:
    """Pide a IRSA por TAP las exposiciones de una colección que cubren el círculo (grados)."""
    import requests

    parametros = {
        "QUERY": CONSULTA_TAP.format(coleccion=coleccion, ra=ra, dec=dec, radio=radio),
        "FORMAT": "csv",
    }
    ultimo_error: Exception | None = None
    for intento in range(1, reintentos + 1):
        try:
            respuesta = requests.get(URL_TAP, params=parametros, timeout=timeout_s)
            respuesta.raise_for_status()
            texto = respuesta.text
            if "QUERY_STATUS" in texto and "ERROR" in texto:
                raise RuntimeError(f"IRSA devolvió un error para {coleccion}: {texto[:200]}")
            filas = [fila_tap_a_sia(f) for f in csv.DictReader(io.StringIO(texto))]
            return [f for f in filas if f is not None]
        except Exception as error:  # red, HTTP 5xx o error de IRSA
            ultimo_error = error
            if intento < reintentos:
                time.sleep(espera_s * intento)
    raise RuntimeError(f"TAP falló en {coleccion} tras {reintentos} intentos: {ultimo_error}")


def consultar_campo(campo: dict, consulta=consultar_tap, explorar_s3=None) -> dict:
    """Consulta las tres colecciones y devuelve el listado.

    `consulta` y `explorar_s3` se pueden sustituir en pruebas. Orden de respaldo cuando
    TAP falla: listado guardado del campo; si no lo hay, exploración de S3.
    """
    filas: dict[str, list[dict]] = {}
    errores: list[str] = []
    for coleccion in COLECCIONES:
        try:
            filas[coleccion] = consulta(campo["ra_grados"], campo["dec_grados"], campo["radio_grados"], coleccion)
        except RuntimeError as error:
            errores.append(str(error))
            print(f"AVISO: {error}", file=sys.stderr)
    if len(errores) == len(COLECCIONES):
        # El archivo de IRSA se cae de vez en cuando (TAP acepta la petición y no
        # ejecuta la consulta). Si ya hay un listado del campo se usa ese: la demo
        # funciona sin red, como manda el diseño (todo precalculado).
        guardado = DIR_DATOS / campo["campo"] / "listado_exposiciones.json"
        if guardado.is_file():
            print(
                "AVISO: TAP no responde; se usa el listado guardado en %s" % guardado,
                file=sys.stderr,
            )
            with open(guardado, encoding="utf-8") as f:
                return json.load(f)
        # Sin listado previo queda la copia pública de SPHEREx en AWS S3: se leen las
        # cabeceras de los FITS y se comprueba la cobertura con su WCS (indice_s3.py).
        if explorar_s3 is None:
            from modulos.m1_adquisicion.indice_s3 import explorar_campo as explorar_s3
        print("AVISO: TAP no responde y no hay listado guardado; se explora S3", file=sys.stderr)
        try:
            listado_s3 = explorar_s3(campo)
        except Exception as error:  # red o S3: se informa de las dos vías
            raise RuntimeError("Ninguna colección respondió por TAP:\n  " + "\n  ".join(errores)
                               + f"\n  y la exploración de S3 falló: {error}") from error
        if listado_s3["exposiciones"]:
            return listado_s3
        raise RuntimeError("Ninguna colección respondió:\n  " + "\n  ".join(errores))
    listado = construir_listado(campo, filas)
    if not listado["exposiciones"]:
        raise RuntimeError(
            f"Ninguna exposición de nivel 2 cubre el campo {campo['campo']!r}. "
            "Comprueba la cobertura o usa el campo de reserva."
        )
    return listado


# --- salida ----------------------------------------------------------------

def escribir_listado(listado: dict, dir_datos: Path = DIR_DATOS) -> Path:
    destino = dir_datos / listado["campo"] / "listado_exposiciones.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(listado, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return destino


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lista las exposiciones de SPHEREx que cubren un campo.")
    parser.add_argument("campo", help="identificador del campo en campos_objetivo.json")
    args = parser.parse_args(argv)
    try:
        campo = buscar_campo(args.campo)
        listado = consultar_campo(campo)
    except (KeyError, ValueError, RuntimeError) as error:
        print(f"ERROR: {error.args[0] if isinstance(error, KeyError) else error}", file=sys.stderr)
        return 1
    destino = escribir_listado(listado)
    detectores = sorted({e["detector"] for e in listado["exposiciones"]})
    print(f"{len(listado['exposiciones'])} exposiciones (detectores {detectores}) -> {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())