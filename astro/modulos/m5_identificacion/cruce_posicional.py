# ============================================================================
# ARCHIVO: modulos/m5_identificacion/cruce_posicional.py
# MODULO: m5_identificacion (Lote B)
# ROL: Decide el estado de catálogo de cada pareja.
# LEE: Respuestas en cache/; fuentes.json; movimiento.json.
# PRODUCE: datos/m5_identificacion/<campo>/identificacion.json.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de consulta_catalogos.py: respuestas en cache/.
#   1. Leer las posiciones predichas  ->  objetos conocidos cercanos
#   2. Medir la distancia a la posición observada  ->  distancia en segundos de arco
#   3. Comparar con la tolerancia de 15 segundos de arco  ->  estado conocido o sin_identificar
#   4. Marcar artefacto_descartado toda pareja no_concluyente sin coincidencia  ->  identificacion.json
#   Entrega a m7: identificacion.json.
# VERIFICACION: El archivo valida contra contratos/identificacion.schema.json; todo estado conocido lleva nombre_objeto con distancia_segarc menor o igual que 15.
# USO: python -m modulos.m5_identificacion.cruce_posicional <campo>
# NOTA: Exige que consulta_catalogos.py haya guardado antes la respuesta de cada pareja.
#       Si falta alguna, falla nombrándola: la demo nunca debe depender de la red en directo.
# ============================================================================
import json
import math
import sys
from pathlib import Path

from modulos.m5_identificacion.consulta_catalogos import consultas_pendientes, nombre_cache

TOLERANCIA_SEGARC = 15.0  # 2 a 3 píxeles: cubre el desplazamiento por la órbita de SPHEREx


def separacion_segarc(ra1, dec1, ra2, dec2):
    """Distancia angular sobre la esfera (fórmula del haversine), en segundos de arco."""
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    h = math.sin((d2 - d1) / 2) ** 2 + math.cos(d1) * math.cos(d2) * math.sin((r2 - r1) / 2) ** 2
    return math.degrees(2 * math.asin(min(1.0, math.sqrt(h)))) * 3600


def objetos_de_la_cache(respuesta):
    """Aplana las respuestas de todos los servicios en una lista de objetos con su catálogo."""
    objetos = []
    for catalogo, r in respuesta.get("respuestas", {}).items():
        if r.get("estado") != "ok":
            continue
        for o in r.get("objetos", []):
            objetos.append({**o, "catalogo": catalogo})
    return objetos


def coincidencia_mas_cercana(ra_grados, dec_grados, objetos):
    """El objeto más cercano a la posición observada, con su distancia; None si no hay objetos."""
    mejor = None
    for o in objetos:
        d = separacion_segarc(ra_grados, dec_grados, o["ra_grados"], o["dec_grados"])
        if mejor is None or d < mejor[1]:
            mejor = (o, d)
    return mejor


def decidir(consulta, clase, respuesta, archivo_cache, tolerancia=TOLERANCIA_SEGARC):
    """Devuelve la entrada de identificacion.json de una pareja."""
    mejor = coincidencia_mas_cercana(consulta["ra_grados"], consulta["dec_grados"], objetos_de_la_cache(respuesta))
    if mejor is not None and mejor[1] <= tolerancia:
        objeto, distancia = mejor
        return {"id_pareja": consulta["id_pareja"], "estado": "conocido", "nombre_objeto": objeto["nombre"],
                "catalogo": objeto["catalogo"],
                "posicion_predicha": {"ra_grados": objeto["ra_grados"], "dec_grados": objeto["dec_grados"]},
                "distancia_segarc": round(distancia, 2), "archivo_cache": archivo_cache}
    estado = "artefacto_descartado" if clase == "no_concluyente" else "sin_identificar"
    return {"id_pareja": consulta["id_pareja"], "estado": estado, "nombre_objeto": None, "catalogo": None,
            "posicion_predicha": None, "distancia_segarc": None, "archivo_cache": archivo_cache}


def construir_identificacion_json(campo, fuentes, movimiento, leer_cache, tolerancia=TOLERANCIA_SEGARC):
    """Monta identificacion.json. `leer_cache(nombre)` devuelve el contenido guardado o lanza FileNotFoundError."""
    clases = {p["id_pareja"]: p["clase"] for p in movimiento["parejas"]}
    identificaciones, faltan = [], []
    for consulta in consultas_pendientes(fuentes, movimiento):
        archivo = nombre_cache(campo, consulta["id_pareja"])
        try:
            respuesta = leer_cache(archivo)
        except FileNotFoundError:
            faltan.append(archivo)
            continue
        identificaciones.append(decidir(consulta, clases[consulta["id_pareja"]], respuesta, archivo, tolerancia))
    if faltan:
        raise FileNotFoundError("faltan respuestas en la caché; ejecutar antes consulta_catalogos: %s" % ", ".join(faltan))
    return {
        "_comentario": "Generado por m5_identificacion. Un estado conocido no confirma la detección: solo dice que había un objeto catalogado en esa posición.",
        "version_contrato": "1",
        "campo": campo,
        "tolerancia_segarc": tolerancia,
        "identificaciones": identificaciones,
    }


def cruzar_campo(campo, raiz_datos="datos"):
    """Lee fuentes.json (m3), movimiento.json (m4) y la caché (m5); escribe identificacion.json. Devuelve su ruta."""
    raiz = Path(raiz_datos)
    fuentes = json.loads((raiz / "m3_deteccion" / campo / "fuentes.json").read_text(encoding="utf-8"))
    movimiento = json.loads((raiz / "m4_movimiento" / campo / "movimiento.json").read_text(encoding="utf-8"))
    cache = raiz / "m5_identificacion" / "cache"

    def leer_cache(nombre):
        return json.loads((cache / nombre).read_text(encoding="utf-8"))

    contenido = construir_identificacion_json(campo, fuentes, movimiento, leer_cache)
    directorio = raiz / "m5_identificacion" / campo
    directorio.mkdir(parents=True, exist_ok=True)
    ruta = directorio / "identificacion.json"
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m5_identificacion.cruce_posicional <campo>")
    ruta_escrita = cruzar_campo(sys.argv[1])
    entradas = json.loads(ruta_escrita.read_text(encoding="utf-8"))["identificaciones"]
    recuento = {e: sum(i["estado"] == e for i in entradas) for e in ("conocido", "sin_identificar", "artefacto_descartado")}
    print("%s: %s" % (ruta_escrita, recuento))
