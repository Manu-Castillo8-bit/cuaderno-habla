import json

from google.genai import Client, types
from pydantic import ValidationError

from modelos import Apunte


MODELO = "gemini-3.8-flash"
INSTRUCCION_SISTEMA = (
    "Actuá como un profesor paciente de bachillerato de El Salvador. "
    "Escribí siempre en español salvadoreño claro. Basate únicamente en lo que "
    "se ve en la imagen y no inventés temas. Si la foto está borrosa, decilo "
    "en el resumen en vez de inventar. Hacé que las opciones incorrectas del "
    "examen sean creíbles, no absurdas, y variá la posición de la respuesta "
    "correcta entre preguntas."
)


class ImagenIlegible(Exception):
    """La imagen no produjo un apunte que se pueda mostrar al usuario."""


class RespuestaIncompleta(Exception):
    """El modelo respondió, pero su contenido no cumple el formato esperado."""


def crear_cliente(api_key: str) -> Client:
    if not api_key or not api_key.strip():
        raise ValueError("La llave de la API no puede estar vacía.")
    return Client(api_key=api_key)


def analizar_pagina(datos_imagen: bytes, tipo_mime: str, cliente: Client) -> Apunte:
    if not datos_imagen:
        raise ValueError("No se recibió una imagen para analizar.")

    respuesta = cliente.models.generate_content(
        model=MODELO,
        contents=[
            types.Part.from_bytes(data=datos_imagen, mime_type=tipo_mime),
            "Analizá esta página y prepará el apunte para estudiar.",
        ],
        config=types.GenerateContentConfig(
            system_instruction=INSTRUCCION_SISTEMA,
            response_mime_type="application/json",
            response_schema=Apunte,
            temperature=0.4,
        ),
    )

    if isinstance(respuesta.parsed, Apunte):
        return respuesta.parsed

    if isinstance(respuesta.text, str) and respuesta.text.strip():
        try:
            return Apunte.model_validate(json.loads(respuesta.text))
        except (json.JSONDecodeError, ValidationError) as error:
            raise RespuestaIncompleta(
                "Gemini leyó la página, pero el apunte no cumplió el formato "
                "esperado (por ejemplo, faltaban tarjetas o conceptos). Volvé a "
                "tocar «Analizar la página»."
            ) from error

    raise ImagenIlegible(
        "No se pudo entender bien la página. Probá tomar otra foto con más luz "
        "y enfocada en los apuntes."
    )


def calificar(apunte: Apunte, respuestas: dict[int, int]) -> tuple[int, int]:
    aciertos = sum(
        respuestas.get(indice) == pregunta.correcta
        for indice, pregunta in enumerate(apunte.examen)
    )
    return aciertos, len(apunte.examen)