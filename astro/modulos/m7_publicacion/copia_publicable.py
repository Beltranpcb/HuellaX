# ============================================================================
# ARCHIVO: modulos/m7_publicacion/copia_publicable.py
# MODULO: m7_publicacion (Lote A)
# ROL: Copia al directorio publicado los archivos que la web lee sin cambios.
# LEE: meta.json, epoca_a.png, epoca_b.png, diferencia.png de m2; espectros.json de m6.
# PRODUCE: Los mismos cinco archivos en datos/m7_publicacion/<campo>/ y, si existe, plantillas.json en datos/m7_publicacion/.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de m2, m6: meta.json, tres PNG, espectros.json.
#   1. Localizar los cinco archivos del campo  ->  rutas de origen
#   2. Copiar a datos/m7_publicacion/campo  ->  archivos publicados
#   Entrega a control_publicacion.py, m9: archivos publicados.
# VERIFICACION: Cada copia es idéntica byte a byte a su original.
# USO: python -m modulos.m7_publicacion.copia_publicable <campo>
# ============================================================================
"""Copia al directorio publicado los archivos que la web lee tal cual.

No transforma nada: la web debe recibir exactamente el mismo meta.json y los
mismos PNG que produjo m2_alineacion, y el mismo espectros.json que produjo
m6_huella_espectral. Cada copia se comprueba byte a byte antes de darla por
buena, de modo que un disco lleno o un archivo truncado no pasen inadvertidos.
"""
import filecmp
import shutil
import sys
from pathlib import Path

RAIZ_DATOS_POR_DEFECTO = "datos"

# Los cuatro archivos que produce m2_alineacion para cada campo.
ARCHIVOS_DE_ALINEACION = ("meta.json", "epoca_a.png", "epoca_b.png", "diferencia.png")


def copiar_archivo(origen, destino):
    """Copia un archivo y comprueba que la copia es idéntica byte a byte."""
    if not origen.is_file():
        raise FileNotFoundError("falta el archivo de origen %s" % origen)
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(origen, destino)
    if not filecmp.cmp(origen, destino, shallow=False):
        raise IOError("la copia de %s no coincide byte a byte" % origen)
    return destino


def copiar_plantillas(raiz):
    """Copia plantillas.json (m6, común a todos los campos) al directorio publicado, si existe.

    Es opcional: sin él la web sigue funcionando, solo que no dibuja las plantillas.
    Devuelve la ruta copiada o None.
    """
    origen = raiz / "m6_huella_espectral" / "plantillas.json"
    if not origen.is_file():
        return None
    return copiar_archivo(origen, raiz / "m7_publicacion" / "plantillas.json")


def copiar_campo(campo, raiz_datos=RAIZ_DATOS_POR_DEFECTO):
    """Copia los cinco archivos publicables del campo. Devuelve sus rutas."""
    raiz = Path(raiz_datos)
    origen_alineacion = raiz / "m2_alineacion" / campo
    origen_espectros = raiz / "m6_huella_espectral" / campo / "espectros.json"
    destino = raiz / "m7_publicacion" / campo

    copiados = [
        copiar_archivo(origen_alineacion / nombre, destino / nombre)
        for nombre in ARCHIVOS_DE_ALINEACION
    ]
    copiados.append(copiar_archivo(origen_espectros, destino / "espectros.json"))
    copiar_plantillas(raiz)
    return copiados


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m7_publicacion.copia_publicable <campo>")
    rutas = copiar_campo(sys.argv[1])
    print("%d archivos copiados a %s" % (len(rutas), rutas[0].parent))
