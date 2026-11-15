# ============================================================================
# ARCHIVO: modulos/m6_huella_espectral/ajuste_planck.py
# MODULO: m6_huella_espectral (Lote C)
# ROL: Estima la temperatura del objeto ajustando la ley de Planck.
# LEE: espectro_medido.json.
# PRODUCE: datos/m6_huella_espectral/<campo>/temperatura.json (intermedio interno).
# FUNCIONAMIENTO PREVISTO:
#   Recibe de fotometria.py: espectro_medido.json.
#   1. Separar los puntos del continuo  ->  puntos fuera de bandas
#   2. Ajustar Planck por mínimos cuadrados  ->  temperatura con incertidumbre
#   3. Aplicar la ley de Wien  ->  temperatura.json
#   Entrega a escritura_espectros.py: temperatura.json.
# VERIFICACION: El producto del pico de Wien por la temperatura vale 2898 micras kelvin con un
#   error menor que 1.
# USO: python -m modulos.m6_huella_espectral.ajuste_planck <campo>
# NOTA: Si el pico de Wien cae más allá de 5 micras la temperatura se extrapola desde la cola de Wien:
#   se marca cuerpo_negro_fuera_de_rango y la web no debe presentarla como medida directa. El ajuste deja libre la amplitud (el brillo absoluto no se conoce) y solo usa la forma.
#   Los puntos dentro de bandas de emisión o absorción conocidas no son continuo; si quedan menos
#   de tres, se usan todos. Sin convergencia, la temperatura queda nula y el contrato lo admite.
# ============================================================================
"""Estima la temperatura del objeto ajustando la ley de Planck al continuo del espectro."""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit

CONSTANTE_PLANCK = 6.62607015e-34  # J s
VELOCIDAD_LUZ = 2.99792458e8       # m/s
CONSTANTE_BOLTZMANN = 1.380649e-23  # J/K
CONSTANTE_WIEN_MICRAS_KELVIN = 2898.0

MINIMO_PUNTOS = 3
LONGITUD_ONDA_MAXIMA = 5.0  # límite superior de SPHEREx; un pico de Wien más allá se extrapola
TEMPERATURA_MINIMA, TEMPERATURA_MAXIMA = 50.0, 3000.0
# Bandas con emisión o absorción conocida: no describen el continuo térmico.
BANDAS_FUERA_DEL_CONTINUO = (
    (0.95, 1.05),  # silicatos
    (1.30, 1.50),  # agua
    (1.90, 2.10),  # silicatos
    (2.70, 3.10),  # hielo de agua
    (3.20, 3.40),  # metano
    (4.15, 4.35),  # CO2
    (4.55, 4.75),  # CO
)

COMENTARIO = (
    "Generado por m6_huella_espectral/ajuste_planck.py. Temperatura estimada por la forma "
    "del continuo; nula si el ajuste no converge."
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


def planck(longitud_onda_micras, temperatura_k):
    """Densidad de flujo de un cuerpo negro, salvo una constante multiplicativa."""
    onda = np.asarray(longitud_onda_micras, dtype=float) * 1e-6
    exponente = np.minimum(
        CONSTANTE_PLANCK * VELOCIDAD_LUZ / (onda * CONSTANTE_BOLTZMANN * temperatura_k), 700.0
    )
    with np.errstate(over="ignore", under="ignore", divide="ignore", invalid="ignore"):
        return 2.0 * CONSTANTE_PLANCK * VELOCIDAD_LUZ ** 2 / onda ** 5 / np.expm1(exponente)


def fuera_de_bandas(longitud_onda_micras):
    """Verdadero si la longitud de onda cae fuera de las bandas de emisión o absorción."""
    return not any(limite_bajo <= longitud_onda_micras <= limite_alto
                   for limite_bajo, limite_alto in BANDAS_FUERA_DEL_CONTINUO)


def puntos_continuo(puntos):
    """Puntos fuera de las bandas; si quedan menos de MINIMO_PUNTOS, se usan todos."""
    continuo = [p for p in puntos if fuera_de_bandas(p["longitud_onda_micras"])]
    return continuo if len(continuo) >= MINIMO_PUNTOS else list(puntos)


def ajustar_puntos(puntos):
    """Temperatura del ajuste de Planck. Devuelve None si no hay puntos suficientes o no converge."""
    if len(puntos) < MINIMO_PUNTOS:
        return None
    continuo = puntos_continuo(puntos)
    onda = np.array([p["longitud_onda_micras"] for p in continuo], dtype=float)
    flujo = np.array([p["flujo_mjy"] for p in continuo], dtype=float)
    error = np.array([p["error_mjy"] for p in continuo], dtype=float)
    if not (np.all(np.isfinite(onda)) and np.all(np.isfinite(flujo)) and np.all(error > 0)):
        raise ValueError("punto con longitud de onda, flujo o error no válido")

    referencia = int(np.argmax(flujo))
    onda_referencia, flujo_referencia = float(onda[referencia]), float(flujo[referencia])
    if flujo_referencia <= 0:
        return None

    def modelo(lam, escala, temperatura):
        return escala * flujo_referencia * planck(lam, temperatura) / planck(onda_referencia, temperatura)

    try:
        parametros, covarianza = curve_fit(
            modelo,
            onda,
            flujo,
            p0=(1.0, 300.0),
            sigma=error,
            absolute_sigma=True,
            bounds=([1e-6, TEMPERATURA_MINIMA], [1e6, TEMPERATURA_MAXIMA]),
            maxfev=20000,
        )
    except (RuntimeError, ValueError):
        return None

    temperatura = float(parametros[1])
    incertidumbre = float(np.sqrt(covarianza[1, 1])) if covarianza.shape == (2, 2) else float("nan")
    if not (np.isfinite(temperatura) and np.isfinite(incertidumbre)) or temperatura <= 0 or incertidumbre <= 0:
        return None

    chi2 = float(np.sum(((flujo - modelo(onda, *parametros)) / error) ** 2))
    return {
        "temperatura_k": round(temperatura, 2),
        "incertidumbre_temperatura_k": round(incertidumbre, 2),
        "pico_wien_micras": round(CONSTANTE_WIEN_MICRAS_KELVIN / temperatura, 3),
        "chi2_reducido": round(chi2 / max(1, len(onda) - 2), 4),
        "puntos_usados": int(len(onda)),
    }


def ajustar_campo(campo, raiz_datos="datos"):
    """Lee espectro_medido.json y escribe temperatura.json con la temperatura de cada pareja."""
    directorio = Path(raiz_datos) / "m6_huella_espectral" / campo
    medido = leer_json(directorio / "espectro_medido.json")
    espectros = []
    for espectro in medido["espectros"]:
        ajuste = ajustar_puntos(espectro["puntos"])
        espectros.append(
            {
                "id_pareja": espectro["id_pareja"],
                "temperatura_k": ajuste["temperatura_k"] if ajuste else None,
                "incertidumbre_temperatura_k": ajuste["incertidumbre_temperatura_k"] if ajuste else None,
                "pico_wien_micras": ajuste["pico_wien_micras"] if ajuste else None,
                "advertencias": (
                    ["cuerpo_negro_fuera_de_rango"]
                    if ajuste and ajuste["pico_wien_micras"] > LONGITUD_ONDA_MAXIMA else []
                ),
            }
        )
    return escribir_json(
        directorio / "temperatura.json",
        {"_comentario": COMENTARIO, "campo": campo, "espectros": espectros},
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m6_huella_espectral.ajuste_planck <campo>")
    ruta_escrita = ajustar_campo(sys.argv[1])
    for espectro in leer_json(ruta_escrita)["espectros"]:
        if espectro["temperatura_k"] is None:
            print("%s: sin ajuste de Planck" % espectro["id_pareja"])
        else:
            print("%s: %.1f K +- %.1f K" % (espectro["id_pareja"], espectro["temperatura_k"], espectro["incertidumbre_temperatura_k"]))
    print(ruta_escrita)
