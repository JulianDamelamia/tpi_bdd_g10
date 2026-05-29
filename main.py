from pymongo import MongoClient
from sqlalchemy import create_engine
from src.config import MONGODB_DATABASE, MONGODB_URL, POSTGRES_URL
from src.generate_synthetic_data import generate
from src.etl_mongo_to_postgres import run_etl
from src.models import Base


def clean_mongo() -> None:
    client = MongoClient(MONGODB_URL)
    db = client[MONGODB_DATABASE]
    db.surveys.drop()
    db.responses.drop()
    print(f"MongoDB cleaned: {MONGODB_DATABASE}.surveys and {MONGODB_DATABASE}.responses")


def clean_postgres() -> None:
    engine = create_engine(POSTGRES_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("Postgres cleaned and tables recreated.")


def main() -> None:
    clean_mongo()
    clean_postgres()
    generate()
    run_etl()

if __name__ == "__main__":
    main()
