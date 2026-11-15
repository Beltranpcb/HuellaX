# ============================================================================
# ARCHIVO: modulos/m6_huella_espectral/pruebas/prueba_huella_espectral.py
# MODULO: m6_huella_espectral (Lote C)
# ROL: Comprueba el ajuste espectral sobre espectros sintéticos.
# LEE: Espectros sintéticos creados en memoria; recortes FITS sintéticos; contratos/espectros.schema.json (copia en esquemas/).
# PRODUCE: El veredicto de pytest.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de prueba: cuerpo negro de 300 K, espectro con pico en 4,26 micras.
#   1. Ejecutar comparación, ajuste de Planck  ->  tipo, temperatura
#   2. Comparar con cometa, con el intervalo de 270 a 330 K  ->  veredicto
#   Entrega a pytest: veredicto.
# VERIFICACION: Es el propio verificador: pasa cuando se cumplen los criterios de aceptación del módulo.
# USO: python -m pytest modulos/m6_huella_espectral/pruebas -q
# ESTRUCTURA: un bloque por archivo del módulo. El campo sintético (fixture `campo`) tiene tres
#             estrellas fijas y un objeto móvil de espectro plano conocido, en siete exposiciones.
# ESTADO: Módulo completo (partes 2, 3 y 4 del Lote C). Cubre los cinco archivos de cálculo.
# ============================================================================
import json
from pathlib import Path

import jsonschema
import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_area

from modulos.m6_huella_espectral import (
    ajuste_planck,
    comparacion_plantillas,
    escritura_espectros,
    fotometria,
    trayectoria,
)

MODULO = Path(__file__).resolve().parents[1]


def _ruta_esquema(nombre):
    """Contratos/ si existe el árbol completo; esquemas/ si el módulo va suelto."""
    for base in Path(__file__).resolve().parents:
        candidato = base / "contratos" / nombre
        if candidato.is_file():
            return candidato
    return MODULO / "esquemas" / nombre


ESQUEMA_ESPECTROS = json.loads(_ruta_esquema("espectros.schema.json").read_text(encoding="utf-8"))
LADO = 118
ESCALA_GRADOS = 6.15 / 3600
RUIDO = 0.01  # MJy/sr
ESTRELLAS = [(30.3, 25.7, 3.0), (85.6, 40.2, 2.0), (50.1, 95.4, 4.0)]
PIXEL_A, PIXEL_B = (64.4, 70.8), (69.4, 72.8)  # el objeto en la rejilla de referencia
MJD_A, MJD_B = 60900.0, 60900.25
FLUJO_MJY = 2.0  # espectro plano del objeto
BANDAS = {1: (0.75, 1.09), 2: (1.10, 1.62), 3: (1.63, 2.41), 4: (2.42, 3.82), 5: (3.83, 4.41), 6: (4.42, 5.00)}
# (id, papel, mjd, detector, desplazamiento del WCS en píxeles)
EXPOSICIONES = [("exp_a", "epoca_a", MJD_A, 3, (0.0, 0.0)),
                ("exp_b", "epoca_b", MJD_B, 3, (0.0, 0.0)),
                ("exp_t", "plantilla", 60720.0, 3, (0.0, 0.0)),
                ("exp_s1", "serie_espectral", 60900.04, 1, (0.0, 0.0)),
                ("exp_s2", "serie_espectral", 60900.10, 2, (2.3, -1.2)),
                ("exp_s5", "serie_espectral", 60900.16, 5, (0.0, 0.0)),
                ("exp_s6", "serie_espectral", 60900.22, 6, (-0.8, 0.5))]


def wcs_desplazado(dx, dy):
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [150.0, 2.0]
    w.wcs.crpix = [LADO / 2 + dx, LADO / 2 + dy]
    w.wcs.cdelt = [-ESCALA_GRADOS, ESCALA_GRADOS]
    return w


WCS_REFERENCIA = wcs_desplazado(0, 0)
A_MJY = 2 * np.pi * fotometria.SIGMA_PIXELES ** 2 * float(proj_plane_pixel_area(WCS_REFERENCIA)) * (np.pi / 180) ** 2 * 1e9


def cielo(pixel):
    ra, dec = WCS_REFERENCIA.pixel_to_world_values(*pixel)
    return float(ra), float(dec)


def gaussiana(x, y, pico):
    filas, columnas = np.indices((LADO, LADO))
    return pico * np.exp(-((columnas - x) ** 2 + (filas - y) ** 2) / (2 * fotometria.SIGMA_PIXELES ** 2))


def recorte(id_exposicion, mjd, detector, desplazamiento, flujo_objeto, semilla):
    """Recorte crudo con las seis extensiones; el objeto va en su posición prevista para esa fecha."""
    dx, dy = desplazamiento
    w = wcs_desplazado(dx, dy)
    azar = np.random.default_rng(semilla)
    zodi = 0.3 + 0.001 * np.indices((LADO, LADO))[1]
    imagen = zodi + azar.normal(0.0, RUIDO, (LADO, LADO))
    for x, y, pico in ESTRELLAS:
        imagen += gaussiana(x + dx, y + dy, pico)
    a, b = ({"ra_grados": r, "dec_grados": d} for r, d in (cielo(PIXEL_A), cielo(PIXEL_B)))
    ra, dec, _ = trayectoria.posicion_en(mjd, a, b, MJD_A, MJD_B)
    x, y = w.world_to_pixel_values(ra, dec)
    if flujo_objeto:
        imagen += gaussiana(float(x), float(y), flujo_objeto / A_MJY)
    lo, hi = BANDAS[detector]
    onda = np.linspace(lo, hi, LADO)[:, None] * np.ones((LADO, LADO))  # longitud de onda por fila
    cabecera = w.to_header()
    return fits.HDUList([fits.PrimaryHDU(),
                         fits.ImageHDU(imagen, cabecera, name="IMAGE"),
                         fits.ImageHDU(np.zeros((LADO, LADO), dtype=np.int32), cabecera, name="FLAGS"),
                         fits.ImageHDU(np.full((LADO, LADO), RUIDO ** 2), cabecera, name="VARIANCE"),
                         fits.ImageHDU(zodi, cabecera, name="ZODI"),
                         fits.ImageHDU(np.ones((5, 5)) / 25.0, name="PSF"),
                         fits.ImageHDU(onda, cabecera, name="WCS-WAVE")])


def escribir_campo(raiz, flujo_objeto=FLUJO_MJY):
    """Deja en raiz/ los datos de m1, m3 y m4 que m6 necesita para campo_prueba."""
    entrada = raiz / "m1_adquisicion" / "campo_prueba"
    (entrada / "recortes").mkdir(parents=True)
    exposiciones = []
    for semilla, (ide, papel, mjd, det, despl) in enumerate(EXPOSICIONES, 10):
        recorte(ide, mjd, det, despl, flujo_objeto, semilla).writeto(entrada / "recortes" / (ide + ".fits"))
        exposiciones.append({"id_exposicion": ide, "papel": papel, "mjd": mjd, "detector": det, "coleccion": "spherex_qr3",
                             "url_acceso": "https://ejemplo.invalid/%s.fits" % ide, "archivo_recorte": ide + ".fits"})
    (entrada / "seleccion.json").write_text(json.dumps({
        "version_contrato": "1", "campo": "campo_prueba", "nombre": "Campo de prueba",
        "centro": {"ra_grados": 150.0, "dec_grados": 2.0}, "radio_grados": 0.1, "exposiciones": exposiciones}), encoding="utf-8")

    def fuente(idf, epoca, pixel):
        ra, dec = cielo(pixel)
        return {"id_fuente": idf, "epoca": epoca, "ra_grados": ra, "dec_grados": dec, "x": pixel[0], "y": pixel[1],
                "flujo_mjy": FLUJO_MJY, "senal_ruido": 30.0, "incertidumbre_posicion_segarc": 0.5, "situacion": "huerfana"}
    (raiz / "m3_deteccion" / "campo_prueba").mkdir(parents=True)
    (raiz / "m3_deteccion" / "campo_prueba" / "fuentes.json").write_text(json.dumps({
        "version_contrato": "1", "campo": "campo_prueba",
        "epocas": {"epoca_a": {"mjd": MJD_A}, "epoca_b": {"mjd": MJD_B}, "plantilla": {"mjd": 60720.0}},
        "fuentes": [fuente("a001", "epoca_a", PIXEL_A), fuente("b001", "epoca_b", PIXEL_B),
                    fuente("a002", "epoca_a", (20.0, 20.0)), fuente("b002", "epoca_b", (20.3, 20.1))],
        "parejas": [{"id_pareja": "p001", "id_fuente_a": "a001", "id_fuente_b": "b001"},
                    {"id_pareja": "p002", "id_fuente_a": "a002", "id_fuente_b": "b002"}]}), encoding="utf-8")
    (raiz / "m4_movimiento" / "campo_prueba").mkdir(parents=True)
    (raiz / "m4_movimiento" / "campo_prueba" / "movimiento.json").write_text(json.dumps({
        "version_contrato": "1", "campo": "campo_prueba",
        "parejas": [{"id_pareja": "p001", "separacion_segarc": 33.1, "horas_transcurridas": 6.0, "velocidad_segarc_por_hora": 5.5,
                     "incertidumbre_velocidad": 0.12, "significancia": 46.8, "clase": "candidata"},
                    {"id_pareja": "p002", "separacion_segarc": 1.9, "horas_transcurridas": 6.0, "velocidad_segarc_por_hora": 0.3,
                     "incertidumbre_velocidad": 0.12, "significancia": 2.7, "clase": "no_concluyente"}]}), encoding="utf-8")
    return raiz


@pytest.fixture
def campo(tmp_path):
    return escribir_campo(tmp_path)


# ---------------------------------------------------------------- trayectoria
def prueba_la_posicion_prevista_coincide_con_a_y_con_b(campo):
    ruta = trayectoria.prever_campo("campo_prueba", raiz_datos=campo)
    objetos = json.loads(ruta.read_text(encoding="utf-8"))["objetos"]
    assert [o["id_pareja"] for o in objetos] == ["p001"]  # p002 es no_concluyente: no se mide
    por_id = {e["id_exposicion"]: e for e in objetos[0]["exposiciones"]}
    ra_a, dec_a = cielo(PIXEL_A)
    ra_b, dec_b = cielo(PIXEL_B)
    assert por_id["exp_a"]["ra_grados"] == pytest.approx(ra_a, abs=1e-6) and por_id["exp_a"]["dec_grados"] == pytest.approx(dec_a, abs=1e-6)
    assert por_id["exp_b"]["ra_grados"] == pytest.approx(ra_b, abs=1e-6) and por_id["exp_b"]["dec_grados"] == pytest.approx(dec_b, abs=1e-6)


def prueba_interpola_en_el_tiempo_y_descarta_la_plantilla(campo):
    objetos = json.loads(trayectoria.prever_campo("campo_prueba", raiz_datos=campo).read_text(encoding="utf-8"))["objetos"]
    ids = [e["id_exposicion"] for e in objetos[0]["exposiciones"]]
    assert ids == ["exp_a", "exp_s1", "exp_s2", "exp_s5", "exp_s6", "exp_b"]  # ordenadas por fecha
    assert objetos[0]["descartadas"] == [{"id_exposicion": "exp_t", "motivo": "fuera_del_intervalo"}]
    mitad = next(e for e in objetos[0]["exposiciones"] if e["id_exposicion"] == "exp_s2")  # mjd a 0,4 del intervalo
    ra_a, dec_a = cielo(PIXEL_A)
    ra_b, dec_b = cielo(PIXEL_B)
    assert mitad["dec_grados"] == pytest.approx(dec_a + 0.4 * (dec_b - dec_a), abs=1e-6)


def prueba_ascension_recta_no_salta_en_el_meridiano_cero():
    a, b = {"ra_grados": 359.99, "dec_grados": 0.0}, {"ra_grados": 0.01, "dec_grados": 0.0}
    ra, _, _ = trayectoria.posicion_en(0.5, a, b, 0.0, 1.0)
    assert ra == pytest.approx(0.0, abs=1e-9)
    assert trayectoria.diferencia_ra(0.01, 359.99) == pytest.approx(0.02)


def prueba_fuera_del_recorte_se_descarta():
    centro = {"ra_grados": 150.0, "dec_grados": 2.0}
    assert trayectoria.dentro_del_recorte(150.05, 2.05, centro, 0.1)
    assert not trayectoria.dentro_del_recorte(150.0, 2.11, centro, 0.1)
    seleccion = {"centro": centro, "radio_grados": 0.1, "exposiciones": [
        {"id_exposicion": "lejos", "archivo_recorte": "l.fits", "mjd": 1.9, "detector": 1}]}
    fuentes = {"epocas": {"epoca_a": {"mjd": 0.0}, "epoca_b": {"mjd": 1.0}},
               "fuentes": [{"id_fuente": "a001", "ra_grados": 150.0, "dec_grados": 2.0},
                           {"id_fuente": "b001", "ra_grados": 150.0, "dec_grados": 2.08}],
               "parejas": [{"id_pareja": "p001", "id_fuente_a": "a001", "id_fuente_b": "b001"}]}
    movimiento = {"parejas": [{"id_pareja": "p001", "clase": "candidata"}]}
    objeto = trayectoria.prever(seleccion, fuentes, movimiento)[0]
    assert objeto["exposiciones"] == []
    assert objeto["descartadas"][0]["motivo"] == "fuera_del_recorte"


# ----------------------------------------------------------------- fotometria
def prueba_recupera_el_flujo_y_la_longitud_de_onda(campo):
    trayectoria.prever_campo("campo_prueba", raiz_datos=campo)
    ruta = fotometria.medir_campo("campo_prueba", raiz_datos=campo)
    espectros = json.loads(ruta.read_text(encoding="utf-8"))["espectros"]
    assert len(espectros) == 1 and espectros[0]["agrupacion"] == "banda"
    puntos = espectros[0]["puntos"]
    assert [p["id_exposicion"] for p in puntos] == ["exp_a", "exp_s1", "exp_s2", "exp_s5", "exp_s6", "exp_b"]
    for p in puntos:
        assert abs(p["flujo_mjy"] - FLUJO_MJY) / FLUJO_MJY < 0.10, p
        assert p["error_mjy"] > 0 and p["senal_ruido"] > 5
        lo, hi = BANDAS[p["detector"]]
        assert lo <= p["longitud_onda_micras"] <= hi, p
        assert 0.75 <= p["longitud_onda_micras"] <= 5.0
    assert [p["mjd"] for p in puntos] == sorted(p["mjd"] for p in puntos)


def prueba_el_ajuste_sigue_al_objeto_en_un_wcs_desplazado(campo):
    """exp_s2 tiene el WCS desplazado (2,3, -1,2) píxeles: el centro ajustado debe caer donde está el objeto."""
    objetos = json.loads(trayectoria.prever_campo("campo_prueba", raiz_datos=campo).read_text(encoding="utf-8"))["objetos"]
    e = next(x for x in objetos[0]["exposiciones"] if x["id_exposicion"] == "exp_s2")
    with fits.open(campo / "m1_adquisicion" / "campo_prueba" / "recortes" / "exp_s2.fits") as hdul:
        medida = fotometria.medir_en_recorte(hdul, e["ra_grados"], e["dec_grados"])
        esperado = WCS(hdul["IMAGE"].header).world_to_pixel_values(e["ra_grados"], e["dec_grados"])
    assert medida is not None
    assert np.hypot(medida["x"] - float(esperado[0]), medida["y"] - float(esperado[1])) < 0.2


def prueba_senal_ruido_baja_promedia_por_detector(tmp_path):
    escribir_campo(tmp_path, flujo_objeto=0.04)  # unas 1,5 sigmas por banda
    trayectoria.prever_campo("campo_prueba", raiz_datos=tmp_path)
    espectros = json.loads(fotometria.medir_campo("campo_prueba", raiz_datos=tmp_path).read_text(encoding="utf-8"))["espectros"]
    e = espectros[0]
    assert e["agrupacion"] == "detector"
    detectores = [p["detector"] for p in e["puntos"]]
    assert len(detectores) == len(set(detectores)) <= 6
    assert next(p for p in e["puntos"] if p["detector"] == 3)["exposiciones_promediadas"] == 2  # exp_a y exp_b
    assert all(p["error_mjy"] > 0 for p in e["puntos"])


def prueba_sin_wcs_wave_falla_y_fuera_de_la_imagen_no_mide():
    hdul = recorte("x", MJD_A, 3, (0.0, 0.0), FLUJO_MJY, 1)
    ra, dec = WCS_REFERENCIA.pixel_to_world_values(1.0, 1.0)
    assert fotometria.medir_en_recorte(hdul, float(ra), float(dec)) is None  # en el borde no cabe la ventana
    del hdul["WCS-WAVE"]
    ra, dec = cielo(PIXEL_A)
    with pytest.raises(ValueError, match="WCS-WAVE"):
        fotometria.medir_en_recorte(hdul, ra, dec)


# ------------------------------------------------- comparación y escritura
def _puntos_sinteticos(lam, flujo, error, primer_detector=1):
    """Puntos con la forma que consume el módulo."""
    return [
        {
            "longitud_onda_micras": float(l),
            "flujo_mjy": float(f),
            "error_mjy": float(e),
            "mjd": 60900.0 + 0.04 * i,
            "detector": int(1 + (primer_detector - 1 + i) % 6),
            "senal_ruido": float(f / e),
        }
        for i, (l, f, e) in enumerate(zip(lam, flujo, error))
    ]


def _planck_de_la_prueba(lam, temperatura):
    """Ley de Planck escrita en la prueba, sin usar la del módulo."""
    h, c, k = 6.62607015e-34, 2.99792458e8, 1.380649e-23
    onda = np.asarray(lam, dtype=float) * 1e-6
    return 2.0 * h * c ** 2 / onda ** 5 / np.expm1(h * c / (onda * k * temperatura))


def prueba_planck_recupera_un_cuerpo_negro_de_300_k():
    lam = np.array([2.42, 3.12, 3.83, 4.41, 4.71, 5.00])
    flujo = _planck_de_la_prueba(lam, 300.0)
    flujo = 2.0 * flujo / flujo.max()
    medida = ajuste_planck.ajustar_puntos(_puntos_sinteticos(lam, flujo, 0.01 * flujo))
    assert medida is not None
    assert 270.0 <= medida["temperatura_k"] <= 330.0
    assert medida["pico_wien_micras"] == pytest.approx(2898.0 / medida["temperatura_k"], rel=1e-3)
    assert medida["incertidumbre_temperatura_k"] > 0


def prueba_un_pico_en_4_26_micras_recibe_el_tipo_cometa():
    lam = np.array([1.50, 2.00, 2.85, 3.50, 4.00, 4.26, 4.67, 4.90])

    def gaussiana(centro, ancho):
        return np.exp(-0.5 * ((lam - centro) / ancho) ** 2)

    flujo = 1.0 - 0.18 * gaussiana(2.85, 0.18) + 2.5 * gaussiana(4.26, 0.06) + 0.9 * gaussiana(4.67, 0.05)
    resultado = comparacion_plantillas.comparar(_puntos_sinteticos(lam, flujo, 0.02 * flujo))
    assert resultado["tipo"] == "cometa"
    assert len(resultado["ajustes"]) == 4
    chi2 = {ajuste["tipo"]: ajuste["chi2_reducido"] for ajuste in resultado["ajustes"]}
    assert chi2["cometa"] < chi2["asteroide_rocoso"]


def prueba_el_ruido_puro_queda_como_indeterminado():
    lam = np.array([1.20, 1.80, 2.50, 3.20, 4.00, 4.80])
    azar = np.random.default_rng(2026)
    flujo = azar.normal(0.0, 0.05, lam.size)
    flujo -= flujo.mean()  # ruido sin flujo neto: no hay nada que detectar
    puntos = _puntos_sinteticos(lam, flujo, np.full(lam.size, 0.05))
    assert comparacion_plantillas.significancia_deteccion(puntos) < 3.0
    assert comparacion_plantillas.comparar(puntos)["tipo"] == "indeterminado"


def prueba_las_plantillas_cubren_el_rango_del_contrato():
    plantillas = comparacion_plantillas.cargar_plantillas()
    assert {plantilla["tipo"] for plantilla in plantillas} == {
        "asteroide_rocoso", "asteroide_oscuro", "cometa", "enana_marron"}
    for plantilla in plantillas:
        assert plantilla["onda"].min() <= 0.75 and plantilla["onda"].max() >= 5.0
        assert np.all(plantilla["flujo"] > 0)


def prueba_la_escritura_produce_un_espectros_json_valido(tmp_path):
    directorio = tmp_path / "m6_huella_espectral" / "campo_prueba"
    directorio.mkdir(parents=True)
    lam = np.array([1.50, 2.50, 3.50, 4.26, 4.67, 4.90])
    flujo = 1.0 + 2.5 * np.exp(-0.5 * ((lam - 4.26) / 0.06) ** 2)
    puntos = _puntos_sinteticos(lam, flujo, 0.02 * flujo)
    (directorio / "espectro_medido.json").write_text(json.dumps({
        "campo": "campo_prueba",
        "espectros": [{"id_pareja": "p001", "agrupacion": "banda", "puntos": puntos}],
    }), encoding="utf-8")
    (directorio / "tipo_espectral.json").write_text(json.dumps({
        "campo": "campo_prueba",
        "espectros": [{"id_pareja": "p001", "tipo": "cometa",
                       "ajustes_plantilla": [{"tipo": "cometa", "chi2_reducido": 1.1},
                                             {"tipo": "asteroide_rocoso", "chi2_reducido": 8.0}]}],
    }), encoding="utf-8")
    (directorio / "temperatura.json").write_text(json.dumps({
        "campo": "campo_prueba",
        "espectros": [{"id_pareja": "p001", "temperatura_k": 255.0,
                       "incertidumbre_temperatura_k": 20.0, "pico_wien_micras": 11.36}],
    }), encoding="utf-8")

    datos = json.loads(
        escritura_espectros.escribir_campo("campo_prueba", raiz_datos=tmp_path).read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator(ESQUEMA_ESPECTROS).validate(datos)
    assert datos["version_contrato"] == "1"
    assert datos["espectros"][0]["tipo"] == "cometa"
    assert set(datos["espectros"][0]["puntos"][0]) == {
        "longitud_onda_micras", "flujo_mjy", "error_mjy", "mjd", "detector"}


def prueba_el_pipeline_completo_clasifica_y_valida(tmp_path):
    directorio = tmp_path / "m6_huella_espectral" / "campo_prueba"
    directorio.mkdir(parents=True)
    lam = np.array([1.50, 2.00, 2.85, 3.50, 4.00, 4.26, 4.67, 4.90])
    flujo = (1.0 - 0.18 * np.exp(-0.5 * ((lam - 2.85) / 0.18) ** 2)
             + 2.5 * np.exp(-0.5 * ((lam - 4.26) / 0.06) ** 2)
             + 0.9 * np.exp(-0.5 * ((lam - 4.67) / 0.05) ** 2))
    (directorio / "espectro_medido.json").write_text(json.dumps({
        "campo": "campo_prueba",
        "espectros": [{"id_pareja": "p001", "agrupacion": "banda",
                       "puntos": _puntos_sinteticos(lam, flujo, 0.02 * flujo)}],
    }), encoding="utf-8")

    comparacion_plantillas.clasificar_campo("campo_prueba", raiz_datos=tmp_path)
    ajuste_planck.ajustar_campo("campo_prueba", raiz_datos=tmp_path)
    datos = json.loads(
        escritura_espectros.escribir_campo("campo_prueba", raiz_datos=tmp_path).read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator(ESQUEMA_ESPECTROS).validate(datos)
    assert datos["espectros"][0]["tipo"] == "cometa"
    assert datos["espectros"][0]["ajustes_plantilla"]
    assert len(datos["espectros"][0]["puntos"]) == len(lam)


def prueba_la_longitud_de_onda_sale_de_la_rejilla_dispersa():
    """WCS-WAVE real no es una imagen: es una rejilla de nodos con (onda, error)."""

    class _Hdu:
        def __init__(self, data=None, header=None):
            self.data = data
            self.header = header or {}

    xs = np.linspace(1, 2040, 9)
    ys = np.linspace(1, 2040, 14)
    valores = np.zeros((14, 9, 2), dtype=float)
    for i, _yv in enumerate(ys):
        for j, xv in enumerate(xs):
            valores[i, j, 0] = 4.4 + 0.6 * (xv / 2040.0)
            valores[i, j, 1] = 0.04
    tipo = np.dtype([("X", "i4", (9,)), ("Y", "i4", (14,)), ("VALUES", "f8", (14, 9, 2))])
    registro = np.zeros(1, dtype=tipo)
    registro["X"][0] = xs.astype("i4")
    registro["Y"][0] = ys.astype("i4")
    registro["VALUES"][0] = valores

    # CRPIX1W negativo: el recorte empieza en la columna 856 del detector.
    hdul = {
        "IMAGE": _Hdu(np.zeros((234, 234)), {"CRPIX1W": -855.0, "CRPIX2W": -830.0}),
        "WCS-WAVE": _Hdu(registro),
    }

    onda = fotometria.longitud_de_onda(hdul, 0.0, 0.0)
    assert onda == pytest.approx(4.4 + 0.6 * (856 / 2040.0), abs=0.01)

    onda2 = fotometria.longitud_de_onda(hdul, 100.0, 50.0)
    assert onda2 == pytest.approx(4.4 + 0.6 * ((100 + 855) / 2040.0), abs=0.01)


# ----------------------------------- chi2 con grados de libertad y advertencias
ESQUEMA_PLANTILLAS = json.loads(_ruta_esquema("plantillas.schema.json").read_text(encoding="utf-8"))


def _espectro_de_cometa(n=8):
    lam = np.linspace(1.5, 4.9, n)
    flujo = 1.0 + 2.5 * np.exp(-0.5 * ((lam - 4.26) / 0.06) ** 2) + 0.2 * (lam - 1.5)
    return _puntos_sinteticos(lam, flujo, 0.02 * flujo)


def prueba_cada_ajuste_declara_grados_de_libertad_y_puntos():
    puntos = _espectro_de_cometa(8)
    resultado = comparacion_plantillas.comparar(puntos)
    assert len(resultado["ajustes"]) == 4
    for ajuste in resultado["ajustes"]:
        assert ajuste["n_puntos"] == 8
        assert ajuste["grados_libertad"] == 7  # N menos la escala ajustada
        assert ajuste["origen_plantilla"] == "sintetica" and ajuste["referencia_plantilla"] is None
    assert any(a["escala"] > 0 for a in resultado["ajustes"])


def prueba_con_un_solo_punto_no_se_inventa_el_chi2():
    resultado = comparacion_plantillas.comparar(_puntos_sinteticos([2.0], [1.0], [0.1]))
    assert resultado["ajustes"] == [] and resultado["tipo"] == "indeterminado"


def prueba_las_advertencias_reflejan_la_calidad_y_el_tipo():
    resultado = comparacion_plantillas.comparar(_espectro_de_cometa(8))
    assert "plantillas_sinteticas" in resultado["advertencias"]
    if resultado["tipo"] == "cometa":
        assert "luz_reflejada_y_termica" in resultado["advertencias"]
    corto = comparacion_plantillas.comparar(_puntos_sinteticos([1.0, 1.5, 2.0], [1.0, 1.1, 1.2], [0.5, 0.5, 0.5]), agrupacion="detector")
    assert {"senal_ruido_baja", "cobertura_espectral_parcial", "agrupado_por_detector"} <= set(corto["advertencias"])


def prueba_planck_avisa_si_el_pico_de_wien_cae_fuera_de_rango(tmp_path):
    directorio = tmp_path / "m6_huella_espectral" / "campo_prueba"
    directorio.mkdir(parents=True)
    lam = np.array([2.42, 3.12, 3.83, 4.41, 4.71, 5.00])
    flujo = _planck_de_la_prueba(lam, 200.0)  # pico de Wien en 14,5 micras
    flujo = 2.0 * flujo / flujo.max()
    (directorio / "espectro_medido.json").write_text(json.dumps({
        "campo": "campo_prueba",
        "espectros": [{"id_pareja": "p001", "agrupacion": "banda", "puntos": _puntos_sinteticos(lam, flujo, 0.01 * flujo)}]}), encoding="utf-8")
    ruta = ajuste_planck.ajustar_campo("campo_prueba", raiz_datos=tmp_path)
    espectro = json.loads(ruta.read_text(encoding="utf-8"))["espectros"][0]
    if espectro["temperatura_k"] is not None:
        assert espectro["pico_wien_micras"] > 5.0
        assert espectro["advertencias"] == ["cuerpo_negro_fuera_de_rango"]


def prueba_espectros_json_trae_calidad_advertencias_y_plantillas_publicadas(tmp_path):
    directorio = tmp_path / "m6_huella_espectral" / "campo_prueba"
    directorio.mkdir(parents=True)
    puntos = _espectro_de_cometa(8)
    (directorio / "espectro_medido.json").write_text(json.dumps({
        "campo": "campo_prueba", "espectros": [{"id_pareja": "p001", "agrupacion": "banda", "puntos": puntos}]}), encoding="utf-8")
    comparacion_plantillas.clasificar_campo("campo_prueba", raiz_datos=tmp_path)
    ajuste_planck.ajustar_campo("campo_prueba", raiz_datos=tmp_path)
    datos = json.loads(escritura_espectros.escribir_campo("campo_prueba", raiz_datos=tmp_path).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(ESQUEMA_ESPECTROS).validate(datos)
    espectro = datos["espectros"][0]
    assert espectro["calidad"]["n_puntos"] == 8
    assert espectro["calidad"]["cobertura_micras"] == [1.5, 4.9]
    assert "plantillas_sinteticas" in espectro["advertencias"]
    publicadas = json.loads((tmp_path / "m6_huella_espectral" / "plantillas.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(ESQUEMA_PLANTILLAS).validate(publicadas)
    assert {p["tipo"] for p in publicadas["plantillas"]} == {"asteroide_rocoso", "asteroide_oscuro", "cometa", "enana_marron"}
    assert all(p["origen_plantilla"] == "sintetica" for p in publicadas["plantillas"])


# ------------------------------------------- composición molecular (sintética)
from modulos.m6_huella_espectral import identificacion_molecular as im  # noqa: E402

LAM_DENSA = np.linspace(0.75, 5.0, 120)  # ~0,036 µm entre puntos: espectro sintético por banda


def _espectro_molecular(rasgos=(), continuo=None, ruido=0.01, semilla=7):
    """Espectro sintético: continuo + rasgos de caja (ventana, profundidad) + ruido gaussiano."""
    azar = np.random.default_rng(semilla)
    base = 1.0 + 0.1 * LAM_DENSA if continuo is None else continuo(LAM_DENSA)
    flujo = base.copy()
    for (bajo, alto), profundidad in rasgos:
        flujo[(LAM_DENSA >= bajo) & (LAM_DENSA <= alto)] += profundidad
    flujo += azar.normal(0.0, ruido, LAM_DENSA.size)
    return [{"longitud_onda_micras": float(l), "flujo_mjy": float(f), "error_mjy": ruido, "mjd": 60900.0, "detector": 1}
            for l, f in zip(LAM_DENSA, flujo)]


def _estados(composicion):
    return {m["formula"]: m["estado"] for m in composicion["moleculas"]}


def _molecula(composicion, formula):
    return next(m for m in composicion["moleculas"] if m["formula"] == formula)


def prueba_banda_aislada_de_co2_se_detecta_en_un_asteroide():
    c = im.analizar(_espectro_molecular([((4.20, 4.33), -0.08)]), tipo="asteroide_rocoso")
    co2 = _molecula(c, "CO2")
    assert co2["estado"] == "detectada" and co2["rasgo"] == "absorcion", co2["explicacion"]
    assert co2["metrica"]["nombre"] == "significancia_sigma" and co2["metrica"]["valor"] < -5
    assert co2["resolucion_espectral"] == 110
    assert _estados(c)["CH4"] == "sin_rasgo"


def prueba_en_un_cometa_el_co2_debe_verse_en_emision():
    emision = _molecula(im.analizar(_espectro_molecular([((4.20, 4.33), 0.08)]), tipo="cometa"), "CO2")
    assert emision["estado"] == "detectada" and emision["rasgo"] == "emision", emision["explicacion"]
    absorcion = _molecula(im.analizar(_espectro_molecular([((4.20, 4.33), -0.08)]), tipo="cometa"), "CO2")
    assert absorcion["estado"] == "candidata"
    assert "se esperaba emision" in absorcion["explicacion"]


def prueba_el_ruido_puro_no_produce_detecciones():
    for semilla in range(5):
        estados = _estados(im.analizar(_espectro_molecular(semilla=semilla), tipo="asteroide_rocoso"))
        assert "detectada" not in estados.values() and "candidata" not in estados.values(), (semilla, estados)


def prueba_un_continuo_curvo_sin_bandas_no_produce_falsos_positivos():
    def termico(lam):
        return 0.4 + 0.02 * np.exp(0.9 * lam)  # subida térmica hacia 5 µm
    estados = _estados(im.analizar(_espectro_molecular(continuo=termico), tipo="asteroide_oscuro"))
    assert "detectada" not in estados.values(), estados


def prueba_el_agua_en_un_asteroide_queda_ambigua_con_minerales_hidratados():
    agua = _molecula(im.analizar(_espectro_molecular([((2.85, 3.15), -0.10)]), tipo="asteroide_oscuro"), "H2O")
    assert agua["estado"] == "candidata"
    assert agua["ambigua_con"] == ["minerales_hidratados_OH"]
    assert "otra explicación plausible" in agua["explicacion"]


def prueba_con_tipo_indeterminado_nada_pasa_de_candidata():
    c = im.analizar(_espectro_molecular([((4.20, 4.33), -0.08)]), tipo="indeterminado")
    assert _molecula(c, "CO2")["estado"] == "candidata"


def prueba_una_banda_sin_resolver_no_se_declara_detectada():
    nh3 = _molecula(im.analizar(_espectro_molecular([((2.17, 2.27), -0.10)]), tipo="enana_marron"), "NH3")
    assert nh3["estado"] != "detectada"
    assert "resolucion_incompatible" in nh3["advertencias"]


def prueba_espectro_por_detector_o_corto_da_datos_insuficientes():
    por_detector = im.analizar(_espectro_molecular([((4.20, 4.33), -0.08)]), agrupacion="detector", tipo="cometa")
    assert set(_estados(por_detector).values()) == {"datos_insuficientes"}
    assert all("agrupado_por_detector" in m["advertencias"] for m in por_detector["moleculas"])
    corto = im.analizar(_espectro_molecular()[:5], tipo="cometa")
    assert set(_estados(corto).values()) == {"datos_insuficientes"}
    assert all(m["metrica"] is None for m in corto["moleculas"])


def prueba_cobertura_parcial_deja_fuera_las_bandas_sin_puntos():
    puntos = [p for p in _espectro_molecular() if p["longitud_onda_micras"] < 3.0]
    estados = _estados(im.analizar(puntos, tipo="asteroide_rocoso"))
    assert estados["CO2"] == estados["CO"] == estados["CH4"] == "datos_insuficientes"


def prueba_la_composicion_llega_a_espectros_json_y_valida(tmp_path):
    directorio = tmp_path / "m6_huella_espectral" / "campo_prueba"
    directorio.mkdir(parents=True)
    puntos = _espectro_molecular([((4.20, 4.33), 0.08)])
    (directorio / "espectro_medido.json").write_text(json.dumps({
        "campo": "campo_prueba", "espectros": [{"id_pareja": "p001", "agrupacion": "banda", "puntos": puntos}]}), encoding="utf-8")
    comparacion_plantillas.clasificar_campo("campo_prueba", raiz_datos=tmp_path)
    ajuste_planck.ajustar_campo("campo_prueba", raiz_datos=tmp_path)
    im.analizar_campo("campo_prueba", raiz_datos=tmp_path)
    datos = json.loads(escritura_espectros.escribir_campo("campo_prueba", raiz_datos=tmp_path).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(ESQUEMA_ESPECTROS).validate(datos)
    composicion = datos["espectros"][0]["composicion"]
    assert [m["formula"] for m in composicion["moleculas"]] == ["H2O", "CH4", "CO2", "CO", "NH3"]
    assert all(m["referencia"] for m in composicion["moleculas"])


def prueba_bandas_vecinas_de_agua_y_metano_se_miden_por_separado():
    """En una enana marrón con H2O y CH4 a la vez, cada banda se mide con su propio continuo."""
    c = im.analizar(_espectro_molecular([((2.85, 3.15), -0.10), ((3.20, 3.45), -0.12)]), tipo="enana_marron")
    estados = _estados(c)
    assert estados["H2O"] in ("candidata", "detectada") and estados["CH4"] in ("candidata", "detectada"), estados
    solo_metano = _estados(im.analizar(_espectro_molecular([((3.20, 3.45), -0.12)]), tipo="enana_marron"))
    assert solo_metano["H2O"] in ("sin_rasgo", "compatible"), solo_metano  # el CH4 no contamina al H2O


def prueba_un_desplazamiento_pequeno_de_la_banda_sigue_dentro_de_la_ventana():
    """Temperatura o entorno pueden mover la banda unas centésimas de micra."""
    desplazada = _molecula(im.analizar(_espectro_molecular([((4.24, 4.33), -0.08)]), tipo="asteroide_rocoso"), "CO2")
    assert desplazada["estado"] in ("candidata", "detectada") and desplazada["rasgo"] == "absorcion"


def prueba_ningun_estado_usa_porcentajes_de_confianza():
    c = im.analizar(_espectro_molecular([((4.20, 4.33), -0.08)]), tipo="asteroide_rocoso")
    for m in c["moleculas"]:
        assert m["metrica"] is None or m["metrica"]["nombre"] == "significancia_sigma"
        assert "confianza" not in m["explicacion"].lower()
