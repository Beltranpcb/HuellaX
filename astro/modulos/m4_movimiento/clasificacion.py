# ============================================================================
# ARCHIVO: modulos/m4_movimiento/clasificacion.py
# MODULO: m4_movimiento (Lote C)
# ROL: Asigna a cada pareja su clase de movimiento.
# LEE: cinematica.json; significancia.json.
# PRODUCE: datos/m4_movimiento/<campo>/movimiento.json.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de incertidumbre.py: significancia.json.
#   1. Leer la velocidad de cinematica.json  ->  medidas por pareja
#   2. Aplicar los umbrales de significancia  ->  clase por pareja
#   3. Escribir el resultado  ->  movimiento.json
#   Entrega a m5, m6, m7: movimiento.json.
# VERIFICACION: Significancia menor que 2 da estacionaria, entre 2 y 5 da no_concluyente, 5 o más da candidata; el archivo valida contra su esquema.
# USO: python -m modulos.m4_movimiento.clasificacion <campo>
# NOTA: Los umbrales son valores iniciales. Cambiarlos exige actualizar contratos/movimiento.schema.json
#       (la descripción del campo clase) en un PR propio.
# ============================================================================
import json
import sys
from pathlib import Path

UMBRAL_NO_CONCLUYENTE = 2.0  # sigmas: por debajo, estacionaria
UMBRAL_CANDIDATA = 5.0       # sigmas: a partir de aquí, candidata


def clase_de(significancia):
    if significancia < UMBRAL_NO_CONCLUYENTE:
        return "estacionaria"
    if significancia < UMBRAL_CANDIDATA:
        return "no_concluyente"
    return "candidata"


def clasificar(cinematica, significancia):
    """Une cinematica.json con significancia.json y asigna la clase. Devuelve las parejas de movimiento.json."""
    por_id = {s["id_pareja"]: s for s in significancia["parejas"]}
    parejas = []
    for c in cinematica["parejas"]:
        s = por_id[c["id_pareja"]]
        parejas.append({"id_pareja": c["id_pareja"],
                        "separacion_segarc": c["separacion_segarc"],
                        "horas_transcurridas": c["horas_transcurridas"],
                        "velocidad_segarc_por_hora": c["velocidad_segarc_por_hora"],
                        "incertidumbre_velocidad": s["incertidumbre_velocidad"],
                        "significancia": s["significancia"],
                        "clase": clase_de(s["significancia"])})
    return parejas


def construir_movimiento_json(campo, cinematica, significancia):
    return {
        "_comentario": "Generado por m4_movimiento. Clase por significancia: <2 estacionaria, 2-5 no_concluyente, >=5 candidata.",
        "version_contrato": "1",
        "campo": campo,
        "parejas": clasificar(cinematica, significancia),
    }


def clasificar_campo(campo, raiz_datos="datos"):
    """Lee cinematica.json con significancia.json y escribe movimiento.json. Devuelve su ruta."""
    directorio = Path(raiz_datos) / "m4_movimiento" / campo
    cinematica = json.loads((directorio / "cinematica.json").read_text(encoding="utf-8"))
    significancia = json.loads((directorio / "significancia.json").read_text(encoding="utf-8"))
    ruta = directorio / "movimiento.json"
    ruta.write_text(json.dumps(construir_movimiento_json(campo, cinematica, significancia), ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return ruta


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m4_movimiento.clasificacion <campo>")
    ruta_escrita = clasificar_campo(sys.argv[1])
    parejas_ = json.loads(ruta_escrita.read_text(encoding="utf-8"))["parejas"]
    recuento = {k: sum(p["clase"] == k for p in parejas_) for k in ("candidata", "no_concluyente", "estacionaria")}
    print("%s: %s" % (ruta_escrita, recuento))
