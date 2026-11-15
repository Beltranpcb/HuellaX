# ============================================================================
# ARCHIVO: modulos/m7_publicacion/union_candidatos.py
# MODULO: m7_publicacion (Lote A)
# ROL: Une los resultados de cada pareja en candidatos.json.
# LEE: fuentes.json; movimiento.json; identificacion.json; espectros.json.
# PRODUCE: datos/m7_publicacion/<campo>/candidatos.json.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de m3, m4, m5, m6: fuentes, movimiento, identificacion, espectros.
#   1. Unir las cuatro tablas por id_pareja  ->  registro por pareja
#   2. Omitir las parejas estacionarias  ->  candidatos.json
#   Entrega a indice_campos.py, control_publicacion.py, m9: candidatos.json.
# VERIFICACION: El archivo valida contra contratos/candidatos.schema.json; no
#   contiene ninguna pareja de clase estacionaria.
# USO: python -m modulos.m7_publicacion.union_candidatos <campo>
# ============================================================================
"""Une fuentes, movimiento, identificacion y espectros en candidatos.json.

El módulo no calcula nada: solo cruza cuatro tablas por `id_pareja` y aplica
una única regla de selección — las parejas estacionarias no se publican.
Si falta una tabla o una pareja, se detiene con un mensaje explícito en vez de
publicar un archivo incompleto.
"""
import json
import sys
from pathlib import Path

VERSION_CONTRATO = "1"
RAIZ_DATOS_POR_DEFECTO = "datos"

COMENTARIO = (
    "Generado por m7_publicacion/union_candidatos.py. Cada entrada es una "
    "pareja A-B verificada contra catálogos, no un descubrimiento."
)

# Origen de cada tabla de entrada, relativo a la raíz de datos.
ENTRADAS = {
    "fuentes": ("m3_deteccion", "fuentes.json"),
    "movimiento": ("m4_movimiento", "movimiento.json"),
    "identificacion": ("m5_identificacion", "identificacion.json"),
    "espectros": ("m6_huella_espectral", "espectros.json"),
}


def leer_json(ruta):
    """Lee un JSON en UTF-8 y lo devuelve como objeto de Python."""
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)


def escribir_json(ruta, contenido):
    """Escribe un objeto de Python como JSON legible, sin escapar acentos."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(contenido, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")
    return ruta


def comprobar_cabecera(documento, campo, nombre_archivo):
    """Comprueba la cabecera común a los cuatro contratos de entrada."""
    if documento.get("version_contrato") != VERSION_CONTRATO:
        raise ValueError(
            "%s: version_contrato %r, se esperaba %r"
            % (nombre_archivo, documento.get("version_contrato"), VERSION_CONTRATO)
        )
    if documento.get("campo") != campo:
        raise ValueError(
            "%s: el campo es %r, se esperaba %r"
            % (nombre_archivo, documento.get("campo"), campo)
        )


def indexar(elementos, clave, nombre_archivo):
    """Devuelve {clave: elemento} y rechaza una clave repetida."""
    indice = {}
    for elemento in elementos:
        valor = elemento[clave]
        if valor in indice:
            raise ValueError("%s: %s repetido: %r" % (nombre_archivo, clave, valor))
        indice[valor] = elemento
    return indice


def construir_candidatos(campo, fuentes, movimiento, identificacion, espectros):
    """Monta candidatos.json según contratos/candidatos.schema.json."""
    for documento, nombre in (
        (fuentes, "fuentes.json"),
        (movimiento, "movimiento.json"),
        (identificacion, "identificacion.json"),
        (espectros, "espectros.json"),
    ):
        comprobar_cabecera(documento, campo, nombre)

    fuentes_por_id = indexar(fuentes["fuentes"], "id_fuente", "fuentes.json")
    parejas_por_id = indexar(fuentes["parejas"], "id_pareja", "fuentes.json")
    movimiento_por_id = indexar(movimiento["parejas"], "id_pareja", "movimiento.json")
    identificacion_por_id = indexar(
        identificacion["identificaciones"], "id_pareja", "identificacion.json"
    )
    espectros_por_id = indexar(espectros["espectros"], "id_pareja", "espectros.json")

    mjd_a = fuentes["epocas"]["epoca_a"]["mjd"]
    mjd_b = fuentes["epocas"]["epoca_b"]["mjd"]

    candidatos = []
    for id_pareja, medida in movimiento_por_id.items():
        # Regla única de selección: una pareja estacionaria no es candidata.
        if medida["clase"] == "estacionaria":
            continue

        pareja = parejas_por_id.get(id_pareja)
        if pareja is None:
            raise ValueError(
                "movimiento.json cita la pareja %r y fuentes.json no la propone"
                % id_pareja
            )

        fuente_a = fuentes_por_id.get(pareja["id_fuente_a"])
        fuente_b = fuentes_por_id.get(pareja["id_fuente_b"])
        if fuente_a is None or fuente_b is None:
            raise ValueError(
                "la pareja %r apunta a fuentes que no están en fuentes.json" % id_pareja
            )

        identificacion_pareja = identificacion_por_id.get(id_pareja)
        if identificacion_pareja is None:
            raise ValueError(
                "identificacion.json no trae la pareja %r (debe traer todas las no "
                "estacionarias)" % id_pareja
            )

        espectro = espectros_por_id.get(id_pareja)
        candidatos.append(
            {
                "id_candidato": id_pareja,
                "estado": identificacion_pareja["estado"],
                "nombre_objeto": identificacion_pareja["nombre_objeto"],
                "distancia_catalogo_segarc": identificacion_pareja["distancia_segarc"],
                "clase_movimiento": medida["clase"],
                "posicion_a": {
                    "ra_grados": fuente_a["ra_grados"],
                    "dec_grados": fuente_a["dec_grados"],
                    "x": fuente_a["x"],
                    "y": fuente_a["y"],
                    "mjd": mjd_a,
                },
                "posicion_b": {
                    "ra_grados": fuente_b["ra_grados"],
                    "dec_grados": fuente_b["dec_grados"],
                    "x": fuente_b["x"],
                    "y": fuente_b["y"],
                    "mjd": mjd_b,
                },
                "separacion_segarc": medida["separacion_segarc"],
                "velocidad_segarc_por_hora": medida["velocidad_segarc_por_hora"],
                "incertidumbre_velocidad": medida["incertidumbre_velocidad"],
                "significancia": medida["significancia"],
                "tiene_espectro": espectro is not None,
                "tipo": espectro["tipo"] if espectro is not None else None,
                "temperatura_k": espectro["temperatura_k"] if espectro is not None else None,
            }
        )

    return {
        "_comentario": COMENTARIO,
        "version_contrato": VERSION_CONTRATO,
        "campo": campo,
        "candidatos": candidatos,
    }


def cargar_tabla(raiz, campo, nombre, directorio, archivo):
    """Lee una tabla de entrada y, si falta, dice qué módulo hay que ejecutar."""
    ruta = raiz / directorio / campo / archivo
    if not ruta.is_file():
        raise FileNotFoundError(
            "falta %s\n  el campo %r todavía no tiene %s: ejecuta %s para ese campo"
            % (ruta, campo, archivo, directorio)
        )
    return leer_json(ruta)


def unir_campo(campo, raiz_datos=RAIZ_DATOS_POR_DEFECTO):
    """Lee las cuatro tablas del campo y escribe su candidatos.json."""
    raiz = Path(raiz_datos)
    tablas = {
        nombre: cargar_tabla(raiz, campo, nombre, directorio, archivo)
        for nombre, (directorio, archivo) in ENTRADAS.items()
    }
    contenido = construir_candidatos(
        campo,
        tablas["fuentes"],
        tablas["movimiento"],
        tablas["identificacion"],
        tablas["espectros"],
    )
    return escribir_json(raiz / "m7_publicacion" / campo / "candidatos.json", contenido)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m7_publicacion.union_candidatos <campo>")
    ruta_escrita = unir_campo(sys.argv[1])
    total = len(leer_json(ruta_escrita)["candidatos"])
    print("%s: %d candidato%s" % (ruta_escrita, total, "" if total == 1 else "s"))
