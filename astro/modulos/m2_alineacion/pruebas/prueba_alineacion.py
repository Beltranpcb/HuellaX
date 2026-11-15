# ============================================================================
# ARCHIVO: modulos/m2_alineacion/pruebas/prueba_alineacion.py
# MODULO: m2_alineacion (Lote A)
# ROL: Comprueba la alineación sobre imágenes sintéticas con estrellas desplazadas.
# LEE: Dos imágenes sintéticas creadas en memoria; contratos/meta.schema.json (copia en esquemas/).
# PRODUCE: El veredicto de pytest.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de prueba: recortes sintéticos con WCS desplazado.
#   1. Ejecutar la reproyección  ->  FITS alineados temporales
#   2. Medir los centroides de las estrellas  ->  desviación en píxeles
#   3. Comparar con 0,2 píxeles  ->  veredicto
#   Entrega a pytest: veredicto.
# VERIFICACION: Es el propio verificador: pasa cuando se cumplen los criterios de aceptación del módulo.
# USO: python -m pytest modulos/m2_alineacion/pruebas -q
# ESTRUCTURA: un campo sintético (fixture `campo`) con cinco estrellas fijas y un objeto móvil;
#             la época B y la plantilla llevan el WCS desplazado una fracción de píxel.
# ============================================================================
import json
from pathlib import Path

import jsonschema
import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image

from modulos.m2_alineacion import exportacion_png, metadatos_campo, reproyeccion, resta_zodiacal

def _ruta_esquema(nombre):
    """Devuelve contratos/<nombre> si existe el arbol completo; si no, esquemas/<nombre>."""
    for base in Path(__file__).resolve().parents:
        candidato = base / "contratos" / nombre
        if candidato.is_file():
            return candidato
    return Path(__file__).resolve().parents[1] / "esquemas" / nombre

ESQUEMA_META = json.loads(_ruta_esquema("meta.schema.json").read_text(encoding="utf-8"))

LADO = 118
ESCALA_GRADOS = 6.15 / 3600
RUIDO = 0.01  # MJy/sr
ESTRELLAS = [(30.3, 25.7, 3.0), (85.6, 40.2, 2.0), (50.1, 95.4, 4.0), (20.4, 80.9, 1.5), (100.2, 100.6, 2.5)]  # x, y, pico en A
MOVIL_A = (64.4, 70.8, 1.2)   # dónde está el objeto móvil en la época A (rejilla de A)
MOVIL_B = (69.4, 72.8, 1.2)   # dónde está en la época B (también en la rejilla de A)
DESPLAZAMIENTOS = {"epoca_a": (0.0, 0.0), "epoca_b": (3.4, -2.1), "plantilla": (-1.7, 4.6)}  # píxeles, (dx, dy)
EXPOSICIONES = {"epoca_a": ("exp_a", 60900.0), "epoca_b": ("exp_b", 60900.25), "plantilla": ("exp_t", 60720.0)}
BIT_MALO, BIT_SOURCE = 1 << 6, 1 << 21


def wcs_desplazado(dx, dy):
    """WCS con el mismo centro del cielo que A, pero con el píxel de referencia desplazado (dx, dy)."""
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [150.0, 2.0]
    w.wcs.crpix = [LADO / 2 + dx, LADO / 2 + dy]
    w.wcs.cdelt = [-ESCALA_GRADOS, ESCALA_GRADOS]
    return w


def gaussianas(fuentes, dx, dy):
    """Fuentes dadas en la rejilla de A, dibujadas en una rejilla desplazada (dx, dy)."""
    filas, columnas = np.indices((LADO, LADO))
    imagen = np.zeros((LADO, LADO))
    sigma = 2.0 / 2.355
    for x, y, pico in fuentes:
        imagen += pico * np.exp(-((columnas - (x + dx)) ** 2 + (filas - (y + dy)) ** 2) / (2 * sigma ** 2))
    return imagen


def recorte_crudo(papel, semilla):
    """Un recorte con las seis extensiones del contrato recortes_fits, en la rejilla desplazada de ese papel."""
    dx, dy = DESPLAZAMIENTOS[papel]
    azar = np.random.default_rng(semilla)
    filas, columnas = np.indices((LADO, LADO))
    zodi = 0.3 + 0.001 * columnas  # luz zodiacal con un gradiente suave
    fuentes = list(ESTRELLAS) + ({"epoca_a": [MOVIL_A], "epoca_b": [MOVIL_B], "plantilla": []}[papel])
    imagen = zodi + gaussianas(fuentes, dx, dy) + azar.normal(0.0, RUIDO, (LADO, LADO))
    flags = np.zeros((LADO, LADO), dtype=np.int32)
    flags[10:13, 40:43] = BIT_MALO
    flags[int(ESTRELLAS[0][1] + dy) - 1:int(ESTRELLAS[0][1] + dy) + 2, int(ESTRELLAS[0][0] + dx) - 1:int(ESTRELLAS[0][0] + dx) + 2] = BIT_SOURCE
    cabecera = wcs_desplazado(dx, dy).to_header()
    return fits.HDUList([
        fits.PrimaryHDU(),
        fits.ImageHDU(imagen, cabecera, name="IMAGE"),
        fits.ImageHDU(flags, cabecera, name="FLAGS"),
        fits.ImageHDU(np.full((LADO, LADO), RUIDO ** 2), cabecera, name="VARIANCE"),
        fits.ImageHDU(zodi, cabecera, name="ZODI"),
        fits.ImageHDU(np.ones((5, 5)) / 25.0, name="PSF"),
        fits.ImageHDU(np.linspace(1.6, 2.4, LADO)[:, None] * np.ones((LADO, LADO)), cabecera, name="WCS-WAVE"),
    ])


@pytest.fixture
def campo(tmp_path):
    """Escribe datos/m1_adquisicion/campo_prueba/ (seleccion.json y recortes/) en un directorio temporal."""
    entrada = tmp_path / "m1_adquisicion" / "campo_prueba"
    (entrada / "recortes").mkdir(parents=True)
    exposiciones = []
    for semilla, (papel, (id_exposicion, mjd)) in enumerate(EXPOSICIONES.items(), 10):
        recorte_crudo(papel, semilla).writeto(entrada / "recortes" / (id_exposicion + ".fits"))
        exposiciones.append({"id_exposicion": id_exposicion, "papel": papel, "mjd": mjd, "detector": 3,
                             "coleccion": "spherex_qr3", "url_acceso": "https://ejemplo.invalid/%s.fits" % id_exposicion,
                             "archivo_recorte": id_exposicion + ".fits"})
    exposiciones.append({"id_exposicion": "exp_s1", "papel": "serie_espectral", "mjd": 60900.04, "detector": 1,
                         "coleccion": "spherex_qr3", "url_acceso": "https://ejemplo.invalid/exp_s1.fits", "archivo_recorte": "exp_s1.fits"})
    (entrada / "seleccion.json").write_text(json.dumps({
        "version_contrato": "1", "campo": "campo_prueba", "nombre": "Campo de prueba",
        "centro": {"ra_grados": 150.0, "dec_grados": 2.0}, "radio_grados": 0.1, "exposiciones": exposiciones}), encoding="utf-8")
    return tmp_path


@pytest.fixture
def alineado(campo):
    """Ejecuta los cuatro pasos del módulo sobre el campo sintético."""
    resta_zodiacal.restar_campo("campo_prueba", raiz_datos=campo)
    reproyeccion.alinear_campo("campo_prueba", raiz_datos=campo)
    metadatos_campo.escribir_meta("campo_prueba", raiz_datos=campo)
    exportacion_png.exportar_campo("campo_prueba", raiz_datos=campo)
    return campo / "m2_alineacion" / "campo_prueba"


def centroide(imagen, x, y, semilado=3):
    """Centroide ponderado por brillo en una ventana alrededor de (x, y). Sin cobertura cuenta como cero."""
    datos = np.nan_to_num(np.asarray(imagen, dtype=float), nan=0.0)
    f0, c0 = int(round(y)) - semilado, int(round(x)) - semilado
    ventana = np.clip(datos[f0:f0 + 2 * semilado + 1, c0:c0 + 2 * semilado + 1], 0, None)
    filas, columnas = np.indices(ventana.shape)
    peso = ventana.sum()
    return c0 + (columnas * ventana).sum() / peso, f0 + (filas * ventana).sum() / peso


# ------------------------------------------------------------- resta_zodiacal
def prueba_resta_zodiacal_acerca_la_mediana_a_cero(campo):
    rutas = resta_zodiacal.restar_campo("campo_prueba", raiz_datos=campo)
    assert set(rutas) == {"epoca_a", "epoca_b", "plantilla"}
    with fits.open(campo / "m1_adquisicion" / "campo_prueba" / "recortes" / "exp_b.fits") as crudo, fits.open(rutas["epoca_b"]) as limpio:
        assert abs(np.median(limpio["IMAGE"].data)) < abs(np.median(crudo["IMAGE"].data))
        assert abs(np.median(limpio["IMAGE"].data)) < 0.01
        assert [h.name for h in limpio] == ["PRIMARY", "IMAGE", "VARIANCE", "FLAGS"]
        assert limpio[0].header["MJD-OBS"] == 60900.25 and limpio[0].header["DETECTOR"] == 3 and limpio[0].header["IDEXPO"] == "exp_b"
        assert WCS(limpio["IMAGE"].header).wcs.crpix[0] == pytest.approx(LADO / 2 + 3.4)


def prueba_falta_zodi_o_falta_un_papel_falla(campo):
    seleccion = json.loads((campo / "m1_adquisicion" / "campo_prueba" / "seleccion.json").read_text(encoding="utf-8"))
    sin_plantilla = {**seleccion, "exposiciones": [e for e in seleccion["exposiciones"] if e["papel"] != "plantilla"]}
    with pytest.raises(ValueError, match="plantilla"):
        resta_zodiacal.exposiciones_por_papel(sin_plantilla)
    hdul = recorte_crudo("epoca_a", 1)
    del hdul["ZODI"]
    with pytest.raises(ValueError, match="ZODI"):
        resta_zodiacal.restar_zodiacal(hdul)


# -------------------------------------------------------------- reproyeccion
def prueba_estrellas_fijas_coinciden_tras_alinear(alineado):
    """Criterio 1: centroides a menos de 0,2 píxeles de su posición en A, en las tres imágenes."""
    for papel in ("epoca_a", "epoca_b", "plantilla"):
        with fits.open(alineado / (papel + ".fits")) as h:
            imagen = h["IMAGE"].data
        for x, y, _ in ESTRELLAS:
            cx, cy = centroide(imagen, x, y)
            assert np.hypot(cx - x, cy - y) <= 0.2, (papel, x, y, cx, cy)


def prueba_el_objeto_movil_sigue_desplazado(alineado):
    with fits.open(alineado / "epoca_a.fits") as ha, fits.open(alineado / "epoca_b.fits") as hb:
        cxa, cya = centroide(ha["IMAGE"].data, MOVIL_A[0], MOVIL_A[1])
        cxb, cyb = centroide(hb["IMAGE"].data, MOVIL_B[0], MOVIL_B[1])
    assert np.hypot(cxa - MOVIL_A[0], cya - MOVIL_A[1]) <= 0.2
    assert np.hypot(cxb - MOVIL_B[0], cyb - MOVIL_B[1]) <= 0.2


def prueba_los_tres_fits_comparten_forma_y_wcs(alineado):
    cabeceras = {}
    for papel in ("epoca_a", "epoca_b", "plantilla"):
        with fits.open(alineado / (papel + ".fits")) as h:
            assert [x.name for x in h] == ["PRIMARY", "IMAGE", "VARIANCE", "FLAGS"]
            assert h["IMAGE"].data.shape == h["VARIANCE"].data.shape == h["FLAGS"].data.shape == (LADO, LADO)
            assert h["IMAGE"].header["BUNIT"] == "MJy/sr"
            cabeceras[papel] = {k: h["IMAGE"].header[k] for k in ("CRPIX1", "CRPIX2", "CRVAL1", "CRVAL2", "CDELT1", "CDELT2", "CTYPE1", "CTYPE2")}
            assert h[0].header["PAPEL"] == papel
    assert cabeceras["epoca_a"] == cabeceras["epoca_b"] == cabeceras["plantilla"]
    assert cabeceras["epoca_a"]["CRPIX1"] == pytest.approx(LADO / 2)


def prueba_sin_cobertura_vale_nan_y_dentro_no(alineado):
    with fits.open(alineado / "epoca_b.fits") as h:
        imagen = h["IMAGE"].data
    # B está desplazada +3,4 px en x: las últimas columnas de la rejilla de A caen fuera de B
    assert np.isnan(imagen[:, -2]).all()
    assert np.isfinite(imagen[10:-10, 10:-10]).all()


def prueba_flags_solo_contiene_valores_de_la_original(alineado):
    """Criterio 2: FLAGS se reproyecta por vecino más cercano, nunca se interpola."""
    for papel in ("epoca_b", "plantilla"):
        with fits.open(alineado / (papel + ".fits")) as h:
            flags = h["FLAGS"].data
        assert np.issubdtype(flags.dtype, np.integer)
        assert set(np.unique(flags)) <= {0, BIT_MALO, BIT_SOURCE}
        assert BIT_MALO in flags and BIT_SOURCE in flags
    with fits.open(alineado / "epoca_b.fits") as h:
        flags_b = h["FLAGS"].data
    x, y, _ = ESTRELLAS[0]
    assert flags_b[int(y), int(x)] == BIT_SOURCE  # la marca viaja con la estrella, no con el píxel


# ----------------------------------------------------------- metadatos_campo
def prueba_meta_json_cumple_el_contrato(alineado):
    """Criterio 4."""
    meta = json.loads((alineado / "meta.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(ESQUEMA_META).validate(meta)
    assert meta["campo"] == "campo_prueba" and meta["nombre"] == "Campo de prueba"
    assert meta["detector"] == 3
    assert meta["tamano_pixeles"] == {"ancho": LADO, "alto": LADO}
    assert meta["escala_segarc_por_pixel"] == pytest.approx(6.15, abs=0.01)
    assert meta["epocas"]["epoca_b"] == {"id_exposicion": "exp_b", "mjd": 60900.25}
    assert meta["horas_entre_a_b"] == pytest.approx((60900.25 - 60900.0) * 24)
    assert meta["imagenes"] == {"epoca_a": "epoca_a.png", "epoca_b": "epoca_b.png", "diferencia": "diferencia.png"}


def prueba_detectores_distintos_o_b_anterior_a_a_fallan():
    seleccion = {"campo": "c", "nombre": "C", "centro": {"ra_grados": 150.0, "dec_grados": 2.0}}
    cabecera = wcs_desplazado(0, 0).to_header()

    def primaria(mjd, detector, ide):
        h = fits.Header()
        h["MJD-OBS"], h["DETECTOR"], h["IDEXPO"] = mjd, detector, ide
        return h
    cabeceras = {"epoca_a": (primaria(60900.0, 3, "a"), cabecera, (LADO, LADO)),
                 "epoca_b": (primaria(60900.25, 2, "b"), cabecera, (LADO, LADO)),
                 "plantilla": (primaria(60720.0, 3, "t"), cabecera, (LADO, LADO))}
    with pytest.raises(ValueError, match="detector"):
        metadatos_campo.construir_meta(seleccion, cabeceras)
    cabeceras["epoca_b"] = (primaria(60899.0, 3, "b"), cabecera, (LADO, LADO))
    with pytest.raises(ValueError, match="posterior"):
        metadatos_campo.construir_meta(seleccion, cabeceras)


# ------------------------------------------------------------ exportacion_png
def prueba_los_tres_png_miden_600_y_pesan_menos_de_1mb(alineado):
    """Criterio 3."""
    for nombre in ("epoca_a.png", "epoca_b.png", "diferencia.png"):
        ruta = alineado / nombre
        with Image.open(ruta) as png:
            assert png.size == (600, 600), nombre
        assert ruta.stat().st_size < 1_000_000


def pixel_png(ruta, x, y, semilado=3):
    """Color medio del PNG alrededor de la posición (x, y) de la rejilla, con la conversión del contrato."""
    with Image.open(ruta) as png:
        rgb = np.asarray(png.convert("RGB"), dtype=float)
    columna = int(round(x * 600 / LADO))
    fila = int(round(600 - y * 600 / LADO))
    return rgb[fila - semilado:fila + semilado + 1, columna - semilado:columna + semilado + 1].mean(axis=(0, 1))


def prueba_las_estrellas_fijas_no_saltan_entre_los_dos_png(alineado):
    for x, y, _ in ESTRELLAS[1:]:
        brillo_a = pixel_png(alineado / "epoca_a.png", x, y)[0]
        brillo_b = pixel_png(alineado / "epoca_b.png", x, y)[0]
        fondo_a = pixel_png(alineado / "epoca_a.png", x + 12, y + 12)[0]
        assert brillo_a > fondo_a + 50 and brillo_b > fondo_a + 50, (x, y)


def prueba_diferencia_pinta_verde_lo_que_aparece_y_coral_lo_que_desaparece(alineado):
    aparece = pixel_png(alineado / "diferencia.png", MOVIL_B[0], MOVIL_B[1])
    desaparece = pixel_png(alineado / "diferencia.png", MOVIL_A[0], MOVIL_A[1])
    fondo = pixel_png(alineado / "diferencia.png", 15, 60)
    assert aparece[1] > aparece[0] + 40          # verde domina donde el objeto está en B
    assert desaparece[0] > desaparece[1] + 40    # coral domina donde estaba en A
    assert np.allclose(fondo, exportacion_png.FONDO, atol=12)  # donde nada cambia, el fondo de la guía visual


def prueba_el_wcs_publicado_reproduce_el_de_astropy(alineado):
    """El WCS de meta.json (base 0) debe dar las mismas RA/DEC que astropy sobre el FITS alineado."""
    metadatos_campo.escribir_meta("campo_prueba", raiz_datos=alineado.parents[1])
    meta = json.loads((alineado / "meta.json").read_text(encoding="utf-8"))
    w = meta["wcs"]
    assert w["proyeccion"] == "TAN"
    with fits.open(alineado / "epoca_a.fits") as h:
        referencia = WCS(h["IMAGE"].header).celestial
    for x, y in ((0.0, 0.0), (10.5, 90.25), (LADO - 1.0, LADO - 1.0)):
        ra, dec = referencia.pixel_to_world_values(x, y)
        xi = w["cd"][0][0] * (x - w["crpix_x"]) + w["cd"][0][1] * (y - w["crpix_y"])
        eta = w["cd"][1][0] * (x - w["crpix_x"]) + w["cd"][1][1] * (y - w["crpix_y"])
        a0, d0, xi, eta = np.radians([w["crval_ra_grados"], w["crval_dec_grados"], xi, eta])
        ra_c = np.degrees(a0 + np.arctan2(xi, np.cos(d0) - eta * np.sin(d0))) % 360
        dec_c = np.degrees(np.arctan((np.sin(d0) + eta * np.cos(d0)) * np.cos(np.radians(ra_c) - a0) / (np.cos(d0) - eta * np.sin(d0))))
        assert abs((ra_c - float(ra) + 180) % 360 - 180) * 3600 < 0.01 and abs(dec_c - float(dec)) * 3600 < 0.01


def prueba_origen_real_solo_si_todo_viene_de_irsa():
    irsa = {"exposiciones": [{"url_acceso": "https://irsa.ipac.caltech.edu/ibe/data/a.fits"}]}
    mezcla = {"exposiciones": [{"url_acceso": "https://irsa.ipac.caltech.edu/a.fits"}, {"url_acceso": "https://ejemplo.invalid/b.fits"}]}
    assert metadatos_campo.origen_de(irsa) == "real"
    assert metadatos_campo.origen_de(mezcla) is None
    assert metadatos_campo.origen_de({"exposiciones": []}) is None
