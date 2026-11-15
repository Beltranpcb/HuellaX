<!--
  ARCHIVO: modulos/m9_sitio/pruebas/lista_visual.md
  ROL: Lista de comprobaciones manuales de la web.
  LEE: La web servida en local.
  PRODUCE: El veredicto de quien revisa el módulo.
  VERIFICACION: Cada punto se marca tras observarlo en pantalla.
-->

# Lista visual de m9_sitio

Servir el repositorio desde la raíz y abrir
`http://127.0.0.1:8765/modulos/m9_sitio/index.html`.

## Portada

- [ ] Se lee el título **HUELLA X** con degradado.
- [ ] Hay un botón: **Explorar**.
- [ ] Aparecen los botones de los campos publicados.
- [ ] Pulsar un campo abre la aplicación en ese campo.

## Visor

- [ ] El lienzo muestra el campo y las fechas de A y B debajo.
- [ ] **Parpadeo**: las dos épocas se alternan cada 450 ms.
- [ ] **Cortina**: aparece una línea vertical; arrastrar sobre el lienzo la mueve.
- [ ] **Diferencia**: lo que aparece se ve en verde y lo que desaparece en rojo.
- [ ] La rueda del ratón hace zoom y el arrastre desplaza la imagen.
- [ ] **Centrar** devuelve el zoom a 1 y la imagen al origen.
- [ ] **Pausa** detiene el parpadeo y **Reproducir** lo reanuda.
- [ ] Cada candidato tiene un círculo en A y una flecha hacia B.
- [ ] Pulsar sobre un círculo selecciona ese candidato.

## Tabla

- [ ] Hay una fila por candidato, con separación, velocidad, significancia y clase.
- [ ] Pulsar una cabecera ordena; pulsar otra vez invierte el orden.
- [ ] Los filtros dejan solo las filas del estado elegido.
- [ ] Pulsar una fila selecciona el candidato y centra el visor.
- [ ] El botón **CSV** descarga la vista actual.

## Ficha

- [ ] Muestra posición, separación, velocidad, significancia y clase.
- [ ] La nota de **candidato** está siempre visible.
- [ ] El mapa aparece centrado en la posición del candidato.
- [ ] El espectro se dibuja con los puntos de `espectros.json`.
- [ ] Cambiar de candidato actualiza el espectro.

## Móvil (ancho menor de 900 px)

- [ ] El visor queda encima y la tabla debajo.
- [ ] No hay desplazamiento horizontal de la página.
- [ ] Los botones siguen siendo pulsables.

## Huellas en 3D

- [ ] El botón **3D** de la cabecera abre `espectro3d.html` con el campo actual.
- [ ] Se dibuja un listón por candidata con su nombre y su color.
- [ ] El eje horizontal marca 1, 2, 3, 4 y 5 µm.
- [ ] Arrastrar gira la escena y la rueda acerca.
- [ ] **Unir listones** muestra una malla translúcida entre ellos; volver a pulsar la quita.
- [ ] **Reiniciar vista** devuelve la cámara a su sitio.
- [ ] En vertical aparece el aviso de girar el dispositivo.
- [ ] Un campo sin huellas muestra un aviso en lugar de una escena vacía.

## Análisis de objetos · Comparar espectros

- [ ] «Análisis de objetos» oculta el visor y la tabla; «Explorador» los devuelve.
- [ ] Los selectores A y B solo listan objetos con espectro válido y muestran su origen.
- [ ] Se ven dos curvas con estilos distintos (línea continua y discontinua) y barras de error.
- [ ] «Espectros normalizados» indica el método y la longitud de onda de normalización.
- [ ] Con datos sintéticos aparece el aviso de que el flujo absoluto no tiene valor físico.
- [ ] Zoom (+, −, rueda) y «Restablecer» funcionan; CSV y PNG se descargan.
- [ ] «Plantillas (objeto A)» dibuja las cuatro curvas con estilos distintos, desactiva B y muestra la tabla de χ² con grados de libertad.
- [ ] El texto dice «más compatible con la plantilla … entre las evaluadas», nunca «es un …».
- [ ] «Identificar» dice que está pendiente.

## Análisis de objetos · Catálogo

- [ ] Es la pestaña que se abre primero; la cuenta dice «N de N objetos».
- [ ] Buscar «slipher» deja solo a (1766) Slipher; «atlas/p00» busca por identificador.
- [ ] Los filtros de clase, identificación y «Solo con espectro» se combinan.
- [ ] La ficha muestra la clasificación con su fuente; un objeto sin clase dice «Sin clase catalogada».
- [ ] Un objeto sin identificar avisa de que no equivale a un descubrimiento.
- [ ] Sin espectro no se dibuja ninguna curva y lo dice.
- [ ] «Misma clasificación» y «Espectros más similares» son listas distintas; los similares muestran χ²ᵣ, intervalo y puntos.
- [ ] «Comparar» abre el comparador con A y B; «Ver en el explorador» abre el campo con el candidato elegido.

## Composición espectral (fichas del explorador y del catálogo)

- [ ] Solo aparece si el candidato tiene espectro con `composicion`; un artefacto o un objeto sin espectro no la muestra.
- [ ] Las franjas de las bandas se distinguen de los puntos medidos y la nota dice que son teóricas.
- [ ] Cada molécula lleva su estado escrito (no solo color), S en sigmas, explicación y referencia.
- [ ] Luhman 16 A (demo): CH4 «Detectada»; la roca oscura de Slipher: H2O «Candidata» con minerales hidratados como alternativa.
- [ ] El resumen nunca cuenta una candidata como detección.

## Análisis de objetos · Identificar

- [ ] La imagen del campo aparece con las detecciones marcadas; la nota dice si es sintética.
- [ ] Un clic muestra píxel, RA/DEC (grados y sexagesimal), época A en UTC y la incertidumbre del clic.
- [ ] Un clic junto a una marca selecciona la detección y muestra su identificación de m5.
- [ ] «Consultar efemérides» muestra «Consultando…» y después la tabla o «no identificado en los catálogos consultados».
- [ ] Sin red aparece el error del servicio externo, sin romper la selección.
- [ ] Un campo sin `wcs` en meta.json avisa y no muestra coordenadas.
- [ ] Rueda o +/− acercan; arrastrar desplaza sin seleccionar.
