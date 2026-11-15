# ============================================================================
# ARCHIVO: modulos/m5_identificacion/pruebas/prueba_identificacion.py
# MODULO: m5_identificacion (Lote B)
# ROL: Comprueba el cruce con una caché sintética sin usar la red.
# LEE: Una caché creada en un directorio temporal; los ejemplos de los contratos (copias en ejemplos/); el esquema identificacion (copia en esquemas/).
# PRODUCE: El veredicto de pytest.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de prueba: caché sintética con objetos a 5, 30 segundos de arco.
#   1. Ejecutar el cruce posicional con la red bloqueada  ->  identificacion.json temporal
#   2. Comparar cada estado con el esperado  ->  veredicto
#   Entrega a pytest: veredicto.
# VERIFICACION: Es el propio verificador: pasa cuando se cumplen los criterios de aceptación del módulo.
# USO: python -m pytest modulos/m5_identificacion/pruebas -q
# ESTRUCTURA: un bloque por archivo del módulo. Toda llamada de red se sustituye por un doble;
#             la fixture `red_bloqueada` hace fallar la prueba si algo intenta salir a la red.
# ============================================================================
import json
import shutil
from pathlib import Path

import pytest

import jsonschema

from modulos.m5_identificacion import consulta_catalogos, cruce_posicional

EJEMPLOS = Path(__file__).resolve().parents[1] / "ejemplos" / "campo_ejemplo"
def _ruta_esquema(nombre):
    """Devuelve contratos/<nombre> si existe el arbol completo; si no, esquemas/<nombre>."""
    for base in Path(__file__).resolve().parents:
        candidato = base / "contratos" / nombre
        if candidato.is_file():
            return candidato
    return Path(__file__).resolve().parents[1] / "esquemas" / nombre

ESQUEMA_IDENTIFICACION = json.loads(_ruta_esquema("identificacion.schema.json").read_text(encoding="utf-8"))

# Fragmento real devuelto por MPChecker el 14-11-2026 para RA 10h, Dec +10, 2025-08-10.
HTML_MPC = """<html><body><pre>
 Object designation         R.A.      Decl.     V       Offsets     Motion/hr   Orbit  <a href="x">Further observations?</a>
                           h  m  s     &#176;  '  "        R.A.   Decl.  R.A.  Decl.        Comment (Elong/Decl/V at date 1)

(258773) 2002 JG59       09 59 58.2 +10 02 16  22.2   0.4W   2.3N    66+    24-   16o  None needed at this time.
         2017 QM93       09 59 54.7 +10 03 58  23.4   1.3W   4.0N    50+    15-    8o  Desirable between 2026 Nov. 14-Dec. 14.
 (17035) Velichko        10 00 20.6 +09 58 54  19.1   5.1E   1.1S    57+    18-   24o  None needed at this time.
</pre></body></html>"""

# Fragmento real devuelto por sb_ident (primer paso) el mismo día.
JSON_JPL = {
    "signature": {"version": "1.1"},
    "fields_first": ["Object name", "Astrometric RA (hh:mm:ss)", "Astrometric Dec (dd mm'ss\")", "Dist. from center RA (\")",
                     "Dist. from center Dec (\")", "Dist. from center Norm (\")", "Visual magnitude (V)", "RA rate (\"/h)",
                     "Dec rate (\"/h)", "Est. error RA (\")", "Est. error Dec (\")"],
    "data_first_pass": [["13182 (1996 SO8)", "09:59:26", "+10 09'11\"", "-506.", "551.", "748.3", "18.9", "2.885E+01", "-1.108E+01", "240.2", "240.2"],
                        ["17035 Velichko (1999 FC10)", "10:00:21", "+09 58'51\"", "313.", "-69.4", "320.6", "19.1", "5.778E+01", "-1.856E+01", "260.6", "260.6"]],
}


@pytest.fixture
def red_bloqueada(monkeypatch):
    """Cualquier intento de salir a la red hace fallar la prueba."""
    def prohibido(*_args, **_kwargs):
        raise AssertionError("la prueba intentó abrir una conexión de red")
    monkeypatch.setattr(consulta_catalogos.requests, "get", prohibido)
    monkeypatch.setattr(consulta_catalogos.requests, "post", prohibido)
    return prohibido


@pytest.fixture
def servicios_falsos(monkeypatch, red_bloqueada):
    """Sustituye las dos llamadas de red por dobles que cuentan cuántas veces se las llama."""
    llamadas = {"mpchecker": 0, "jpl_sb_ident": 0}

    def mpc(_formulario):
        llamadas["mpchecker"] += 1
        return HTML_MPC

    def jpl(_parametros):
        llamadas["jpl_sb_ident"] += 1
        return JSON_JPL
    monkeypatch.setattr(consulta_catalogos, "_pedir_mpchecker", mpc)
    monkeypatch.setattr(consulta_catalogos, "_pedir_jpl", jpl)
    return llamadas


def copiar_ejemplos(raiz):
    """Deja fuentes.json y movimiento.json del campo de ejemplo en la disposición real de datos/."""
    (raiz / "m3_deteccion" / "campo_ejemplo").mkdir(parents=True)
    (raiz / "m4_movimiento" / "campo_ejemplo").mkdir(parents=True)
    shutil.copy(EJEMPLOS / "fuentes.json", raiz / "m3_deteccion" / "campo_ejemplo" / "fuentes.json")
    shutil.copy(EJEMPLOS / "movimiento.json", raiz / "m4_movimiento" / "campo_ejemplo" / "movimiento.json")


# ================================================== 4. consulta_catalogos
def prueba_conversion_de_fechas():
    assert consulta_catalogos.fecha_jpl(60900.25) == "2025-08-13_06:00:00"
    assert consulta_catalogos.fecha_mpc(60900.25) == ("2025", "08", "13.25")


def prueba_conversion_a_sexagesimal_y_vuelta():
    assert consulta_catalogos.ra_grados_a_horas(150.0, "-") == "10-00-00.00"
    assert consulta_catalogos.ra_grados_a_horas(150.0, " ") == "10 00 00.00"
    assert consulta_catalogos.dec_grados_a_sexagesimal(-5.5, "-", signo_negativo="M") == "M05-30-00.00"
    assert consulta_catalogos.dec_grados_a_sexagesimal(2.0, " ", signo_positivo="+") == "+02 00 00.00"
    assert abs(consulta_catalogos.sexagesimal_a_grados("09:59:26", es_ra=True) - 149.858333) < 1e-5
    assert abs(consulta_catalogos.sexagesimal_a_grados("+10 09'11\"") - 10.153056) < 1e-5
    assert abs(consulta_catalogos.sexagesimal_a_grados("-05 12 03.5") + 5.200972) < 1e-5


def prueba_parametros_jpl_siguen_el_formato_de_la_api():
    p = consulta_catalogos.parametros_jpl(150.0, -2.0, 60900.0)
    assert p["obs-time"] == "2025-08-13_00:00:00"
    assert p["fov-ra-center"] == "10-00-00.00"
    assert p["fov-dec-center"] == "M02-00-00.00"
    assert p["fov-ra-hwidth"] == p["fov-dec-hwidth"] == round(consulta_catalogos.RADIO_BUSQUEDA_SEGARC / 3600, 5)
    assert p["two-pass"] == "true"


def prueba_formulario_mpchecker_usa_geocentro_y_radio_en_minutos():
    f = consulta_catalogos.formulario_mpchecker(150.0, 2.0, 60900.25)
    assert (f["year"], f["month"], f["day"]) == ("2025", "08", "13.25")
    assert f["ra"] == "10 00 00.00" and f["decl"] == "+02 00 00.00"
    assert f["oc"] == "500" and f["radius"] == str(int(consulta_catalogos.RADIO_BUSQUEDA_SEGARC / 60))


def prueba_interpretar_mpchecker_devuelve_los_tres_objetos():
    objetos = consulta_catalogos.interpretar_mpchecker(HTML_MPC)
    assert [o["nombre"] for o in objetos] == ["(258773) 2002 JG59", "2017 QM93", "(17035) Velichko"]
    velichko = objetos[2]
    assert abs(velichko["ra_grados"] - 150.085833) < 1e-5
    assert abs(velichko["dec_grados"] - 9.981667) < 1e-5
    assert velichko["magnitud_v"] == 19.1


def prueba_interpretar_mpchecker_sin_objetos_y_sin_bloque():
    assert consulta_catalogos.interpretar_mpchecker("<html>No known minor planets, brighter than V = 24.0, were found</html>") == []
    with pytest.raises(ValueError):
        consulta_catalogos.interpretar_mpchecker("<html><body>Error 500</body></html>")


def prueba_interpretar_jpl_normaliza_la_tabla():
    objetos = consulta_catalogos.interpretar_jpl(JSON_JPL)
    assert [o["nombre"] for o in objetos] == ["13182 (1996 SO8)", "17035 Velichko (1999 FC10)"]
    assert abs(objetos[0]["ra_grados"] - 149.858333) < 1e-5
    assert abs(objetos[0]["dec_grados"] - 10.153056) < 1e-5
    assert objetos[1]["magnitud_v"] == 19.1
    segundo_paso = {"fields_second": JSON_JPL["fields_first"][:9], "data_second_pass": [JSON_JPL["data_first_pass"][1][:9]]}
    assert [o["nombre"] for o in consulta_catalogos.interpretar_jpl(segundo_paso)] == ["17035 Velichko (1999 FC10)"]


def prueba_consultas_pendientes_omiten_las_parejas_estacionarias():
    fuentes = json.loads((EJEMPLOS / "fuentes.json").read_text(encoding="utf-8"))
    movimiento = json.loads((EJEMPLOS / "movimiento.json").read_text(encoding="utf-8"))
    assert [c["id_pareja"] for c in consulta_catalogos.consultas_pendientes(fuentes, movimiento)] == ["p001", "p002"]
    movimiento["parejas"][0]["clase"] = "estacionaria"
    pendientes = consulta_catalogos.consultas_pendientes(fuentes, movimiento)
    assert [c["id_pareja"] for c in pendientes] == ["p002"]
    assert pendientes[0]["mjd"] == fuentes["epocas"]["epoca_a"]["mjd"]
    assert pendientes[0]["ra_grados"] == 149.99


def prueba_primera_ejecucion_escribe_la_cache(tmp_path, servicios_falsos):
    copiar_ejemplos(tmp_path)
    nuevos, existentes, fallidos = consulta_catalogos.consultar_campo("campo_ejemplo", raiz_datos=tmp_path)
    assert [r.name for r in nuevos] == ["campo_ejemplo_p001.json", "campo_ejemplo_p002.json"]
    assert existentes == [] and fallidos == []
    assert servicios_falsos == {"mpchecker": 2, "jpl_sb_ident": 2}
    contenido = json.loads(nuevos[0].read_text(encoding="utf-8"))
    assert contenido["id_pareja"] == "p001"
    assert contenido["consulta"]["radio_segarc"] == consulta_catalogos.RADIO_BUSQUEDA_SEGARC
    assert contenido["respuestas"]["mpchecker"]["estado"] == "ok"
    assert len(contenido["respuestas"]["mpchecker"]["objetos"]) == 3
    assert len(contenido["respuestas"]["jpl_sb_ident"]["objetos"]) == 2


def prueba_segunda_ejecucion_no_abre_la_red(tmp_path, servicios_falsos, monkeypatch):
    copiar_ejemplos(tmp_path)
    consulta_catalogos.consultar_campo("campo_ejemplo", raiz_datos=tmp_path)

    def prohibido(*_a, **_k):
        raise AssertionError("segunda ejecución con llamada de red")
    monkeypatch.setattr(consulta_catalogos, "_pedir_mpchecker", prohibido)
    monkeypatch.setattr(consulta_catalogos, "_pedir_jpl", prohibido)

    nuevos, existentes, fallidos = consulta_catalogos.consultar_campo("campo_ejemplo", raiz_datos=tmp_path)
    assert nuevos == [] and fallidos == []
    assert len(existentes) == 2


def prueba_basta_con_que_un_servicio_responda(tmp_path, servicios_falsos, monkeypatch):
    copiar_ejemplos(tmp_path)

    def jpl_caido(_p):
        raise consulta_catalogos.requests.ReadTimeout("Read timed out")
    monkeypatch.setattr(consulta_catalogos, "_pedir_jpl", jpl_caido)
    nuevos, _, fallidos = consulta_catalogos.consultar_campo("campo_ejemplo", raiz_datos=tmp_path)
    assert len(nuevos) == 2 and fallidos == []
    respuestas = json.loads(nuevos[0].read_text(encoding="utf-8"))["respuestas"]
    assert respuestas["mpchecker"]["estado"] == "ok"
    assert respuestas["jpl_sb_ident"]["estado"] == "error"
    assert "ReadTimeout" in respuestas["jpl_sb_ident"]["mensaje"]


def prueba_si_fallan_los_dos_no_se_escribe_nada(tmp_path, servicios_falsos, monkeypatch):
    copiar_ejemplos(tmp_path)

    def caido(_x):
        raise ConnectionError("sin red")
    monkeypatch.setattr(consulta_catalogos, "_pedir_jpl", caido)
    monkeypatch.setattr(consulta_catalogos, "_pedir_mpchecker", caido)
    nuevos, existentes, fallidos = consulta_catalogos.consultar_campo("campo_ejemplo", raiz_datos=tmp_path)
    assert nuevos == [] and existentes == []
    assert [f[0] for f in fallidos] == ["p001", "p002"]
    assert list((tmp_path / "m5_identificacion" / "cache").iterdir()) == []


# ==================================================== 5. cruce_posicional
FUENTES_EJEMPLO = json.loads((EJEMPLOS / "fuentes.json").read_text(encoding="utf-8"))
MOVIMIENTO_EJEMPLO = json.loads((EJEMPLOS / "movimiento.json").read_text(encoding="utf-8"))
POSICION_P001 = (150.0100, 2.0050)  # fuente a001 del ejemplo
POSICION_P002 = (149.9900, 1.9950)  # fuente a002 del ejemplo


def desplazada(posicion, segarc):
    """La misma ascensión recta, con la declinación desplazada `segarc` segundos de arco."""
    return {"ra_grados": posicion[0], "dec_grados": round(posicion[1] + segarc / 3600, 7)}


def respuesta_cache(id_pareja, mpc=(), jpl=(), estado_jpl="ok"):
    objetos = lambda lista: [{"nombre": n, **pos, "magnitud_v": 20.0} for n, pos in lista]
    return {"campo": "campo_ejemplo", "id_pareja": id_pareja,
            "respuestas": {"mpchecker": {"estado": "ok", "mensaje": None, "objetos": objetos(mpc)},
                           "jpl_sb_ident": {"estado": estado_jpl, "mensaje": None, "objetos": objetos(jpl)}}}


def cruzar_con_cache(cache):
    """Ejecuta el cruce sobre el campo de ejemplo con una caché dada en memoria."""
    def leer(nombre):
        if nombre not in cache:
            raise FileNotFoundError(nombre)
        return cache[nombre]
    return cruce_posicional.construir_identificacion_json("campo_ejemplo", FUENTES_EJEMPLO, MOVIMIENTO_EJEMPLO, leer)


def prueba_separacion_angular():
    assert abs(cruce_posicional.separacion_segarc(150.0, 2.0, 150.0, 2.0 + 5 / 3600) - 5.0) < 1e-6
    assert abs(cruce_posicional.separacion_segarc(0.0, 0.0, 0.0, 1.0) - 3600.0) < 1e-6
    assert abs(cruce_posicional.separacion_segarc(150.0, 60.0, 150.0 + 2 / 3600, 60.0) - 1.0) < 1e-3


def prueba_objeto_a_5_segundos_da_conocido(red_bloqueada):
    cache = {"campo_ejemplo_p001.json": respuesta_cache("p001", jpl=[("2015 TE267", desplazada(POSICION_P001, 5))]),
             "campo_ejemplo_p002.json": respuesta_cache("p002")}
    e = {i["id_pareja"]: i for i in cruzar_con_cache(cache)["identificaciones"]}
    assert e["p001"]["estado"] == "conocido"
    assert e["p001"]["nombre_objeto"] == "2015 TE267"
    assert e["p001"]["catalogo"] == "jpl_sb_ident"
    assert abs(e["p001"]["distancia_segarc"] - 5.0) <= 0.01
    assert e["p001"]["posicion_predicha"] == desplazada(POSICION_P001, 5)


def prueba_objeto_a_30_segundos_da_sin_identificar():
    cache = {"campo_ejemplo_p001.json": respuesta_cache("p001", mpc=[("lejano", desplazada(POSICION_P001, 30))]),
             "campo_ejemplo_p002.json": respuesta_cache("p002")}
    e = {i["id_pareja"]: i for i in cruzar_con_cache(cache)["identificaciones"]}
    assert e["p001"]["estado"] == "sin_identificar"  # p001 es candidata
    assert e["p001"]["nombre_objeto"] is None and e["p001"]["distancia_segarc"] is None


def prueba_no_concluyente_sin_coincidencia_da_artefacto_descartado():
    cache = {"campo_ejemplo_p001.json": respuesta_cache("p001"),
             "campo_ejemplo_p002.json": respuesta_cache("p002", mpc=[("lejano", desplazada(POSICION_P002, 40))])}
    e = {i["id_pareja"]: i for i in cruzar_con_cache(cache)["identificaciones"]}
    assert e["p002"]["estado"] == "artefacto_descartado"  # p002 es no_concluyente
    assert e["p001"]["estado"] == "sin_identificar"


def prueba_gana_la_coincidencia_mas_cercana_entre_los_dos_servicios():
    cache = {"campo_ejemplo_p001.json": respuesta_cache("p001", mpc=[("mpc 8s", desplazada(POSICION_P001, 8))],
                                                         jpl=[("jpl 3s", desplazada(POSICION_P001, 3)), ("jpl 12s", desplazada(POSICION_P001, 12))]),
             "campo_ejemplo_p002.json": respuesta_cache("p002")}
    e = {i["id_pareja"]: i for i in cruzar_con_cache(cache)["identificaciones"]}
    assert (e["p001"]["nombre_objeto"], e["p001"]["catalogo"]) == ("jpl 3s", "jpl_sb_ident")


def prueba_un_servicio_en_error_no_aporta_objetos():
    cache = {"campo_ejemplo_p001.json": respuesta_cache("p001", jpl=[("fantasma", desplazada(POSICION_P001, 1))], estado_jpl="error"),
             "campo_ejemplo_p002.json": respuesta_cache("p002")}
    e = {i["id_pareja"]: i for i in cruzar_con_cache(cache)["identificaciones"]}
    assert e["p001"]["estado"] == "sin_identificar"


def prueba_dentro_de_la_tolerancia_es_conocido_y_fuera_no():
    cache = {"campo_ejemplo_p001.json": respuesta_cache("p001", mpc=[("borde", desplazada(POSICION_P001, 14.9))]),
             "campo_ejemplo_p002.json": respuesta_cache("p002", mpc=[("fuera", desplazada(POSICION_P002, 15.1))])}
    e = {i["id_pareja"]: i for i in cruzar_con_cache(cache)["identificaciones"]}
    assert e["p001"]["estado"] == "conocido" and e["p001"]["distancia_segarc"] <= 15
    assert e["p002"]["estado"] == "artefacto_descartado"


def prueba_falta_una_respuesta_en_cache_falla_nombrandola():
    with pytest.raises(FileNotFoundError, match="campo_ejemplo_p002.json"):
        cruzar_con_cache({"campo_ejemplo_p001.json": respuesta_cache("p001")})


def prueba_reproduce_el_ejemplo_del_contrato():
    ejemplo = json.loads((EJEMPLOS / "identificacion.json").read_text(encoding="utf-8"))
    predicha = ejemplo["identificaciones"][0]["posicion_predicha"]
    cache = {"campo_ejemplo_p001.json": respuesta_cache("p001", jpl=[("Asteroide de ejemplo", predicha)]),
             "campo_ejemplo_p002.json": respuesta_cache("p002")}
    contenido = cruzar_con_cache(cache)
    jsonschema.Draft202012Validator(ESQUEMA_IDENTIFICACION).validate(contenido)
    assert contenido["identificaciones"] == ejemplo["identificaciones"]
    assert contenido["tolerancia_segarc"] == ejemplo["tolerancia_segarc"]


def prueba_modulo_completo_sin_red(tmp_path, servicios_falsos):
    """consulta_catalogos -> cruce_posicional sobre el campo de ejemplo, con dobles de los servicios."""
    copiar_ejemplos(tmp_path)
    consulta_catalogos.consultar_campo("campo_ejemplo", raiz_datos=tmp_path)
    ruta = cruce_posicional.cruzar_campo("campo_ejemplo", raiz_datos=tmp_path)

    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(ESQUEMA_IDENTIFICACION).validate(contenido)
    assert ruta == tmp_path / "m5_identificacion" / "campo_ejemplo" / "identificacion.json"
    estados = {i["id_pareja"]: i["estado"] for i in contenido["identificaciones"]}
    # los objetos de los fragmentos reales están a RA 10h Dec +10, lejos del campo de ejemplo
    assert estados == {"p001": "sin_identificar", "p002": "artefacto_descartado"}
    for i in contenido["identificaciones"]:
        assert (tmp_path / "m5_identificacion" / "cache" / i["archivo_cache"]).exists()
