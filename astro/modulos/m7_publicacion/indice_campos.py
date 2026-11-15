# ============================================================================
# ARCHIVO: modulos/m7_publicacion/indice_campos.py
# MODULO: m7_publicacion (Lote A)
# ROL: Escribe campos.json con la lista de campos publicados.
# LEE: Los directorios de datos/m7_publicacion/ con su meta.json, su candidatos.json.
# PRODUCE: datos/m7_publicacion/campos.json.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de union_candidatos.py, copia_publicable.py: candidatos.json, meta.json de cada campo.
#   1. Recorrer los campos publicados  ->  directorios de campo
#   2. Contar los candidatos de cada uno  ->  campos.json
#   Entrega a control_publicacion.py, m9: campos.json.
# VERIFICACION: El archivo valida contra contratos/campos.schema.json;
#   numero_candidatos coincide con el recuento real; un meta.json o un
#   candidatos.json incompleto se rechaza con un mensaje que nombra el archivo.
# USO: python -m modulos.m7_publicacion.indice_campos
# ============================================================================
"""Escribe el índice campos.json a partir de los directorios ya publicados.

Solo entran los directorios que tienen a la vez meta.json y candidatos.json:
un campo a medio publicar no se anuncia en la web. La falta de esos archivos
la denuncia control_publicacion.py, no este índice.
"""
import json
import sys
from pathlib import Path

VERSION_CONTRATO = "1"
RAIZ_DATOS_POR_DEFECTO = "datos"

COMENTARIO = (
    "Generado por m7_publicacion/indice_campos.py. Un campo aparece aquí solo "
    "cuando su meta.json y su candidatos.json están publicados."
)


def leer_json(ruta):
    """Lee un JSON en UTF-8 y lo devuelve como objeto de Python."""
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)


def leer_campo(directorio):
    """Devuelve (nombre, número de candidatos) de un campo ya publicado.

    Un archivo a medio escribir no debe reventar con un KeyError: se avisa de
    qué archivo falta qué clave, para que se pueda volver a lanzar el módulo
    que lo genera.
    """
    ruta_meta = directorio / "meta.json"
    ruta_candidatos = directorio / "candidatos.json"

    try:
        meta = leer_json(ruta_meta)
    except json.JSONDecodeError as error:
        raise ValueError("%s: JSON ilegible (%s)" % (ruta_meta, error.msg)) from error
    if "nombre" not in meta:
        raise ValueError(
            "%s: falta la clave 'nombre' (¿se escribió a medias?)" % ruta_meta
        )

    try:
        candidatos = leer_json(ruta_candidatos)
    except json.JSONDecodeError as error:
        raise ValueError("%s: JSON ilegible (%s)" % (ruta_candidatos, error.msg)) from error
    if "candidatos" not in candidatos:
        raise ValueError(
            "%s: falta la clave 'candidatos' (¿se escribió a medias?)" % ruta_candidatos
        )

    return meta["nombre"], len(candidatos["candidatos"])


def construir_campos(raiz_datos=RAIZ_DATOS_POR_DEFECTO):
    """Devuelve el contenido de campos.json según contratos/campos.schema.json."""
    base = Path(raiz_datos) / "m7_publicacion"
    if not base.is_dir():
        raise FileNotFoundError("no existe el directorio publicado %s" % base)

    campos = []
    for directorio in sorted(ruta for ruta in base.iterdir() if ruta.is_dir()):
        if not ((directorio / "meta.json").is_file() and (directorio / "candidatos.json").is_file()):
            continue

        nombre, numero_candidatos = leer_campo(directorio)
        campos.append(
            {
                "campo": directorio.name,
                "nombre": nombre,
                "ruta": directorio.name,
                "numero_candidatos": numero_candidatos,
            }
        )

    return {
        "_comentario": COMENTARIO,
        "version_contrato": VERSION_CONTRATO,
        "campos": campos,
    }


def escribir_campos(raiz_datos=RAIZ_DATOS_POR_DEFECTO):
    """Escribe datos/m7_publicacion/campos.json y devuelve su ruta."""
    contenido = construir_campos(raiz_datos)
    destino = Path(raiz_datos) / "m7_publicacion" / "campos.json"
    with open(destino, "w", encoding="utf-8") as archivo:
        json.dump(contenido, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")
    return destino


if __name__ == "__main__":
    if len(sys.argv) != 1:
        sys.exit("Uso: python -m modulos.m7_publicacion.indice_campos")
    ruta_escrita = escribir_campos()
    total = len(leer_json(ruta_escrita)["campos"])
    print("%s: %d campo%s" % (ruta_escrita, total, "" if total == 1 else "s"))
