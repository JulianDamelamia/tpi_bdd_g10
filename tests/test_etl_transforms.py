import datetime as dt

from src.generate_synthetic_data import build_response_documents
from src.etl_mongo_to_postgres import build_respondent_rows


def test_build_response_documents_tiene_3_respuestas():
    import random
    random.seed(1)
    docs = build_response_documents(1, [dt.date(2024, 1, 1)])
    assert len(docs) == 4
    assert all(len(d["respuestas"]) == 3 for d in docs)
    assert all("opcion_id" in a for d in docs for a in d["respuestas"])


def test_build_respondent_rows_mapea_campos():
    docs = [{"_id": "person_00001", "respondent_id": "person_00001", "edad": 40,
             "grupo_etario": "30-44", "region": "AMBA", "nse": "alto", "genero": "F"}]
    assert build_respondent_rows(docs) == [{"respondent_id": "person_00001", "edad": 40,
        "grupo_etario": "30-44", "region": "AMBA", "nse": "alto", "genero": "F"}]
