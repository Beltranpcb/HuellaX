# ============================================================================
# ARCHIVO: herramientas/pruebas/prueba_extremo_a_extremo.py
# ROL: Comprueba que los módulos encajan entre sí por sus contratos, de la medida
#      del espectro (m6) a lo que lee la web (m7 publicado), y que los datos de
#      demostración de m9 pasan el mismo control que los reales.
# LEE: contratos/ejemplos/ (entradas de m2 a m5), espectros sintéticos creados aquí,
#      modulos/m9_sitio/ejemplos/generar_datos.py.
# PRODUCE: El veredicto de pytest.
# VERIFICACION: `python -m pytest herramientas/pruebas -q` pasa.
# NOTA: Es la única prueba que importa varios módulos a la vez: los módulos no se
#       importan entre sí, pero una prueba de integración sí puede. Todos los datos
#       son sintéticos y llevan origen «sintetico». No usa la red.
# ============================================================================
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import jsonschema
import numpy as np
import pytest
from astropy.wcs import WCS

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from modulos.m6_huella_espectral import (  # noqa: E402
    ajuste_planck, comparacion_plantillas, escritura_espectros, identificacion_molecular)
from modulos.m7_publicacion import control_publicacion, indice_catalogo  # noqa: E402
from modulos.m7_publicacion.copia_publicable import copiar_campo  # noqa: E402
from modulos.m7_publicacion.indice_campos import escribir_campos  # noqa: E402
from modulos.m7_publicacion.union_candidatos import unir_campo  # noqa: E402

CONTRATOS = RAIZ / "contratos"
EJEMPLO = CONTRATOS / "ejemplos" / "campo_ejemplo"
CAMPO = "campo_ejemplo"


def esquema(nombre):
    return jsonschema.Draft202012Validator(json.loads((CONTRATOS / nombre).read_text(encoding="utf-8")))


def leer(ruta):
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def png_600():
    ihdr = struct.pack(">II", 600, 600) + b"\x08\x02\x00\x00\x00"
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + ihdr + b"\x00\x00\x00\x00"


def espectro_sintetico():
    """120 puntos de 0,75 a 5 µm: continuo con pendiente, banda de CO2 en absorción y ruido fijo."""
    lam = np.linspace(0.75, 5.0, 120)
    flujo = 1.0 + 0.1 * lam
    flujo[(lam >= 4.20) & (lam <= 4.33)] -= 0.08
    flujo += np.random.default_rng(11).normal(0.0, 0.01, lam.size)
    return [{"longitud_onda_micras": float(l), "flujo_mjy": float(f), "error_mjy": 0.01, "mjd": 60900.0, "detector": 1}
            for l, f in zip(lam, flujo)]


@pytest.fixture
def pipeline(tmp_path):
    """Entradas de m2 a m5 del ejemplo + m6 ejecutado de verdad + publicación de m7."""
    raiz = tmp_path / "datos"
    for directorio, archivo in (("m2_alineacion", "meta.json"), ("m3_deteccion", "fuentes.json"),
                                ("m4_movimiento", "movimiento.json"), ("m5_identificacion", "identificacion.json")):
        destino = raiz / directorio / CAMPO / archivo
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(EJEMPLO / archivo, destino)
    for nombre in ("epoca_a.png", "epoca_b.png", "diferencia.png"):
        (raiz / "m2_alineacion" / CAMPO / nombre).write_bytes(png_600())
    m6 = raiz / "m6_huella_espectral" / CAMPO
    m6.mkdir(parents=True)
    (m6 / "espectro_medido.json").write_text(json.dumps({"campo": CAMPO, "espectros": [
        {"id_pareja": "p001", "agrupacion": "banda", "puntos": espectro_sintetico()}]}), encoding="utf-8")

    comparacion_plantillas.clasificar_campo(CAMPO, raiz_datos=raiz)
    ajuste_planck.ajustar_campo(CAMPO, raiz_datos=raiz)
    identificacion_molecular.analizar_campo(CAMPO, raiz_datos=raiz)
    escritura_espectros.escribir_campo(CAMPO, raiz_datos=raiz)
    copiar_campo(CAMPO, str(raiz))
    unir_campo(CAMPO, str(raiz))
    escribir_campos(str(raiz))
    indice_catalogo.escribir_catalogo(str(raiz))
    return raiz


def prueba_la_publicacion_completa_pasa_el_control(pipeline):
    assert control_publicacion.validar(str(pipeline)) == []
    publicado = pipeline / "m7_publicacion"
    for archivo, contrato in (("plantillas.json", "plantillas.schema.json"), ("catalogo.json", "catalogo.schema.json")):
        assert (publicado / archivo).is_file(), archivo
        esquema(contrato).validate(leer(publicado / archivo))


def prueba_el_espectro_medido_llega_a_la_web_con_su_analisis(pipeline):
    publicado = pipeline / "m7_publicacion" / CAMPO
    espectro = leer(publicado / "espectros.json")["espectros"][0]
    assert espectro["id_pareja"] == "p001" and len(espectro["puntos"]) == 120
    assert all({"grados_libertad", "n_puntos", "origen_plantilla"} <= set(a) for a in espectro["ajustes_plantilla"])
    assert espectro["calidad"]["n_puntos"] == 120
    assert "plantillas_sinteticas" in espectro["advertencias"]
    formulas = [m["formula"] for m in espectro["composicion"]["moleculas"]]
    assert formulas == ["H2O", "CH4", "CO2", "CO", "NH3"]
    co2 = next(m for m in espectro["composicion"]["moleculas"] if m["formula"] == "CO2")
    assert co2["estado"] in ("candidata", "detectada") and co2["rasgo"] == "absorcion"
    candidatos = {c["id_candidato"]: c for c in leer(publicado / "candidatos.json")["candidatos"]}
    assert candidatos["p001"]["tiene_espectro"] is True
    assert candidatos["p001"]["tipo"] == espectro["tipo"]


def prueba_el_catalogo_refleja_lo_publicado_sin_inventar(pipeline):
    catalogo = leer(pipeline / "m7_publicacion" / "catalogo.json")
    objetos = {o["id_candidato"]: o for o in catalogo["objetos"]}
    assert set(objetos) == {"p001"}                       # p002 es un artefacto descartado
    assert objetos["p001"]["datos"] == {"imagen": True, "trayectoria": True, "espectro": "sintetico"}
    assert objetos["p001"]["n_puntos_espectrales"] == 120


def prueba_el_control_rechaza_un_catalogo_que_anuncia_un_espectro_inexistente(pipeline):
    ruta = pipeline / "m7_publicacion" / "catalogo.json"
    catalogo = leer(ruta)
    catalogo["objetos"].append({**catalogo["objetos"][0], "id_objeto": "campo_ejemplo/p002", "id_candidato": "p002"})
    ruta.write_text(json.dumps(catalogo), encoding="utf-8")
    problemas = control_publicacion.validar(str(pipeline))
    assert any("p002 anuncia un espectro" in p for p in problemas)


@pytest.fixture
def demo(tmp_path):
    """Los datos de demostración de m9, con la composición de m6 y el catálogo de m7."""
    raiz = tmp_path / "datos"
    salida = raiz / "m7_publicacion"
    subprocess.run([sys.executable, str(RAIZ / "modulos" / "m9_sitio" / "ejemplos" / "generar_datos.py"), "--salida", str(salida)],
                   check=True, capture_output=True)
    identificacion_molecular.anotar_espectros(salida)
    indice_catalogo.escribir_catalogo(str(raiz))
    return raiz


def prueba_los_datos_de_demostracion_cumplen_los_contratos(demo):
    # La demo no trae PNG a propósito (la web los sintetiza y lo avisa): al declarar origen
    # «sintetico», el control no los exige y la demo convive con campos reales publicados.
    assert control_publicacion.validar(str(demo)) == []
    esquema("catalogo.schema.json").validate(leer(demo / "m7_publicacion" / "catalogo.json"))
    esquema("plantillas.schema.json").validate(leer(demo / "m7_publicacion" / "plantillas.json"))
    for meta in (demo / "m7_publicacion").glob("*/meta.json"):
        assert leer(meta)["origen"] == "sintetico"


def prueba_en_la_demo_el_wcs_publicado_explica_las_posiciones(demo):
    """La web convierte clics con meta.wcs: las RA/DEC de los candidatos deben salir de ese mismo WCS."""
    for ruta in (demo / "m7_publicacion").glob("*/meta.json"):
        w = leer(ruta)["wcs"]
        astro = WCS(naxis=2)
        astro.wcs.ctype = ["RA---TAN", "DEC--TAN"]
        astro.wcs.crval = [w["crval_ra_grados"], w["crval_dec_grados"]]
        astro.wcs.crpix = [w["crpix_x"] + 1, w["crpix_y"] + 1]
        astro.wcs.cd = w["cd"]
        for c in leer(ruta.with_name("candidatos.json"))["candidatos"]:
            for clave in ("posicion_a", "posicion_b"):
                p = c[clave]
                ra, dec = astro.pixel_to_world_values(p["x"], p["y"])
                d_ra = ((float(ra) - p["ra_grados"] + 180) % 360 - 180) * np.cos(np.radians(p["dec_grados"]))
                assert np.hypot(d_ra, float(dec) - p["dec_grados"]) * 3600 < 0.01, (ruta.parent.name, c["id_candidato"], clave)


def prueba_un_campo_real_sin_png_sigue_rechazado(demo):
    meta = demo / "m7_publicacion" / "slipher" / "meta.json"
    datos = leer(meta)
    datos["origen"] = "real"
    meta.write_text(json.dumps(datos), encoding="utf-8")
    problemas = control_publicacion.validar(str(demo))
    assert any("slipher" in p and "epoca_a.png" in p for p in problemas)
