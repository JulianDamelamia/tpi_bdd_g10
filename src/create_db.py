from src.modelos.base import Base
from modelos.dimensiones import *
from modelos.hechos import *
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL
from sqlalchemy import create_engine

engine = create_engine(
    DATABASE_URL['postgres'],
    echo=True
)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)
