# ============================================================================
# ARCHIVO: modulos/m4_movimiento/incertidumbre.py
# MODULO: m4_movimiento (Lote C)
# ROL: Propaga la incertidumbre de posición hasta la velocidad.
# LEE: fuentes.json; cinematica.json.
# PRODUCE: datos/m4_movimiento/<campo>/significancia.json (intermedio interno).
# FUNCIONAMIENTO PREVISTO:
#   Recibe de cinematica.py: cinematica.json.
#   1. Leer las incertidumbres de posición de fuentes.json  ->  sigma de A, sigma de B
#   2. Combinar en cuadratura  ->  sigma de la separación
#   3. Dividir la separación entre su sigma  ->  significancia.json
#   Entrega a clasificacion.py: significancia.json.
# VERIFICACION: La incertidumbre de la separación es la suma en cuadratura de las dos incertidumbres de posición.
# USO: python -m modulos.m4_movimiento.incertidumbre <campo>
# ============================================================================
import json
import math
import sys
from pathlib import Path


def propagar(fuentes, cinematica):
    """Incertidumbre de la separación, de la velocidad y significancia de cada pareja."""
    por_id = {f["id_fuente"]: f for f in fuentes["fuentes"]}
    parejas_fuentes = {p["id_pareja"]: p for p in fuentes["parejas"]}
    resultado = []
    for c in cinematica["parejas"]:
        p = parejas_fuentes[c["id_pareja"]]
        sigma_a = por_id[p["id_fuente_a"]]["incertidumbre_posicion_segarc"]
        sigma_b = por_id[p["id_fuente_b"]]["incertidumbre_posicion_segarc"]
        sigma_sep = math.hypot(sigma_a, sigma_b)
        if sigma_sep <= 0:
            raise ValueError("incertidumbre de posición nula en la pareja %s" % c["id_pareja"])
        resultado.append({"id_pareja": c["id_pareja"],
                          "incertidumbre_separacion_segarc": round(sigma_sep, 4),
                          "incertidumbre_velocidad": round(sigma_sep / c["horas_transcurridas"], 4),
                          "significancia": round(c["separacion_segarc"] / sigma_sep, 2)})
    return resultado


def propagar_campo(campo, raiz_datos="datos"):
    """Lee fuentes.json (m3) con cinematica.json (m4) y escribe significancia.json. Devuelve su ruta."""
    raiz = Path(raiz_datos)
    fuentes = json.loads((raiz / "m3_deteccion" / campo / "fuentes.json").read_text(encoding="utf-8"))
    directorio = raiz / "m4_movimiento" / campo
    cinematica = json.loads((directorio / "cinematica.json").read_text(encoding="utf-8"))
    ruta = directorio / "significancia.json"
    ruta.write_text(json.dumps({"campo": campo, "parejas": propagar(fuentes, cinematica)}, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return ruta


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m4_movimiento.incertidumbre <campo>")
    ruta_escrita = propagar_campo(sys.argv[1])
    for pareja_ in json.loads(ruta_escrita.read_text(encoding="utf-8"))["parejas"]:
        print("%s: sigma %.3f\" -> %.2f sigmas" % (pareja_["id_pareja"], pareja_["incertidumbre_separacion_segarc"], pareja_["significancia"]))
    print(ruta_escrita)
