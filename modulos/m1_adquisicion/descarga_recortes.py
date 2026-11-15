# ============================================================================
# ARCHIVO: modulos/m1_adquisicion/descarga_recortes.py
# MODULO: m1_adquisicion (Lote A)
# ROL: Descarga el recorte FITS de cada exposición seleccionada.
# LEE: seleccion.json; servicio de recortes de IRSA.
# PRODUCE: datos/m1_adquisicion/<campo>/recortes/<id_exposicion>.fits.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de seleccion_epocas.py: seleccion.json.
#   1. Si la exposición es un DataLink, resolver la ruta del FITS  ->  ruta relativa
#   2. Añadir center y size a la ruta  ->  URL de recorte
#   3. Pedir el recorte a IRSA  ->  bytes FITS
#   4. Guardar con el nombre archivo_recorte  ->  recortes FITS crudos
#   Entrega a m2, m6: recortes FITS crudos.
# VERIFICACION: Existe un FITS por exposición de seleccion.json; cada uno cumple contratos/recortes_fits.md.
# NOTA: SPHEREx no se sirve por SIA sino por DataLink; `url_acceso` es un DataLink
#       y la descarga pasa por el servicio de recortes (ver issue #2).
# ESTADO: Esqueleto sin código. Este archivo solo documenta el trabajo pendiente.
# ============================================================================
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

from modulos.m1_adquisicion.consulta_sia import DIR_DATOS

# Extensiones que exige contratos/recortes_fits.md
EXTENSIONES_OBLIGATORIAS = ("IMAGE", "FLAGS", "VARIANCE", "ZODI", "PSF", "WCS-WAVE")

# Nombres admitidos por extensión. Los recortes reales de SPHEREx llaman `EPSF`
# a la PSF; el contrato la nombra `PSF`. Se acepta cualquiera de las dos.
ALIAS_EXTENSIONES = {"PSF": ("PSF", "EPSF")}

# Servicio de recortes del IRSA: se le pasa la ruta relativa del FITS, no la URL.
URL_CUTOUT = "https://irsa.ipac.caltech.edu/ibe/cutout"


class RecorteInvalido(ValueError):
    """El archivo descargado no es un FITS o le faltan extensiones del contrato."""


def url_recorte(url_acceso: str, ra_grados: float, dec_grados: float, radio_grados: float) -> str:
    """Añade center y size a la URL. `radio_grados` es el semilado, así que size (lado completo) es el doble."""
    base = url_acceso.split("?")[0]
    return f"{base}?center={ra_grados:.8f},{dec_grados:.8f}&size={2 * radio_grados:.6g}"


def es_datalink(url: str) -> bool:
    """True si la URL es un DataLink del IRSA: el FITS se resuelve en dos pasos."""
    return "/datalink/links/" in str(url)


def ruta_de_datalink(url_datalink: str, obtener) -> str:
    """Pide el DataLink y devuelve la ruta relativa del FITS científico.

    La respuesta trae varias filas (imagen científica, plantillas de calibración,
    servicio de recortes). La imagen es la única celda que empieza por `spherex/`
    y acaba en `.fits`: las demás son URLs o claves de S3.
    """
    xml = obtener(url_datalink).decode("utf-8", "replace")
    for fila in re.findall(r"<TR>(.*?)</TR>", xml, re.S):
        for celda in re.findall(r"<TD>(.*?)</TD>", fila, re.S):
            celda = celda.strip()
            if celda.startswith("spherex/") and celda.endswith(".fits"):
                return celda
    raise RecorteInvalido(f"el DataLink no trae la ruta del FITS científico: {url_datalink}")


def url_recorte_datalink(url_datalink: str, ra_grados: float, dec_grados: float,
                         radio_grados: float, obtener) -> str:
    """URL de recorte para una exposición servida por DataLink."""
    ruta = ruta_de_datalink(url_datalink, obtener)
    return (
        f"{URL_CUTOUT}?path={quote(ruta, safe='')}"
        f"&center={ra_grados:.8f},{dec_grados:.8f}&size={2 * radio_grados:.6g}"
    )


def obtener_bytes(url: str, reintentos: int = 5, espera_s: float = 3.0, timeout_s: float = 300.0) -> bytes:
    """Descarga una URL con reintentos y espera creciente. Se puede sustituir en pruebas.

    El servicio de recortes del IRSA devuelve 503 con frecuencia; cinco intentos
    con espera 3, 6, 12 y 24 s resuelven los fallos pasajeros. Un 503 repetido en
    todos los intentos suele ser definitivo para ese archivo, no del servicio.
    """
    import requests

    ultimo_error: Exception | None = None
    for intento in range(1, reintentos + 1):
        try:
            respuesta = requests.get(url, timeout=timeout_s)
            respuesta.raise_for_status()
            return respuesta.content
        except requests.RequestException as error:
            ultimo_error = error
            if intento < reintentos:
                time.sleep(min(espera_s * 2 ** (intento - 1), 30.0))
    raise RuntimeError(f"No se pudo descargar {url} tras {reintentos} intentos: {ultimo_error}")


def extensiones_que_faltan(ruta: Path) -> list[str]:
    """Extensiones del contrato ausentes en el FITS. Lanza RecorteInvalido si no se puede abrir como FITS."""
    from astropy.io import fits

    try:
        with fits.open(ruta, memmap=False) as hdus:
            presentes = {h.name.upper() for h in hdus}
    except (OSError, ValueError) as error:
        raise RecorteInvalido(f"{ruta.name} no es un FITS legible: {error}") from error
    return [
        exigida
        for exigida in EXTENSIONES_OBLIGATORIAS
        if not any(nombre in presentes for nombre in ALIAS_EXTENSIONES.get(exigida, (exigida,)))
    ]


def _nombre_seguro(nombre: str) -> str:
    if Path(nombre).name != nombre or not nombre.endswith(".fits"):
        raise ValueError(f"archivo_recorte no válido: {nombre!r}")
    return nombre


INTENTOS_DE_TRIO = 3


def _descargar_exposiciones(seleccion, carpeta, obtener, forzar):
    """Descarga las exposiciones de `seleccion`. Devuelve (listos, fallos, ids_fallidos)."""
    ra, dec = seleccion["centro"]["ra_grados"], seleccion["centro"]["dec_grados"]
    radio = seleccion["radio_grados"]
    listos, fallos, fallidas = [], [], set()

    for exposicion in seleccion["exposiciones"]:
        destino = carpeta / _nombre_seguro(exposicion["archivo_recorte"])
        if destino.exists() and not forzar:
            try:
                if not extensiones_que_faltan(destino):
                    listos.append(destino)
                    continue
            except RecorteInvalido:
                pass  # archivo anterior corrupto: se vuelve a descargar
        if es_datalink(exposicion["url_acceso"]):
            construir = lambda r: url_recorte_datalink(exposicion["url_acceso"], ra, dec, r, obtener)
        else:
            construir = lambda r: url_recorte(exposicion["url_acceso"], ra, dec, r)

        parcial = destino.with_name(destino.name + ".parte")
        try:
            contenido = None
            ultimo_fallo = None
            # El servicio de recortes falla con 503 según el tamaño pedido: en las
            # pruebas, 0,4° daba 503 y 0,2° del mismo archivo respondía 200. Se
            # reintenta con medio lado antes de dar la exposición por perdida.
            for radio_intento in (radio, radio / 2):
                try:
                    contenido = obtener(construir(radio_intento))
                    break
                except RuntimeError as error:
                    ultimo_fallo = error
            if contenido is None:
                raise ultimo_fallo
            parcial.write_bytes(contenido)
            faltan = extensiones_que_faltan(parcial)
            if faltan:
                raise RecorteInvalido(
                    f"{destino.name} no trae las extensiones {faltan}. "
                    "Si IRSA las nombra distinto, corrige contratos/recortes_fits.md en un PR propio."
                )
            os.replace(parcial, destino)  # solo un FITS completo y válido ocupa el nombre final
            listos.append(destino)
        except (RecorteInvalido, RuntimeError, OSError) as error:
            parcial.unlink(missing_ok=True)
            fallos.append(f"{exposicion['id_exposicion']}: {error}")
            fallidas.add(exposicion["id_exposicion"])
    return listos, fallos, fallidas


def _reseleccionar_sin(campo, dir_datos, fallidas):
    """Vuelve a elegir trío descartando las exposiciones que no se pudieron descargar.

    Hay archivos de DR1 que el servicio de recortes no sabe cortar (503 en todos
    los intentos). En vez de dar el campo por perdido se prueba la siguiente
    pareja A-B disponible.
    """
    from modulos.m1_adquisicion import seleccion_epocas

    ruta_listado = dir_datos / campo / "listado_exposiciones.json"
    if not ruta_listado.is_file():
        return None
    listado = json.loads(ruta_listado.read_text(encoding="utf-8"))
    restantes = [e for e in listado["exposiciones"] if e["identificador"] not in fallidas]
    if len(restantes) == len(listado["exposiciones"]):
        return None
    try:
        nueva = seleccion_epocas.seleccionar({**listado, "exposiciones": restantes})
    except seleccion_epocas.SeleccionImposible:
        return None
    seleccion_epocas.escribir_seleccion(nueva, dir_datos)
    return nueva


def descargar_campo(campo: str, dir_datos: Path = DIR_DATOS, obtener=obtener_bytes,
                    forzar: bool = False) -> list[Path]:
    """Descarga y valida un recorte por exposición de seleccion.json. Devuelve las rutas de los FITS.

    Si una exposición no se puede descargar, se prueba otro trío descartándola
    (hasta INTENTOS_DE_TRIO). Al final se lanza un único error con lo que falló.
    """
    ruta_seleccion = dir_datos / campo / "seleccion.json"
    carpeta = dir_datos / campo / "recortes"
    carpeta.mkdir(parents=True, exist_ok=True)

    fallos: list[str] = []
    for intento in range(1, INTENTOS_DE_TRIO + 1):
        with open(ruta_seleccion, encoding="utf-8") as f:
            seleccion = json.load(f)
        listos, fallos, fallidas = _descargar_exposiciones(seleccion, carpeta, obtener, forzar)
        if not fallos:
            return listos
        if intento == INTENTOS_DE_TRIO:
            break
        nueva = _reseleccionar_sin(campo, dir_datos, fallidas)
        if nueva is None:
            break
        print(
            "AVISO: %d recorte(s) no se pudieron descargar; se reintenta con otro trío."
            % len(fallos),
            file=sys.stderr,
        )

    raise RuntimeError(
        f"{len(fallos)} recorte(s) fallaron en {campo} tras {INTENTOS_DE_TRIO} intentos:\n  "
        + "\n  ".join(fallos)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Descarga los recortes FITS de las exposiciones seleccionadas.")
    parser.add_argument("campo", help="identificador del campo")
    parser.add_argument("--forzar", action="store_true", help="volver a descargar aunque el recorte ya exista y sea válido")
    args = parser.parse_args(argv)
    try:
        rutas = descargar_campo(args.campo, forzar=args.forzar)
    except FileNotFoundError:
        print(f"ERROR: falta datos/m1_adquisicion/{args.campo}/seleccion.json. Ejecuta antes seleccion_epocas.", file=sys.stderr)
        return 1
    except (RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"{len(rutas)} recortes en {rutas[0].parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())