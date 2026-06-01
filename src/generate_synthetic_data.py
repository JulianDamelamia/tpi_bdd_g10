import datetime as dt
import random

from pymongo import MongoClient, ReplaceOne

try:
    from src.config import MONGODB_DATABASE, MONGODB_URL
    from src.demographics import profile_for, party_weights, approval_weights
except ModuleNotFoundError:
    from config import MONGODB_DATABASE, MONGODB_URL
    from demographics import profile_for, party_weights, approval_weights


RANDOM_SEED = 20260527
SURVEY_COUNT = 10
METADATA_PREGUNTAS = {
    1:("A que espacio politico votaria si las elecciones fueran hoy?",
        "multiple_choice",
        "intencion_voto"
    ),
    2:(
        "Como evalua la gestion del gobierno nacional?",
        "multiple_choice",
        "imagen_gobierno",
    ),
    3:(
        "Cual deberia ser la principal prioridad de la agenda publica?",
        "multiple_choice",
        "prioridad_publica",
    ),
    4:(
        "Qué expectativa tiene sobre su economía a futuro?",
        "multiple_choice",
        "imagen_gobierno",
    ),
    5:(
        "Qué imagen tiene del candidato A?",
        "multiple_choice",
        "imagen_gobierno",
    ),
    6:(
        "Qué imagen tiene del candidato B?",
        "multiple_choice",
        "imagen_gobierno",
    ),
    7:(
        "Qué imagen tiene del candidato C?",
        "multiple_choice",
        "imagen_gobierno",
    ),
    8:(
        "Qué imagen tiene del candidato D?",
        "multiple_choice",
        "imagen_gobierno",
    ),
    9:(
        "Qué imagen tiene del candidato F?",
        "multiple_choice",
        "imagen_gobierno",
    ),
}
QUESTIONS_PER_SURVEY = len(METADATA_PREGUNTAS)
RESPONSES_PER_SURVEY = 10_000
TIME_DAYS = 1000

TOPICS = [
    "intencion_voto_presidencial",
    "imagen_gobierno",
    "economia_domestica",
    "seguridad",
    "educacion",
    "salud_publica",
    "obra_publica",
    "mineria",
]
SOURCES = ["web", "telefono", "presencial", "app"]
PARTIES = [
    "Frente Federal",
    "Movimiento Popular",
    "Union Republicana",
    "Alianza Verde",
    "Partido Vecinal",
]
APPROVAL = ["Muy buena", "Buena", "Regular", "Mala", "Muy mala"]
PRIORITIES = ["Inflacion", "Seguridad", "Empleo", "Educacion", "Salud"]


def option_texts_for(question_number: int) -> list[str]:
    if question_number == 1:
        return PARTIES
    if question_number == 3:
        return PRIORITIES
    return APPROVAL


def question_metadata(question_number: int, metadata_preguntas:dict) -> tuple[str, str, str]:
    return metadata_preguntas[question_number]


def build_survey_document(survey_number: int, created_base: dt.datetime) -> dict:
    topic = TOPICS[(survey_number - 1) % len(TOPICS)]
    survey_id = f"survey_{survey_number:04d}"
    questions = []

    for question_number in range(1, QUESTIONS_PER_SURVEY + 1):
        question_id = f"{survey_id}_q{question_number:02d}"
        question_text, question_type, category = question_metadata(question_number, METADATA_PREGUNTAS)
        questions.append(
            {
                "pregunta_id": question_id,
                "tipo": question_type,
                "texto": question_text,
                "categoria": category,
                "opciones": [
                    {
                        "option_id": f"{question_id}_opt{option_code:02d}",
                        "codigo": option_code,
                        "texto": option_text,
                    }
                    for option_code, option_text in enumerate(
                        option_texts_for(question_number),
                        start=1,
                    )
                ],
            }
        )

    return {
        "_id": survey_id,
        "titulo": f"Encuesta politica {survey_number:04d} - {topic}",
        "creator_id": f"org_{(survey_number % 40) + 1:03d}",
        "status": "active" if survey_number % 10 else "closed",
        "fecha_creacion": (created_base + dt.timedelta(hours=survey_number)).isoformat(),
        "tema": topic,
        "preguntas": questions,
    }


def build_response_documents(survey_number: int, valid_dates: list[dt.date]) -> list[dict]:
    survey_id = f"survey_{survey_number:04d}"
    responses = []
    numero_respuestas = int(random.gauss(RESPONSES_PER_SURVEY, RESPONSES_PER_SURVEY/7))
    print(f'Generando {numero_respuestas} respuestas sintéticas')
    for response_number in range(1, numero_respuestas + 1):
        response_id = f"resp_{survey_number:04d}_{response_number:03d}"
        respondent_id = f"person_{((survey_number * 17 + response_number) % 25000):05d}"
        submitted_date = random.choice(valid_dates)
        submitted_at = dt.datetime.combine(
            submitted_date,
            dt.time(random.randrange(8, 22), random.randrange(0, 60), random.randrange(0, 60)),
        )
        source = random.choice(SOURCES)
        profile = profile_for(respondent_id)
        answers = []

        for question_number in range(1, QUESTIONS_PER_SURVEY + 1):
            question_id = f"{survey_id}_q{question_number:02d}"
            n_opts = len(option_texts_for(question_number))
            if question_number == 1:
                weights = party_weights(profile["region"], profile["nse"])
                answer_code = random.choices(range(1, n_opts + 1), weights=weights)[0]
            elif question_number == 3:
                answer_code = random.randint(1, n_opts)
            else:
                weights = approval_weights(profile["nse"], submitted_date)
                answer_code = random.choices(range(1, n_opts + 1), weights=weights)[0]
            answers.append(
                {
                    "pregunta_id": question_id,
                    "opcion_id": f"{question_id}_opt{answer_code:02d}",
                    "valor": answer_code,
                    "texto": option_texts_for(question_number)[answer_code - 1],
                }
            )

        responses.append(
            {
                "_id": response_id,
                "encuesta_id": survey_id,
                "encuestado_id": respondent_id,
                "fecha": submitted_at.isoformat(),
                "fuente": source,
                "respuestas": answers,
            }
        )

    return responses


def generate() -> tuple[int, int]:
    random.seed(RANDOM_SEED)
    client = MongoClient(MONGODB_URL)
    db = client[MONGODB_DATABASE]
    created_base = dt.datetime(2026, 1, 1, 9, 0, 0)
    start_date = dt.date(2024, 1, 1)
    valid_dates = [start_date + dt.timedelta(days=offset) for offset in range(TIME_DAYS)]

    survey_operations = []
    response_operations = []

    respondent_ids = set()
    for survey_number in range(1, SURVEY_COUNT + 1):
        survey = build_survey_document(survey_number, created_base)
        survey_operations.append(ReplaceOne({"_id": survey["_id"]}, survey, upsert=True))

        for response in build_response_documents(survey_number, valid_dates):
            response_operations.append(ReplaceOne({"_id": response["_id"]}, response, upsert=True))
            respondent_ids.add(response["encuestado_id"])

    respondent_operations = [
        ReplaceOne({"_id": rid}, {"_id": rid, **profile_for(rid)}, upsert=True)
        for rid in sorted(respondent_ids)
    ]

    if survey_operations:
        db.surveys.bulk_write(survey_operations, ordered=False)
    if response_operations:
        db.responses.bulk_write(response_operations, ordered=False)
    if respondent_operations:
        db.respondents.bulk_write(respondent_operations, ordered=False)

    db.responses.create_index("encuesta_id")

    print(f"Loaded {len(survey_operations)} survey documents into MongoDB.")
    print(f"Loaded {len(response_operations)} response documents into MongoDB.")
    print(f"Loaded {len(respondent_operations)} respondent documents into MongoDB.")
    return len(survey_operations), len(response_operations)


if __name__ == "__main__":
    generate()
