# ============================================================================
# ARCHIVO: modulos/m6_huella_espectral/trayectoria.py
# MODULO: m6_huella_espectral (Lote C)
# ROL: Predice dónde está el objeto en el instante de cada exposición.
# LEE: seleccion.json; fuentes.json; movimiento.json.
# PRODUCE: datos/m6_huella_espectral/<campo>/posiciones_previstas.json (intermedio interno).
# FUNCIONAMIENTO PREVISTO:
#   Recibe de m1, m3, m4: seleccion.json, fuentes.json, movimiento.json.
#   1. Leer las posiciones A, B de cada pareja candidata  ->  dos puntos con fecha
#   2. Interpolar linealmente en el tiempo  ->  posición por exposición
#   3. Descartar las exposiciones sin el objeto dentro del recorte  ->  posiciones_previstas.json
#   Entrega a fotometria.py: posiciones_previstas.json.
# VERIFICACION: La posición prevista en la fecha de la época A coincide con la observada en A, igual que en B.
# USO: python -m modulos.m6_huella_espectral.trayectoria <campo>
# NOTA: El recorte de cada exposición es el cuadrado de semilado radio_grados alrededor del centro
#       del campo (seleccion.json), así que no hace falta abrir ningún FITS para saber si el objeto
#       cae dentro. La extrapolación se limita a un intervalo A-B más allá de cada extremo: la
#       plantilla, a seis meses, queda siempre fuera.
# ============================================================================
import json
import math
import sys
from pathlib import Path

MARGEN_EXTRAPOLACION = 1.0  # fracción del intervalo A-B admitida antes de A y después de B


def diferencia_ra(ra_destino, ra_origen):
    """ra_destino - ra_origen llevada a (-180, 180], para no saltar en el meridiano 0/360."""
    return (ra_destino - ra_origen + 180.0) % 360.0 - 180.0


def posicion_en(mjd, a, b, mjd_a, mjd_b):
    """Posición interpolada (o extrapolada) linealmente entre A y B en la fecha pedida."""
    f = (mjd - mjd_a) / (mjd_b - mjd_a)
    ra = (a["ra_grados"] + diferencia_ra(b["ra_grados"], a["ra_grados"]) * f) % 360.0
    dec = a["dec_grados"] + (b["dec_grados"] - a["dec_grados"]) * f
    return ra, dec, f


def dentro_del_recorte(ra, dec, centro, radio_grados):
    dx = abs(diferencia_ra(ra, centro["ra_grados"])) * math.cos(math.radians(centro["dec_grados"]))
    return dx <= radio_grados and abs(dec - centro["dec_grados"]) <= radio_grados


def prever(seleccion, fuentes, movimiento):
    """Lista de objetos (parejas candidatas) con la posición prevista en cada exposición útil."""
    por_id = {f["id_fuente"]: f for f in fuentes["fuentes"]}
    clases = {p["id_pareja"]: p["clase"] for p in movimiento["parejas"]}
    mjd_a, mjd_b = fuentes["epocas"]["epoca_a"]["mjd"], fuentes["epocas"]["epoca_b"]["mjd"]
    if mjd_b <= mjd_a:
        raise ValueError("la época B debe ser posterior a la época A")
    objetos = []
    for pareja in fuentes["parejas"]:
        if clases.get(pareja["id_pareja"]) != "candidata":
            continue
        a, b = por_id[pareja["id_fuente_a"]], por_id[pareja["id_fuente_b"]]
        exposiciones, descartadas = [], []
        for e in seleccion["exposiciones"]:
            ra, dec, f = posicion_en(e["mjd"], a, b, mjd_a, mjd_b)
            if f < -MARGEN_EXTRAPOLACION or f > 1.0 + MARGEN_EXTRAPOLACION:
                descartadas.append({"id_exposicion": e["id_exposicion"], "motivo": "fuera_del_intervalo"})
            elif not dentro_del_recorte(ra, dec, seleccion["centro"], seleccion["radio_grados"]):
                descartadas.append({"id_exposicion": e["id_exposicion"], "motivo": "fuera_del_recorte"})
            else:
                exposiciones.append({"id_exposicion": e["id_exposicion"], "archivo_recorte": e["archivo_recorte"],
                                     "mjd": e["mjd"], "detector": e["detector"],
                                     "ra_grados": round(ra, 7), "dec_grados": round(dec, 7)})
        exposiciones.sort(key=lambda x: x["mjd"])
        objetos.append({"id_pareja": pareja["id_pareja"], "id_fuente_a": a["id_fuente"], "id_fuente_b": b["id_fuente"],
                        "exposiciones": exposiciones, "descartadas": descartadas})
    return objetos


def prever_campo(campo, raiz_datos="datos"):
    """Lee seleccion.json (m1), fuentes.json (m3), movimiento.json (m4); escribe posiciones_previstas.json."""
    raiz = Path(raiz_datos)
    seleccion = json.loads((raiz / "m1_adquisicion" / campo / "seleccion.json").read_text(encoding="utf-8"))
    fuentes = json.loads((raiz / "m3_deteccion" / campo / "fuentes.json").read_text(encoding="utf-8"))
    movimiento = json.loads((raiz / "m4_movimiento" / campo / "movimiento.json").read_text(encoding="utf-8"))
    directorio = raiz / "m6_huella_espectral" / campo
    directorio.mkdir(parents=True, exist_ok=True)
    ruta = directorio / "posiciones_previstas.json"
    ruta.write_text(json.dumps({"campo": campo, "objetos": prever(seleccion, fuentes, movimiento)}, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return ruta


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m6_huella_espectral.trayectoria <campo>")
    ruta_escrita = prever_campo(sys.argv[1])
    for objeto_ in json.loads(ruta_escrita.read_text(encoding="utf-8"))["objetos"]:
        print("%s: %d exposiciones útiles, %d descartadas" % (objeto_["id_pareja"], len(objeto_["exposiciones"]), len(objeto_["descartadas"])))
    print(ruta_escrita)
