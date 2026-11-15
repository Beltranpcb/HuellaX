# ============================================================================
# ARCHIVO: modulos/m1_adquisicion/pruebas/prueba_adquisicion.py
# MODULO: m1_adquisicion (Lote A)
# ROL: Comprueba la selección de épocas sobre un listado sintético sin usar la red.
# LEE: Un listado de exposiciones construido en memoria; contratos/seleccion.schema.json.
# PRODUCE: El veredicto de pytest.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de prueba: listado sintético.
#   1. Ejecutar la selección de épocas  ->  seleccion.json temporal
#   2. Validar contra seleccion.schema.json  ->  veredicto
#   Entrega a pytest: veredicto.
# VERIFICACION: Es el propio verificador: pasa cuando se cumplen los criterios de aceptación del módulo.
# ESTADO: Esqueleto sin código. Este archivo solo documenta el trabajo pendiente.
# ============================================================================
from __future__ import annotations

import io
import json
import socket
from pathlib import Path

import pytest

from modulos.m1_adquisicion import consulta_sia, descarga_recortes, seleccion_epocas

RAIZ = Path(__file__).resolve().parents[3]
ESQUEMA = RAIZ / "contratos" / "seleccion.schema.json"
MJD_A = 60900.0


@pytest.fixture(autouse=True)
def sin_red(monkeypatch):
    """Criterio 5: cualquier intento de abrir una conexión hace fallar la prueba."""
    def prohibido(*args, **kwargs):
        raise AssertionError("La prueba intentó abrir una conexión de red")

    monkeypatch.setattr(socket.socket, "connect", prohibido)
    monkeypatch.setattr(socket, "getaddrinfo", prohibido)


def _exp(identificador, t_min, detector, coleccion="spherex_qr3"):
    return {
        "identificador": identificador,
        "t_min": t_min,
        "detector": detector,
        "access_url": f"https://ejemplo.invalid/spherex/{identificador}.fits",
        "coleccion": coleccion,
    }


def _listado(exposiciones):
    return {
        "campo": "campo_sintetico",
        "nombre": "Campo sintético",
        "centro": {"ra_grados": 150.0, "dec_grados": 2.0},
        "radio_grados": 0.1,
        "exposiciones": sorted(exposiciones, key=lambda e: e["t_min"]),
    }


def _listado_sintetico():
    """Detector 3 sirve para A-B y plantilla; los detectores 1, 5 y 6 aportan serie; uno queda fuera de la ventana."""
    return _listado([
        _exp("d3_plantilla", MJD_A - 180.0, 3),
        _exp("d3_a", MJD_A, 3),
        _exp("d3_b", MJD_A + 0.25, 3),            # 6 h después de A
        _exp("d3_lejana", MJD_A + 3.5, 3),        # 84 h: fuera del máximo de 72 h
        _exp("d1_serie", MJD_A + 0.04, 1),
        _exp("d5_serie", MJD_A + 0.16, 5),
        _exp("d6_fuera_de_ventana", MJD_A + 2.0, 6),
        _exp("d2_sola", MJD_A + 0.1, 2),          # un único detector-2: no puede formar trío
    ])


def _seleccion():
    return seleccion_epocas.seleccionar(_listado_sintetico())


def _por_papel(seleccion, papel):
    return [e for e in seleccion["exposiciones"] if e["papel"] == papel]


# --- criterios de aceptación ----------------------------------------------

def prueba_la_red_esta_bloqueada():
    with pytest.raises(AssertionError):
        socket.create_connection(("irsa.ipac.caltech.edu", 443))


def prueba_seleccion_valida_contra_el_contrato(tmp_path):
    jsonschema = pytest.importorskip("jsonschema")
    esquema = json.loads(ESQUEMA.read_text(encoding="utf-8"))
    destino = seleccion_epocas.escribir_seleccion(_seleccion(), tmp_path)
    datos = json.loads(destino.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(esquema).validate(datos)


def prueba_un_unico_papel_de_cada_tipo():
    seleccion = _seleccion()
    for papel in ("epoca_a", "epoca_b", "plantilla"):
        assert len(_por_papel(seleccion, papel)) == 1, papel
    identificadores = [e["id_exposicion"] for e in seleccion["exposiciones"]]
    assert len(identificadores) == len(set(identificadores))


def prueba_a_b_y_plantilla_comparten_detector():
    seleccion = _seleccion()
    detectores = {e["detector"] for e in seleccion["exposiciones"] if e["papel"] in ("epoca_a", "epoca_b", "plantilla")}
    assert detectores == {3}


def prueba_a_dista_de_b_entre_0_5_y_72_horas():
    seleccion = _seleccion()
    a = _por_papel(seleccion, "epoca_a")[0]
    b = _por_papel(seleccion, "epoca_b")[0]
    horas = (b["mjd"] - a["mjd"]) * 24
    assert 0.5 <= horas <= 72
    assert horas == pytest.approx(6.0)


def prueba_plantilla_dista_mas_de_120_dias_de_a():
    seleccion = _seleccion()
    a = _por_papel(seleccion, "epoca_a")[0]
    plantilla = _por_papel(seleccion, "plantilla")[0]
    assert abs(plantilla["mjd"] - a["mjd"]) > 120


# --- comportamiento de la selección ---------------------------------------

def prueba_la_serie_espectral_abarca_otros_detectores_dentro_de_la_ventana():
    seleccion = _seleccion()
    serie = {e["id_exposicion"] for e in _por_papel(seleccion, "serie_espectral")}
    assert {"d1_serie", "d5_serie", "d2_sola"} <= serie
    assert "d6_fuera_de_ventana" not in serie
    assert "d3_lejana" not in serie


def prueba_url_de_acceso_sin_parametros_de_recorte():
    listado = _listado_sintetico()
    for e in listado["exposiciones"]:
        e["access_url"] += "?center=1,2&size=3"
    for e in seleccion_epocas.seleccionar(listado)["exposiciones"]:
        assert "?" not in e["url_acceso"]


def prueba_url_de_acceso_conserva_el_id_del_datalink():
    # SPHEREx se sirve por DataLink: el identificador viaja en la consulta y no
    # se puede borrar al quitar los parámetros de recorte.
    listado = _listado_sintetico()
    for e in listado["exposiciones"]:
        e["access_url"] = (
            "https://irsa.invalid/datalink/links/spherex?ID=ivo://irsa.ipac/spherex_dr1?x/D1"
            "&center=1,2&size=3"
        )
    for e in seleccion_epocas.seleccionar(listado)["exposiciones"]:
        assert "center=" not in e["url_acceso"]
        assert "size=" not in e["url_acceso"]
        assert e["url_acceso"].startswith("https://irsa.invalid/datalink/links/spherex?ID=")


def prueba_sin_pareja_valida_se_explica_el_motivo():
    # Solo dos exposiciones separadas 100 días: no hay pareja A-B ni plantilla.
    listado = _listado([_exp("x1", MJD_A, 4), _exp("x2", MJD_A + 100.0, 4)])
    with pytest.raises(seleccion_epocas.SeleccionImposible, match="detector 4"):
        seleccion_epocas.seleccionar(listado)


def prueba_una_pareja_a_mas_de_72_horas_no_vale():
    # Con plantilla correcta, pero A y B separadas 80 h: ninguna pareja cumple el máximo.
    listado = _listado([_exp("p", MJD_A - 180.0, 2), _exp("a", MJD_A, 2), _exp("b", MJD_A + 80.0 / 24.0, 2)])
    with pytest.raises(seleccion_epocas.SeleccionImposible):
        seleccion_epocas.seleccionar(listado)


def prueba_una_pareja_a_menos_de_media_hora_no_vale():
    listado = _listado([_exp("p", MJD_A - 180.0, 2), _exp("a", MJD_A, 2), _exp("b", MJD_A + 0.3 / 24.0, 2)])
    with pytest.raises(seleccion_epocas.SeleccionImposible):
        seleccion_epocas.seleccionar(listado)


def prueba_los_limites_exactos_de_separacion_se_admiten():
    for horas in (0.5, 72.0):
        listado = _listado([_exp("p", MJD_A - 180.0, 2), _exp("a", MJD_A, 2), _exp("b", MJD_A + horas / 24.0, 2)])
        seleccion = seleccion_epocas.seleccionar(listado)
        a, b = _por_papel(seleccion, "epoca_a")[0], _por_papel(seleccion, "epoca_b")[0]
        assert (b["mjd"] - a["mjd"]) * 24 == pytest.approx(horas)


def prueba_sin_plantilla_lejana_no_hay_seleccion():
    # Pareja A-B correcta, pero la única plantilla está a 100 días (menos de 120).
    listado = _listado([_exp("p", MJD_A - 100.0, 2), _exp("a", MJD_A, 2), _exp("b", MJD_A + 0.25, 2)])
    with pytest.raises(seleccion_epocas.SeleccionImposible):
        seleccion_epocas.seleccionar(listado)


# --- consulta_sia: normalización y orden (sin red) --------------------------

def prueba_el_listado_sale_ordenado_por_t_min_con_los_datos_necesarios():
    base = "https://irsa.ipac.caltech.edu/ibe/data/spherex/qr/level2/2025W19_2B/l2b-v11/{d}/level2_2025W19_2B_0073_2D{d}_spx_l2b-v11.fits"
    filas = {
        "spherex_qr3": [
            {"access_url": base.format(d=4), "t_min": 60900.30, "energy_bandpassname": "SPHEREx-D4", "calib_level": 2},
            {"access_url": base.format(d=2), "t_min": 60900.10, "energy_bandpassname": "SPHEREx-D2", "calib_level": 2},
        ],
        "spherex_dr1": [
            {"access_url": base.format(d=2), "t_min": 60900.10, "energy_bandpassname": "SPHEREx-D2", "calib_level": 2},  # duplicado
            {"access_url": base.format(d=5).replace("2D5", "2D5x"), "t_min": 60900.20, "energy_bandpassname": None, "calib_level": 3},  # nivel 3: se descarta
        ],
    }
    campo = {"campo": "campo_sintetico", "nombre": "Campo sintético", "ra_grados": 150.0, "dec_grados": 2.0, "radio_grados": 0.1}
    listado = consulta_sia.construir_listado(campo, filas)
    tiempos = [e["t_min"] for e in listado["exposiciones"]]
    assert tiempos == sorted(tiempos) == [60900.10, 60900.30]
    for e in listado["exposiciones"]:
        assert {"identificador", "t_min", "detector", "access_url"} <= e.keys()
    assert [e["detector"] for e in listado["exposiciones"]] == [2, 4]


def prueba_el_detector_sale_de_la_banda_o_del_nombre_del_archivo():
    assert consulta_sia.detector_de_fila("SPHEREx-D3", "https://x.invalid/a.fits") == 3
    assert consulta_sia.detector_de_fila(None, "https://x.invalid/level2_2025W18_1B_0023_2D4_spx_l2b.fits") == 4
    assert consulta_sia.detector_de_fila(None, "https://x.invalid/sin_pista.fits") is None


def prueba_consultar_campo_ordena_con_una_consulta_falsa():
    campo = {"campo": "campo_sintetico", "nombre": "Campo sintético", "ra_grados": 150.0, "dec_grados": 2.0, "radio_grados": 0.1}

    def consulta_falsa(ra, dec, radio, coleccion):
        if coleccion != "spherex_qr3":
            return []
        return [
            {"access_url": "https://x.invalid/b_2D1_.fits", "t_min": 5.0, "energy_bandpassname": "SPHEREx-D1"},
            {"access_url": "https://x.invalid/a_2D1_.fits", "t_min": 1.0, "energy_bandpassname": "SPHEREx-D1"},
        ]

    listado = consulta_sia.consultar_campo(campo, consulta=consulta_falsa)
    assert [e["t_min"] for e in listado["exposiciones"]] == [1.0, 5.0]


def prueba_campos_objetivo_bien_formados():
    campos = consulta_sia.cargar_campos()  # valida los cinco datos y el patrón del identificador
    identificadores = [c["campo"] for c in campos]
    assert len(identificadores) == len(set(identificadores))


def prueba_un_campo_mal_formado_se_rechaza():
    with pytest.raises(ValueError):
        consulta_sia.validar_campo({"campo": "Campo Mayusculas", "nombre": "x", "ra_grados": 1, "dec_grados": 1, "radio_grados": 0.1})
    with pytest.raises(ValueError):
        consulta_sia.validar_campo({"campo": "ok", "nombre": "x", "ra_grados": 1, "dec_grados": 1})


# --- descarga_recortes: URL y validación del FITS ---------------------------

def _fits_sintetico(extensiones):
    from astropy.io import fits
    import numpy as np

    hdus = [fits.PrimaryHDU()] + [fits.ImageHDU(np.zeros((4, 4), dtype=np.float32), name=n) for n in extensiones]
    memoria = io.BytesIO()
    fits.HDUList(hdus).writeto(memoria)
    return memoria.getvalue()


def prueba_la_url_de_recorte_lleva_center_y_el_lado_completo():
    url = descarga_recortes.url_recorte("https://irsa.invalid/x.fits?viejo=1", 150.0, 2.0, 0.1)
    assert url == "https://irsa.invalid/x.fits?center=150.00000000,2.00000000&size=0.2"


def _preparar_seleccion(tmp_path):
    seleccion = _seleccion()
    seleccion_epocas.escribir_seleccion(seleccion, tmp_path)
    return seleccion


def prueba_se_guarda_un_fits_por_exposicion_con_su_nombre(tmp_path):
    seleccion = _preparar_seleccion(tmp_path)
    pedidas = []

    def obtener_falso(url):
        pedidas.append(url)
        return _fits_sintetico(descarga_recortes.EXTENSIONES_OBLIGATORIAS)

    rutas = descarga_recortes.descargar_campo("campo_sintetico", tmp_path, obtener=obtener_falso)
    esperados = {e["archivo_recorte"] for e in seleccion["exposiciones"]}
    assert {r.name for r in rutas} == esperados
    assert {p.name for p in (tmp_path / "campo_sintetico" / "recortes").iterdir()} == esperados  # sin restos .parte
    assert all("center=150.00000000,2.00000000&size=0.2" in u for u in pedidas)
    assert descarga_recortes.extensiones_que_faltan(rutas[0]) == []


def prueba_no_se_vuelve_a_descargar_lo_que_ya_es_valido(tmp_path):
    _preparar_seleccion(tmp_path)
    llamadas = []

    def obtener_falso(url):
        llamadas.append(url)
        return _fits_sintetico(descarga_recortes.EXTENSIONES_OBLIGATORIAS)

    descarga_recortes.descargar_campo("campo_sintetico", tmp_path, obtener=obtener_falso)
    n = len(llamadas)
    descarga_recortes.descargar_campo("campo_sintetico", tmp_path, obtener=obtener_falso)
    assert len(llamadas) == n
    descarga_recortes.descargar_campo("campo_sintetico", tmp_path, obtener=obtener_falso, forzar=True)
    assert len(llamadas) == 2 * n


def prueba_un_fits_sin_las_seis_extensiones_se_rechaza(tmp_path):
    _preparar_seleccion(tmp_path)

    def obtener_falso(url):
        return _fits_sintetico(("IMAGE", "FLAGS"))  # faltan VARIANCE, ZODI, PSF, WCS-WAVE

    with pytest.raises(RuntimeError, match="PSF"):
        descarga_recortes.descargar_campo("campo_sintetico", tmp_path, obtener=obtener_falso)
    assert not any((tmp_path / "campo_sintetico" / "recortes").iterdir())  # no queda ningún archivo inválido


def prueba_la_psf_puede_llamarse_epsf(tmp_path):
    # Los recortes reales de SPHEREx traen EPSF; el contrato la nombra PSF.
    _preparar_seleccion(tmp_path)

    def obtener_falso(url):
        return _fits_sintetico(("IMAGE", "FLAGS", "VARIANCE", "ZODI", "EPSF", "WCS-WAVE"))

    rutas = descarga_recortes.descargar_campo("campo_sintetico", tmp_path, obtener=obtener_falso)
    assert rutas, "con EPSF el recorte debe aceptarse"
    assert descarga_recortes.extensiones_que_faltan(rutas[0]) == []


def prueba_un_archivo_que_no_es_fits_se_rechaza(tmp_path):
    _preparar_seleccion(tmp_path)
    with pytest.raises(RuntimeError, match="no es un FITS"):
        descarga_recortes.descargar_campo("campo_sintetico", tmp_path, obtener=lambda url: b"<html>error</html>")


def prueba_un_nombre_de_recorte_con_ruta_se_rechaza():
    with pytest.raises(ValueError):
        descarga_recortes._nombre_seguro("../fuera.fits")

def prueba_sin_red_se_usa_el_listado_guardado(tmp_path, monkeypatch):
    campo = {"campo": "campo_cache", "nombre": "Con caché", "ra_grados": 10.0,
             "dec_grados": 20.0, "radio_grados": 0.2}
    guardado = {"campo": "campo_cache", "nombre": "Con caché",
                "centro": {"ra_grados": 10.0, "dec_grados": 20.0}, "radio_grados": 0.2,
                "exposiciones": [{"identificador": "x1", "t_min": 61000.0, "detector": 1,
                                  "access_url": "https://x/1.fits", "coleccion": "spherex_dr1"}]}
    destino = tmp_path / "campo_cache"
    destino.mkdir()
    (destino / "listado_exposiciones.json").write_text(json.dumps(guardado), encoding="utf-8")

    monkeypatch.setattr(consulta_sia, "DIR_DATOS", tmp_path)

    def sin_red(*_a, **_k):
        raise RuntimeError("TAP caído")

    listado = consulta_sia.consultar_campo(campo, consulta=sin_red)
    assert listado["exposiciones"][0]["identificador"] == "x1"


# --------------------------------------------------------------- indice_s3
import datetime  # noqa: E402

from astropy.io import fits as _fits  # noqa: E402
from astropy.wcs import WCS as _WCS  # noqa: E402

from modulos.m1_adquisicion import indice_s3  # noqa: E402

LADO_SPHEREX = 2040
ESCALA_GRADOS = 6.15 / 3600


def _cabecera_imagen(ra, dec, obsid="2025W48_2A_0120_1", detector=3, mjd=61007.0282):
    """Cabecera IMAGE sintética con la forma de las reales: TAN, 2040 px, OBSID, DETECTOR, MJD-OBS."""
    w = _WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [ra, dec]
    w.wcs.crpix = [LADO_SPHEREX / 2 + 0.5, LADO_SPHEREX / 2 + 0.5]
    w.wcs.cdelt = [-ESCALA_GRADOS, ESCALA_GRADOS]
    h = w.to_header()
    h["XTENSION"] = "IMAGE"
    h["NAXIS1"], h["NAXIS2"] = LADO_SPHEREX, LADO_SPHEREX
    h["OBSID"], h["DETECTOR"], h["MJD-OBS"] = obsid, detector, mjd
    return h.tostring()


def _fits_texto(cabecera_imagen):
    """Primeros bloques de un FITS: cabecera primaria mínima y después la de IMAGE."""
    primaria = _fits.PrimaryHDU().header.tostring()
    return primaria + cabecera_imagen + "x" * 1000


def prueba_las_semanas_probables_incluyen_las_pasadas_conocidas():
    semanas = indice_s3.semanas_probables(160.617, 30.67, hasta=datetime.date(2026, 6, 1))
    assert "2025W48" in semanas              # pasada comprobada en IRSA (sphx_a)
    assert any(s.startswith("2026W2") for s in semanas)  # la pasada opuesta, seis meses después
    assert len(semanas) <= 12                # pocas semanas: la exploración es cara


def prueba_se_extrae_la_segunda_cabecera_del_fits():
    cabecera = _cabecera_imagen(150.0, 2.0)
    extraida = indice_s3.cabecera_imagen_de(_fits_texto(cabecera))
    h = _fits.Header.fromstring(extraida)
    assert h["EXTNAME"] == "IMAGE" if "EXTNAME" in h else h["XTENSION"] == "IMAGE"
    assert h["OBSID"] == "2025W48_2A_0120_1" and h["DETECTOR"] == 3


def prueba_cubre_exige_que_el_recorte_quepa_entero():
    registro = {"cabecera": _cabecera_imagen(150.0, 2.0)}
    assert indice_s3.cubre(registro, 150.0, 2.0, 0.2)
    assert indice_s3.cubre(registro, 150.0, 3.4, 0.2)          # cerca del borde, pero cabe
    assert not indice_s3.cubre(registro, 150.0, 3.6, 0.2)      # el cuadrado se sale
    assert not indice_s3.cubre(registro, 150.0, 2.0, 1.8)      # más grande que la imagen
    assert not indice_s3.cubre(registro, 330.0, -2.0, 0.2)     # otro lado del cielo


def prueba_url_de_acceso_apunta_al_mismo_fits_en_irsa():
    clave = "dr1/level2/2025W48_2A/l2b-v27/6/level2_2025W48_2A_0120_1D6_spx_l2b-v27.fits"
    url = indice_s3.url_acceso("dr1", clave)
    assert url == "https://irsa.ipac.caltech.edu/ibe/data/spherex/" + clave
    with pytest.raises(ValueError):
        indice_s3.url_acceso("qr3", clave)


def _listar_falso(claves):
    """Imita el listado de S3: carpetas por delimitador y claves completas sin él."""
    def listar(prefijo, delimitador=True):
        bajo = [c for c in claves if c.startswith(prefijo)]
        if not delimitador:
            return [], bajo
        carpetas = sorted({prefijo + c[len(prefijo):].split("/")[0] + "/" for c in bajo if "/" in c[len(prefijo):]})
        return carpetas, [c for c in bajo if "/" not in c[len(prefijo):]]
    return listar


def _clave(mitad, n, k, d, proceso="l2b-v27-2026-209"):
    return f"dr1/level2/{mitad}/{proceso}/{d}/level2_{mitad}_{n:04d}_{k}D{d}_spx_{proceso}.fits"


def prueba_claves_de_mitad_prefiere_la_carpeta_normal_a_la_de_reintento():
    claves = [_clave("2025W48_2A", 120, 1, 3), _clave("2025W48_2A", 120, 1, 3, "l2b_retry-v27-2026-209"),
              _clave("2025W48_2A", 121, 1, 3, "l2b_retry-v27-2026-209")]
    elegidas = indice_s3.claves_de_mitad("dr1", "2025W48_2A", _listar_falso(claves))
    assert elegidas == [claves[0], claves[2]]


def prueba_la_exploracion_lee_primero_tres_detectores_y_luego_solo_lo_que_acierta(tmp_path, monkeypatch):
    monkeypatch.setattr(indice_s3, "DIR_CACHE", tmp_path / "indice_s3")
    mitad = "2025W48_2A"
    claves = [_clave(mitad, n, k, d) for n in (119, 120) for k in (1, 2) for d in range(1, 7)]
    cielo = {119: (164.2, 12.8), 120: (160.6, 30.8)}   # solo la 0120 cubre el campo...
    leidas = []

    def leer(clave):
        leidas.append(clave)
        m = indice_s3.PATRON.search(clave)
        n, d = int(m["n"]), int(m["d"])
        ra, dec = cielo[n]
        ra += 4.0 * ((3 - d) % 3)  # ...y solo con la pareja de detectores 3/6: cada pareja mira a otro sitio
        return _cabecera_imagen(ra, dec, obsid=f"{mitad}_{n:04d}_{m['k']}", detector=d, mjd=61007.0 + n / 1e4 + int(m["k"]) / 1e3)

    campo = {"campo": "sphx_a", "nombre": "Campo A", "ra_grados": 160.617, "dec_grados": 30.67, "radio_grados": 0.2}
    listado = indice_s3.explorar_campo(campo, ["2025W48"], listar_fn=_listar_falso(claves), leer_fn=leer, hilos=2,
                                       aviso=lambda texto: None)
    ids = sorted(e["identificador"] for e in listado["exposiciones"])
    assert ids == [f"{mitad}_0120_{k}_D{d}" for k in (1, 2) for d in (3, 6)]
    assert all(e["access_url"].startswith(indice_s3.IBE + "dr1/") and e["coleccion"] == "spherex_dr1"
               for e in listado["exposiciones"])
    assert [e["t_min"] for e in listado["exposiciones"]] == sorted(e["t_min"] for e in listado["exposiciones"])
    # Primera pasada: subexposición 1 de D1-D3 de las dos exposiciones (6 lecturas).
    primeras = leidas[:6]
    assert all(indice_s3.PATRON.search(c)["k"] == "1" and int(indice_s3.PATRON.search(c)["d"]) <= 3 for c in primeras)
    # Segunda pasada: solo la 0120, detectores 3 y 6 (el gemelo), las dos subexposiciones; nunca la 0119 en D4-D6.
    segundas = leidas[6:]
    assert segundas and all("_0120_" in c for c in segundas)
    assert {int(indice_s3.PATRON.search(c)["d"]) for c in segundas} == {3, 6}
    # La caché evita volver a leer: una segunda exploración no toca la red.
    leidas.clear()
    indice_s3.explorar_campo(campo, ["2025W48"], listar_fn=_listar_falso(claves), leer_fn=leer, hilos=2, aviso=lambda t: None)
    assert leidas == []


def prueba_sin_tap_ni_listado_guardado_se_explora_s3(tmp_path, monkeypatch):
    monkeypatch.setattr(consulta_sia, "DIR_DATOS", tmp_path)
    campo = {"campo": "campo_s3", "nombre": "Vía S3", "ra_grados": 10.0, "dec_grados": 20.0, "radio_grados": 0.2}

    def sin_red(*_a, **_k):
        raise RuntimeError("TAP caído")

    def s3_falso(c):
        assert c is campo
        return {"campo": "campo_s3", "nombre": "Vía S3", "centro": {"ra_grados": 10.0, "dec_grados": 20.0},
                "radio_grados": 0.2, "exposiciones": [{"identificador": "s3_1", "t_min": 61000.0, "detector": 3,
                                                       "access_url": indice_s3.IBE + "dr1/x.fits", "coleccion": "spherex_dr1"}]}

    listado = consulta_sia.consultar_campo(campo, consulta=sin_red, explorar_s3=s3_falso)
    assert listado["exposiciones"][0]["identificador"] == "s3_1"

    def s3_roto(c):
        raise OSError("sin salida a S3")

    with pytest.raises(RuntimeError, match="S3"):
        consulta_sia.consultar_campo(campo, consulta=sin_red, explorar_s3=s3_roto)


def prueba_cubre_no_se_deja_enganar_por_la_inversion_sip_que_diverge():
    """Regresión con cabeceras reales: 0214_3_D2 mira a ~50° de sphx_a; antes «cubría» el campo."""
    reales = json.loads((Path(__file__).with_name("cabeceras_reales.json")).read_text(encoding="utf-8"))["cabeceras"]
    lejos, cerca = reales["2025W48_1A_0214_3_D2"], reales["2025W48_1A_0272_1_D2"]
    assert not indice_s3.cubre(lejos, 160.617, 30.67, 0.2)
    assert indice_s3.cubre(cerca, 160.617, 30.67, 0.2)
    assert indice_s3.separacion_grados(10.0, 0.0, 10.0, 1.0) == pytest.approx(1.0)
