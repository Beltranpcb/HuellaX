# ============================================================================
# ARCHIVO: modulos/m6_huella_espectral/escritura_espectros.py
# MODULO: m6_huella_espectral (Lote C)
# ROL: Reúne medida, tipo, temperatura en el archivo del contrato.
# LEE: espectro_medido.json; tipo_espectral.json; temperatura.json; composicion.json (opcional).
# PRODUCE: datos/m6_huella_espectral/<campo>/espectros.json.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de comparacion_plantillas.py, ajuste_planck.py: tipo_espectral.json, temperatura.json.
#   1. Leer espectro_medido.json  ->  puntos por objeto
#   2. Unir por id_pareja  ->  registro por objeto
#   3. Añadir advertencias y calidad, y publicar plantillas.json  ->  espectros.json, plantillas.json
#   Entrega a m7: espectros.json.
# VERIFICACION: El archivo valida contra contratos/espectros.schema.json; hay un espectro por
#   pareja candidata medida.
# USO: python -m modulos.m6_huella_espectral.escritura_espectros <campo>
# NOTA: Un espectro sin puntos medidos no se publica (el contrato exige al menos un punto); m7 lo
#   marcará con tiene_espectro falso. Las tres tablas deben cubrir las mismas parejas.
# ============================================================================
"""Une la medida, el tipo y la temperatura en el espectros.json del contrato."""
import json
import sys
from pathlib import Path

import numpy as np

VERSION_CONTRATO = "1"
CAMPOS_DEL_PUNTO = ("longitud_onda_micras", "flujo_mjy", "error_mjy", "mjd", "detector")
RUTA_PLANTILLAS = Path(__file__).resolve().parent / "plantillas.json"
CAMPOS_PLANTILLA = ("tipo", "etiqueta_publica", "origen_plantilla", "referencia", "longitud_onda_micras", "flujo_normalizado")
COMENTARIO = (
    "Generado por m6_huella_espectral/escritura_espectros.py. Un espectro por pareja candidata "
    "medida, con su tipo y su temperatura."
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


def calidad_de(puntos):
    """Resumen de calidad del espectro: nº de puntos, cobertura y mediana de la señal/ruido."""
    onda = [p["longitud_onda_micras"] for p in puntos]
    snr = [abs(p["flujo_mjy"]) / p["error_mjy"] for p in puntos]
    return {
        "n_puntos": len(puntos),
        "cobertura_micras": [min(onda), max(onda)],
        "senal_ruido_mediana": round(float(np.median(snr)), 2),
        "resolucion_espectral": None,  # no se mide: SPHEREx no la entrega por punto
    }


def unir_advertencias(*listas):
    """Unión sin repetidos que conserva el orden de aparición."""
    vistas = []
    for lista in listas:
        for aviso in lista or []:
            if aviso not in vistas:
                vistas.append(aviso)
    return vistas


def publicar_plantillas(raiz_datos="datos"):
    """Escribe datos/m6_huella_espectral/plantillas.json según contratos/plantillas.schema.json."""
    origen = leer_json(RUTA_PLANTILLAS)
    contenido = {
        "_comentario": "Generado por m6_huella_espectral/escritura_espectros.py desde plantillas.json del módulo. "
                       "Las plantillas con origen_plantilla sintetica no son espectros de referencia medidos.",
        "version_contrato": VERSION_CONTRATO,
        "plantillas": [{nombre: plantilla[nombre] for nombre in CAMPOS_PLANTILLA} for plantilla in origen["plantillas"]],
    }
    return escribir_json(Path(raiz_datos) / "m6_huella_espectral" / "plantillas.json", contenido)


def construir_espectros(campo, medido, tipos, temperaturas, composiciones=None):
    """Monta el espectros.json del contrato a partir de las tres tablas del campo."""
    for documento, nombre in (
        (medido, "espectro_medido.json"),
        (tipos, "tipo_espectral.json"),
        (temperaturas, "temperatura.json"),
    ):
        if documento.get("campo") != campo:
            raise ValueError(
                "%s: el campo es %r, se esperaba %r" % (nombre, documento.get("campo"), campo)
            )

    tipos_por_id = {espectro["id_pareja"]: espectro for espectro in tipos["espectros"]}
    temperaturas_por_id = {
        espectro["id_pareja"]: espectro for espectro in temperaturas["espectros"]
    }

    composicion_por_id = {e["id_pareja"]: e["composicion"] for e in (composiciones or {}).get("espectros", [])}

    espectros = []
    for medida in medido["espectros"]:
        if not medida["puntos"]:
            continue
        id_pareja = medida["id_pareja"]
        if id_pareja not in tipos_por_id:
            raise ValueError("tipo_espectral.json no trae la pareja %r" % id_pareja)
        if id_pareja not in temperaturas_por_id:
            raise ValueError("temperatura.json no trae la pareja %r" % id_pareja)
        tipo = tipos_por_id[id_pareja]
        temperatura = temperaturas_por_id[id_pareja]
        espectros.append(
            {
                "id_pareja": id_pareja,
                "agrupacion": medida["agrupacion"],
                "puntos": [
                    {nombre: punto[nombre] for nombre in CAMPOS_DEL_PUNTO}
                    for punto in medida["puntos"]
                ],
                "tipo": tipo["tipo"],
                "ajustes_plantilla": tipo["ajustes_plantilla"],
                "advertencias": unir_advertencias(tipo.get("advertencias"), temperatura.get("advertencias")),
                "calidad": calidad_de(medida["puntos"]),
                **({"composicion": composicion_por_id[id_pareja]} if id_pareja in composicion_por_id else {}),
                "temperatura_k": temperatura["temperatura_k"],
                "incertidumbre_temperatura_k": temperatura["incertidumbre_temperatura_k"],
                "pico_wien_micras": temperatura["pico_wien_micras"],
            }
        )

    return {
        "_comentario": COMENTARIO,
        "version_contrato": VERSION_CONTRATO,
        "campo": campo,
        "espectros": espectros,
    }


def escribir_campo(campo, raiz_datos="datos"):
    """Lee las tres tablas del campo y escribe espectros.json.

    Si falta alguna de las tres (por ejemplo porque la fotometría no pudo medir
    nada), escribe un espectros.json vacío y avisa: m7 puede seguir publicando el
    campo con `tiene_espectro: false`, en lugar de romper toda la cadena.
    """
    directorio = Path(raiz_datos) / "m6_huella_espectral" / campo
    entradas = ("espectro_medido.json", "tipo_espectral.json", "temperatura.json")
    faltan = [nombre for nombre in entradas if not (directorio / nombre).exists()]
    if faltan:
        print(
            "AVISO: faltan %s en %s; se publica espectros.json vacío."
            % (", ".join(faltan), directorio),
            file=sys.stderr,
        )
        return escribir_json(
            directorio / "espectros.json",
            {
                "_comentario": "Sin espectros: faltan %s." % ", ".join(faltan),
                "version_contrato": "1",
                "campo": campo,
                "espectros": [],
            },
        )
    contenido = construir_espectros(
        campo,
        leer_json(directorio / "espectro_medido.json"),
        leer_json(directorio / "tipo_espectral.json"),
        leer_json(directorio / "temperatura.json"),
        leer_json(directorio / "composicion.json") if (directorio / "composicion.json").is_file() else None,
    )
    publicar_plantillas(raiz_datos)
    return escribir_json(directorio / "espectros.json", contenido)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m6_huella_espectral.escritura_espectros <campo>")
    ruta_escrita = escribir_campo(sys.argv[1])
    total = len(leer_json(ruta_escrita)["espectros"])
    print("%s: %d espectro%s" % (ruta_escrita, total, "" if total == 1 else "s"))
