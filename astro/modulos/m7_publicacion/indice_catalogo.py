# ============================================================================
# ARCHIVO: modulos/m7_publicacion/indice_catalogo.py
# MODULO: m7_publicacion (Lote A)
# ROL: Escribe catalogo.json: un objeto por pareja publicada, con su
#      clasificación, los datos disponibles y los objetos relacionados.
# LEE: datos/m7_publicacion/campos.json y, de cada campo, meta.json,
#      candidatos.json, espectros.json y la presencia de epoca_a.png.
# PRODUCE: datos/m7_publicacion/catalogo.json.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de indice_campos.py, copia_publicable.py, union_candidatos.py: los archivos publicados.
#   1. Recorrer los candidatos de cada campo (sin artefactos)  ->  objetos
#   2. Declarar qué datos existen de verdad (imagen, trayectoria, espectro)  ->  datos
#   3. Agrupar por clasificación catalogada  ->  misma_clasificacion
#   4. Comparar la forma de los espectros dos a dos  ->  espectros_similares
#   Entrega a control_publicacion.py, m9: catalogo.json.
# VERIFICACION: El archivo valida contra contratos/catalogo.schema.json; ningún
#   objeto declara un espectro que no está en espectros.json.
# USO: python -m modulos.m7_publicacion.indice_catalogo
# NOTA: Solo lee lo ya publicado, así que sirve igual para el pipeline real y para
#   los datos de demostración de m9. Usa solo la biblioteca estándar.
#   Similitud espectral: en el intervalo común de A y B (al menos 0,5 µm y 3 puntos
#   de A), B se interpola linealmente en las longitudes de onda de A; cada espectro
#   se divide por la mediana de su flujo en ese intervalo y se calcula
#   chi2 reducido = sum((a - b)^2 / (sa^2 + sb^2)) / (N - 1). Es una medida de
#   parecido de forma, no una clasificación: la interpolación solo se usa para
#   comparar, nunca se publica como dato observado.
# ============================================================================
"""Escribe el catálogo navegable a partir de los campos ya publicados."""
import json
import re
import statistics
import sys
from pathlib import Path

VERSION_CONTRATO = "1"
RAIZ_DATOS_POR_DEFECTO = "datos"
LAMBDA_MIN, LAMBDA_MAX = 0.75, 5.0
MINIMO_PUNTOS_ESPECTRO = 2
MINIMO_PUNTOS_COMUNES = 3
SOLAPE_MINIMO_MICRAS = 0.5
MAXIMO_SIMILARES = 5
METRICA = "chi2_reducido_entre_formas"
NORMALIZACION = "cada espectro dividido por la mediana de su flujo en el intervalo común"
FUENTE_CLASE_M5 = "identificacion.json (m5, catálogo de cuerpos menores)"

COMENTARIO = (
    "Generado por m7_publicacion/indice_catalogo.py. Solo objetos detectados en los campos "
    "publicados (sin artefactos descartados). La similitud espectral compara formas, no clasifica."
)


def leer_json(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)


def escribir_json(ruta, contenido):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(contenido, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")
    return ruta


# ----------------------------------------------------------------- nombres
def designacion_de(nombre):
    """Número o designación oficial al principio del nombre: (1766) Slipher -> 1766, 3I/ATLAS -> 3I."""
    if not nombre:
        return None
    numerado = re.match(r"^\((\d+)\)", nombre)
    if numerado:
        return numerado.group(1)
    cometa = re.match(r"^(\d+[PCDIX])/", nombre)
    return cometa.group(1) if cometa else None


# ----------------------------------------------------------------- espectros
def puntos_validos(espectro):
    if not espectro:
        return []
    puntos = [
        p for p in espectro.get("puntos", [])
        if isinstance(p.get("longitud_onda_micras"), (int, float))
        and LAMBDA_MIN <= p["longitud_onda_micras"] <= LAMBDA_MAX
        and isinstance(p.get("flujo_mjy"), (int, float))
        and isinstance(p.get("error_mjy"), (int, float)) and p["error_mjy"] > 0
    ]
    return sorted(puntos, key=lambda p: p["longitud_onda_micras"])


def interpolar(puntos, x):
    """Flujo y error de `puntos` en x por interpolación lineal; x debe estar dentro del rango."""
    for izquierda, derecha in zip(puntos, puntos[1:]):
        x0, x1 = izquierda["longitud_onda_micras"], derecha["longitud_onda_micras"]
        if x0 <= x <= x1:
            t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
            flujo = izquierda["flujo_mjy"] + t * (derecha["flujo_mjy"] - izquierda["flujo_mjy"])
            error = izquierda["error_mjy"] + t * (derecha["error_mjy"] - izquierda["error_mjy"])
            return flujo, error
    ultimo = puntos[-1]
    return ultimo["flujo_mjy"], ultimo["error_mjy"]


def similitud(a, b):
    """Parecido de forma entre dos listas de puntos. None si no hay base suficiente."""
    bajo = max(a[0]["longitud_onda_micras"], b[0]["longitud_onda_micras"])
    alto = min(a[-1]["longitud_onda_micras"], b[-1]["longitud_onda_micras"])
    if alto - bajo < SOLAPE_MINIMO_MICRAS:
        return None
    comunes = [p for p in a if bajo <= p["longitud_onda_micras"] <= alto]
    if len(comunes) < MINIMO_PUNTOS_COMUNES:
        return None
    interpolados = [interpolar(b, p["longitud_onda_micras"]) for p in comunes]
    norma_a = statistics.median(p["flujo_mjy"] for p in comunes)
    norma_b = statistics.median(f for f, _ in interpolados)
    if norma_a <= 0 or norma_b <= 0:
        return None
    chi2 = 0.0
    for p, (flujo_b, error_b) in zip(comunes, interpolados):
        diferencia = p["flujo_mjy"] / norma_a - flujo_b / norma_b
        varianza = (p["error_mjy"] / norma_a) ** 2 + (error_b / norma_b) ** 2
        chi2 += diferencia ** 2 / varianza
    return {
        "valor": round(chi2 / (len(comunes) - 1), 3),
        "rango_comun_micras": [round(bajo, 4), round(alto, 4)],
        "n_puntos": len(comunes),
    }


# ----------------------------------------------------------------- catálogo
def estado_espectro(candidato, espectro, puntos, meta):
    if espectro is not None and len(puntos) >= MINIMO_PUNTOS_ESPECTRO:
        origen = espectro.get("origen") or meta.get("origen")
        return origen if origen in ("real", "sintetico") else "no_declarado"
    return "pendiente" if candidato["estado"] == "conocido" else "ninguno"


def objetos_de_campo(campo, directorio):
    meta = leer_json(directorio / "meta.json")
    candidatos = leer_json(directorio / "candidatos.json")["candidatos"]
    ruta_espectros = directorio / "espectros.json"
    espectros = leer_json(ruta_espectros)["espectros"] if ruta_espectros.is_file() else []
    por_pareja = {e["id_pareja"]: e for e in espectros}
    hay_imagen = (directorio / meta["imagenes"]["epoca_a"]).is_file()
    objetos = []
    for c in candidatos:
        if c["estado"] == "artefacto_descartado":
            continue
        espectro = por_pareja.get(c["id_candidato"])
        puntos = puntos_validos(espectro)
        clase = c.get("clase_objeto") or "desconocida"
        objetos.append({
            "objeto": {
                "id_objeto": "%s/%s" % (campo, c["id_candidato"]),
                "campo": campo,
                "id_candidato": c["id_candidato"],
                "nombre": c["nombre_objeto"] or "Sin identificar (%s/%s)" % (campo, c["id_candidato"]),
                "designacion": designacion_de(c["nombre_objeto"]),
                "estado_identificacion": c["estado"],
                "clasificacion": clase,
                "fuente_clasificacion": FUENTE_CLASE_M5 if clase != "desconocida" else None,
                "datos": {
                    "imagen": hay_imagen,
                    "trayectoria": bool(c.get("posicion_a") and c.get("posicion_b")),
                    "espectro": estado_espectro(c, espectro, puntos, meta),
                },
                "n_puntos_espectrales": len(puntos),
                "tipo_espectral": espectro.get("tipo") if espectro else None,
            },
            "puntos": puntos,
        })
    return objetos


def relacionar(entradas):
    """Rellena misma_clasificacion y espectros_similares de cada objeto."""
    for entrada in entradas:
        objeto = entrada["objeto"]
        misma = []
        if objeto["clasificacion"] != "desconocida":
            misma = [
                o["objeto"]["id_objeto"] for o in entradas
                if o is not entrada and o["objeto"]["clasificacion"] == objeto["clasificacion"]
            ]
        similares = []
        if len(entrada["puntos"]) >= MINIMO_PUNTOS_ESPECTRO:
            for otra in entradas:
                if otra is entrada or len(otra["puntos"]) < MINIMO_PUNTOS_ESPECTRO:
                    continue
                medida = similitud(entrada["puntos"], otra["puntos"])
                if medida is None:
                    continue
                similares.append({"id_objeto": otra["objeto"]["id_objeto"], "metrica": METRICA,
                                  "valor": medida["valor"], "rango_comun_micras": medida["rango_comun_micras"],
                                  "normalizacion": NORMALIZACION, "n_puntos": medida["n_puntos"]})
            similares.sort(key=lambda s: s["valor"])
        objeto["relacionados"] = {"misma_clasificacion": misma, "espectros_similares": similares[:MAXIMO_SIMILARES]}


def construir_catalogo(raiz_datos=RAIZ_DATOS_POR_DEFECTO):
    publicado = Path(raiz_datos) / "m7_publicacion"
    campos = leer_json(publicado / "campos.json")["campos"]
    entradas = []
    for campo in campos:
        entradas.extend(objetos_de_campo(campo["campo"], publicado / campo["ruta"]))
    relacionar(entradas)
    return {
        "_comentario": COMENTARIO,
        "version_contrato": VERSION_CONTRATO,
        "objetos": [e["objeto"] for e in entradas],
    }


def escribir_catalogo(raiz_datos=RAIZ_DATOS_POR_DEFECTO):
    destino = Path(raiz_datos) / "m7_publicacion" / "catalogo.json"
    return escribir_json(destino, construir_catalogo(raiz_datos))


if __name__ == "__main__":
    if len(sys.argv) > 2:
        sys.exit("Uso: python -m modulos.m7_publicacion.indice_catalogo [raiz_datos]")
    ruta = escribir_catalogo(sys.argv[1] if len(sys.argv) == 2 else RAIZ_DATOS_POR_DEFECTO)
    total = len(leer_json(ruta)["objetos"])
    print("%s: %d objeto%s" % (ruta, total, "" if total == 1 else "s"))
