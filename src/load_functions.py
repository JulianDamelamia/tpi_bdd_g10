"""Carga las funciones SQL del Data Warehouse en Postgres.

Las funciones viven en sql/*.sql y NO las crea el ORM (Base.metadata.create_all)
ni el ETL: hay que ejecutarlas aparte. main.py llama a load_functions() al final
del pipeline para que `python main.py` deje la base lista para el dashboard.

También se puede correr suelto (reusa POSTGRES_URL de tu .env):

    python -m src.load_functions
"""
import pathlib

from sqlalchemy import create_engine, text

from src.config import POSTGRES_URL

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Orden no importa: cada archivo es un CREATE OR REPLACE FUNCTION independiente.
SQL_FILES = ("sql/segmentar_respuestas.sql", "sql/predecir_shares.sql")


def load_functions(engine=None) -> None:
    """Ejecuta cada sql/*.sql contra Postgres (idempotente: CREATE OR REPLACE).

    Usa text() + execute (mismo patrón que tests/test_funciones_sql.py): escapa
    los ``%`` literales de los archivos (porcentajes) y soporta ``$$ ... $$`` y
    varios statements por archivo (ej. el drop+create de predecir_shares.sql).
    """
    engine = engine or create_engine(POSTGRES_URL)
    for rel in SQL_FILES:
        sql = (ROOT / rel).read_text(encoding="utf-8")
        with engine.begin() as conn:
            conn.execute(text(sql))
        print(f"función cargada: {rel}")


if __name__ == "__main__":
    load_functions()
