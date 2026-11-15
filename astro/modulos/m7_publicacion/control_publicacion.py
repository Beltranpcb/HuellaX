# ============================================================================
# ARCHIVO: modulos/m7_publicacion/control_publicacion.py
# MODULO: m7_publicacion (Lote A)
# ROL: Rechaza la publicación cuando un archivo incumple su contrato.
# LEE: Todo el contenido de datos/m7_publicacion/; los esquemas de contratos/.
# PRODUCE: Un informe por pantalla con código de salida 0 si todo cumple.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de indice_campos.py: directorio publicado completo.
#   1. Validar cada JSON contra su esquema  ->  lista de incumplimientos
#   2. Medir el tamaño de cada archivo  ->  archivos de más de 1 MB
#   3. Leer la cabecera de los tres PNG  ->  PNG que no miden 600 x 600
#   4. Fijar el código de salida  ->  informe de control
#   Entrega a quien publica: informe de control.
# VERIFICACION: Con los ejemplos sale con código 0; con un JSON inválido, un
#   archivo de más de 1 MB o un PNG de otro tamaño sale con código distinto de cero.
# USO: python -m modulos.m7_publicacion.control_publicacion
# ============================================================================
"""Puerta de salida de la publicación: nada llega a la web sin pasar por aquí.

Comprueba cinco cosas y las reúne en un solo informe:
  1. que cada JSON valide contra el esquema de contratos/;
  2. que no falte ninguno de los seis archivos que la web espera de un campo;
  3. que ningún archivo supere 1 MB (los PNG deben pesar menos; el resto son
     JSON pequeños);
  4. que los tres PNG midan 600 x 600, como fija contratos/imagenes_png.md;
  5. que el número de candidatos anunciado en campos.json sea el real.

El punto 5 es el más silencioso: un índice desfasado deja la web mostrando un
campo vacío sin dar ningún error.
"""
import json
import struct
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

RAIZ_MODULO = Path(__file__).resolve().parent
RAIZ_DATOS_POR_DEFECTO = "datos"

# Los esquemas viven en contratos/ cuando el árbol completo está presente. Si
# este módulo se usa suelto, se leen los que viajan con él en esquemas/.
RAIZ_ESQUEMAS_PROPIOS = RAIZ_MODULO / "esquemas"


def buscar_contratos():
    """Sube por los directorios padre hasta encontrar contratos/."""
    for base in RAIZ_MODULO.parents:
        candidato = base / "contratos"
        if candidato.is_dir():
            return candidato
    return None

# Nombre de archivo publicado -> esquema que debe cumplir.
ESQUEMAS = {
    "campos.json": "campos.schema.json",
    "meta.json": "meta.schema.json",
    "candidatos.json": "candidatos.schema.json",
    "espectros.json": "espectros.schema.json",
}

# Archivos comunes a todos los campos que la web lee si existen (plantillas de m6, catálogo de m7).
ESQUEMAS_OPCIONALES = {
    "plantillas.json": "plantillas.schema.json",
    "catalogo.json": "catalogo.schema.json",
}

# Lo que la web necesita encontrar en el directorio de cada campo.
ARCHIVOS_PNG = ("epoca_a.png", "epoca_b.png", "diferencia.png")
ARCHIVOS_DEL_CAMPO = ("meta.json", "candidatos.json", "espectros.json") + ARCHIVOS_PNG

MAXIMO_BYTES = 1024 * 1024

# Tamaño que exige contratos/imagenes_png.md para los tres PNG.
TAMANO_PNG = (600, 600)
FIRMA_PNG = b"\x89PNG\r\n\x1a\n"


def leer_json(ruta):
    """Lee un JSON en UTF-8 y lo devuelve como objeto de Python."""
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)


def resolver_contratos(raiz_contratos=None):
    """Devuelve el directorio de esquemas que se debe usar.

    Orden de preferencia: el que pida quien llama, luego `contratos/` del
    repositorio y, si no existe, los esquemas propios del módulo. Así el
    control funciona igual dentro del árbol completo que suelto.
    """
    if raiz_contratos is not None:
        return Path(raiz_contratos)
    canonico = buscar_contratos()
    if canonico is not None:
        return canonico
    return RAIZ_ESQUEMAS_PROPIOS


def cargar_validador(raiz_contratos, nombre_esquema):
    """Devuelve un validador del esquema pedido, o None si no se puede leer."""
    ruta = Path(raiz_contratos) / nombre_esquema
    if not ruta.is_file():
        return None
    return Draft202012Validator(leer_json(ruta))


def describir_error(error):
    """Resume un error de esquema en una línea legible."""
    lugar = ".".join(str(parte) for parte in error.absolute_path)
    return "%s: %s" % (lugar, error.message) if lugar else error.message


def validar_json(ruta, validador):
    """Devuelve la lista de incumplimientos de un archivo contra su esquema."""
    try:
        documento = leer_json(ruta)
    except json.JSONDecodeError as error:
        return ["%s: JSON ilegible (%s)" % (ruta, error.msg)]

    errores = sorted(validador.iter_errors(documento), key=lambda e: list(e.absolute_path))
    return ["%s: %s" % (ruta, describir_error(error)) for error in errores]


def dimensiones_png(ruta):
    """Devuelve (ancho, alto) leyendo la cabecera IHDR, o None si no es un PNG.

    Se leen solo los primeros 24 bytes: la firma y el bloque IHDR. Así no hace
    falta ninguna biblioteca de imagen para comprobar el tamaño.
    """
    with open(ruta, "rb") as archivo:
        cabecera = archivo.read(24)
    if len(cabecera) < 24 or cabecera[:8] != FIRMA_PNG or cabecera[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", cabecera[16:24])


def validar_pngs(directorio):
    """Comprueba que los tres PNG del campo miden lo que fija el contrato."""
    problemas = []
    for nombre in ARCHIVOS_PNG:
        ruta = directorio / nombre
        if not ruta.is_file():
            continue  # la ausencia ya la denuncia la lista de archivos
        medidas = dimensiones_png(ruta)
        if medidas is None:
            problemas.append("%s: no se puede leer como PNG" % ruta)
        elif medidas != TAMANO_PNG:
            problemas.append(
                "%s: mide %d x %d, el contrato exige %d x %d"
                % (ruta, medidas[0], medidas[1], TAMANO_PNG[0], TAMANO_PNG[1])
            )
    return problemas


def es_sintetico(directorio):
    """Verdadero si el meta.json del campo declara origen «sintetico»."""
    ruta = directorio / "meta.json"
    try:
        return ruta.is_file() and leer_json(ruta).get("origen") == "sintetico"
    except (json.JSONDecodeError, AttributeError):
        return False


def validar_catalogo_contra_candidatos(base):
    """Cada objeto de catalogo.json debe ser un candidato publicado y no anunciar un espectro que no existe."""
    ruta = base / "catalogo.json"
    if not ruta.is_file():
        return []
    try:
        objetos = leer_json(ruta)["objetos"]
    except (json.JSONDecodeError, KeyError):
        return []  # el esquema ya lo denuncia
    problemas = []
    for objeto in objetos:
        ruta_candidatos = base / objeto.get("campo", "") / "candidatos.json"
        if not ruta_candidatos.is_file():
            problemas.append("catalogo.json: %s es de un campo no publicado" % objeto.get("id_objeto"))
            continue
        candidatos = {c["id_candidato"]: c for c in leer_json(ruta_candidatos)["candidatos"]}
        candidato = candidatos.get(objeto.get("id_candidato"))
        if candidato is None:
            problemas.append("catalogo.json: %s no está en candidatos.json" % objeto.get("id_objeto"))
        elif objeto.get("datos", {}).get("espectro") in ("real", "sintetico", "no_declarado") and not candidato["tiene_espectro"]:
            problemas.append("catalogo.json: %s anuncia un espectro que candidatos.json no tiene" % objeto.get("id_objeto"))
    return problemas


def validar(raiz_datos=RAIZ_DATOS_POR_DEFECTO, raiz_contratos=None):
    """Recorre la publicación y devuelve la lista de incumplimientos."""
    raiz_contratos = resolver_contratos(raiz_contratos)
    base = Path(raiz_datos) / "m7_publicacion"
    if not base.is_dir():
        return ["no existe el directorio publicado %s" % base]

    problemas = []

    # 1. El índice de campos es el punto de entrada de la web.
    ruta_campos = base / "campos.json"
    validador_campos = cargar_validador(raiz_contratos, ESQUEMAS["campos.json"])
    if validador_campos is None:
        problemas.append("no se encuentra %s/contratos/%s" % (raiz_contratos, ESQUEMAS["campos.json"]))
    elif not ruta_campos.is_file():
        problemas.append("falta %s" % ruta_campos)
    else:
        problemas.extend(validar_json(ruta_campos, validador_campos))

    # 2. Cada campo publicado completo y conforme a su esquema.
    for directorio in sorted(ruta for ruta in base.iterdir() if ruta.is_dir()):
        # Un campo que se declara sintético (datos de demostración de m9) puede no traer los PNG:
        # la web los sintetiza y lo avisa. Un campo real o sin origen declarado sí los necesita.
        exigidos = ARCHIVOS_DEL_CAMPO
        if es_sintetico(directorio):
            exigidos = tuple(n for n in ARCHIVOS_DEL_CAMPO if n not in ARCHIVOS_PNG)
        faltan = [nombre for nombre in exigidos if not (directorio / nombre).is_file()]
        for nombre in faltan:
            problemas.append("%s: falta %s" % (directorio, nombre))

        for ruta in sorted(directorio.iterdir()):
            if ruta.is_file() and ruta.stat().st_size > MAXIMO_BYTES:
                problemas.append(
                    "%s: %.1f MB, supera el máximo de 1 MB"
                    % (ruta, ruta.stat().st_size / MAXIMO_BYTES)
                )

        problemas.extend(validar_pngs(directorio))

        for nombre, esquema in ESQUEMAS.items():
            ruta = directorio / nombre
            if nombre == "campos.json" or not ruta.is_file():
                continue
            validador = cargar_validador(raiz_contratos, esquema)
            if validador is None:
                problemas.append("no se encuentra %s/contratos/%s" % (raiz_contratos, esquema))
                continue
            problemas.extend(validar_json(ruta, validador))

    # 2 bis. Archivos comunes opcionales: si están, cumplen su contrato.
    for nombre, esquema in ESQUEMAS_OPCIONALES.items():
        ruta = base / nombre
        if not ruta.is_file():
            continue
        validador = cargar_validador(raiz_contratos, esquema)
        if validador is None:
            problemas.append("no se encuentra %s/contratos/%s" % (raiz_contratos, esquema))
            continue
        problemas.extend(validar_json(ruta, validador))
    problemas.extend(validar_catalogo_contra_candidatos(base))

    # 3. El recuento anunciado tiene que ser el real.
    if ruta_campos.is_file() and validador_campos is not None:
        try:
            anunciado = leer_json(ruta_campos)["campos"]
        except (json.JSONDecodeError, KeyError):
            anunciado = []
        for entrada in anunciado:
            ruta_candidatos = base / entrada["ruta"] / "candidatos.json"
            if not ruta_candidatos.is_file():
                problemas.append("campos.json anuncia %r y no existe %s" % (entrada["campo"], ruta_candidatos))
                continue
            reales = len(leer_json(ruta_candidatos)["candidatos"])
            if reales != entrada["numero_candidatos"]:
                problemas.append(
                    "campos.json dice %d candidatos en %r y hay %d"
                    % (entrada["numero_candidatos"], entrada["campo"], reales)
                )

    return problemas


def main():
    """Imprime el informe y devuelve 0 si la publicación es válida."""
    problemas = validar()
    if problemas:
        print("Publicación rechazada: %d incumplimientos" % len(problemas))
        for problema in problemas:
            print("  - %s" % problema)
        return 1
    print("Publicación válida: todos los archivos cumplen su contrato.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
