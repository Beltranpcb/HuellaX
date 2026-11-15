# Módulo heredado: AstroNova / HUELLA X

**Estado: heredado / referencia. No es el producto principal de HuellaX.**

`astro/` conserva el upstream AstroNova / HUELLA X dentro de HuellaX como un
módulo heredado claramente identificado. Es una demo estática más un pipeline
de Python offline. El producto principal de HuellaX es **MoveScope + SQL**, en
[`system/`](../system/), documentado en la [portada del repositorio](../README.md).
Este módulo no es el runtime SQL principal ni la vía de datos/ciencia soportada.

## Procedencia y atribución

| Dato | Valor |
|---|---|
| Repositorio upstream | [Beltranpcb/AstroNova](https://github.com/Beltranpcb/AstroNova) |
| Commit analizado | `1253925ab13419b5d44db323548784c939a93a6e` |
| Origen | Equipo AstroNova, NASA Space Apps Challenge 2026, reto SPHEREx / Planeta X |
| Idioma original | Español (interfaz de la demo, documentación, comentarios y nombres de campo) |
| Integración | copiado a `astro/`; se conservan rutas, código y textos originales |
| Autoría | proyecto anterior del propio equipo de HuellaX, misma cuenta de GitHub |

Atribución: el diseño, los textos en español, los datos de demostración y el
pipeline provienen del equipo AstroNova / HUELLA X, que es el mismo equipo de
HuellaX. Fusionamos nuestros dos proyectos para combinar sus funcionalidades;
HuellaX conserva las rutas, el código y la interfaz original de AstroNova.

## Nota sobre NASA Space Apps

AstroNova / HUELLA X se desarrolló para el NASA Space Apps Challenge 2026
(reto SPHEREx / Planeta X). Esta nota solo registra la participación en el
evento. NASA no respalda este proyecto y aquí no se reclama ninguna afiliación
con NASA.

## Aviso sobre los datos

- Los campos y ejemplos de la demo son **sintéticos**. No representan el cielo
  real ni un resultado científico validado.
- La validación con datos reales de SPHEREx y con Gaia está **pendiente**.
- Esta demo no hace afirmaciones de descubrimiento ni del Planeta X. Un objeto
  sin coincidencia en catálogos es un «candidato no identificado», nunca un
  objeto nuevo.
- No uses este módulo como fuente principal ni como base de conclusiones
  científicas.

## Producto principal

El producto principal de HuellaX es **MoveScope + SQL** en [`system/`](../system/):

- [Portada del repositorio](../README.md) y [aplicación MoveScope](http://127.0.0.1:8790/).
- Este módulo heredado no debe presentarse como el runtime principal ni como la
  fuente de datos principal.

## Licencia

AstroNova es trabajo propio y forma parte de este repositorio, por lo que está
cubierto por la licencia Apache-2.0 ([LICENSE](../LICENSE)) y el
[NOTICE](../NOTICE) del repositorio. Los datos y medios de terceros conservan
sus propias condiciones; consulta el README de `astro/` y los avisos del
repositorio.

## Conservación

- No se traduce toda la interfaz heredada: el español es el original.
- No se elimina el código fuente del upstream.
- El aviso bilingüe de `modulos/m9_sitio/index.html` es solo un envoltorio de
  integración, no una reescritura de la interfaz.

## Documentos relacionados

- [UPSTREAM.md](UPSTREAM.md): procedencia y conservación.
- [README.md](README.md): README original en español.
- [LEGACY.md](LEGACY.md): versión en inglés.
- [Demo estática](modulos/m9_sitio/index.html).
