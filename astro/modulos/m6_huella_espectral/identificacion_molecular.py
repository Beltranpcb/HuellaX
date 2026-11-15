# ============================================================================
# ARCHIVO: modulos/m6_huella_espectral/identificacion_molecular.py
# MODULO: m6_huella_espectral (Lote C)
# ROL: Evalúa, banda por banda, si el espectro medido muestra rasgos compatibles
#      con H2O, CH4, CO2, CO o NH3, y con qué nivel de evidencia.
# LEE: espectro_medido.json; tipo_espectral.json (opcional, para el sentido esperado).
# PRODUCE: datos/m6_huella_espectral/<campo>/composicion.json (intermedio interno).
# FUNCIONAMIENTO PREVISTO:
#   Recibe de fotometria.py, comparacion_plantillas.py: espectro_medido.json, tipo_espectral.json.
#   1. Control de calidad: puntos válidos, agrupación, cobertura  ->  puntos utilizables
#   2. Continuo local: polinomio de grado 2 en los dos flancos de cada banda  ->  C(lambda) y su varianza
#   3. Rasgo por banda: media pesada de F - C dentro de la banda  ->  significancia en sigmas
#   4. Robustez: se repite con una recta en flancos más estrechos  ->  el rasgo debe sobrevivir
#   5. Estado con reglas fijas (ver UMBRALES)  ->  composicion.json
#   Entrega a escritura_espectros.py: composicion.json.
# VERIFICACION: Un espectro sintético con una banda de CO2 de 8 sigmas sale «detectada»; el ruido
#   puro sale «sin_rasgo»; un espectro promediado por detector sale «datos_insuficientes».
# USO: python -m modulos.m6_huella_espectral.identificacion_molecular <campo>
# NOTA: Las ventanas de banda son orientativas (con margen para desplazamientos por temperatura y
#   entorno) y salen de las referencias citadas en REFERENCIAS. La resolución es la nominal de
#   SPHEREx por detector. No se interpola para ganar resolución ni se da ningún porcentaje de
#   confianza: la métrica es la significancia del rasgo en sigmas, con sus grados de libertad.
#   «detectada» exige, a la vez: |S| >= 5 con los dos continuos, al menos 3 puntos en la banda,
#   banda resuelta (>= 2 elementos de resolución), sentido esperado para el tipo de objeto y
#   ninguna alternativa física plausible para ese tipo. Si falla algo, se queda en «candidata».
# ============================================================================
"""Evalúa rasgos moleculares en el espectro medido, sin forzar detecciones."""
import json
import sys
from pathlib import Path

import numpy as np

VERSION_METODO = "1.0"
CONTINUO = ("local_por_banda: polinomio de grado 2 con los 6 puntos libres más cercanos a cada lado "
            "(robustez: recta con 3 puntos a cada lado)")
LONGITUD_ONDA_MIN, LONGITUD_ONDA_MAX = 0.75, 5.0
MINIMO_PUNTOS_ESPECTRO = 8
MARGEN_CONTINUO = 0.05          # micras que se apartan de cada banda al ajustar el continuo
DISTANCIA_MAXIMA_FLANCO = 0.8   # micras: más lejos el continuo ya no describe la banda
# Continuo local a ambos lados de cada banda: (puntos por flanco, grado del polinomio).
CONTINUO_PRINCIPAL = (6, 2)     # sigue la curvatura de un continuo térmico o de luz reflejada
CONTINUO_ROBUSTEZ = (3, 1)      # alternativa más simple y más local: el rasgo debe sobrevivir a las dos
UMBRALES = {"compatible": 2.0, "candidata": 3.0, "detectada": 5.0}  # |S| en sigmas
MINIMO_PUNTOS_DETECCION = 3
MINIMO_ELEMENTOS_RESOLUCION = 2.0

# Resolución nominal de SPHEREx por detector: (lambda mínima, lambda máxima, R).
RESOLUCION_SPHEREX = ((0.75, 1.10, 41), (1.10, 1.63, 41), (1.63, 2.42, 41),
                      (2.42, 3.83, 35), (3.83, 4.42, 110), (4.42, 5.00, 130))
REFERENCIA_RESOLUCION = "Crill et al. 2020, Proc. SPIE 11443 (SPHEREx), resolución nominal por detector"

REFERENCIAS = {
    "hielos": "Gerakines et al. 1995, A&A 296, 810; Hudgins et al. 1993, ApJS 86, 713 (bandas de hielos)",
    "gas": "NIST Chemistry WebBook, espectros IR en fase gaseosa",
}

# Una ventana por molécula, dentro del rango de SPHEREx. Posiciones orientativas.
BANDAS = (
    {"molecula": "agua", "formula": "H2O", "banda": (2.85, 3.15), "referencia": REFERENCIAS["hielos"]},
    {"molecula": "metano", "formula": "CH4", "banda": (3.20, 3.45), "referencia": REFERENCIAS["gas"]},
    {"molecula": "dioxido_de_carbono", "formula": "CO2", "banda": (4.20, 4.33), "referencia": REFERENCIAS["hielos"]},
    {"molecula": "monoxido_de_carbono", "formula": "CO", "banda": (4.55, 4.75), "referencia": REFERENCIAS["hielos"]},
    {"molecula": "amoniaco", "formula": "NH3", "banda": (2.17, 2.27), "referencia": REFERENCIAS["hielos"]},
)

ASTEROIDES = ("asteroide_rocoso", "asteroide_oscuro")

# Otras explicaciones físicas del mismo rasgo según el tipo de objeto (m6, por plantillas).
ALTERNATIVAS = {
    "agua": {ASTEROIDES: ["minerales_hidratados_OH"], ("indeterminado", None): ["minerales_hidratados_OH"]},
    "metano": {("cometa", "indeterminado", None): ["hidrocarburos_con_enlace_CH"]},
    "amoniaco": {("enana_marron", "indeterminado", None, *ASTEROIDES): ["metano_2_3_micras"]},
}

# Sentido esperado del rasgo: en cometas el gas emite por fluorescencia; en el resto, absorbe.
def sentido_esperado(tipo, molecula):
    if tipo in (None, "indeterminado"):
        return None
    if tipo == "cometa" and molecula in ("agua", "dioxido_de_carbono", "monoxido_de_carbono"):
        return "emision"
    return "absorcion"


def alternativas_de(molecula, tipo):
    for tipos, lista in ALTERNATIVAS.get(molecula, {}).items():
        if tipo in tipos:
            return list(lista)
    return []


def leer_json(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)


def escribir_json(ruta, contenido):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(contenido, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")
    return ruta


def resolucion_en(lam):
    for bajo, alto, r in RESOLUCION_SPHEREX:
        if bajo <= lam <= alto:
            return r
    return None


def arrays_validos(puntos):
    onda, flujo, error = [], [], []
    for p in puntos:
        l, f, e = p.get("longitud_onda_micras"), p.get("flujo_mjy"), p.get("error_mjy")
        if all(isinstance(v, (int, float)) and np.isfinite(v) for v in (l, f, e)) and e > 0 \
                and LONGITUD_ONDA_MIN <= l <= LONGITUD_ONDA_MAX:
            onda.append(l), flujo.append(f), error.append(e)
    orden = np.argsort(onda)
    return np.asarray(onda)[orden], np.asarray(flujo)[orden], np.asarray(error)[orden]


def continuo_local(onda, flujo, error, banda, puntos_por_flanco, grado):
    """Polinomio pesado en los dos flancos de la banda, sin tocar ninguna banda.

    Cada flanco son los `puntos_por_flanco` puntos más cercanos a ese lado que no caen en
    ninguna banda (con su margen), hasta DISTANCIA_MAXIMA_FLANCO: si una banda vecina tapa
    el flanco, se salta y se sigue más lejos. Devuelve (función valor, función varianza) o
    None si falta apoyo a algún lado: sin continuo a ambos lados no se distingue un rasgo
    de una pendiente.
    """
    bajo, alto = banda
    libre = np.ones(onda.shape, dtype=bool)
    for otra in BANDAS:
        o_bajo, o_alto = otra["banda"]
        libre &= ~((onda >= o_bajo - MARGEN_CONTINUO) & (onda <= o_alto + MARGEN_CONTINUO))
    izquierda = np.flatnonzero(libre & (onda < bajo) & (onda >= bajo - DISTANCIA_MAXIMA_FLANCO))[::-1][:puntos_por_flanco]
    derecha = np.flatnonzero(libre & (onda > alto) & (onda <= alto + DISTANCIA_MAXIMA_FLANCO))[:puntos_por_flanco]
    if izquierda.size < puntos_por_flanco or derecha.size < puntos_por_flanco:
        return None
    centro = (bajo + alto) / 2  # se ajusta en lambda - centro: mejor condicionado
    mascara = np.concatenate([izquierda, derecha])
    coef, cov = np.polyfit(onda[mascara] - centro, flujo[mascara], grado, w=1.0 / error[mascara], cov="unscaled")

    def valor(x):
        return np.polyval(coef, np.asarray(x) - centro)

    def varianza(x):
        jac = np.vander(np.atleast_1d(x) - centro, grado + 1)
        return np.einsum("ij,jk,ik->i", jac, cov, jac)

    return valor, varianza


def significancia(onda, flujo, error, continuo, banda):
    """(S, n_puntos, profundidad relativa) del rasgo en la banda; None si hay menos de 2 puntos."""
    bajo, alto = banda
    dentro = (onda >= bajo) & (onda <= alto)
    n = int(dentro.sum())
    if n < 2:
        return None
    valor, varianza = continuo
    c = valor(onda[dentro])
    residuo = flujo[dentro] - c
    pesos = 1.0 / error[dentro] ** 2
    media = float(np.sum(pesos * residuo) / np.sum(pesos))
    # El error del continuo está correlacionado entre los puntos de la banda: se suma entero, sin dividir por n.
    sigma = float(np.sqrt(1.0 / np.sum(pesos) + np.mean(varianza(onda[dentro]))))
    nivel = float(np.mean(c))
    return media / sigma, n, (media / nivel if nivel > 0 else None)


def estado_por_umbral(s):
    a = abs(s)
    if a >= UMBRALES["detectada"]:
        return "detectada"
    if a >= UMBRALES["candidata"]:
        return "candidata"
    if a >= UMBRALES["compatible"]:
        return "compatible"
    return "sin_rasgo"


def coma(x, d=1):
    return ("%.*f" % (d, x)).replace(".", ",")


def evaluar_banda(b, onda, flujo, error, tipo):
    """Resultado de una molécula con su estado, métrica y explicación."""
    bajo, alto = b["banda"]
    centro = (bajo + alto) / 2
    r = resolucion_en(centro)
    base = {"molecula": b["molecula"], "formula": b["formula"], "banda_micras": [bajo, alto],
            "referencia": b["referencia"], "resolucion_espectral": r, "ambigua_con": [], "advertencias": []}
    principal = continuo_local(onda, flujo, error, b["banda"], *CONTINUO_PRINCIPAL)
    robustez = continuo_local(onda, flujo, error, b["banda"], *CONTINUO_ROBUSTEZ)
    if principal is None:
        return {**base, "estado": "datos_insuficientes", "rasgo": None, "metrica": None,
                "explicacion": "No hay continuo medido a los dos lados de la banda: no se distingue un rasgo de una pendiente."}
    medida = significancia(onda, flujo, error, principal, b["banda"])
    if medida is None:
        n = int(((onda >= bajo) & (onda <= alto)).sum())
        return {**base, "estado": "datos_insuficientes", "rasgo": None, "metrica": None,
                "explicacion": "Solo %d punto%s dentro de la banda: no se puede medir un rasgo." % (n, "" if n == 1 else "s")}
    s2, n, profundidad = medida
    medida_robustez = significancia(onda, flujo, error, robustez, b["banda"]) if robustez else None
    s1 = medida_robustez[0] if medida_robustez else None
    rasgo = "emision" if s2 > 0 else "absorcion"
    estado = estado_por_umbral(s2)
    metrica = {"nombre": "significancia_sigma", "valor": round(float(s2), 2), "incertidumbre": None, "grados_libertad": 1}
    if estado == "sin_rasgo":
        return {**base, "estado": "sin_rasgo", "rasgo": None, "metrica": metrica,
                "explicacion": "Banda cubierta con %d puntos y sin rasgo por encima de %s sigmas (S = %s): "
                               "no confirma ni descarta la molécula." % (n, coma(UMBRALES["compatible"], 0), coma(s2, 2))}

    motivos = []
    alternativas = alternativas_de(b["molecula"], tipo)
    esperado = sentido_esperado(tipo, b["molecula"])
    elementos = (alto - bajo) / (centro / r) if r else 0.0
    if elementos < MINIMO_ELEMENTOS_RESOLUCION:
        base["advertencias"].append("resolucion_incompatible")
    if tipo in ASTEROIDES + ("cometa",) and centro > 3.5:
        base["advertencias"].append("luz_reflejada_y_termica")
    if estado == "detectada":
        if s1 is None or abs(s1) < UMBRALES["detectada"] or np.sign(s1) != np.sign(s2):
            motivos.append("no sobrevive a un continuo recto más local (S = %s)" % ("—" if s1 is None else coma(s1, 2)))
        if n < MINIMO_PUNTOS_DETECCION:
            motivos.append("solo %d puntos en la banda" % n)
        if elementos < MINIMO_ELEMENTOS_RESOLUCION:
            motivos.append("la banda ocupa %s elementos de resolución (R = %d)" % (coma(elementos, 1), r))
        if esperado is None:
            motivos.append("el tipo del objeto es indeterminado: no hay sentido esperado")
        elif esperado != rasgo:
            motivos.append("se esperaba %s y se mide %s" % (esperado, rasgo))
        if alternativas:
            motivos.append("otra explicación plausible: %s" % ", ".join(alternativas))
        if motivos:
            estado = "candidata"
    if estado in ("candidata", "compatible"):
        base["ambigua_con"] = alternativas
    texto = "%s en la banda con S = %s sigmas en %d puntos" % ("Emisión" if rasgo == "emision" else "Absorción", coma(s2, 2), n)
    if profundidad is not None:
        texto += " (%s %% del continuo)" % coma(100 * abs(profundidad), 1)
    if estado == "detectada":
        texto += "; supera los criterios: robusto al continuo, banda resuelta, sentido esperado y sin alternativas."
    elif motivos:
        texto += "; no llega a detectada porque " + "; ".join(motivos) + "."
    else:
        texto += "; por debajo de %s sigmas no se asocia a una banda concreta." % coma(UMBRALES["detectada"], 0)
    return {**base, "estado": estado, "rasgo": rasgo, "metrica": metrica, "explicacion": texto}


def analizar(puntos, agrupacion="banda", tipo=None):
    """Composición de un espectro: un resultado por molécula, nunca vacío."""
    onda, flujo, error = arrays_validos(puntos)
    comun = {"version_metodo": VERSION_METODO, "continuo": CONTINUO, "resolucion_espectral": None,
             "origen_referencias": "bibliografia"}
    motivo = None
    if agrupacion == "detector":
        motivo = ("El espectro está promediado por detector (6 puntos anchos): no resuelve bandas de 0,1-0,3 µm.",
                  ["agrupado_por_detector"])
    elif onda.size < MINIMO_PUNTOS_ESPECTRO:
        motivo = ("Solo %d puntos válidos en el espectro (mínimo %d)." % (onda.size, MINIMO_PUNTOS_ESPECTRO),
                  ["cobertura_espectral_parcial"])
    if motivo:
        return {**comun, "moleculas": [
            {"molecula": b["molecula"], "formula": b["formula"], "banda_micras": list(b["banda"]),
             "estado": "datos_insuficientes", "rasgo": None, "metrica": None, "explicacion": motivo[0],
             "ambigua_con": [], "referencia": b["referencia"], "resolucion_espectral": resolucion_en(sum(b["banda"]) / 2),
             "advertencias": list(motivo[1])} for b in BANDAS]}
    return {**comun, "moleculas": [evaluar_banda(b, onda, flujo, error, tipo) for b in BANDAS]}


def analizar_campo(campo, raiz_datos="datos"):
    """Lee espectro_medido.json (y tipo_espectral.json si existe) y escribe composicion.json."""
    directorio = Path(raiz_datos) / "m6_huella_espectral" / campo
    medido = leer_json(directorio / "espectro_medido.json")
    ruta_tipos = directorio / "tipo_espectral.json"
    tipos = {e["id_pareja"]: e["tipo"] for e in leer_json(ruta_tipos)["espectros"]} if ruta_tipos.is_file() else {}
    espectros = [{"id_pareja": e["id_pareja"],
                  "composicion": analizar(e["puntos"], e.get("agrupacion", "banda"), tipos.get(e["id_pareja"]))}
                 for e in medido["espectros"] if e["puntos"]]
    return escribir_json(directorio / "composicion.json", {
        "_comentario": "Generado por m6_huella_espectral/identificacion_molecular.py. Estados con reglas fijas; "
                       "ninguna molécula se declara detectada por una coincidencia aproximada de longitud de onda.",
        "campo": campo, "espectros": espectros})


def anotar_espectros(ruta):
    """Añade `composicion` a un espectros.json ya escrito (contrato), usando su tipo y agrupación.

    Pensado para los datos de demostración de m9, que se generan ya publicados: así el
    cálculo sigue estando solo aquí. En el pipeline real la composición llega por
    escritura_espectros.py. `ruta` puede ser un archivo o un directorio con */espectros.json.
    Devuelve las rutas reescritas.
    """
    ruta = Path(ruta)
    archivos = sorted(ruta.glob("*/espectros.json")) if ruta.is_dir() else [ruta]
    for archivo in archivos:
        documento = leer_json(archivo)
        for espectro in documento["espectros"]:
            espectro["composicion"] = analizar(espectro["puntos"], espectro.get("agrupacion", "banda"), espectro.get("tipo"))
        escribir_json(archivo, documento)
    return archivos


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--anotar":
        for archivo in anotar_espectros(sys.argv[2]):
            print("composición añadida a %s" % archivo)
        sys.exit(0)
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m6_huella_espectral.identificacion_molecular <campo>\n"
                 "     python -m modulos.m6_huella_espectral.identificacion_molecular --anotar <espectros.json | directorio>")
    ruta_escrita = analizar_campo(sys.argv[1])
    for espectro in leer_json(ruta_escrita)["espectros"]:
        estados = ", ".join("%s=%s" % (m["formula"], m["estado"]) for m in espectro["composicion"]["moleculas"])
        print("%s: %s" % (espectro["id_pareja"], estados))
    print(ruta_escrita)
