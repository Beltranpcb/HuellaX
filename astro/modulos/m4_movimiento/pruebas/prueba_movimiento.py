# ============================================================================
# ARCHIVO: modulos/m4_movimiento/pruebas/prueba_movimiento.py
# MODULO: m4_movimiento (Lote C)
# ROL: Comprueba las medidas de movimiento sobre el ejemplo del contrato.
# LEE: ejemplos/campo_ejemplo/fuentes.json; ejemplos/campo_ejemplo/movimiento.json (copias de contratos/ejemplos/); esquemas/movimiento.schema.json.
# PRODUCE: El veredicto de pytest.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de prueba: fuentes.json de ejemplo.
#   1. Ejecutar cinemática, incertidumbre, clasificación  ->  movimiento.json temporal
#   2. Comparar con el movimiento.json de ejemplo  ->  diferencia relativa
#   3. Comparar con el 1 %  ->  veredicto
#   Entrega a pytest: veredicto.
# VERIFICACION: Es el propio verificador: pasa cuando se cumplen los criterios de aceptación del módulo.
# USO: python -m pytest modulos/m4_movimiento/pruebas -q
# ============================================================================
import copy
import json
import shutil
from pathlib import Path

import jsonschema
import pytest

from modulos.m4_movimiento import cinematica, clasificacion, incertidumbre

MODULO = Path(__file__).resolve().parents[1]
EJEMPLOS = MODULO / "ejemplos" / "campo_ejemplo"
ESQUEMA = json.loads((MODULO / "esquemas" / "movimiento.schema.json").read_text(encoding="utf-8"))
FUENTES = json.loads((EJEMPLOS / "fuentes.json").read_text(encoding="utf-8"))
MOVIMIENTO_EJEMPLO = json.loads((EJEMPLOS / "movimiento.json").read_text(encoding="utf-8"))


def ejecutar(fuentes, campo="campo_ejemplo"):
    """Los tres pasos del módulo en memoria. Devuelve el contenido de movimiento.json."""
    cin = {"campo": campo, "parejas": cinematica.calcular_cinematica(fuentes)}
    sig = {"campo": campo, "parejas": incertidumbre.propagar(fuentes, cin)}
    return clasificacion.construir_movimiento_json(campo, cin, sig)


def por_pareja(movimiento):
    return {p["id_pareja"]: p for p in movimiento["parejas"]}


# --------------------------------------------------------------- cinematica
def prueba_separacion_sobre_la_esfera():
    assert cinematica.separacion_segarc(150.0, 2.0, 150.0, 2.0 + 10 / 3600) == pytest.approx(10.0, abs=1e-6)
    assert cinematica.separacion_segarc(0.0, 0.0, 1.0, 0.0) == pytest.approx(3600.0, abs=1e-6)
    # a 60 grados de declinación, un grado de ascensión recta mide medio grado sobre el cielo
    assert cinematica.separacion_segarc(10.0, 60.0, 11.0, 60.0) == pytest.approx(1800.0, rel=1e-3)
    assert cinematica.separacion_segarc(150.0, 2.0, 150.0, 2.0) == 0.0


def prueba_velocidad_coincide_con_el_ejemplo_al_1_por_ciento():
    """Criterio 1."""
    obtenido, esperado = por_pareja(ejecutar(FUENTES)), por_pareja(MOVIMIENTO_EJEMPLO)
    assert set(obtenido) == set(esperado) == {"p001", "p002"}
    for id_pareja, e in esperado.items():
        o = obtenido[id_pareja]
        assert abs(o["velocidad_segarc_por_hora"] - e["velocidad_segarc_por_hora"]) / e["velocidad_segarc_por_hora"] < 0.01
        assert o["separacion_segarc"] == pytest.approx(e["separacion_segarc"], rel=0.01)
        assert o["horas_transcurridas"] == pytest.approx(e["horas_transcurridas"])


def prueba_epoca_b_anterior_a_a_falla():
    fuentes = copy.deepcopy(FUENTES)
    fuentes["epocas"]["epoca_b"]["mjd"] = fuentes["epocas"]["epoca_a"]["mjd"] - 1
    with pytest.raises(ValueError, match="posterior"):
        cinematica.calcular_cinematica(fuentes)


# ------------------------------------------------------------ incertidumbre
def prueba_incertidumbre_en_cuadratura():
    fuentes = copy.deepcopy(FUENTES)
    por_id = {f["id_fuente"]: f for f in fuentes["fuentes"]}
    por_id["a001"]["incertidumbre_posicion_segarc"] = 3.0
    por_id["b001"]["incertidumbre_posicion_segarc"] = 4.0
    cin = {"campo": "c", "parejas": cinematica.calcular_cinematica(fuentes)}
    sig = {s["id_pareja"]: s for s in incertidumbre.propagar(fuentes, cin)}
    assert sig["p001"]["incertidumbre_separacion_segarc"] == pytest.approx(5.0)
    assert sig["p001"]["incertidumbre_velocidad"] == pytest.approx(5.0 / 6.0, abs=1e-4)
    assert sig["p001"]["significancia"] == pytest.approx(cin["parejas"][0]["separacion_segarc"] / 5.0, abs=0.01)


def prueba_incertidumbre_de_velocidad_coincide_con_el_ejemplo():
    obtenido, esperado = por_pareja(ejecutar(FUENTES)), por_pareja(MOVIMIENTO_EJEMPLO)
    for id_pareja, e in esperado.items():
        assert obtenido[id_pareja]["incertidumbre_velocidad"] == pytest.approx(e["incertidumbre_velocidad"], rel=0.01)
        assert obtenido[id_pareja]["significancia"] == pytest.approx(e["significancia"], rel=0.01)


# ------------------------------------------------------------- clasificacion
def prueba_umbrales_de_clase():
    assert clasificacion.clase_de(0.0) == "estacionaria"
    assert clasificacion.clase_de(1.99) == "estacionaria"
    assert clasificacion.clase_de(2.0) == "no_concluyente"
    assert clasificacion.clase_de(4.99) == "no_concluyente"
    assert clasificacion.clase_de(5.0) == "candidata"
    assert clasificacion.clase_de(16.44) == "candidata"


def prueba_posiciones_identicas_dan_estacionaria():
    """Criterio 2."""
    fuentes = copy.deepcopy(FUENTES)
    por_id = {f["id_fuente"]: f for f in fuentes["fuentes"]}
    por_id["b001"]["ra_grados"] = por_id["a001"]["ra_grados"]
    por_id["b001"]["dec_grados"] = por_id["a001"]["dec_grados"]
    p001 = por_pareja(ejecutar(fuentes))["p001"]
    assert p001["clase"] == "estacionaria"
    assert p001["separacion_segarc"] == 0.0 and p001["velocidad_segarc_por_hora"] == 0.0 and p001["significancia"] == 0.0


def prueba_clases_coinciden_con_el_ejemplo():
    """Criterio 3."""
    obtenido, esperado = por_pareja(ejecutar(FUENTES)), por_pareja(MOVIMIENTO_EJEMPLO)
    assert {k: v["clase"] for k, v in obtenido.items()} == {k: v["clase"] for k, v in esperado.items()}
    assert esperado["p001"]["clase"] == "candidata" and esperado["p002"]["clase"] == "no_concluyente"


def prueba_movimiento_json_cumple_el_contrato():
    """Criterio 4."""
    contenido = ejecutar(FUENTES)
    jsonschema.Draft202012Validator(ESQUEMA).validate(contenido)
    assert contenido["version_contrato"] == "1" and contenido["campo"] == "campo_ejemplo"
    # sin pareja alguna también es un archivo válido
    vacio = copy.deepcopy(FUENTES)
    vacio["parejas"] = []
    jsonschema.Draft202012Validator(ESQUEMA).validate(ejecutar(vacio))


# ------------------------------------------------------------ módulo completo
def prueba_modulo_completo_sobre_el_ejemplo(tmp_path):
    """Los tres comandos del LEEME, de fuentes.json a movimiento.json, con la disposición real de datos/."""
    (tmp_path / "m3_deteccion" / "campo_ejemplo").mkdir(parents=True)
    shutil.copy(EJEMPLOS / "fuentes.json", tmp_path / "m3_deteccion" / "campo_ejemplo" / "fuentes.json")

    cinematica.calcular_campo("campo_ejemplo", raiz_datos=tmp_path)
    incertidumbre.propagar_campo("campo_ejemplo", raiz_datos=tmp_path)
    ruta = clasificacion.clasificar_campo("campo_ejemplo", raiz_datos=tmp_path)

    assert ruta == tmp_path / "m4_movimiento" / "campo_ejemplo" / "movimiento.json"
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(ESQUEMA).validate(contenido)
    assert contenido["parejas"] == MOVIMIENTO_EJEMPLO["parejas"]
