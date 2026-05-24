from db.base import Base
from db.conexion import engine

from modelos.dimensiones import *
from modelos.hechos import *

Base.metadata.create_all(engine)

print("Tablas creadas.")