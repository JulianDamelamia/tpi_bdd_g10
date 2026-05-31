from src.etl_mongo_to_postgres import run_etl

def main() -> None:
    """Ejecución incremental del ETL: procesa nuevos datos sin borrar los existentes."""
    run_etl()

if __name__ == "__main__":
    main()
