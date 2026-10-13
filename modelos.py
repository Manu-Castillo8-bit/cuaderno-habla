from pydantic import BaseModel, Field, field_validator, model_validator


class Concepto(BaseModel):
    termino: str = Field(description="Término o concepto relevante que aparece en los apuntes del estudiante.")
    explicacion: str = Field(description="Explicación clara y breve del término, adecuada para un estudiante de bachillerato.")


class Tarjeta(BaseModel):
    pregunta: str = Field(description="Pregunta breve para repasar un contenido importante de los apuntes.")
    respuesta: str = Field(description="Respuesta correcta y concisa a la pregunta de repaso.")


class Pregunta(BaseModel):
    enunciado: str = Field(description="Enunciado claro de una pregunta de opción múltiple sobre el contenido de los apuntes.")
    opciones: list[str] = Field(description="Lista de opciones de respuesta para la pregunta, incluyendo la opción correcta.")
    correcta: int = Field(description="Índice, comenzando en cero, de la opción correcta dentro de la lista de opciones.")

    @field_validator("opciones")
    @classmethod
    def validar_opciones(cls, opciones: list[str]) -> list[str]:
        if len(opciones) != 4:
            raise ValueError(f"La pregunta debe tener exactamente cuatro opciones; se recibieron {len(opciones)}.")
        if len({opcion.casefold() for opcion in opciones}) != 4:
            raise ValueError("Las cuatro opciones deben ser distintas; hay opciones repetidas sin distinguir mayúsculas y minúsculas.")
        return opciones

    @model_validator(mode="after")
    def validar_indice_correcto(self) -> "Pregunta":
        if not 0 <= self.correcta < len(self.opciones):
            raise ValueError(
                f"El índice 'correcta' ({self.correcta}) no corresponde a ninguna opción; debe estar entre 0 y {len(self.opciones) - 1}."
            )
        return self


class Apunte(BaseModel):
    titulo: str = Field(description="Título breve que identifica el tema principal de la página del cuaderno.")
    materia: str = Field(description="Nombre de la materia escolar a la que corresponde el contenido.")
    resumen: str = Field(description="Resumen organizado de las ideas principales de la página, sin agregar información que no aparezca en ella.")
    conceptos: list[Concepto] = Field(description="Conceptos importantes identificados en la página, cada uno con su explicación.")
    tarjetas: list[Tarjeta] = Field(description="Tarjetas de pregunta y respuesta para ayudar a estudiar los contenidos de la página.")
    examen: list[Pregunta] = Field(description="Preguntas de opción múltiple para evaluar la comprensión de los contenidos de la página.")
    dificultad: int = Field(description="Valor entero que representa la dificultad general de los contenidos de la página.")

    @field_validator("dificultad")
    @classmethod
    def validar_dificultad(cls, dificultad: int) -> int:
        if not 1 <= dificultad <= 5:
            raise ValueError(f"La dificultad debe estar entre 1 y 5; se recibió {dificultad}.")
        return dificultad

    @model_validator(mode="after")
    def validar_contenido_minimo(self) -> "Apunte":
        faltantes = []
        for campo, nombre, minimo in (
            ("conceptos", "conceptos", 3),
            ("tarjetas", "tarjetas", 5),
            ("examen", "preguntas de examen", 3),
        ):
            cantidad = len(getattr(self, campo))
            if cantidad < minimo:
                faltantes.append(f"debe incluir al menos {minimo} {nombre}; se recibieron {cantidad}")
        if faltantes:
            raise ValueError("El apunte no cumple el contenido mínimo: " + "; ".join(faltantes) + ".")
        return self
