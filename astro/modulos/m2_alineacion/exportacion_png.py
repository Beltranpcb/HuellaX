# ============================================================================
# ARCHIVO: modulos/m2_alineacion/exportacion_png.py
# MODULO: m2_alineacion (Lote A)
# ROL: Exporta las imágenes PNG que la web muestra.
# LEE: FITS alineados.
# PRODUCE: epoca_a.png, epoca_b.png, diferencia.png en datos/m2_alineacion/<campo>/.
# FUNCIONAMIENTO PREVISTO:
#   Recibe de reproyeccion.py: FITS alineados.
#   1. Calcular límites ZScale sobre la época A  ->  límites de contraste
#   2. Aplicar el mismo estirado asinh a las épocas A, B  ->  epoca_a.png, epoca_b.png
#   3. Restar B menos A con un mapa de dos tonos  ->  diferencia.png
# VERIFICACION: Los tres PNG miden 600 x 600 píxeles; las estrellas fijas no saltan al alternar epoca_a.png con epoca_b.png.
# USO: python -m modulos.m2_alineacion.exportacion_png <campo>
# NOTA: Orientación del contrato imagenes_png: la fila 0 de la rejilla queda abajo, así que
#       x_png = x * 600 / ancho, y_png = 600 - y * 600 / alto. Colores de contratos/guia_visual.md:
#       lo que aparece en verde menta (--acierto), lo que desaparece en coral (--fallo).
# ============================================================================
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.visualization import AsinhStretch, ImageNormalize, ZScaleInterval
from PIL import Image

LADO_PNG = 600
FONDO = np.array([11, 15, 26], dtype=float)        # #0B0F1A
APARECE = np.array([74, 222, 128], dtype=float)    # #4ADE80, lo que hay en B y no en A
DESAPARECE = np.array([248, 113, 113], dtype=float)  # #F87171, lo que hay en A y no en B
SIGMAS_UMBRAL = 2.0      # cambios por debajo de esto son ruido y se dejan en el fondo
SIGMAS_DIFERENCIA = 5.0  # cambios que saturan el color, en sigmas
FRACCION_FLUJO = 0.10    # error proporcional al brillo local: tapa los residuos de interpolación en las estrellas fijas


def limites_contraste(imagen_a):
    """Límites ZScale de la época A, ignorando los píxeles sin cobertura."""
    valores = np.asarray(imagen_a, dtype=float)
    valores = valores[np.isfinite(valores)]
    if valores.size == 0:
        return 0.0, 1.0
    vmin, vmax = ZScaleInterval().get_limits(valores)
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax <= vmin:
        vmin, vmax = np.percentile(valores, [1, 99])
        if vmax <= vmin:
            vmax = vmin + 1.0
    return float(vmin), float(vmax)


def a_gris(imagen, limites):
    """Imagen en 0..255 con estirado asinh entre los límites dados. Sin cobertura: negro."""
    vmin, vmax = limites
    norma = ImageNormalize(vmin=vmin, vmax=vmax, stretch=AsinhStretch(0.1), clip=True)
    datos = np.asarray(imagen, dtype=float)
    valores = np.ma.filled(norma(np.where(np.isfinite(datos), datos, vmin)), 0.0)
    return np.clip(np.rint(valores * 255.0), 0, 255).astype(np.uint8)


def sigma_robusta(valores):
    """1,4826 veces la desviación absoluta mediana; nunca cero."""
    valores = valores[np.isfinite(valores)]
    if valores.size == 0:
        return 1.0
    mediana = np.median(valores)
    sigma = 1.4826 * np.median(np.abs(valores - mediana))
    return float(sigma) if sigma > 0 else float(np.std(valores)) or 1.0


def imagen_diferencia(imagen_a, imagen_b):
    """B menos A en dos tonos: verde donde aparece brillo, coral donde desaparece, fondo donde no cambia.

    El cambio se mide en sigmas frente a un error que suma el ruido del fondo y una fracción del
    brillo local, como en la fotometría de diferencias: así una estrella fija con un residuo del
    1 % no se pinta, pero un objeto que aparece o desaparece entero satura el color.
    """
    a = np.asarray(imagen_a, dtype=float)
    b = np.asarray(imagen_b, dtype=float)
    diferencia = b - a
    sigma = sigma_robusta(diferencia)
    brillo_local = np.nan_to_num(np.fmax(np.abs(a), np.abs(b)), nan=0.0)
    error = np.sqrt(sigma ** 2 + (FRACCION_FLUJO * brillo_local) ** 2)
    significancia = np.abs(np.nan_to_num(diferencia, nan=0.0)) / error
    intensidad = np.clip((significancia - SIGMAS_UMBRAL) / (SIGMAS_DIFERENCIA - SIGMAS_UMBRAL), 0.0, 1.0)[..., None]
    color = np.where((diferencia > 0)[..., None], APARECE, DESAPARECE)
    rgb = FONDO + intensidad * (color - FONDO)
    return np.clip(np.rint(rgb), 0, 255).astype(np.uint8)


def guardar_png(matriz, ruta):
    """Vuelca la matriz (fila 0 abajo) a un PNG de LADO_PNG x LADO_PNG."""
    imagen = Image.fromarray(np.flipud(matriz))
    imagen.resize((LADO_PNG, LADO_PNG), Image.BILINEAR).save(ruta, optimize=True)
    return ruta


def exportar_campo(campo, raiz_datos="datos"):
    """Lee epoca_a.fits y epoca_b.fits alineados; escribe los tres PNG. Devuelve sus rutas."""
    directorio = Path(raiz_datos) / "m2_alineacion" / campo
    with fits.open(directorio / "epoca_a.fits") as ha, fits.open(directorio / "epoca_b.fits") as hb:
        imagen_a = np.asarray(ha["IMAGE"].data, dtype=float)
        imagen_b = np.asarray(hb["IMAGE"].data, dtype=float)
    limites = limites_contraste(imagen_a)
    return {
        "epoca_a": guardar_png(a_gris(imagen_a, limites), directorio / "epoca_a.png"),
        "epoca_b": guardar_png(a_gris(imagen_b, limites), directorio / "epoca_b.png"),
        "diferencia": guardar_png(imagen_diferencia(imagen_a, imagen_b), directorio / "diferencia.png"),
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m modulos.m2_alineacion.exportacion_png <campo>")
    for nombre_, ruta_ in exportar_campo(sys.argv[1]).items():
        print("%s: %s  %d bytes" % (nombre_, ruta_, ruta_.stat().st_size))
