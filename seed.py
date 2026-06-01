"""Reset completo de un solo uso: limpia Mongo y Postgres, regenera datos
sinteticos y corre el ETL. NO usar en el cron: destruye todo. El ETL diario
debe ser incremental (ver main.py)."""
from pymongo import MongoClient
from sqlalchemy import create_engine

from src.config import MONGODB_DATABASE, MONGODB_URL, POSTGRES_URL
from src.generate_synthetic_data import generate
from src.etl_mongo_to_postgres import run_etl
from src.models import Base


def clean_mongo() -> None:
    db = MongoClient(MONGODB_URL)[MONGODB_DATABASE]
    db.surveys.drop()
    db.responses.drop()
    db.respondents.drop()
    print(f"MongoDB cleaned: {MONGODB_DATABASE}.surveys/responses/respondents")


def clean_postgres() -> None:
    engine = create_engine(POSTGRES_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("Postgres cleaned and tables recreated.")


def main() -> None:
    clean_mongo()
    clean_postgres()
    generate()
    run_etl(batch_size=1000)


if __name__ == "__main__":
    main()
