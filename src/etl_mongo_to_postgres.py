import datetime as dt
import uuid
from collections import Counter
from decimal import Decimal

from pymongo import MongoClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

try:
    from src.config import ENVIRONMENT, MONGODB_DATABASE, MONGODB_URL, POSTGRES_URL
    from src.models import (
        Base,
        DimAnswerOption,
        DimQuestion,
        DimSurvey,
        DimTime,
        EtlProcessExecution,
        FactSurveyResponse,
    )
except ModuleNotFoundError:
    from config import ENVIRONMENT, MONGODB_DATABASE, MONGODB_URL, POSTGRES_URL
    from models import (
        Base,
        DimAnswerOption,
        DimQuestion,
        DimSurvey,
        DimTime,
        EtlProcessExecution,
        FactSurveyResponse,
    )


TABLES_TO_AUDIT = (
    "dim_answer_options",
    "dim_questions",
    "dim_surveys",
    "dim_time",
    "fact_survey_responses",
)


def parse_datetime(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def to_date_key(value: dt.datetime) -> int:
    return int(value.strftime("%Y%m%d"))


def build_time_row(submitted_at: dt.datetime) -> dict:
    full_date = submitted_at.date()
    return {
        "date_key": to_date_key(submitted_at),
        "full_date": full_date,
        "day_of_week": full_date.strftime("%A"),
        "day": full_date.day,
        "month": full_date.strftime("%B"),
        "month_number": full_date.month,
        "year": full_date.year,
    }


def build_dimension_rows(survey_docs: list[dict], seen_keys: dict[str, set]) -> dict[str, list[dict]]:
    surveys = []
    questions = []
    options = []

    for survey_doc in survey_docs:
        survey_id = survey_doc["_id"]
        if survey_id not in seen_keys["dim_surveys"]:
            surveys.append(
                {
                    "survey_id": survey_id,
                    "title": survey_doc["titulo"],
                    "creator_id": survey_doc["creator_id"],
                    "status": survey_doc["status"],
                    "created_at": parse_datetime(survey_doc["fecha_creacion"]),
                    "topic": survey_doc["tema"],
                }
            )
            seen_keys["dim_surveys"].add(survey_id)

        for question in survey_doc.get("preguntas", []):
            question_id = question["pregunta_id"]
            if question_id in seen_keys["dim_questions"]:
                continue

            questions.append(
                {
                    "question_id": question_id,
                    "survey_id": survey_id,
                    "question_text": question["texto"],
                    "question_type": question["tipo"],
                    "category": question.get("categoria", "sin_categoria"),
                }
            )
            seen_keys["dim_questions"].add(question_id)

            for option in question.get("opciones", []):
                option_id = option["option_id"]
                if option_id in seen_keys["dim_answer_options"]:
                    continue

                options.append(
                    {
                        "option_id": option_id,
                        "question_id": question_id,
                        "option_code": int(option["codigo"]),
                        "option_text": option["texto"],
                    }
                )
                seen_keys["dim_answer_options"].add(option_id)

    return {
        "dim_surveys": surveys,
        "dim_questions": questions,
        "dim_answer_options": options,
    }


def upsert_dimension_rows(session: Session, rows_by_table: dict[str, list[dict]], table_counts: Counter) -> None:
    survey_rows = rows_by_table["dim_surveys"]
    if survey_rows:
        stmt = insert(DimSurvey).values(survey_rows)
        result = session.execute(
            stmt.on_conflict_do_update(
                index_elements=["survey_id"],
                set_={
                    "title": stmt.excluded.title,
                    "creator_id": stmt.excluded.creator_id,
                    "status": stmt.excluded.status,
                    "created_at": stmt.excluded.created_at,
                    "topic": stmt.excluded.topic,
                },
            )
        )
        table_counts["dim_surveys"] += result.rowcount or 0

    question_rows = rows_by_table["dim_questions"]
    if question_rows:
        stmt = insert(DimQuestion).values(question_rows)
        result = session.execute(
            stmt.on_conflict_do_update(
                index_elements=["question_id"],
                set_={
                    "survey_id": stmt.excluded.survey_id,
                    "question_text": stmt.excluded.question_text,
                    "question_type": stmt.excluded.question_type,
                    "category": stmt.excluded.category,
                },
            )
        )
        table_counts["dim_questions"] += result.rowcount or 0

    option_rows = rows_by_table["dim_answer_options"]
    if option_rows:
        stmt = insert(DimAnswerOption).values(option_rows)
        result = session.execute(
            stmt.on_conflict_do_update(
                index_elements=["option_id"],
                set_={
                    "question_id": stmt.excluded.question_id,
                    "option_code": stmt.excluded.option_code,
                    "option_text": stmt.excluded.option_text,
                },
            )
        )
        table_counts["dim_answer_options"] += result.rowcount or 0


def insert_time_rows(session: Session, time_rows_by_key: dict[int, dict], table_counts: Counter) -> None:
    time_rows = list(time_rows_by_key.values())
    if not time_rows:
        return

    stmt = insert(DimTime).values(time_rows)
    result = session.execute(stmt.on_conflict_do_nothing(index_elements=["date_key"]))
    table_counts["dim_time"] += result.rowcount or 0


def build_fact_rows(response_docs: list[dict], time_rows_by_key: dict[int, dict]) -> tuple[list[dict], dt.datetime | None, dt.datetime | None]:
    fact_rows = []
    process_from = None
    process_to = None

    for response_doc in response_docs:
        submitted_at = parse_datetime(response_doc["fecha"])
        process_from = submitted_at if process_from is None else min(process_from, submitted_at)
        process_to = submitted_at if process_to is None else max(process_to, submitted_at)
        time_rows_by_key.setdefault(to_date_key(submitted_at), build_time_row(submitted_at))

        for answer in response_doc.get("respuestas", []):
            value = answer.get("valor")
            numeric_value = Decimal(str(value)) if isinstance(value, (int, float)) else None
            fact_rows.append(
                {
                    "response_id": response_doc["_id"],
                    "survey_id": response_doc["encuesta_id"],
                    "question_id": answer["pregunta_id"],
                    "option_id": answer.get("opcion_id"),
                    "respondent_id": response_doc["encuestado_id"],
                    "answer_text": answer.get("texto") or str(value),
                    "answer_numeric": numeric_value,
                    "date_key": to_date_key(submitted_at),
                    "source": response_doc["fuente"],
                    "submitted_at": submitted_at,
                }
            )

    return fact_rows, process_from, process_to


def insert_fact_rows(session: Session, fact_rows: list[dict], table_counts: Counter) -> int:
    if not fact_rows:
        return 0

    stmt = insert(FactSurveyResponse).values(fact_rows)
    result = session.execute(
        stmt.on_conflict_do_nothing(
            constraint="uq_fact_response_question",
        )
    )
    inserted_rows = result.rowcount or 0
    table_counts["fact_survey_responses"] += inserted_rows
    return inserted_rows


def register_process_executions(
    session: Session,
    *,
    process_id: str,
    table_counts: Counter,
    process_from: dt.datetime | None,
    process_to: dt.datetime | None,
    started_at: dt.datetime,
    finished_at: dt.datetime,
    status: str,
) -> None:
    for table_name in TABLES_TO_AUDIT:
        session.add(
            EtlProcessExecution(
                process_id=process_id,
                table_name=table_name,
                process_from=process_from,
                process_to=process_to,
                started_at=started_at,
                finished_at=finished_at,
                environment=ENVIRONMENT,
                status=status,
                records_loaded=table_counts[table_name],
            )
        )


def run_etl(batch_size: int = 1000) -> None:
    process_id = str(uuid.uuid4())
    started_at = dt.datetime.now(dt.timezone.utc)
    process_from: dt.datetime | None = None
    process_to: dt.datetime | None = None
    table_counts: Counter = Counter()
    seen_keys = {table_name: set() for table_name in TABLES_TO_AUDIT}
    mongo_client = MongoClient(MONGODB_URL)
    mongo_db = mongo_client[MONGODB_DATABASE]
    engine = create_engine(POSTGRES_URL)
    Base.metadata.create_all(engine)

    processed_docs = 0
    inserted_facts = 0

    with Session(engine) as session:
        last_response_id = None
        while True:
            query = {}
            if last_response_id is not None:
                query = {"_id": {"$gt": last_response_id}}

            response_docs = list(
                mongo_db.responses.find(query).sort("_id", 1).limit(batch_size)
            )
            if not response_docs:
                break

            last_response_id = response_docs[-1]["_id"]
            survey_ids = sorted({response_doc["encuesta_id"] for response_doc in response_docs})
            survey_docs = list(mongo_db.surveys.find({"_id": {"$in": survey_ids}}))
            survey_docs_by_id = {survey_doc["_id"]: survey_doc for survey_doc in survey_docs}
            missing_survey_ids = set(survey_ids) - set(survey_docs_by_id)
            if missing_survey_ids:
                raise RuntimeError(f"Missing survey documents: {sorted(missing_survey_ids)}")

            rows_by_table = build_dimension_rows(survey_docs, seen_keys)
            upsert_dimension_rows(session, rows_by_table, table_counts)

            time_rows_by_key: dict[int, dict] = {}
            fact_rows, batch_from, batch_to = build_fact_rows(response_docs, time_rows_by_key)
            insert_time_rows(session, time_rows_by_key, table_counts)
            inserted_facts += insert_fact_rows(session, fact_rows, table_counts)
            session.commit()

            process_from = batch_from if process_from is None else min(process_from, batch_from)
            process_to = batch_to if process_to is None else max(process_to, batch_to)
            processed_docs += len(response_docs)

        register_process_executions(
            session,
            process_id=process_id,
            table_counts=table_counts,
            process_from=process_from,
            process_to=process_to,
            started_at=started_at,
            finished_at=dt.datetime.now(dt.timezone.utc),
            status="success",
        )
        session.commit()

    with Session(engine) as session:
        total_facts = session.scalar(select(func.count()).select_from(FactSurveyResponse))

    print(f"Processed Mongo response documents: {processed_docs}")
    print(f"Inserted fact rows in this run: {inserted_facts}")
    print(f"Total fact rows in Postgres: {total_facts}")
    print(f"ETL process id: {process_id}")


if __name__ == "__main__":
    run_etl()
