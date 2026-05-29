from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import POSTGRES_URL
from src.models import Base


engine = create_engine(POSTGRES_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)
