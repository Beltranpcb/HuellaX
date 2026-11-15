# ============================================================================
# ARCHIVO: modulos/m5_identificacion/consulta_catalogos.py
# MODULO: m5_identificacion (Lote B)
# ROL: Obtiene la respuesta del catálogo de cuerpos menores para cada pareja en movimiento.
# LEE: fuentes.json; movimiento.json; datos/m5_identificacion/cache/; API sb_ident de JPL; MPChecker del MPC.
# PRODUCE: Un archivo de respuesta por pareja en datos/m5_identificacion/cache/.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de m3_deteccion, m4_movimiento: fuentes.json, movimiento.json.
#   1. Leer posición, fecha de cada pareja no estacionaria  ->  consultas pendientes
#   2. Buscar cada respuesta en la caché  ->  consultas sin respuesta guardada
#   3. Preguntar a MPChecker y a JPL sb_ident (los dos; basta con que uno responda)  ->  respuesta nueva
#   4. Guardar la respuesta normalizada  ->  respuestas en cache/
#   Entrega a cruce_posicional.py: respuestas en cache/.
# VERIFICACION: Una segunda ejecución sobre el mismo campo no abre ninguna conexión de red.
# USO: python -m modulos.m5_identificacion.consulta_catalogos <campo>
# NOTA: Observador geocéntrico (MPC: código 500; JPL: lat 0, lon 0, alt 0). SPHEREx orbita a
#       ~650 km; el error de paralaje para un objeto a 1 UA es menor que 9", dentro de la
#       tolerancia de 15" del contrato. Para un objeto muy cercano a la Tierra podría superarla.
# ============================================================================
import datetime
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

RADIO_BUSQUEDA_SEGARC = 60.0  # 1 minuto de arco: ~85 veces el error de posición típico (0,7″)
URL_JPL = "https://ssd-api.jpl.nasa.gov/sb_ident.api"
URL_MPCHECKER = "https://minorplanetcenter.net/cgi-bin/mpcheck.cgi"
TIEMPO_MAXIMO_JPL_S = 30  # JPL tarda hasta 170 s con integración numérica; 30 s basta para identificar
TIEMPO_MAXIMO_MPC_S = 30
AGENTE = "HUELLA-X/0.1 (NASA Space Apps 2026; python-requests)"
SERVICIOS = ("mpchecker", "jpl_sb_ident")
CONSULTAS_EN_PARALELO = 8


# ------------------------------------------------------------- conversiones
def mjd_a_datetime(mjd):
    return datetime.datetime(1858, 11, 17, tzinfo=datetime.timezone.utc) + datetime.timedelta(days=float(mjd))


def fecha_jpl(mjd):
    """MJD -> 'YYYY-MM-DD_hh:mm:ss' (formato obs-time de sb_ident)."""
    return mjd_a_datetime(mjd).strftime("%Y-%m-%d_%H:%M:%S")


def fecha_mpc(mjd):
    """MJD -> (año, mes, día decimal con dos cifras) para el formulario de MPChecker."""
    f = mjd_a_datetime(mjd)
    dia = f.day + (f.hour + f.minute / 60 + f.second / 3600) / 24
    return "%d" % f.year, "%02d" % f.month, "%05.2f" % dia


def _sexagesimal(valor, partes_por_grado, separador, signo_negativo="-"):
    signo = signo_negativo if valor < 0 else ""
    total = abs(valor) * partes_por_grado * 3600
    h = int(total // 3600)
    m = int((total - h * 3600) // 60)
    s = total - h * 3600 - m * 60
    if round(s, 2) >= 60:
        s, m = 0.0, m + 1
    if m >= 60:
        m, h = 0, h + 1
    return "%s%02d%s%02d%s%05.2f" % (signo, h, separador, m, separador, s)


def ra_grados_a_horas(ra_grados, separador):
    return _sexagesimal(ra_grados / 15.0, 1, separador)


def dec_grados_a_sexagesimal(dec_grados, separador, signo_negativo="-", signo_positivo=""):
    texto = _sexagesimal(dec_grados, 1, separador, signo_negativo)
    return texto if dec_grados < 0 else signo_positivo + texto


def sexagesimal_a_grados(texto, es_ra=False):
    """'09:59:26.2', '+10 09'11\"', '-05 12 03.5' -> grados."""
    m = re.match(r"\s*([+-]?)\s*(\d+)\D+(\d+)\D+(\d+(?:\.\d+)?)", texto)
    if not m:
        raise ValueError("coordenada ilegible: %r" % texto)
    valor = int(m.group(2)) + int(m.group(3)) / 60 + float(m.group(4)) / 3600
    if es_ra:
        valor *= 15.0
    return -valor if m.group(1) == "-" else valor


def _magnitud(texto):
    try:
        return float(str(texto).strip())
    except (TypeError, ValueError):
        return None


# -------------------------------------------------------------- JPL sb_ident
def parametros_jpl(ra_grados, dec_grados, mjd, radio_segarc=RADIO_BUSQUEDA_SEGARC):
    semilado = radio_segarc / 3600.0
    return {
        "obs-time": fecha_jpl(mjd),
        "fov-ra-center": ra_grados_a_horas(ra_grados, "-"),
        "fov-dec-center": dec_grados_a_sexagesimal(dec_grados, "-", signo_negativo="M"),
        "fov-ra-hwidth": round(semilado, 5),
        "fov-dec-hwidth": round(semilado, 5),
        "lat": 0, "lon": 0, "alt": 0,
        "two-pass": "true", "suppress-first-pass": "true",
    }


def _pedir_jpl(parametros):
    """Única llamada de red a JPL. Las pruebas la sustituyen."""
    respuesta = requests.get(URL_JPL, params=parametros, timeout=TIEMPO_MAXIMO_JPL_S, headers={"User-Agent": AGENTE})
    respuesta.raise_for_status()
    return respuesta.json()


def interpretar_jpl(datos):
    """Normaliza la respuesta JSON de sb_ident a una lista de objetos."""
    if "data_second_pass" in datos:
        campos, filas = datos.get("fields_second") or [], datos.get("data_second_pass") or []
    elif "data_first_pass" in datos:
        campos, filas = datos.get("fields_first") or [], datos.get("data_first_pass") or []
    else:
        raise ValueError("respuesta de JPL sin tabla de objetos: %s" % sorted(datos))

    def indice(prefijo):
        for i, nombre in enumerate(campos):
            if nombre.startswith(prefijo):
                return i
        raise ValueError("JPL no devuelve el campo %r" % prefijo)

    i_nombre, i_ra, i_dec = indice("Object name"), indice("Astrometric RA"), indice("Astrometric Dec")
    i_mag = next((i for i, n in enumerate(campos) if n.startswith("Visual magnitude")), None)
    return [{"nombre": fila[i_nombre].strip(),
             "ra_grados": round(sexagesimal_a_grados(fila[i_ra], es_ra=True), 6),
             "dec_grados": round(sexagesimal_a_grados(fila[i_dec]), 6),
             "magnitud_v": _magnitud(fila[i_mag]) if i_mag is not None else None}
            for fila in filas]


def consultar_jpl(ra_grados, dec_grados, mjd):
    return interpretar_jpl(_pedir_jpl(parametros_jpl(ra_grados, dec_grados, mjd)))


# --------------------------------------------------------------- MPChecker
def formulario_mpchecker(ra_grados, dec_grados, mjd, radio_segarc=RADIO_BUSQUEDA_SEGARC):
    ano, mes, dia = fecha_mpc(mjd)
    return {
        "year": ano, "month": mes, "day": dia, "which": "pos",
        "ra": ra_grados_a_horas(ra_grados, " "),
        "decl": dec_grados_a_sexagesimal(dec_grados, " ", signo_positivo="+"),
        "TextArea": "", "radius": "%d" % max(1, round(radio_segarc / 60.0)), "limit": "24.0",
        "oc": "500", "sort": "d", "mot": "h", "tmot": "s", "pdes": "u", "needed": "f", "ps": "n", "type": "p",
    }


def _pedir_mpchecker(formulario):
    """Única llamada de red al MPC. Las pruebas la sustituyen."""
    respuesta = requests.post(URL_MPCHECKER, data=formulario, timeout=TIEMPO_MAXIMO_MPC_S, headers={"User-Agent": AGENTE})
    respuesta.raise_for_status()
    return respuesta.text


FILA_MPC = re.compile(r"^(\d{2} \d{2} \d{2}(?:\.\d+)?)\s+([+-]\d{2} \d{2} \d{2}(?:\.\d+)?)\s+(\d{1,2}\.\d+)?")


def interpretar_mpchecker(html):
    """Normaliza la página HTML de MPChecker a una lista de objetos.

    Cada fila del bloque <pre> lleva la designación en las 25 primeras columnas, seguida de
    la ascensión recta (hh mm ss.s), la declinación (+dd mm ss) y la magnitud V.
    """
    bloque = re.search(r"<pre>(.*?)</pre>", html, re.S | re.I)
    if not bloque:
        if re.search(r"No known minor planets", html, re.I):
            return []
        raise ValueError("MPChecker no devolvió el bloque de resultados")
    objetos = []
    for linea in bloque.group(1).splitlines():
        if len(linea) <= 25:
            continue
        m = FILA_MPC.match(linea[25:])
        if not m:
            continue
        objetos.append({"nombre": re.sub(r"\s+", " ", linea[:25]).strip(),
                        "ra_grados": round(sexagesimal_a_grados(m.group(1), es_ra=True), 6),
                        "dec_grados": round(sexagesimal_a_grados(m.group(2)), 6),
                        "magnitud_v": _magnitud(m.group(3))})
    return objetos


def consultar_mpchecker(ra_grados, dec_grados, mjd):
    return interpretar_mpchecker(_pedir_mpchecker(formulario_mpchecker(ra_grados, dec_grados, mjd)))


# ------------------------------------------------------------------ caché
CONSULTAS = {"mpchecker": consultar_mpchecker, "jpl_sb_ident": consultar_jpl}


def nombre_cache(campo, id_pareja):
    return "%s_%s.json" % (campo, id_pareja)


def consultas_pendientes(fuentes, movimiento):
    """Parejas no estacionarias con la posición de su fuente A y la fecha de la época A.

    """
    por_id = {f["id_fuente"]: f for f in fuentes["fuentes"]}
    clases = {p["id_pareja"]: p["clase"] for p in movimiento["parejas"]}
    mjd_a = fuentes["epocas"]["epoca_a"]["mjd"]
    pendientes = []
    for pareja in fuentes["parejas"]:
        if clases.get(pareja["id_pareja"], "estacionaria") == "estacionaria":
            continue
        a = por_id[pareja["id_fuente_a"]]
        pendientes.append({"id_pareja": pareja["id_pareja"], "ra_grados": a["ra_grados"],
                           "dec_grados": a["dec_grados"], "mjd": mjd_a})
    return pendientes


def consultar_servicios(ra_grados, dec_grados, mjd):
    """Pregunta a los dos servicios. Devuelve {servicio: {"estado", "mensaje", "objetos"}}."""
    respuestas = {}
    for servicio in SERVICIOS:
        try:
            objetos = CONSULTAS[servicio](ra_grados, dec_grados, mjd)
            respuestas[servicio] = {"estado": "ok", "mensaje": None, "objetos": objetos}
        except Exception as error:  # red, HTTP, formato: se anota y se sigue con el otro servicio
            respuestas[servicio] = {"estado": "error", "mensaje": "%s: %s" % (type(error).__name__, error), "objetos": []}
    return respuestas


def consultar_campo(campo, raiz_datos="datos"):
    """Rellena la caché de un campo. Devuelve (archivos nuevos, archivos ya en caché, parejas sin respuesta)."""
    raiz = Path(raiz_datos)
    fuentes = json.loads((raiz / "m3_deteccion" / campo / "fuentes.json").read_text(encoding="utf-8"))
    movimiento = json.loads((raiz / "m4_movimiento" / campo / "movimiento.json").read_text(encoding="utf-8"))
    cache = raiz / "m5_identificacion" / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    nuevos, existentes, fallidos = [], [], []

    def atender(consulta):
        """Consulta una pareja y guarda su respuesta. Devuelve (estado, ruta, fallo)."""
        ruta = cache / nombre_cache(campo, consulta["id_pareja"])
        if ruta.exists():
            return "existente", ruta, None
        respuestas = consultar_servicios(consulta["ra_grados"], consulta["dec_grados"], consulta["mjd"])
        if all(r["estado"] == "error" for r in respuestas.values()):
            return "fallido", None, (consulta["id_pareja"], {s: r["mensaje"] for s, r in respuestas.items()})
        contenido = {
            "_comentario": "Respuesta guardada de los catálogos de cuerpos menores. Generado por m5_identificacion.",
            "campo": campo,
            "id_pareja": consulta["id_pareja"],
            "consulta": {**consulta, "radio_segarc": RADIO_BUSQUEDA_SEGARC,
                         "fecha_consulta_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
            "respuestas": respuestas,
        }
        ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8")
        return "nuevo", ruta, None

    pendientes = consultas_pendientes(fuentes, movimiento)
    # En paralelo: con 42 parejas y los timeouts por servicio, en serie no cabe en
    # los dos minutos de demo (medido: 6 respuestas en 15 minutos).
    with ThreadPoolExecutor(max_workers=CONSULTAS_EN_PARALELO) as pool:
        for estado, ruta, fallo in pool.map(atender, pendientes):
            if estado == "nuevo":
                nuevos.append(ruta)
            elif estado == "existente":
                existentes.append(ruta)
            else:
                fallidos.append(fallo)
    return nuevos, existentes, fallidos


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m5_identificacion.consulta_catalogos <campo>")
    nuevos_, existentes_, fallidos_ = consultar_campo(sys.argv[1])
    print("caché: %d respuestas nuevas, %d ya guardadas, %d parejas sin respuesta" % (len(nuevos_), len(existentes_), len(fallidos_)))
    for id_pareja_, mensajes_ in fallidos_:
        print("  %s sin respuesta: %s" % (id_pareja_, mensajes_))
    sys.exit(1 if fallidos_ else 0)
