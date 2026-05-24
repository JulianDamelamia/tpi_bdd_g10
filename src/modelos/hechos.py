import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, String, ForeignKey

from db.base import Base
class FactRespuesta(Base):
    __tablename__ = "fact_respuestas"

    respuesta_key: Mapped[int] = mapped_column(
        primary_key=True
    )

    nosql_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    encuesta_key: Mapped[int] = mapped_column(
        ForeignKey("dim_encuesta.encuesta_key")
    )

    pregunta_key: Mapped[int] = mapped_column(
        ForeignKey("dim_pregunta.pregunta_key")
    )

    opcion_key: Mapped[int | None] = mapped_column(
        ForeignKey("dim_opcion_respuesta.opcion_key")
    )

    fecha_key: Mapped[int] = mapped_column(
        ForeignKey("dim_fecha.fecha_key")
    )

    id_encuestado: Mapped[str] = mapped_column(
        String(30),
        index=True
    ) #hash telefono

    respuesta_numerica: Mapped[int | None]

    respuesta_texto: Mapped[str | None] = mapped_column(
        String(300)
    )

    fecha_respuesta: Mapped[datetime.datetime]