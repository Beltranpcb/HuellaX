#!/usr/bin/env python3
"""Actualiza la publicación con una política de caché.

El pipeline tarda y depende de IRSA, que se cae de vez en cuando. En un servidor
no se puede servir una web vacía porque el archivo no responda: se refresca cada
cierto tiempo y, si el refresco falla, **se sigue sirviendo lo último publicado**.

Reglas:

1. Cada campo tiene una fecha de última actualización en `datos/m7_publicacion/_estado.json`.
2. Un campo se refresca cuando no está publicado, cuando han pasado `--ttl-dias`,
   o cuando se pasa `--forzar`.
3. Si el refresco falla, **no se borra nada**: se conserva lo publicado, se apunta
   el error y se suma un intento fallido. La web sigue funcionando con datos viejos.
4. Si el refresco sale bien pero publica menos candidatas que antes, se conserva el
   resultado anterior salvo `--aceptar-degradacion` (evita que un mal día de IRSA
   deje la demo vacía).
5. Todo lo que escribe vive en `datos/`, que no entra en git.

Uso:

    python -m herramientas.actualizar_publicacion            # respeta el TTL
    python -m herramientas.actualizar_publicacion --forzar   # refresca todo
    python -m herramientas.actualizar_publicacion --estado   # solo muestra el estado
    python -m herramientas.actualizar_publicacion --ttl-dias 3 --campo sphx_a
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PUBLICADO = RAIZ / "datos" / "m7_publicacion"
MANIFIESTO = PUBLICADO / "_estado.json"
CAMPOS_OBJETIVO = RAIZ / "modulos" / "m1_adquisicion" / "campos_objetivo.json"

# Pasos del pipeline, en orden. None = el comando no lleva el nombre del campo.
PASOS = [
    ("m1_adquisicion", "consulta_sia", True),
    ("m1_adquisicion", "seleccion_epocas", True),
    ("m1_adquisicion", "descarga_recortes", True),
    ("m2_alineacion", "resta_zodiacal", True),
    ("m2_alineacion", "reproyeccion", True),
    ("m2_alineacion", "metadatos_campo", True),
    ("m2_alineacion", "exportacion_png", True),
    ("m3_deteccion", "deteccion_fuentes", True),
    ("m3_deteccion", "emparejamiento", True),
    ("m3_deteccion", "propuesta_parejas", True),
    ("m4_movimiento", "cinematica", True),
    ("m4_movimiento", "incertidumbre", True),
    ("m4_movimiento", "clasificacion", True),
    ("m5_identificacion", "consulta_catalogos", True),
    ("m5_identificacion", "cruce_posicional", True),
    ("m6_huella_espectral", "trayectoria", True),
    ("m6_huella_espectral", "fotometria", True),
    ("m6_huella_espectral", "comparacion_plantillas", True),
    ("m6_huella_espectral", "ajuste_planck", True),
    ("m6_huella_espectral", "identificacion_molecular", True),
    ("m6_huella_espectral", "escritura_espectros", True),
    ("m7_publicacion", "union_candidatos", True),
    ("m7_publicacion", "copia_publicable", True),
    ("m7_publicacion", "indice_campos", False),
    ("m7_publicacion", "indice_catalogo", False),
    ("m7_publicacion", "control_publicacion", True),
]


def ahora_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def leer_manifiesto() -> dict:
    if MANIFIESTO.is_file():
        try:
            return json.loads(MANIFIESTO.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"version": 1, "campos": {}}


def escribir_manifiesto(datos: dict) -> None:
    PUBLICADO.mkdir(parents=True, exist_ok=True)
    MANIFIESTO.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def campos_declarados() -> list[str]:
    if not CAMPOS_OBJETIVO.is_file():
        return []
    return [c["campo"] for c in json.loads(CAMPOS_OBJETIVO.read_text(encoding="utf-8"))["campos"]]


def candidatas_publicadas(campo: str) -> int | None:
    ruta = PUBLICADO / campo / "candidatos.json"
    if not ruta.is_file():
        return None
    try:
        return len(json.loads(ruta.read_text(encoding="utf-8"))["candidatos"])
    except (json.JSONDecodeError, KeyError):
        return None


def edad_dias(registro: dict) -> float | None:
    marca = registro.get("actualizado_utc")
    if not marca:
        return None
    cuando = datetime.datetime.strptime(marca, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc)
    return (datetime.datetime.now(datetime.timezone.utc) - cuando).total_seconds() / 86400


def ejecutar_paso(modulo: str, archivo: str, campo: str | None) -> tuple[bool, str]:
    orden = [sys.executable, "-m", f"modulos.{modulo}.{archivo}"]
    if campo:
        orden.append(campo)
    # Los módulos escriben en UTF-8 (acentos, µ, →): se fuerza en el hijo y al leerlo, también en Windows.
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proceso = subprocess.run(orden, cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace", env=entorno)
    if proceso.returncode != 0:
        cola = (proceso.stderr or proceso.stdout).strip().splitlines()
        return False, cola[-1] if cola else f"código {proceso.returncode}"
    return True, ""


def refrescar(campo: str, aceptar_degradacion: bool) -> tuple[bool, str]:
    """Ejecuta el pipeline para un campo. Devuelve (éxito, motivo)."""
    antes = candidatas_publicadas(campo)
    for modulo, archivo, con_campo in PASOS:
        ok, motivo = ejecutar_paso(modulo, archivo, campo if con_campo else None)
        if not ok:
            return False, f"{modulo}.{archivo}: {motivo}"
    despues = candidatas_publicadas(campo)
    if (
        not aceptar_degradacion
        and antes is not None
        and despues is not None
        and despues < antes
    ):
        return False, (
            f"el refresco publicó {despues} candidatas y había {antes}; "
            "se conserva lo anterior (usa --aceptar-degradacion para forzarlo)"
        )
    return True, ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ttl-dias", type=float, default=7.0,
                        help="días que se considera fresco un campo (por defecto 7)")
    parser.add_argument("--campo", action="append", help="campo concreto (repetible)")
    parser.add_argument("--forzar", action="store_true", help="refrescar aunque esté fresco")
    parser.add_argument("--aceptar-degradacion", action="store_true",
                        help="aceptar un refresco con menos candidatas que el anterior")
    parser.add_argument("--estado", action="store_true", help="solo mostrar el estado y salir")
    args = parser.parse_args(argv)

    manifiesto = leer_manifiesto()
    campos = args.campo or campos_declarados()

    if args.estado:
        if not campos:
            print("No hay campos declarados en campos_objetivo.json")
            return 0
        print(f"{'campo':<14}{'publicado':<10}{'edad':<10}{'fallos':<8}último error")
        for campo in campos:
            registro = manifiesto["campos"].get(campo, {})
            edad = edad_dias(registro)
            print(
                f"{campo:<14}"
                f"{str(candidatas_publicadas(campo)):<10}"
                f"{(f'{edad:.1f} d' if edad is not None else '—'):<10}"
                f"{registro.get('intentos_fallidos', 0):<8}"
                f"{registro.get('ultimo_error') or ''}"
            )
        return 0

    if not campos:
        print("No hay campos declarados en campos_objetivo.json", file=sys.stderr)
        return 1

    refrescados, conservados, fallos = [], [], []
    for campo in campos:
        registro = manifiesto["campos"].get(campo, {})
        edad = edad_dias(registro)
        publicado = candidatas_publicadas(campo) is not None
        toca = args.forzar or not publicado or edad is None or edad >= args.ttl_dias

        if not toca:
            conservados.append((campo, f"fresco ({edad:.1f} d)"))
            continue

        print(f"→ refrescando {campo} …", flush=True)
        ok, motivo = refrescar(campo, args.aceptar_degradacion)
        if ok:
            registro.update({
                "actualizado_utc": ahora_utc(),
                "intentos_fallidos": 0,
                "ultimo_error": None,
                "candidatas": candidatas_publicadas(campo),
            })
            manifiesto["campos"][campo] = registro
            refrescados.append(campo)
            print(f"  ✓ {campo}: {registro['candidatas']} candidatas")
        else:
            registro["intentos_fallidos"] = registro.get("intentos_fallidos", 0) + 1
            registro["ultimo_error"] = motivo
            manifiesto["campos"][campo] = registro
            fallos.append((campo, motivo))
            estado = "se conserva lo publicado" if publicado else "no hay datos previos"
            print(f"  ✗ {campo}: {motivo} — {estado}", file=sys.stderr)
        escribir_manifiesto(manifiesto)

    escribir_manifiesto(manifiesto)
    print(
        f"\nresumen: {len(refrescados)} refrescados · {len(conservados)} frescos · "
        f"{len(fallos)} con error"
    )
    for campo, motivo in fallos:
        print(f"  {campo}: {motivo}", file=sys.stderr)
    return 0 if not fallos else 2


if __name__ == "__main__":
    # En Windows la consola o una redirección usan cp1252 y «→ ✓ ✗» rompen el print:
    # se fuerza UTF-8 (y se reemplaza lo que no quepa) antes de escribir nada.
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
