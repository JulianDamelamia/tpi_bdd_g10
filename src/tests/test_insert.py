from datetime import date

from db.conexion import SessionLocal

from modelos.dimensiones import (
    DimFecha,
    DimEncuesta
)

from modelos.hechos import FactRespuesta


session = SessionLocal()

fecha = DimFecha(
    fecha_key=20260520,
    fecha=date(2026, 5, 20),
    dia=20,
    mes=5,
    anio=2026
)

encuesta = DimEncuesta(
    encuesta_key=1,
    titulo="Encuesta presidencial"
)

fact = FactRespuesta(
    respuesta_key=1,
    nosql_id="mongo_123",
    encuesta_key=1,
    fecha_key=20260520,
    respuesta_numerica=2
)

session.add(fecha)
session.add(encuesta)
session.add(fact)
session.commit()

print("Insert OK")