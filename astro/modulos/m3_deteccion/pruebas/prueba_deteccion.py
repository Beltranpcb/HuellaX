# ============================================================================
# ARCHIVO: modulos/m3_deteccion/pruebas/prueba_deteccion.py
# MODULO: m3_deteccion (Lote B)
# ROL: Comprueba la detección sobre imágenes de ruido con fuentes inyectadas.
# LEE: Tres imágenes sintéticas creadas en memoria; contratos/fuentes.schema.json (copia en esquemas/).
# PRODUCE: El veredicto de pytest.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de prueba: FITS sintéticos con una fuente desplazada.
#   1. Ejecutar detección, emparejamiento, propuesta  ->  fuentes.json temporal
#   2. Comparar con las posiciones inyectadas  ->  error en píxeles
#   3. Validar contra fuentes.schema.json  ->  veredicto
#   Entrega a pytest: veredicto.
# VERIFICACION: Es el propio verificador: pasa cuando se cumplen los criterios de aceptación del módulo.
# USO: python -m pytest modulos/m3_deteccion/pruebas -q
# ESTRUCTURA: tres bloques, uno por archivo del módulo (deteccion_fuentes, emparejamiento,
#             propuesta_parejas), más una prueba del módulo completo al final.
# ============================================================================
import json
from pathlib import Path

import jsonschema
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from modulos.m3_deteccion import deteccion_fuentes, emparejamiento, propuesta_parejas

def _ruta_esquema(nombre):
    """Devuelve contratos/<nombre> si existe el arbol completo; si no, esquemas/<nombre>."""
    for base in Path(__file__).resolve().parents:
        candidato = base / "contratos" / nombre
        if candidato.is_file():
            return candidato
    return Path(__file__).resolve().parents[1] / "esquemas" / nombre

ESQUEMA_FUENTES = json.loads(_ruta_esquema("fuentes.schema.json").read_text(encoding="utf-8"))

LADO = 118
ESCALA_GRADOS = 6.15 / 3600
RUIDO = 0.01  # MJy/sr
ESTRELLAS_FIJAS = [(30.3, 25.7, 3.0), (85.6, 40.2, 2.0), (50.1, 95.4, 4.0)]  # x, y, pico
MOVIL_EN_A, MOVIL_EN_B = (64.4, 70.8, 1.0), (69.4, 72.8, 1.0)  # se desplaza 5,4 píxeles entre A y B
META = {
    "campo": "campo_prueba",
    "escala_segarc_por_pixel": 6.15,
    "horas_entre_a_b": 6.0,  # separación máxima admisible: 60 * 6 / 6,15 = 58,5 píxeles
    "epocas": {"epoca_a": {"mjd": 60900.0}, "epoca_b": {"mjd": 60900.25}, "plantilla": {"mjd": 60720.0}},
}


# --------------------------------------------------------------- utilidades
def rejilla():
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [150.0, 2.0]
    wcs.wcs.crpix = [LADO / 2, LADO / 2]
    wcs.wcs.cdelt = [-ESCALA_GRADOS, ESCALA_GRADOS]
    return wcs


def imagen_sintetica(fuentes, semilla):
    """Ruido gaussiano con un fondo de 0,5 MJy/sr más fuentes gaussianas de 2 píxeles de anchura."""
    azar = np.random.default_rng(semilla)
    imagen = 0.5 + azar.normal(0.0, RUIDO, (LADO, LADO))
    filas, columnas = np.indices(imagen.shape)
    sigma = deteccion_fuentes.ANCHURA_PIXELES / 2.355
    for x, y, pico in fuentes:
        imagen += pico * np.exp(-((columnas - x) ** 2 + (filas - y) ** 2) / (2 * sigma ** 2))
    varianza = np.full(imagen.shape, RUIDO ** 2)
    flags = np.zeros(imagen.shape, dtype=np.int32)
    return imagen, varianza, flags


def escribir_campo_sintetico(raiz):
    """Escribe en raiz/m2_alineacion/campo_prueba los tres FITS alineados con su meta.json."""
    entrada = raiz / "m2_alineacion" / "campo_prueba"
    entrada.mkdir(parents=True)
    moviles = {"epoca_a": MOVIL_EN_A, "epoca_b": MOVIL_EN_B, "plantilla": None}
    for semilla, (epoca, movil) in enumerate(moviles.items(), 10):
        imagen, varianza, flags = imagen_sintetica(ESTRELLAS_FIJAS + ([movil] if movil else []), semilla)
        cabecera = rejilla().to_header()
        fits.HDUList([fits.PrimaryHDU(),
                      fits.ImageHDU(imagen, cabecera, name="IMAGE"),
                      fits.ImageHDU(varianza, cabecera, name="VARIANCE"),
                      fits.ImageHDU(flags, cabecera, name="FLAGS")]).writeto(entrada / (epoca + ".fits"))
    (entrada / "meta.json").write_text(json.dumps(META), encoding="utf-8")


def mas_cercana(fuentes, x, y):
    return min(fuentes, key=lambda f: np.hypot(f["x"] - x, f["y"] - y))


def deteccion(id_fuente, epoca, x, y, toca_mascara=False, flujo=1.0, situacion=None):
    d = {"id_fuente": id_fuente, "epoca": epoca, "ra_grados": 150.0, "dec_grados": 2.0, "x": x, "y": y,
         "flujo_mjy": flujo, "senal_ruido": 20.0, "incertidumbre_posicion_segarc": 0.5}
    if situacion is None:
        d["toca_mascara"] = toca_mascara
    else:
        d["situacion"] = situacion
        d["coincidencias"] = {"epoca_a": None, "epoca_b": None, "plantilla": None}
    return d


def situaciones(fuentes):
    return {f["id_fuente"]: f["situacion"] for f in fuentes}


def validar_fuentes(contenido):
    jsonschema.Draft202012Validator(ESQUEMA_FUENTES).validate(contenido)


# ======================================================= 1. deteccion_fuentes
def prueba_fuente_inyectada_se_recupera():
    imagen, varianza, flags = imagen_sintetica(ESTRELLAS_FIJAS + [(64.4, 70.8, 0.5)], semilla=1)
    fuentes = deteccion_fuentes.detectar_en_imagen(imagen, varianza, flags, rejilla())
    for x, y, _ in ESTRELLAS_FIJAS + [(64.4, 70.8, 0.5)]:
        hallada = mas_cercana(fuentes, x, y)
        assert np.hypot(hallada["x"] - x, hallada["y"] - y) <= 0.5


def prueba_cada_deteccion_cumple_los_minimos():
    imagen, varianza, flags = imagen_sintetica(ESTRELLAS_FIJAS, semilla=2)
    fuentes = deteccion_fuentes.detectar_en_imagen(imagen, varianza, flags, rejilla())
    assert len(fuentes) >= len(ESTRELLAS_FIJAS)
    for f in fuentes:
        assert f["senal_ruido"] >= 5
        assert f["incertidumbre_posicion_segarc"] >= 0.5


def prueba_coordenadas_del_cielo_coinciden_con_la_rejilla():
    imagen, varianza, flags = imagen_sintetica(ESTRELLAS_FIJAS, semilla=3)
    wcs = rejilla()
    fuentes = deteccion_fuentes.detectar_en_imagen(imagen, varianza, flags, wcs)
    x, y, _ = ESTRELLAS_FIJAS[0]
    hallada = mas_cercana(fuentes, x, y)
    ra, dec = wcs.pixel_to_world_values(x, y)
    assert abs(hallada["dec_grados"] - dec) * 3600 <= 0.5 * 6.15
    assert abs(hallada["ra_grados"] - ra) * 3600 <= 0.5 * 6.15


def prueba_pixel_marcado_en_flags_no_genera_fuente():
    imagen, varianza, flags = imagen_sintetica(ESTRELLAS_FIJAS, semilla=4)
    imagen[60, 60] += 50.0  # píxel caliente
    flags[60, 60] = 1 << 6
    fuentes = deteccion_fuentes.detectar_en_imagen(imagen, varianza, flags, rejilla())
    assert all(np.hypot(f["x"] - 60, f["y"] - 60) > 2 for f in fuentes)


def prueba_bit_source_no_borra_la_estrella():
    imagen, varianza, flags = imagen_sintetica(ESTRELLAS_FIJAS, semilla=5)
    x, y, _ = ESTRELLAS_FIJAS[0]
    flags[int(y) - 2:int(y) + 3, int(x) - 2:int(x) + 3] = 1 << 21
    fuentes = deteccion_fuentes.detectar_en_imagen(imagen, varianza, flags, rejilla())
    hallada = mas_cercana(fuentes, x, y)
    assert np.hypot(hallada["x"] - x, hallada["y"] - y) <= 0.5
    assert hallada["toca_mascara"] is False


def prueba_ruido_puro_no_da_detecciones():
    for semilla in range(20, 25):
        imagen, varianza, flags = imagen_sintetica([], semilla)
        assert deteccion_fuentes.detectar_en_imagen(imagen, varianza, flags, rejilla()) == []


def prueba_deteccion_escribe_detecciones_json(tmp_path):
    escribir_campo_sintetico(tmp_path)
    ruta = deteccion_fuentes.detectar_campo("campo_prueba", raiz_datos=tmp_path)
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert ruta == tmp_path / "m3_deteccion" / "campo_prueba" / "detecciones.json"
    por_epoca = {e: [d for d in datos["detecciones"] if d["epoca"] == e] for e in ("epoca_a", "epoca_b", "plantilla")}
    assert len(por_epoca["epoca_a"]) == 4
    assert len(por_epoca["epoca_b"]) == 4
    assert len(por_epoca["plantilla"]) == 3
    assert por_epoca["epoca_a"][0]["id_fuente"] == "a001"
    assert por_epoca["plantilla"][0]["id_fuente"] == "t001"


# ========================================================== 2. emparejamiento
ESCENARIO = [
    # estrella fija en las tres imágenes (desviaciones menores que 1 píxel)
    deteccion("a001", "epoca_a", 30.0, 25.0),
    deteccion("b001", "epoca_b", 30.4, 25.3),
    deteccion("t001", "plantilla", 29.7, 24.8),
    # objeto que se mueve 5 píxeles entre A y B, ausente en la plantilla
    deteccion("a002", "epoca_a", 64.0, 70.0),
    deteccion("b002", "epoca_b", 69.0, 72.0),
    # estrella presente en A y en la plantilla pero no detectada en B
    deteccion("a003", "epoca_a", 85.0, 40.0),
    deteccion("t003", "plantilla", 85.5, 40.2),
    # fuente sobre píxeles marcados en FLAGS
    deteccion("b004", "epoca_b", 10.0, 10.0, toca_mascara=True),
]


def prueba_toda_fuente_recibe_situacion():
    fuentes = emparejamiento.clasificar(ESCENARIO)
    assert len(fuentes) == len(ESCENARIO)
    assert all(f["situacion"] in ("estacionaria", "huerfana", "descartada") for f in fuentes)
    assert all("toca_mascara" not in f for f in fuentes)


def prueba_estrella_en_las_tres_imagenes_es_estacionaria():
    s = situaciones(emparejamiento.clasificar(ESCENARIO))
    assert s["a001"] == s["b001"] == s["t001"] == "estacionaria"


def prueba_objeto_desplazado_queda_huerfano_en_a_y_en_b():
    s = situaciones(emparejamiento.clasificar(ESCENARIO))
    assert s["a002"] == "huerfana"
    assert s["b002"] == "huerfana"


def prueba_estrella_solo_en_a_y_plantilla_es_estacionaria():
    s = situaciones(emparejamiento.clasificar(ESCENARIO))
    assert s["a003"] == "estacionaria"
    assert s["t003"] == "estacionaria"


def prueba_fuente_sobre_mascara_queda_descartada():
    assert situaciones(emparejamiento.clasificar(ESCENARIO))["b004"] == "descartada"


def prueba_coincidencias_apuntan_a_los_ids_correctos():
    fuentes = {f["id_fuente"]: f for f in emparejamiento.clasificar(ESCENARIO)}
    assert fuentes["a001"]["coincidencias"] == {"epoca_a": "a001", "epoca_b": "b001", "plantilla": "t001"}
    assert fuentes["a002"]["coincidencias"] == {"epoca_a": "a002", "epoca_b": None, "plantilla": None}


def prueba_cada_destino_se_usa_una_sola_vez():
    origen = [deteccion("a001", "epoca_a", 50.0, 50.0), deteccion("a002", "epoca_a", 50.6, 50.0)]
    destino = [deteccion("b001", "epoca_b", 50.1, 50.0)]
    assert emparejamiento.emparejar_imagenes(origen, destino) == {"a001": "b001", "a002": None}


def prueba_a_un_pixel_justo_coincide_y_mas_lejos_no():
    origen = [deteccion("a001", "epoca_a", 0.0, 0.0)]
    assert emparejamiento.emparejar_imagenes(origen, [deteccion("b001", "epoca_b", 1.0, 0.0)])["a001"] == "b001"
    assert emparejamiento.emparejar_imagenes(origen, [deteccion("b001", "epoca_b", 1.01, 0.0)])["a001"] is None


def prueba_emparejamiento_escribe_situaciones_json(tmp_path):
    directorio = tmp_path / "m3_deteccion" / "campo_prueba"
    directorio.mkdir(parents=True)
    (directorio / "detecciones.json").write_text(
        json.dumps({"campo": "campo_prueba", "detecciones": ESCENARIO}), encoding="utf-8")
    ruta = emparejamiento.emparejar_campo("campo_prueba", raiz_datos=tmp_path)
    assert ruta == directorio / "situaciones.json"
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert datos["campo"] == "campo_prueba"
    assert situaciones(datos["fuentes"])["a002"] == "huerfana"


# ======================================================= 3. propuesta_parejas
def prueba_una_fuente_desplazada_da_exactamente_una_pareja():
    fuentes = [deteccion("a001", "epoca_a", 30.0, 25.0, situacion="estacionaria"),
               deteccion("b001", "epoca_b", 30.0, 25.0, situacion="estacionaria"),
               deteccion("a002", "epoca_a", 64.0, 70.0, situacion="huerfana"),
               deteccion("b002", "epoca_b", 69.0, 72.0, situacion="huerfana")]
    assert propuesta_parejas.proponer(fuentes, META) == [{"id_pareja": "p001", "id_fuente_a": "a002", "id_fuente_b": "b002"}]


def prueba_fuentes_estacionarias_o_descartadas_no_forman_parejas():
    fuentes = [deteccion("a001", "epoca_a", 30.0, 25.0, situacion="estacionaria"),
               deteccion("b001", "epoca_b", 35.0, 25.0, situacion="descartada")]
    assert propuesta_parejas.proponer(fuentes, META) == []


def prueba_separacion_mayor_que_la_velocidad_maxima_no_forma_pareja():
    tope = propuesta_parejas.separacion_maxima_pixeles(META)
    fuentes = [deteccion("a001", "epoca_a", 10.0, 10.0, situacion="huerfana"),
               deteccion("b001", "epoca_b", 10.0 + tope + 1.0, 10.0, situacion="huerfana")]
    assert propuesta_parejas.proponer(fuentes, META) == []
    fuentes[1]["x"] = 10.0 + tope - 1.0
    assert len(propuesta_parejas.proponer(fuentes, META)) == 1


def prueba_brillo_muy_distinto_no_forma_pareja():
    fuentes = [deteccion("a001", "epoca_a", 10.0, 10.0, flujo=1.0, situacion="huerfana"),
               deteccion("b001", "epoca_b", 15.0, 10.0, flujo=2.5, situacion="huerfana")]
    assert propuesta_parejas.proponer(fuentes, META) == []
    fuentes[1]["flujo_mjy"] = 1.9
    assert len(propuesta_parejas.proponer(fuentes, META)) == 1


def prueba_cada_fuente_entra_en_una_sola_pareja_y_gana_la_mas_cercana():
    fuentes = [deteccion("a001", "epoca_a", 10.0, 10.0, situacion="huerfana"),
               deteccion("b001", "epoca_b", 14.0, 10.0, situacion="huerfana"),
               deteccion("b002", "epoca_b", 18.0, 10.0, situacion="huerfana")]
    assert propuesta_parejas.proponer(fuentes, META) == [{"id_pareja": "p001", "id_fuente_a": "a001", "id_fuente_b": "b001"}]


def prueba_fuentes_json_cumple_el_contrato():
    fuentes = [deteccion("a001", "epoca_a", 30.0, 25.0, situacion="estacionaria"),
               deteccion("t001", "plantilla", 30.0, 25.0, situacion="estacionaria"),
               deteccion("a002", "epoca_a", 64.0, 70.0, situacion="huerfana"),
               deteccion("b002", "epoca_b", 69.0, 72.0, situacion="huerfana"),
               deteccion("b003", "epoca_b", 1.0, 1.0, situacion="descartada")]
    contenido = propuesta_parejas.construir_fuentes_json("campo_prueba", fuentes, META)
    validar_fuentes(contenido)
    assert all("coincidencias" not in f for f in contenido["fuentes"])
    assert contenido["epocas"]["epoca_b"]["mjd"] == 60900.25
    for p in contenido["parejas"]:
        assert p["id_fuente_a"].startswith("a") and p["id_fuente_b"].startswith("b")


# ========================================================= módulo completo
def prueba_modulo_completo_sobre_fits_sinteticos(tmp_path):
    """Detección -> emparejamiento -> parejas: de los FITS alineados a un fuentes.json válido."""
    escribir_campo_sintetico(tmp_path)

    deteccion_fuentes.detectar_campo("campo_prueba", raiz_datos=tmp_path)
    emparejamiento.emparejar_campo("campo_prueba", raiz_datos=tmp_path)
    ruta = propuesta_parejas.proponer_campo("campo_prueba", raiz_datos=tmp_path)

    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    validar_fuentes(contenido)
    assert ruta == tmp_path / "m3_deteccion" / "campo_prueba" / "fuentes.json"
    assert len(contenido["parejas"]) == 1
    por_id = {f["id_fuente"]: f for f in contenido["fuentes"]}
    pareja = contenido["parejas"][0]
    assert abs(por_id[pareja["id_fuente_a"]]["x"] - MOVIL_EN_A[0]) <= 0.5
    assert abs(por_id[pareja["id_fuente_b"]]["x"] - MOVIL_EN_B[0]) <= 0.5
    assert sum(f["situacion"] == "estacionaria" for f in contenido["fuentes"]) == 3 * len(ESTRELLAS_FIJAS)
