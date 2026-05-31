import os
import pathlib

import pytest
from sqlalchemy import create_engine, text

ROOT = pathlib.Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(
    not (ROOT / ".env").exists() and not os.getenv("host"),
    reason="sin credenciales de DB",
)


@pytest.fixture(scope="module")
def eng():
    from src.config import POSTGRES_URL
    e = create_engine(POSTGRES_URL)
    with e.begin() as c:
        c.execute(text((ROOT / "sql/segmentar_respuestas.sql").read_text()))
        c.execute(text((ROOT / "sql/predecir_shares.sql").read_text()))
    return e


def test_segmentar_por_region(eng):
    with eng.connect() as c:
        rows = c.execute(text(
            "select * from segmentar_respuestas('intencion_voto','2024-01-01','2026-12-31','region')"
        )).all()
    assert {r[0] for r in rows} <= {"AMBA", "Centro", "NOA", "NEA", "Cuyo", "Patagonia"}
    assert abs(sum(r[2] for r in rows) - 100) < 1.0


def test_segmentar_por_nse(eng):
    with eng.connect() as c:
        rows = c.execute(text(
            "select * from segmentar_respuestas('imagen_gobierno','2024-01-01','2026-12-31','nse')"
        )).all()
    assert {r[0] for r in rows} <= {"alto", "medio", "bajo"}


def test_predecir_filtra_por_region(eng):
    with eng.connect() as c:
        rows = c.execute(text(
            "select * from predecir_shares('intencion_voto','2026-09-26',0.0,5.0,'AMBA',null)"
        )).all()
    assert len(rows) == 5
    assert abs(sum(r[3] for r in rows) - 100) < 1.0


def test_predecir_region_cambia_resultado(eng):
    with eng.connect() as c:
        amba = {r[0]: r[3] for r in c.execute(text(
            "select * from predecir_shares('intencion_voto','2026-09-26',0.0,5.0,'AMBA',null)")).all()}
        cuyo = {r[0]: r[3] for r in c.execute(text(
            "select * from predecir_shares('intencion_voto','2026-09-26',0.0,5.0,'Cuyo',null)")).all()}
    assert amba != cuyo
