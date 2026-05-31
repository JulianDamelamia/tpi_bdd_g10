from src.etl_mongo_to_postgres import run_etl
from src.load_functions import load_functions


def main() -> None:
    """Ejecución incremental del ETL: procesa nuevos datos sin borrar los existentes."""
    run_etl()
    load_functions()  # crea/actualiza las funciones SQL que consume el dashboard


if __name__ == "__main__":
    main()
