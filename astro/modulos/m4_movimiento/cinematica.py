# ============================================================================
# ARCHIVO: modulos/m4_movimiento/cinematica.py
# MODULO: m4_movimiento (Lote C)
# ROL: Calcula la velocidad angular de cada pareja propuesta.
# LEE: fuentes.json.
# PRODUCE: datos/m4_movimiento/<campo>/cinematica.json (intermedio interno).
# FUNCIONAMIENTO PREVISTO:
#   Recibe de m3_deteccion: fuentes.json.
#   1. Leer posiciones, fechas de cada pareja  ->  coordenadas, MJD
#   2. Calcular la separación angular sobre la esfera  ->  separación en segundos de arco
#   3. Dividir por las horas transcurridas  ->  cinematica.json
#   Entrega a incertidumbre.py, clasificacion.py: cinematica.json.
# VERIFICACION: La separación se mide sobre la esfera; la velocidad es separación entre horas transcurridas.
# USO: python -m modulos.m4_movimiento.cinematica <campo>
# ============================================================================
import json
import math
import sys
from pathlib import Path


def separacion_segarc(ra1, dec1, ra2, dec2):
    """Distancia angular sobre la esfera (fórmula del haversine), en segundos de arco."""
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    h = math.sin((d2 - d1) / 2) ** 2 + math.cos(d1) * math.cos(d2) * math.sin((r2 - r1) / 2) ** 2
    return math.degrees(2 * math.asin(min(1.0, math.sqrt(h)))) * 3600


def horas_entre_epocas(fuentes):
    horas = (fuentes["epocas"]["epoca_b"]["mjd"] - fuentes["epocas"]["epoca_a"]["mjd"]) * 24.0
    if horas <= 0:
        raise ValueError("la época B debe ser posterior a la época A (horas transcurridas: %s)" % horas)
    return horas


def calcular_cinematica(fuentes):
    """Separación con velocidad de cada pareja de fuentes.json. Devuelve la lista de parejas."""
    por_id = {f["id_fuente"]: f for f in fuentes["fuentes"]}
    horas = horas_entre_epocas(fuentes)
    parejas = []
    for p in fuentes["parejas"]:
        a, b = por_id[p["id_fuente_a"]], por_id[p["id_fuente_b"]]
        sep = separacion_segarc(a["ra_grados"], a["dec_grados"], b["ra_grados"], b["dec_grados"])
        parejas.append({"id_pareja": p["id_pareja"], "separacion_segarc": round(sep, 3),
                        "horas_transcurridas": round(horas, 6), "velocidad_segarc_por_hora": round(sep / horas, 4)})
    return parejas


def calcular_campo(campo, raiz_datos="datos"):
    """Lee fuentes.json (m3) y escribe cinematica.json. Devuelve su ruta."""
    raiz = Path(raiz_datos)
    fuentes = json.loads((raiz / "m3_deteccion" / campo / "fuentes.json").read_text(encoding="utf-8"))
    directorio = raiz / "m4_movimiento" / campo
    directorio.mkdir(parents=True, exist_ok=True)
    ruta = directorio / "cinematica.json"
    ruta.write_text(json.dumps({"campo": campo, "parejas": calcular_cinematica(fuentes)}, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return ruta


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m4_movimiento.cinematica <campo>")
    ruta_escrita = calcular_campo(sys.argv[1])
    for pareja_ in json.loads(ruta_escrita.read_text(encoding="utf-8"))["parejas"]:
        print("%s: %.3f\" en %.2f h -> %.4f \"/h" % (pareja_["id_pareja"], pareja_["separacion_segarc"],
                                                   pareja_["horas_transcurridas"], pareja_["velocidad_segarc_por_hora"]))
    print(ruta_escrita)
