# ============================================================================
# ARCHIVO: modulos/m6_huella_espectral/comparacion_plantillas.py
# MODULO: m6_huella_espectral (Lote C)
# ROL: Asigna al espectro medido el tipo de la plantilla más parecida.
# LEE: espectro_medido.json; plantillas.json.
# PRODUCE: datos/m6_huella_espectral/<campo>/tipo_espectral.json (intermedio interno).
# FUNCIONAMIENTO PREVISTO:
#   Recibe de fotometria.py: espectro_medido.json.
#   1. Leer las cuatro curvas de plantillas.json  ->  plantillas remuestreadas
#   2. Escalar cada plantilla por mínimos cuadrados  ->  chi cuadrado reducido por tipo
#   3. Elegir el menor  ->  tipo_espectral.json (con grados de libertad, nº de puntos y avisos)
#   Entrega a escritura_espectros.py: tipo_espectral.json.
# VERIFICACION: Cada objeto recibe un chi cuadrado reducido por plantilla; el tipo es el del
#   menor, o indeterminado si ninguno baja del umbral.
# USO: python -m modulos.m6_huella_espectral.comparacion_plantillas <campo>
# NOTA: El chi cuadrado reducido es chi2 / (N - 1): N puntos y una escala libre. Con menos de
#   dos puntos no se calcula (no hay grados de libertad) y no se inventa. La suma es diagonal:
#   no modela correlaciones entre canales ni errores sistemáticos. El tipo es el de la plantilla
#   más compatible entre las evaluadas, no un diagnóstico. La escala queda libre porque una plantilla normalizada no predice el brillo; solo se
#   compara la forma. Un tipo se acepta si su chi cuadrado reducido baja de UMBRAL_CHI2, su
#   escala es significativa y el flujo medido se separa del cero.
# ============================================================================
"""Compara el espectro medido con las cuatro plantillas y elige el tipo."""
import json
import sys
from pathlib import Path

import numpy as np

RAIZ_MODULO = Path(__file__).resolve().parent
RUTA_PLANTILLAS = RAIZ_MODULO / "plantillas.json"

UMBRAL_CHI2 = 3.0
SIGNIFICANCIA_MINIMA_ESCALA = 3.0
SIGNIFICANCIA_MINIMA_DETECCION = 3.0
LONGITUD_ONDA_MIN, LONGITUD_ONDA_MAX = 0.75, 5.0

COMENTARIO = (
    "Generado por m6_huella_espectral/comparacion_plantillas.py. El tipo es el de la "
    "plantilla que mejor reproduce la forma del espectro medido, no un diagnóstico."
)


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


def cargar_plantillas(ruta=RUTA_PLANTILLAS):
    """Devuelve las cuatro plantillas con su longitud de onda y su flujo como arrays."""
    datos = leer_json(ruta)
    plantillas = []
    for plantilla in datos["plantillas"]:
        onda = np.asarray(plantilla["longitud_onda_micras"], dtype=float)
        flujo = np.asarray(plantilla["flujo_normalizado"], dtype=float)
        if onda.size != flujo.size or onda.size < 2:
            raise ValueError("la plantilla %r no trae una curva válida" % plantilla.get("tipo"))
        if onda.min() > LONGITUD_ONDA_MIN or onda.max() < LONGITUD_ONDA_MAX:
            raise ValueError(
                "la plantilla %r no cubre de %g a %g micras"
                % (plantilla["tipo"], LONGITUD_ONDA_MIN, LONGITUD_ONDA_MAX)
            )
        if np.any(np.diff(onda) <= 0) or np.any(flujo <= 0) or not np.all(np.isfinite(flujo)):
            raise ValueError("la plantilla %r trae ondas desordenadas o flujo no positivo" % plantilla["tipo"])
        plantillas.append(
            {
                "tipo": plantilla["tipo"],
                "etiqueta_publica": plantilla.get("etiqueta_publica", plantilla["tipo"]),
                "onda": onda,
                "flujo": flujo,
                "origen_plantilla": plantilla.get("origen_plantilla", "sintetica"),
                "referencia": plantilla.get("referencia"),
            }
        )
    return plantillas


def _arrays(puntos):
    """Ondas, flujos y errores de una lista de puntos del contrato, como arrays."""
    onda = np.array([p["longitud_onda_micras"] for p in puntos], dtype=float)
    flujo = np.array([p["flujo_mjy"] for p in puntos], dtype=float)
    error = np.array([p["error_mjy"] for p in puntos], dtype=float)
    if not (np.all(np.isfinite(onda)) and np.all(np.isfinite(flujo)) and np.all(error > 0)):
        raise ValueError("punto con longitud de onda, flujo o error no válido")
    return onda, flujo, error


def significancia_deteccion(puntos):
    """Cuántas sigmas se separa el flujo medio del cero: un espectro de ruido no la supera."""
    if not puntos:
        return 0.0
    _, flujo, error = _arrays(puntos)
    pesos = 1.0 / error ** 2
    media = float(np.sum(pesos * flujo) / np.sum(pesos))
    sigma_media = float(1.0 / np.sqrt(np.sum(pesos)))
    return abs(media) / sigma_media if sigma_media > 0 else 0.0


def ajustar_plantilla(puntos, plantilla):
    """Ajuste por mínimos cuadrados de una plantilla a los puntos. None si no se solapan."""
    onda, flujo, error = _arrays(puntos)
    if onda.min() < plantilla["onda"].min() or onda.max() > plantilla["onda"].max():
        return None
    modelo = np.interp(onda, plantilla["onda"], plantilla["flujo"])
    pesos = 1.0 / error ** 2
    denominador = float(np.sum(pesos * modelo ** 2))
    if denominador <= 0:
        return None
    escala = float(np.sum(pesos * modelo * flujo) / denominador)
    error_escala = float(1.0 / np.sqrt(denominador))
    grados_libertad = len(puntos) - 1  # N puntos menos la escala ajustada
    if grados_libertad < 1:
        return None
    chi2 = float(np.sum(((flujo - escala * modelo) / error) ** 2))
    return {
        "tipo": plantilla["tipo"],
        "chi2_reducido": round(chi2 / grados_libertad, 4),
        "grados_libertad": grados_libertad,
        "n_puntos": len(puntos),
        "escala": escala,
        "significancia_escala": escala / error_escala if error_escala > 0 else 0.0,
        "origen_plantilla": plantilla.get("origen_plantilla", "sintetica"),
        "referencia_plantilla": plantilla.get("referencia"),
    }


SNR_BAJA = 5.0
COBERTURA_MINIMA = 0.8  # fracción de 0,75-5,0 micras
TIPOS_CON_LUZ_REFLEJADA = ("asteroide_rocoso", "asteroide_oscuro", "cometa")


def advertencias_de(puntos, agrupacion, ajustes, tipo):
    """Códigos de advertencia del contrato espectros.schema.json para este espectro."""
    avisos = []
    if any(a["origen_plantilla"] == "sintetica" for a in ajustes):
        avisos.append("plantillas_sinteticas")
    if puntos:
        onda, flujo, error = _arrays(puntos)
        if float(np.median(np.abs(flujo) / error)) < SNR_BAJA:
            avisos.append("senal_ruido_baja")
        if float(onda.max() - onda.min()) < COBERTURA_MINIMA * (LONGITUD_ONDA_MAX - LONGITUD_ONDA_MIN):
            avisos.append("cobertura_espectral_parcial")
    if agrupacion == "detector":
        avisos.append("agrupado_por_detector")
    if tipo in TIPOS_CON_LUZ_REFLEJADA:
        avisos.append("luz_reflejada_y_termica")
    return avisos


def _ajuste_publico(ajuste):
    """Campos del contrato. La escala solo se publica si es positiva (una escala negativa no dibuja nada)."""
    publico = {
        "tipo": ajuste["tipo"],
        "chi2_reducido": ajuste["chi2_reducido"],
        "grados_libertad": ajuste["grados_libertad"],
        "n_puntos": ajuste["n_puntos"],
        "origen_plantilla": ajuste["origen_plantilla"],
        "referencia_plantilla": ajuste["referencia_plantilla"],
    }
    if ajuste["escala"] > 0:
        publico["escala"] = round(ajuste["escala"], 6)
    return publico


def comparar(puntos, plantillas=None, agrupacion="banda"):
    """Ajusta las cuatro plantillas y devuelve el tipo más compatible con sus chi cuadrados y avisos."""
    plantillas = cargar_plantillas() if plantillas is None else plantillas
    if not puntos:
        return {"tipo": "indeterminado", "ajustes": [], "advertencias": advertencias_de([], agrupacion, [], "indeterminado")}

    ajustes = []
    for plantilla in plantillas:
        ajuste = ajustar_plantilla(puntos, plantilla)
        if ajuste is not None:
            ajustes.append(ajuste)

    validos = [
        ajuste
        for ajuste in ajustes
        if ajuste["chi2_reducido"] <= UMBRAL_CHI2
        and ajuste["significancia_escala"] >= SIGNIFICANCIA_MINIMA_ESCALA
    ]
    tipo = "indeterminado"
    if validos and significancia_deteccion(puntos) >= SIGNIFICANCIA_MINIMA_DETECCION:
        tipo = min(validos, key=lambda ajuste: ajuste["chi2_reducido"])["tipo"]

    return {
        "tipo": tipo,
        "ajustes": [_ajuste_publico(ajuste) for ajuste in ajustes],
        "advertencias": advertencias_de(puntos, agrupacion, ajustes, tipo),
    }


def clasificar_campo(campo, raiz_datos="datos"):
    """Lee espectro_medido.json y escribe tipo_espectral.json con el tipo de cada pareja."""
    directorio = Path(raiz_datos) / "m6_huella_espectral" / campo
    medido = leer_json(directorio / "espectro_medido.json")
    plantillas = cargar_plantillas()
    espectros = []
    for espectro in medido["espectros"]:
        resultado = comparar(espectro["puntos"], plantillas, espectro.get("agrupacion", "banda"))
        espectros.append(
            {
                "id_pareja": espectro["id_pareja"],
                "tipo": resultado["tipo"],
                "ajustes_plantilla": resultado["ajustes"],
                "advertencias": resultado["advertencias"],
            }
        )
    return escribir_json(
        directorio / "tipo_espectral.json",
        {"_comentario": COMENTARIO, "campo": campo, "espectros": espectros},
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m6_huella_espectral.comparacion_plantillas <campo>")
    ruta_escrita = clasificar_campo(sys.argv[1])
    for espectro in leer_json(ruta_escrita)["espectros"]:
        print("%s: tipo %s" % (espectro["id_pareja"], espectro["tipo"]))
    print(ruta_escrita)
