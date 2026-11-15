# ============================================================================
# ARCHIVO: modulos/m7_publicacion/pruebas/prueba_publicacion.py
# MODULO: m7_publicacion (Lote A)
# ROL: Comprueba la unión sobre los ejemplos de los contratos.
# LEE: Los siete JSON de modulos/m7_publicacion/ejemplos/.
# PRODUCE: El veredicto de pytest.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de prueba: ejemplos de los contratos.
#   1. Ejecutar unión, índice, control en un directorio temporal  ->  publicación temporal
#   2. Comparar con candidatos.json, campos.json de ejemplo  ->  veredicto
#   Entrega a pytest: veredicto.
# VERIFICACION: Es el propio verificador: pasa cuando se cumplen los criterios
#   de aceptación del módulo.
# USO: python -m pytest modulos/m7_publicacion/pruebas -q
# ============================================================================
"""Pruebas de m7_publicacion contra los ejemplos escritos a mano de contratos/.

El árbol de datos se monta en un directorio temporal: nunca se toca datos/ del
repositorio. Los ejemplos son la referencia de aceptación, de modo que si un
contrato cambia y estos archivos se actualizan, la prueba sigue el cambio.
"""
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from modulos.m7_publicacion.control_publicacion import validar  # noqa: E402
from modulos.m7_publicacion.copia_publicable import copiar_campo  # noqa: E402
from modulos.m7_publicacion.indice_campos import escribir_campos  # noqa: E402
from modulos.m7_publicacion import indice_catalogo  # noqa: E402
from modulos.m7_publicacion.union_candidatos import unir_campo  # noqa: E402

CAMPO = "campo_ejemplo"
EJEMPLOS = RAIZ / "modulos" / "m7_publicacion" / "ejemplos"
CONTRATOS = RAIZ / "modulos" / "m7_publicacion" / "esquemas"

# (directorio de datos, archivo del ejemplo que se copia tal cual)
TABLAS_DE_ENTRADA = (
    ("m2_alineacion", "meta.json"),
    ("m3_deteccion", "fuentes.json"),
    ("m4_movimiento", "movimiento.json"),
    ("m5_identificacion", "identificacion.json"),
    ("m6_huella_espectral", "espectros.json"),
)

def png_de_prueba(ancho=600, alto=600):
    """Devuelve una cabecera PNG válida con el tamaño pedido.

    Solo la firma y el bloque IHDR: basta para que control_publicacion mida el
    tamaño, y evita depender de una biblioteca de imagen en las pruebas.
    """
    ihdr = struct.pack(">II", ancho, alto) + b"\x08\x02\x00\x00\x00"
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + ihdr + b"\x00\x00\x00\x00"


PNG_DE_EJEMPLO = png_de_prueba()


def leer_json(ruta):
    """Lee un JSON en UTF-8."""
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)


def escribir_json(ruta, contenido):
    """Escribe un JSON en UTF-8."""
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(contenido, archivo, ensure_ascii=False, indent=2)


def sin_comentario(documento):
    """Quita el comentario libre: no forma parte del contrato."""
    return {clave: valor for clave, valor in documento.items() if clave != "_comentario"}


def resumen(ruta):
    """Huella de un archivo, para comparar copias byte a byte."""
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


@pytest.fixture
def raiz_datos(tmp_path):
    """Monta un datos/ temporal con los ejemplos de los contratos."""
    raiz = tmp_path / "datos"
    origen = EJEMPLOS / CAMPO

    for directorio, archivo in TABLAS_DE_ENTRADA:
        destino = raiz / directorio / CAMPO / archivo
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origen / archivo, destino)

    # m2 también produce los tres PNG; aquí basta con que existan y sean pequeños.
    for nombre in ("epoca_a.png", "epoca_b.png", "diferencia.png"):
        (raiz / "m2_alineacion" / CAMPO / nombre).write_bytes(PNG_DE_EJEMPLO)

    return raiz


@pytest.fixture
def publicado(raiz_datos):
    """Deja el campo ejemplo publicado (copia, unión e índice)."""
    copiar_campo(CAMPO, str(raiz_datos))
    unir_campo(CAMPO, str(raiz_datos))
    escribir_campos(str(raiz_datos))
    return raiz_datos


def prueba_union_coincide_con_el_ejemplo(raiz_datos):
    unir_campo(CAMPO, str(raiz_datos))
    obtenido = leer_json(raiz_datos / "m7_publicacion" / CAMPO / "candidatos.json")
    esperado = leer_json(EJEMPLOS / CAMPO / "candidatos.json")
    assert sin_comentario(obtenido) == sin_comentario(esperado)


def prueba_indice_coincide_con_el_ejemplo(publicado):
    obtenido = leer_json(publicado / "m7_publicacion" / "campos.json")
    esperado = leer_json(EJEMPLOS / "campos.json")
    assert sin_comentario(obtenido) == sin_comentario(esperado)


def prueba_copia_es_identica_byte_a_byte(raiz_datos):
    copiar_campo(CAMPO, str(raiz_datos))
    for directorio, nombre in (
        *(("m2_alineacion", n) for n in ("meta.json", "epoca_a.png", "epoca_b.png", "diferencia.png")),
        ("m6_huella_espectral", "espectros.json"),
    ):
        origen = raiz_datos / directorio / CAMPO / nombre
        destino = raiz_datos / "m7_publicacion" / CAMPO / nombre
        assert destino.is_file(), "no se copió %s" % nombre
        assert resumen(destino) == resumen(origen), "la copia de %s difiere" % nombre


def prueba_control_aprueba_la_publicacion(publicado):
    assert validar(str(publicado), str(CONTRATOS)) == []


def prueba_union_omite_las_parejas_estacionarias(raiz_datos):
    ruta = raiz_datos / "m4_movimiento" / CAMPO / "movimiento.json"
    movimiento = leer_json(ruta)
    movimiento["parejas"].append(
        {
            "id_pareja": "p003",
            "separacion_segarc": 0.3,
            "horas_transcurridas": 6.0,
            "velocidad_segarc_por_hora": 0.05,
            "incertidumbre_velocidad": 0.2,
            "significancia": 0.25,
            "clase": "estacionaria",
        }
    )
    escribir_json(ruta, movimiento)

    unir_campo(CAMPO, str(raiz_datos))
    candidatos = leer_json(raiz_datos / "m7_publicacion" / CAMPO / "candidatos.json")["candidatos"]
    assert [c["id_candidato"] for c in candidatos] == ["p001", "p002"]
    assert all(c["clase_movimiento"] != "estacionaria" for c in candidatos)


def prueba_union_falla_si_falta_una_identificacion(raiz_datos):
    ruta = raiz_datos / "m5_identificacion" / CAMPO / "identificacion.json"
    identificacion = leer_json(ruta)
    identificacion["identificaciones"] = [
        i for i in identificacion["identificaciones"] if i["id_pareja"] != "p002"
    ]
    escribir_json(ruta, identificacion)

    with pytest.raises(ValueError) as error:
        unir_campo(CAMPO, str(raiz_datos))
    assert "p002" in str(error.value)


def prueba_union_falla_si_el_campo_no_coincide(raiz_datos):
    ruta = raiz_datos / "m3_deteccion" / CAMPO / "fuentes.json"
    fuentes = leer_json(ruta)
    fuentes["campo"] = "otro_campo"
    escribir_json(ruta, fuentes)

    with pytest.raises(ValueError) as error:
        unir_campo(CAMPO, str(raiz_datos))
    assert "otro_campo" in str(error.value)


def prueba_control_rechaza_un_candidato_fuera_de_contrato(publicado):
    ruta = publicado / "m7_publicacion" / CAMPO / "candidatos.json"
    candidatos = leer_json(ruta)
    candidatos["candidatos"][0]["estado"] = "dudoso"
    escribir_json(ruta, candidatos)

    problemas = validar(str(publicado), str(CONTRATOS))
    assert problemas
    assert any("estado" in problema for problema in problemas)


def prueba_control_rechaza_un_archivo_de_mas_de_un_megabyte(publicado):
    (publicado / "m7_publicacion" / CAMPO / "sobrante.bin").write_bytes(b"0" * (1024 * 1024 + 1))

    problemas = validar(str(publicado), str(CONTRATOS))
    assert any("1 MB" in problema for problema in problemas)


def prueba_control_rechaza_un_campo_incompleto(publicado):
    (publicado / "m7_publicacion" / CAMPO / "espectros.json").unlink()

    problemas = validar(str(publicado), str(CONTRATOS))
    assert any("falta espectros.json" in problema for problema in problemas)


def prueba_control_rechaza_un_indice_desfasado(publicado):
    ruta = publicado / "m7_publicacion" / "campos.json"
    indice = leer_json(ruta)
    indice["campos"][0]["numero_candidatos"] = 99
    escribir_json(ruta, indice)

    problemas = validar(str(publicado), str(CONTRATOS))
    assert any("99" in problema for problema in problemas)


def prueba_control_rechaza_un_json_ilegible(publicado):
    (publicado / "m7_publicacion" / CAMPO / "meta.json").write_text("{ no es json", encoding="utf-8")

    problemas = validar(str(publicado), str(CONTRATOS))
    assert any("JSON ilegible" in problema for problema in problemas)


def prueba_control_sale_con_codigo_cero_por_linea_de_ordenes(publicado, tmp_path):
    """La orden documentada debe poder ejecutarse tal cual, sin argumentos.

    Se ejecuta desde un directorio ajeno al repositorio y sin `contratos/`:
    el control debe encontrar por sí solo los esquemas que viajan con el módulo.
    """

    entorno = dict(os.environ)
    entorno["PYTHONPATH"] = str(RAIZ)
    proceso = subprocess.run(
        [sys.executable, "-m", "modulos.m7_publicacion.control_publicacion"],
        cwd=str(tmp_path),
        env=entorno,
        capture_output=True,
        text=True,
    )
    assert proceso.returncode == 0, proceso.stdout + proceso.stderr
    assert "Publicación válida" in proceso.stdout


def prueba_control_rechaza_un_png_que_no_mide_600(publicado):
    (publicado / "m7_publicacion" / CAMPO / "epoca_a.png").write_bytes(png_de_prueba(10, 10))

    problemas = validar(str(publicado), str(CONTRATOS))
    assert any("mide 10 x 10" in problema for problema in problemas)


def prueba_union_avisa_del_modulo_que_falta(raiz_datos):
    (raiz_datos / "m4_movimiento" / CAMPO / "movimiento.json").unlink()

    with pytest.raises(FileNotFoundError) as error:
        unir_campo(CAMPO, str(raiz_datos))
    assert "m4_movimiento" in str(error.value)


def prueba_publica_dos_campos(raiz_datos):
    """Dos campos en la misma publicación: el índice tiene que listar los dos."""
    otro = "campo_dos"
    for directorio, archivo in TABLAS_DE_ENTRADA:
        contenido = leer_json(raiz_datos / directorio / CAMPO / archivo)
        contenido["campo"] = otro
        destino = raiz_datos / directorio / otro / archivo
        destino.parent.mkdir(parents=True, exist_ok=True)
        escribir_json(destino, contenido)
    for nombre in ("epoca_a.png", "epoca_b.png", "diferencia.png"):
        shutil.copyfile(
            raiz_datos / "m2_alineacion" / CAMPO / nombre,
            raiz_datos / "m2_alineacion" / otro / nombre,
        )

    for campo in (CAMPO, otro):
        copiar_campo(campo, str(raiz_datos))
        unir_campo(campo, str(raiz_datos))
    escribir_campos(str(raiz_datos))

    indice = leer_json(raiz_datos / "m7_publicacion" / "campos.json")
    assert [entrada["campo"] for entrada in indice["campos"]] == [otro, CAMPO]
    assert [entrada["numero_candidatos"] for entrada in indice["campos"]] == [2, 2]
    assert validar(str(raiz_datos), str(CONTRATOS)) == []


def prueba_sin_movimiento_publica_cero_candidatos(raiz_datos):
    """Si todas las parejas son estacionarias, el campo publica una lista vacía."""
    ruta = raiz_datos / "m4_movimiento" / CAMPO / "movimiento.json"
    movimiento = leer_json(ruta)
    for pareja in movimiento["parejas"]:
        pareja["clase"] = "estacionaria"
    escribir_json(ruta, movimiento)

    copiar_campo(CAMPO, str(raiz_datos))
    unir_campo(CAMPO, str(raiz_datos))
    escribir_campos(str(raiz_datos))

    candidatos = leer_json(raiz_datos / "m7_publicacion" / CAMPO / "candidatos.json")
    assert candidatos["candidatos"] == []

    indice = leer_json(raiz_datos / "m7_publicacion" / "campos.json")
    assert indice["campos"][0]["numero_candidatos"] == 0

    assert validar(str(raiz_datos), str(CONTRATOS)) == []


def prueba_indice_avisa_si_el_meta_esta_incompleto(publicado):
    """Un meta.json a medio escribir debe nombrar el archivo, no dar KeyError."""
    ruta = publicado / "m7_publicacion" / CAMPO / "meta.json"
    meta = leer_json(ruta)
    meta.pop("nombre")
    escribir_json(ruta, meta)

    with pytest.raises(ValueError) as error:
        escribir_campos(str(publicado))
    assert "meta.json" in str(error.value)
    assert "nombre" in str(error.value)


def prueba_indice_avisa_si_el_candidatos_esta_incompleto(publicado):
    ruta = publicado / "m7_publicacion" / CAMPO / "candidatos.json"
    escribir_json(ruta, {"version_contrato": "1", "campo": CAMPO})

    with pytest.raises(ValueError) as error:
        escribir_campos(str(publicado))
    assert "candidatos.json" in str(error.value)
    assert "candidatos" in str(error.value)


def prueba_copia_plantillas_si_existen_y_no_falla_si_faltan(raiz_datos):
    copiar_campo(CAMPO, str(raiz_datos))
    assert not (raiz_datos / "m7_publicacion" / "plantillas.json").exists()  # opcional: sin origen no se crea
    origen = raiz_datos / "m6_huella_espectral" / "plantillas.json"
    shutil.copyfile(EJEMPLOS / "plantillas.json", origen)
    copiar_campo(CAMPO, str(raiz_datos))
    assert resumen(raiz_datos / "m7_publicacion" / "plantillas.json") == resumen(origen)


# -------------------------------------------------------------- catálogo
def _punto(lam, flujo, error=0.1):
    return {"longitud_onda_micras": lam, "flujo_mjy": flujo, "error_mjy": error, "mjd": 60900.0, "detector": 1}


def prueba_catalogo_coincide_con_el_ejemplo_y_valida(publicado):
    import jsonschema
    ruta = indice_catalogo.escribir_catalogo(str(publicado))
    obtenido = leer_json(ruta)
    jsonschema.Draft202012Validator(leer_json(CONTRATOS / "catalogo.schema.json")).validate(obtenido)
    assert sin_comentario(obtenido) == sin_comentario(leer_json(EJEMPLOS / "catalogo.json"))


def prueba_catalogo_excluye_artefactos_y_no_inventa_espectros(publicado):
    objetos = {o["id_candidato"]: o for o in leer_json(indice_catalogo.escribir_catalogo(str(publicado)))["objetos"]}
    assert "p002" not in objetos  # artefacto descartado
    candidatos = leer_json(publicado / "m7_publicacion" / CAMPO / "candidatos.json")
    for c in candidatos["candidatos"]:
        if c["id_candidato"] in objetos:
            tiene = objetos[c["id_candidato"]]["datos"]["espectro"] in ("real", "sintetico", "no_declarado")
            assert tiene == c["tiene_espectro"]


def prueba_estado_del_espectro_segun_origen_y_estado():
    conocido, nuevo = {"estado": "conocido"}, {"estado": "sin_identificar"}
    puntos = [_punto(1, 1), _punto(2, 1)]
    assert indice_catalogo.estado_espectro(conocido, {"origen": "real"}, puntos, {}) == "real"
    assert indice_catalogo.estado_espectro(conocido, {}, puntos, {"origen": "sintetico"}) == "sintetico"
    assert indice_catalogo.estado_espectro(conocido, {}, puntos, {}) == "no_declarado"  # nunca se supone real
    assert indice_catalogo.estado_espectro(conocido, None, [], {}) == "pendiente"
    assert indice_catalogo.estado_espectro(nuevo, None, [], {}) == "ninguno"


def prueba_designacion_solo_si_el_nombre_la_trae():
    assert indice_catalogo.designacion_de("(1766) Slipher") == "1766"
    assert indice_catalogo.designacion_de("3I/ATLAS") == "3I"
    assert indice_catalogo.designacion_de("1P/Halley") == "1P"
    assert indice_catalogo.designacion_de("Luhman 16 A") is None
    assert indice_catalogo.designacion_de(None) is None


def prueba_similitud_mide_la_forma_no_la_escala():
    a = [_punto(1.0 + 0.5 * i, 1.0 + 0.2 * i, 0.05) for i in range(7)]
    b = [{**p, "flujo_mjy": 3 * p["flujo_mjy"], "error_mjy": 3 * p["error_mjy"]} for p in a]
    plano = [{**p, "flujo_mjy": 1.0} for p in a]
    assert indice_catalogo.similitud(a, b)["valor"] == 0.0  # misma forma, otra escala
    assert indice_catalogo.similitud(a, plano)["valor"] > 1.0
    medida = indice_catalogo.similitud(a, b)
    assert medida["rango_comun_micras"] == [1.0, 4.0] and medida["n_puntos"] == 7


def prueba_similitud_exige_solape_y_puntos():
    a = [_punto(1.0, 1), _punto(1.2, 1), _punto(1.4, 1)]
    b = [_punto(3.0, 1), _punto(4.0, 1)]
    assert indice_catalogo.similitud(a, b) is None                      # sin solape
    c = [_punto(1.0, 1), _punto(3.0, 1)]
    d = [_punto(1.0, 1), _punto(3.0, 1)]
    assert indice_catalogo.similitud(c, d) is None                      # menos de 3 puntos comunes


def prueba_misma_clasificacion_solo_con_clase_catalogada():
    def entrada(ide, clase):
        return {"objeto": {"id_objeto": ide, "clasificacion": clase}, "puntos": []}
    entradas = [entrada("c/p001", "asteroide"), entrada("c/p002", "asteroide"), entrada("c/p003", "desconocida"),
                entrada("c/p004", "desconocida")]
    indice_catalogo.relacionar(entradas)
    assert entradas[0]["objeto"]["relacionados"]["misma_clasificacion"] == ["c/p002"]
    assert entradas[2]["objeto"]["relacionados"]["misma_clasificacion"] == []  # «desconocida» no agrupa
