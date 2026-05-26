import datetime

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String,ForeignKey, DateTime

from .base import Base
from .hechos import FactRespuesta
#Convención nomenclatura
# class PascalCaseSingular(Base):
#     __talbename__ = "snake_case_plural"
#     atributo_castellano:Tipo = definición

class DimEncuesta(Base):
    __tablename__ = "dim_encuesta"
    encuesta_key: Mapped[int] = mapped_column(primary_key=True)
   
    encuesta_id_origen: Mapped[int] = mapped_column(
            unique=True,
            nullable=False
        )
    titulo: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    preguntas: Mapped[list["DimPregunta"]] = relationship(
        back_populates="encuesta",
        cascade="all, delete-orphan"
    )

    respuestas: Mapped[list["FactRespuesta"]] = relationship(
        back_populates="encuesta"
    )

class DimPregunta(Base):
    __tablename__ = "dim_pregunta"

    pregunta_key: Mapped[int] = mapped_column(primary_key=True)

    pregunta_id_origen: Mapped[int] = mapped_column(
        unique=True,
        nullable=False
    )

    encuesta_key: Mapped[int] = mapped_column(
        ForeignKey("dim_encuesta.encuesta_key")
    )

    texto: Mapped[str] = mapped_column(String(500))

    label: Mapped[str] = mapped_column(String(100))
    
class DimFecha(Base):
    __tablename__ = "dim_fecha"

    fecha_key: Mapped[int] = mapped_column(
        primary_key=True
    )

    fecha: Mapped[datetime.datetime]

    dia: Mapped[int]
    mes: Mapped[int]
    anio: Mapped[int]

    nombre_mes: Mapped[str] = mapped_column(
        String(20)
    )

    nombre_dia: Mapped[str] = mapped_column(
        String(20)
    )

class DimOpcionRespuesta(Base):
    __tablename__ = "dim_opcion_respuesta"

    opcion_key: Mapped[int] = mapped_column(primary_key=True)

    pregunta_key: Mapped[int] = mapped_column(
        ForeignKey("dim_pregunta.pregunta_key")
    )

    valor_numerico: Mapped[int] = mapped_column()

    texto_respuesta: Mapped[str] = mapped_column(
        String(300)
    )