import streamlit as st

from cerebro import (
    ImagenIlegible,
    RespuestaIncompleta,
    analizar_pagina,
    calificar,
    crear_cliente,
)


st.set_page_config(page_title="Mi cuaderno habla", page_icon="📓", layout="centered")

try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error(
        "Falta configurar `GEMINI_API_KEY`. En la raíz del proyecto, creá "
        "`.streamlit/secrets.toml` con esta línea:\n\n"
        'GEMINI_API_KEY = "tu-clave-de-Gemini"'
    )
    st.stop()


# Streamlit vuelve a ejecutar este archivo ante cada interacción; session_state conserva el progreso.
if "apunte" not in st.session_state:
    st.session_state.apunte = None
if "respuestas_examen" not in st.session_state:
    st.session_state.respuestas_examen = {}
if "examen_entregado" not in st.session_state:
    st.session_state.examen_entregado = False


st.title("Mi cuaderno habla")

pestana_foto, pestana_subir = st.tabs(["Tomar foto", "Subir imagen"])
with pestana_foto:
    imagen_camara = st.camera_input("Tomá una foto de la página")
with pestana_subir:
    imagen_archivo = st.file_uploader(
        "Elegí una imagen de tus apuntes",
        type=["png", "jpg", "jpeg", "webp"],
    )

imagen = imagen_camara if imagen_camara is not None else imagen_archivo

if st.button("Analizar la página", type="primary"):
    if imagen is None:
        st.warning("Primero tomá una foto o subí una imagen de tus apuntes.")
    else:
        try:
            with st.spinner("Analizando la página..."):
                cliente = crear_cliente(api_key)
                apunte = analizar_pagina(
                    imagen.getvalue(), imagen.type or "image/jpeg", cliente
                )
            st.session_state.apunte = apunte
            st.session_state.respuestas_examen = {}
            st.session_state.examen_entregado = False
        except (ImagenIlegible, RespuestaIncompleta) as error:
            st.warning(str(error))
        except Exception as error:
            codigo_error = getattr(error, "code", None)
            if codigo_error in (429, 503):
                st.error(
                    "Gemini está con mucha demanda en este momento. Esperá un "
                    "momento y volvé a tocar «Analizar la página»."
                )
            elif codigo_error in (401, 403):
                st.error(
                    "Gemini no aceptó la llave configurada. Revisá "
                    "`GEMINI_API_KEY` en `.streamlit/secrets.toml`."
                )
            else:
                st.error(
                    "No se pudo analizar la imagen. Revisá tu conexión y "
                    "probá de nuevo."
                )


apunte = st.session_state.apunte
if apunte is not None:
    st.header(apunte.titulo)
    st.write(f"**Materia:** {apunte.materia}")
    estrellas = "★" * apunte.dificultad + "☆" * (5 - apunte.dificultad)
    st.write(f"**Dificultad:** {estrellas}")

    st.subheader("Resumen")
    st.write(apunte.resumen)

    st.subheader("Conceptos")
    for concepto in apunte.conceptos:
        st.markdown(f"- **{concepto.termino}:** {concepto.explicacion}")

    st.subheader("Tarjetas de repaso")
    for tarjeta in apunte.tarjetas:
        with st.expander(tarjeta.pregunta):
            st.write(tarjeta.respuesta)

    st.subheader("Examen")
    respuestas = st.session_state.respuestas_examen
    examen_entregado = st.session_state.examen_entregado
    for indice, pregunta in enumerate(apunte.examen):
        seleccion = st.radio(
            pregunta.enunciado,
            pregunta.opciones,
            index=None,
            key=f"respuesta_{indice}",
            disabled=examen_entregado,
        )
        if seleccion is None:
            respuestas.pop(indice, None)
        else:
            respuestas[indice] = pregunta.opciones.index(seleccion)

    if st.button("Entregar examen", disabled=examen_entregado):
        st.session_state.examen_entregado = True

    if st.session_state.examen_entregado:
        aciertos, total = calificar(apunte, respuestas)
        st.metric("Puntaje", f"{aciertos}/{total}")

        for indice, pregunta in enumerate(apunte.examen):
            respuesta = respuestas.get(indice)
            puntaje_pregunta, _ = calificar(
                apunte, {indice: respuesta} if respuesta is not None else {}
            )
            if puntaje_pregunta:
                st.success(f"Pregunta {indice + 1}: correcta")
            else:
                opcion_correcta = pregunta.opciones[pregunta.correcta]
                st.error(
                    f"Pregunta {indice + 1}: incorrecta. "
                    f"Respuesta correcta: {opcion_correcta}"
                )

        if total and aciertos == total:
            st.balloons()

    guia = [
        f"# {apunte.titulo}",
        f"**Materia:** {apunte.materia}",
        f"**Dificultad:** {estrellas}",
        "",
        "## Resumen",
        apunte.resumen,
        "",
        "## Conceptos",
    ]
    guia.extend(f"- **{concepto.termino}:** {concepto.explicacion}" for concepto in apunte.conceptos)
    guia.extend(["", "## Tarjetas de repaso"])
    for tarjeta in apunte.tarjetas:
        guia.extend([f"### {tarjeta.pregunta}", tarjeta.respuesta, ""])
    guia.append("## Examen")
    for indice, pregunta in enumerate(apunte.examen, start=1):
        guia.append(f"{indice}. {pregunta.enunciado}")
        guia.extend(f"   - {opcion}" for opcion in pregunta.opciones)
    st.download_button(
        "Descargar guía de estudio",
        data="\n".join(guia),
        file_name="guia-de-estudio.md",
        mime="text/markdown",
    )