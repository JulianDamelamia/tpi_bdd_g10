# TPI BDD — Demografía + Minería + Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar los ítems faltantes del TPI: agregar demografía del encuestado (fuente → ETL → estrella), arreglar la orquestación del cron (separar seed de ETL incremental), enriquecer las funciones dinámicas de segmentación/predicción y construir un dashboard BI de 4 elementos — todo con datos que muestran patrones reales.

**Architecture:** OLTP MongoDB Atlas (raw) → ETL Python → OLAP Postgres/Supabase (esquema estrella). Se agrega `dim_respondent` alimentada desde una nueva colección Mongo `respondents`. El generador asigna demografía determinística por `encuestado_id` (hash) e inyecta correlación región/NSE→voto para que la minería no dé planos. Cron pasa a ETL incremental; el reset full vive en un `seed.py` aparte.

**Tech Stack:** Python 3.11, PyMongo, SQLAlchemy 2.x, psycopg2, PostgreSQL 17 (Supabase), MongoDB Atlas, PL/pgSQL, Streamlit + Plotly (dashboard), pytest (tests).

**Working dir:** `/Users/tk/Documents/Personal/Lab/datascience-2026/ingenieria-software-unsam/tpi_bdd_g10`
**Intérprete:** reusar `/tmp/tpi_bdd_g10/.venv/bin/python` (las deps ya están; evita crear `.venv` pesada en iCloud). Alternativa: crear venv local y agregar `.venv/` a `.gitignore`.

---

## File Structure

**Crear:**
- `src/demographics.py` — perfilado determinístico del encuestado + pesos de correlación. Lógica pura, sin I/O. Testeable aislada.
- `seed.py` — reset completo de un solo uso (clean + generate + ETL). Reemplaza la responsabilidad de reset que hoy tiene `main.py`.
- `dashboard/app.py` — app Streamlit BI (4 elementos) sobre Postgres.
- `dashboard/requirements.txt` — deps del dashboard.
- `tests/test_demographics.py` — tests unitarios de la lógica pura.
- `tests/test_etl_transforms.py` — tests unitarios de las transformaciones (sin DB).
- `tests/test_funciones_sql.py` — tests de integración de las funciones PL/pgSQL (con DB).

**Modificar:**
- `src/models/dimensiones.py` — agregar `DimRespondent`.
- `src/models/hechos.py` — `FactSurveyResponse` gana FK + relationship a `dim_respondents`.
- `src/models/__init__.py` — exportar `DimRespondent`.
- `src/generate_synthetic_data.py` — usar demografía + correlación; escribir colección `respondents`.
- `src/etl_mongo_to_postgres.py` — cargar `dim_respondents`; agregar a auditoría.
- `main.py` — pasar a solo `run_etl()` (incremental).
- `.github/workflows/etl_schedule.yml` — aclarar que es ETL incremental.
- `sql/segmentar_respuestas.sql` — nuevas dimensiones region/nse/grupo_etario/genero.
- `sql/predecir_shares.sql` — filtros opcionales p_region / p_nse.
- `requirements.txt` — agregar `pytest`.

---

## Phase 0 — Persistir el trabajo (hacer YA)

### Task 1: Branch + commit del trabajo hecho y empujar a remoto

El repo vive en `Documents/.../tpi_bdd_g10` (iCloud: vigilar copias en conflicto `archivo 2.ext`). La persistencia durable es el remoto `origin`.

**Files:** `sql/segmentar_respuestas.sql`, `sql/predecir_shares.sql`, `sql/busquedas.sql`, este plan.

- [ ] **Step 1: Verificar que `.env` está ignorado**

Run: `git check-ignore .env && echo IGNORED`
Expected: imprime `.env` e `IGNORED`.

- [ ] **Step 2: Crear branch**

```bash
git checkout -b feat/mineria-demografia-dashboard
```

- [ ] **Step 3: Stagear solo lo intencional (revisar que NO aparezca `.env` ni archivos " 2")**

```bash
git add sql/ docs/superpowers/plans/
git status --porcelain
```

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: funciones dinamicas segmentacion/prediccion + busquedas + plan"
```

- [ ] **Step 5: Push (requiere acceso al remoto)**

Run: `git push -u origin feat/mineria-demografia-dashboard`
Expected: branch en GitHub. Si falla por permisos, parar y resolver `gh auth status` antes de seguir.

---

## Phase 1 — Demografía: lógica pura

### Task 2: Módulo `demographics.py` — perfil determinístico

**Files:** Create `src/demographics.py`; Test `tests/test_demographics.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_demographics.py
from src.demographics import profile_for, grupo_etario, party_weights, approval_weights, PARTIES

def test_profile_es_deterministico():
    assert profile_for("person_00018") == profile_for("person_00018")

def test_profile_tiene_campos_y_rangos():
    p = profile_for("person_01234")
    assert set(p) == {"respondent_id","edad","grupo_etario","region","nse","genero"}
    assert 16 <= p["edad"] <= 90
    assert p["region"] in {"AMBA","Centro","NOA","NEA","Cuyo","Patagonia"}
    assert p["nse"] in {"alto","medio","bajo"}
    assert p["genero"] in {"F","M","X"}

def test_grupo_etario_bordes():
    assert grupo_etario(16) == "16-29"
    assert grupo_etario(29) == "16-29"
    assert grupo_etario(30) == "30-44"
    assert grupo_etario(64) == "45-64"
    assert grupo_etario(65) == "65+"

def test_party_weights_largo_y_positivos():
    w = party_weights("AMBA","bajo")
    assert len(w) == len(PARTIES) == 5 and all(x > 0 for x in w)

def test_party_weights_correlacion():
    idx = PARTIES.index("Union Republicana")
    assert party_weights("Centro","alto")[idx] > party_weights("Centro","bajo")[idx]

def test_approval_weights_correlacion():
    assert approval_weights("alto")[0] > approval_weights("bajo")[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/tmp/tpi_bdd_g10/.venv/bin/python -m pip install -q pytest && /tmp/tpi_bdd_g10/.venv/bin/python -m pytest tests/test_demographics.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'src.demographics'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/demographics.py
"""Perfilado determinístico del encuestado + pesos de correlación.

La demografía se deriva por hash del respondent_id: la misma persona mantiene
siempre el mismo perfil entre encuestas sin persistir estado aleatorio. Los pesos
introducen correlación region/NSE -> respuesta para que segmentación y predicción
muestren patrones reales."""
import hashlib

REGIONS = ["AMBA", "Centro", "NOA", "NEA", "Cuyo", "Patagonia"]
NSE_LEVELS = ["alto", "medio", "bajo"]
PARTIES = ["Frente Federal", "Movimiento Popular", "Union Republicana",
           "Alianza Verde", "Partido Vecinal"]
APPROVAL = ["Muy buena", "Buena", "Regular", "Mala", "Muy mala"]


def grupo_etario(edad: int) -> str:
    if edad < 30:
        return "16-29"
    if edad < 45:
        return "30-44"
    if edad < 65:
        return "45-64"
    return "65+"


def profile_for(respondent_id: str) -> dict:
    h = hashlib.sha256(respondent_id.encode("utf-8")).digest()
    region = REGIONS[h[0] % len(REGIONS)]
    nse = NSE_LEVELS[h[1] % len(NSE_LEVELS)]
    g = h[2] % 100
    genero = "X" if g < 4 else ("F" if g % 2 == 0 else "M")
    edad = 16 + (int.from_bytes(h[3:5], "big") % 75)
    return {"respondent_id": respondent_id, "edad": edad,
            "grupo_etario": grupo_etario(edad), "region": region,
            "nse": nse, "genero": genero}


_REGION_BIAS = {
    "AMBA":      [1.6, 1.3, 0.7, 1.0, 0.6],
    "Centro":    [0.8, 0.9, 1.8, 1.1, 0.7],
    "NOA":       [1.7, 1.2, 0.6, 0.8, 1.0],
    "NEA":       [1.6, 1.3, 0.6, 0.7, 1.1],
    "Cuyo":      [0.9, 0.8, 1.6, 1.0, 0.9],
    "Patagonia": [1.0, 0.9, 1.1, 1.6, 0.8],
}
_NSE_BIAS = {
    "alto":  [0.7, 0.8, 1.8, 1.2, 0.6],
    "medio": [1.1, 1.1, 1.0, 1.0, 1.0],
    "bajo":  [1.7, 1.3, 0.6, 0.7, 1.2],
}
_APPROVAL_BY_NSE = {
    "alto":  [1.6, 1.5, 1.0, 0.7, 0.5],
    "medio": [1.0, 1.2, 1.4, 1.0, 0.8],
    "bajo":  [0.6, 0.8, 1.2, 1.5, 1.6],
}


def party_weights(region: str, nse: str) -> list[float]:
    rb, nb = _REGION_BIAS[region], _NSE_BIAS[nse]
    return [rb[i] * nb[i] for i in range(len(PARTIES))]


def approval_weights(nse: str) -> list[float]:
    return list(_APPROVAL_BY_NSE[nse])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/tmp/tpi_bdd_g10/.venv/bin/python -m pytest tests/test_demographics.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit** (agregar `pytest` a `requirements.txt` antes)

```bash
echo "pytest" >> requirements.txt
git add src/demographics.py tests/test_demographics.py requirements.txt
git commit -m "feat: modulo demographics con perfil deterministico y correlacion"
```

---

## Phase 2 — Modelo: `dim_respondent`

### Task 3: Agregar `DimRespondent` + FK en la fact

**Files:** Modify `src/models/dimensiones.py`, `src/models/hechos.py`, `src/models/__init__.py`

- [ ] **Step 1: Clase `DimRespondent` al final de `dimensiones.py`**

```python
class DimRespondent(Base):
    __tablename__ = "dim_respondents"

    respondent_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    edad: Mapped[int] = mapped_column(Integer, nullable=False)
    grupo_etario: Mapped[str] = mapped_column(String(15), nullable=False)
    region: Mapped[str] = mapped_column(String(30), nullable=False)
    nse: Mapped[str] = mapped_column(String(10), nullable=False)
    genero: Mapped[str] = mapped_column(String(5), nullable=False)

    responses: Mapped[list["FactSurveyResponse"]] = relationship(back_populates="respondent")
```

- [ ] **Step 2: FK + relationship en `hechos.py`**

Reemplazar `respondent_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)` por:

```python
    respondent_id: Mapped[str] = mapped_column(
        ForeignKey("dim_respondents.respondent_id"), nullable=False, index=True,
    )
```

Y en las relationships de `FactSurveyResponse` agregar:

```python
    respondent: Mapped["DimRespondent"] = relationship(back_populates="responses")
```

- [ ] **Step 3: Exportar en `__init__.py`**

Cambiar el import a `from .dimensiones import DimAnswerOption, DimQuestion, DimRespondent, DimSurvey, DimTime` y agregar `"DimRespondent",` a `__all__`.

- [ ] **Step 4: Verificar metadata**

Run: `/tmp/tpi_bdd_g10/.venv/bin/python -c "from src.models import Base, DimRespondent; print('dim_respondents' in Base.metadata.tables)"`
Expected: `True`.

- [ ] **Step 5: Commit**

```bash
git add src/models/
git commit -m "feat: dim_respondents + FK respondent_id en la fact"
```

---

## Phase 3 — Generador: demografía + correlación + colección `respondents`

### Task 4: Generar perfiles y respuestas correlacionadas

**Files:** Modify `src/generate_synthetic_data.py`; Test `tests/test_etl_transforms.py`

- [ ] **Step 1: Import**

Arriba de `generate_synthetic_data.py`:

```python
from src.demographics import profile_for, party_weights, approval_weights
```

(mantener el patrón `except ModuleNotFoundError: from demographics import ...` del archivo).

- [ ] **Step 2: Pesos por demografía en `build_response_documents`**

Reemplazar el bloque que arma `answers`:

```python
        profile = profile_for(respondent_id)
        answers = []
        for question_number in range(1, QUESTIONS_PER_SURVEY + 1):
            question_id = f"{survey_id}_q{question_number:02d}"
            n_opts = len(option_texts_for(question_number))
            if question_number == 1:
                weights = party_weights(profile["region"], profile["nse"])
                answer_code = random.choices(range(1, n_opts + 1), weights=weights)[0]
            elif question_number == 2:
                weights = approval_weights(profile["nse"])
                answer_code = random.choices(range(1, n_opts + 1), weights=weights)[0]
            else:
                answer_code = random.randint(1, n_opts)
            answers.append({
                "pregunta_id": question_id,
                "opcion_id": f"{question_id}_opt{answer_code:02d}",
                "valor": answer_code,
                "texto": option_texts_for(question_number)[answer_code - 1],
            })
```

- [ ] **Step 3: Escribir colección `respondents` en `generate()`**

Antes de los `bulk_write`:

```python
    respondent_ids = set()
    for survey_number in range(1, SURVEY_COUNT + 1):
        for response_number in range(1, RESPONSES_PER_SURVEY + 1):
            respondent_ids.add(f"person_{((survey_number * 17 + response_number) % 25000):05d}")
    respondent_operations = [
        ReplaceOne({"_id": rid}, {"_id": rid, **profile_for(rid)}, upsert=True)
        for rid in sorted(respondent_ids)
    ]
    if respondent_operations:
        db.respondents.bulk_write(respondent_operations, ordered=False)
```

- [ ] **Step 4: Test de humo**

```python
# tests/test_etl_transforms.py
import datetime as dt
from src.generate_synthetic_data import build_response_documents

def test_build_response_documents_tiene_3_respuestas():
    import random; random.seed(1)
    docs = build_response_documents(1, [dt.date(2024, 1, 1)])
    assert len(docs) == 4
    assert all(len(d["respuestas"]) == 3 for d in docs)
    assert all("opcion_id" in a for d in docs for a in d["respuestas"])
```

- [ ] **Step 5: Run test**

Run: `/tmp/tpi_bdd_g10/.venv/bin/python -m pytest tests/test_etl_transforms.py -v -k build_response`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/generate_synthetic_data.py tests/test_etl_transforms.py
git commit -m "feat: generador con demografia correlacionada + coleccion respondents"
```

---

## Phase 4 — ETL: cargar `dim_respondents`

### Task 5: Transformación + carga

**Files:** Modify `src/etl_mongo_to_postgres.py`; Test `tests/test_etl_transforms.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_etl_transforms.py  (agregar)
from src.etl_mongo_to_postgres import build_respondent_rows

def test_build_respondent_rows_mapea_campos():
    docs = [{"_id": "person_00001", "respondent_id": "person_00001", "edad": 40,
             "grupo_etario": "30-44", "region": "AMBA", "nse": "alto", "genero": "F"}]
    assert build_respondent_rows(docs) == [{"respondent_id": "person_00001", "edad": 40,
        "grupo_etario": "30-44", "region": "AMBA", "nse": "alto", "genero": "F"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/tmp/tpi_bdd_g10/.venv/bin/python -m pytest tests/test_etl_transforms.py -v -k respondent_rows`
Expected: FAIL con `ImportError: cannot import name 'build_respondent_rows'`.

- [ ] **Step 3: Implementar**

En `src/etl_mongo_to_postgres.py`: (a) agregar `DimRespondent` a ambos bloques de import de modelos; (b) agregar `"dim_respondents"` a `TABLES_TO_AUDIT`; (c) funciones:

```python
def build_respondent_rows(respondent_docs: list[dict]) -> list[dict]:
    return [{
        "respondent_id": doc.get("respondent_id", doc["_id"]),
        "edad": int(doc["edad"]), "grupo_etario": doc["grupo_etario"],
        "region": doc["region"], "nse": doc["nse"], "genero": doc["genero"],
    } for doc in respondent_docs]


def upsert_respondent_rows(session: Session, rows: list[dict], table_counts: Counter) -> None:
    if not rows:
        return
    stmt = insert(DimRespondent).values(rows)
    result = session.execute(stmt.on_conflict_do_update(
        index_elements=["respondent_id"],
        set_={"edad": stmt.excluded.edad, "grupo_etario": stmt.excluded.grupo_etario,
              "region": stmt.excluded.region, "nse": stmt.excluded.nse,
              "genero": stmt.excluded.genero}))
    table_counts["dim_respondents"] += result.rowcount or 0
```

(d) En `run_etl`, después de `Base.metadata.create_all(engine)` y antes del loop de batches (la fact tiene FK a esta dim → debe existir antes):

```python
    with Session(engine) as session:
        upsert_respondent_rows(session, build_respondent_rows(list(mongo_db.respondents.find({}))), table_counts)
        session.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/tmp/tpi_bdd_g10/.venv/bin/python -m pytest tests/test_etl_transforms.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/etl_mongo_to_postgres.py tests/test_etl_transforms.py
git commit -m "feat: ETL carga dim_respondents desde coleccion respondents"
```

---

## Phase 5 — Orquestación: seed vs ETL incremental

### Task 6: `seed.py` + `main.py` solo ETL

**Files:** Create `seed.py`; Modify `main.py`, `.github/workflows/etl_schedule.yml`

- [ ] **Step 1: `seed.py`**

```python
# seed.py
"""Reset completo de un solo uso: limpia Mongo y Postgres, regenera datos
sinteticos y corre el ETL. NO usar en el cron: destruye todo."""
from pymongo import MongoClient
from sqlalchemy import create_engine

from src.config import MONGODB_DATABASE, MONGODB_URL, POSTGRES_URL
from src.generate_synthetic_data import generate
from src.etl_mongo_to_postgres import run_etl
from src.models import Base


def clean_mongo() -> None:
    db = MongoClient(MONGODB_URL)[MONGODB_DATABASE]
    db.surveys.drop(); db.responses.drop(); db.respondents.drop()
    print(f"MongoDB cleaned: {MONGODB_DATABASE}.surveys/responses/respondents")


def clean_postgres() -> None:
    engine = create_engine(POSTGRES_URL)
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    print("Postgres cleaned and tables recreated.")


def main() -> None:
    clean_mongo(); clean_postgres(); generate(); run_etl()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Reescribir `main.py`**

```python
# main.py
"""Punto de entrada del ETL diario (incremental). Lee respuestas nuevas de
Mongo y las carga en Postgres idempotentemente. Reset de demo: usar seed.py."""
from src.etl_mongo_to_postgres import run_etl


def main() -> None:
    run_etl()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Workflow**

En `.github/workflows/etl_schedule.yml` cambiar `name: ETL encuestas` por `name: ETL encuestas (incremental diario)`.

- [ ] **Step 4: Verificar imports**

Run: `/tmp/tpi_bdd_g10/.venv/bin/python -c "import main, seed; print('imports OK')"`
Expected: `imports OK`.

- [ ] **Step 5: Commit**

```bash
git add main.py seed.py .github/workflows/etl_schedule.yml
git commit -m "refactor: separar seed (reset) de main (ETL incremental)"
```

---

## Phase 6 — Re-seed end-to-end

### Task 7: Correr seed contra DBs reales y validar

**Files:** ninguno (ejecución). Requiere `.env` (ambiente=TEST).

- [ ] **Step 1: Seed**

Run: `/tmp/tpi_bdd_g10/.venv/bin/python seed.py`
Expected: limpieza Mongo, recreación PG, conteos (surveys 1000, responses 4000, respondents únicos ~3900, fact 12000).

- [ ] **Step 2: Validar dim + correlación**

```bash
/tmp/tpi_bdd_g10/.venv/bin/python - <<'PY'
from src.config import POSTGRES_URL
from sqlalchemy import create_engine, text
with create_engine(POSTGRES_URL).connect() as c:
    print("dim_respondents:", c.execute(text("select count(*) from dim_respondents")).scalar())
    print("facts huerfanas (0):", c.execute(text("""select count(*) from fact_survey_responses f
        left join dim_respondents r on f.respondent_id=r.respondent_id where r.respondent_id is null""")).scalar())
    print("voto por region:")
    for row in c.execute(text("""select r.region, o.option_text, count(*) n
        from fact_survey_responses f
        join dim_questions q on f.question_id=q.question_id
        join dim_answer_options o on f.option_id=o.option_id
        join dim_respondents r on f.respondent_id=r.respondent_id
        where q.category='intencion_voto' group by 1,2 order by 1,3 desc""")):
        print("  ", tuple(row))
PY
```
Expected: dim_respondents > 0; huérfanas = 0; partido dominante distinto por región (correlación visible).

---

## Phase 7 — Funciones enriquecidas

### Task 8: Segmentación por dimensiones demográficas

**Files:** Modify `sql/segmentar_respuestas.sql`; Test `tests/test_funciones_sql.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_funciones_sql.py
import os, pathlib, pytest
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.skipif(not pathlib.Path(__file__).resolve().parent.parent.joinpath(".env").exists()
                                and not os.getenv("host"), reason="sin credenciales de DB")
ROOT = pathlib.Path(__file__).resolve().parent.parent

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
        rows = c.execute(text("select * from segmentar_respuestas('intencion_voto','2024-01-01','2026-12-31','region')")).all()
    assert {r[0] for r in rows} <= {"AMBA","Centro","NOA","NEA","Cuyo","Patagonia"}
    assert abs(sum(r[2] for r in rows) - 100) < 1.0

def test_segmentar_por_nse(eng):
    with eng.connect() as c:
        rows = c.execute(text("select * from segmentar_respuestas('imagen_gobierno','2024-01-01','2026-12-31','nse')")).all()
    assert {r[0] for r in rows} <= {"alto","medio","bajo"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/tmp/tpi_bdd_g10/.venv/bin/python -m pytest tests/test_funciones_sql.py -v -k region`
Expected: FAIL — la dimensión `'region'` lanza `la dimension region no vale`.

- [ ] **Step 3: Ampliar la función**

En `sql/segmentar_respuestas.sql`, cambiar la validación por:

```sql
    if p_dimension not in ('opcion','fuente','mes','region','nse','grupo_etario','genero') then
        raise exception 'la dimension % no vale, usa: opcion/fuente/mes/region/nse/grupo_etario/genero', p_dimension;
    end if;
```

y reemplazar el CTE `base` (CASE ampliado + join a `dim_respondents`):

```sql
    with base as (
        select
            (case p_dimension
                when 'opcion'       then o.option_text
                when 'fuente'       then f.source
                when 'mes'          then t.month
                when 'region'       then r.region
                when 'nse'          then r.nse
                when 'grupo_etario' then r.grupo_etario
                when 'genero'       then r.genero
            end)::text as segmento
        from fact_survey_responses f
        join dim_questions      q on f.question_id   = q.question_id
        join dim_time           t on f.date_key      = t.date_key
        join dim_respondents    r on f.respondent_id = r.respondent_id
        left join dim_answer_options o on f.option_id = o.option_id
        where q.category = p_categoria
          and t.full_date between p_fecha_desde and p_fecha_hasta
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/tmp/tpi_bdd_g10/.venv/bin/python -m pytest tests/test_funciones_sql.py -v -k "region or nse"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sql/segmentar_respuestas.sql tests/test_funciones_sql.py
git commit -m "feat: segmentacion por region/nse/grupo_etario/genero"
```

### Task 9: Predicción con filtros demográficos

**Files:** Modify `sql/predecir_shares.sql`; Test `tests/test_funciones_sql.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_funciones_sql.py  (agregar)
def test_predecir_filtra_por_region(eng):
    with eng.connect() as c:
        rows = c.execute(text("select * from predecir_shares('intencion_voto','2026-09-26',0.0,5.0,'AMBA',null)")).all()
    assert len(rows) == 5
    assert abs(sum(r[3] for r in rows) - 100) < 1.0

def test_predecir_region_cambia_resultado(eng):
    with eng.connect() as c:
        amba = {r[0]: r[3] for r in c.execute(text("select * from predecir_shares('intencion_voto','2026-09-26',0.0,5.0,'AMBA',null)")).all()}
        cuyo = {r[0]: r[3] for r in c.execute(text("select * from predecir_shares('intencion_voto','2026-09-26',0.0,5.0,'Cuyo',null)")).all()}
    assert amba != cuyo
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/tmp/tpi_bdd_g10/.venv/bin/python -m pytest tests/test_funciones_sql.py -v -k predecir`
Expected: FAIL — la función tiene 4 params, no acepta `p_region`.

- [ ] **Step 3: Agregar filtros opcionales**

En `sql/predecir_shares.sql`, cambiar la firma:

```sql
create or replace function predecir_shares(
    p_categoria   text,
    p_fecha_corte date,
    p_lambda      numeric default 0.0,
    p_alpha0      numeric default 5.0,
    p_region      text default null,
    p_nse         text default null
)
```

y el CTE `obs` (join + filtros NULL-safe):

```sql
    obs as (
        select o.option_text as opcion,
               exp( -p_lambda * (p_fecha_corte - t.full_date) ) as w
        from fact_survey_responses f
        join dim_questions      q on f.question_id   = q.question_id
        join dim_answer_options o on f.option_id     = o.option_id
        join dim_time           t on f.date_key      = t.date_key
        join dim_respondents    r on f.respondent_id = r.respondent_id
        where q.category = p_categoria
          and t.full_date <= p_fecha_corte
          and (p_region is null or r.region = p_region)
          and (p_nse    is null or r.nse    = p_nse)
    ),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/tmp/tpi_bdd_g10/.venv/bin/python -m pytest tests/test_funciones_sql.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sql/predecir_shares.sql tests/test_funciones_sql.py
git commit -m "feat: prediccion con filtros opcionales por region/nse"
```

---

## Phase 8 — Dashboard BI (4 elementos)

### Task 10: App Streamlit

**Files:** Create `dashboard/app.py`, `dashboard/requirements.txt`

- [ ] **Step 1: `dashboard/requirements.txt`**

```text
streamlit
pandas
plotly
sqlalchemy
psycopg2-binary
python-dotenv
```

- [ ] **Step 2: `dashboard/app.py`**

```python
# dashboard/app.py
"""Dashboard BI — consultora Inteligencia Colectiva. 4 elementos."""
import sys, pathlib
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.config import POSTGRES_URL

st.set_page_config(page_title="Inteligencia Colectiva — BI", layout="wide")
engine = create_engine(POSTGRES_URL)

@st.cache_data(ttl=300)
def q(sql: str, params: dict | None = None) -> pd.DataFrame:
    with engine.connect() as c:
        return pd.read_sql(text(sql), c, params=params or {})

st.title("Inteligencia Colectiva — Tablero de Opinión Pública")

st.subheader("1 · Intención de voto — predicción bayesiana")
pred = q("select * from predecir_shares('intencion_voto', :c, 0.0, 5.0)", {"c": "2026-09-26"})
fig1 = go.Figure()
fig1.add_bar(x=pred["opcion"], y=pred["share_pred"],
             error_y=dict(type="data", array=pred["ic_alto"] - pred["share_pred"],
                          arrayminus=pred["share_pred"] - pred["ic_bajo"]))
fig1.update_layout(yaxis_title="share %")
st.plotly_chart(fig1, use_container_width=True)

st.subheader("2 · Segmentación por región")
seg = q("select * from segmentar_respuestas('intencion_voto','2024-01-01','2026-12-31','region')")
st.plotly_chart(px.pie(seg, names="segmento", values="cantidad"), use_container_width=True)

st.subheader("3 · Evolución mensual de imagen de gobierno")
serie = q("""select t.year, t.month_number, o.option_text, count(*) n
    from fact_survey_responses f
    join dim_questions q on f.question_id=q.question_id
    join dim_answer_options o on f.option_id=o.option_id
    join dim_time t on f.date_key=t.date_key
    where q.category='imagen_gobierno' group by 1,2,3 order by 1,2""")
serie["periodo"] = serie["year"].astype(str) + "-" + serie["month_number"].astype(str).str.zfill(2)
st.plotly_chart(px.line(serie, x="periodo", y="n", color="option_text"), use_container_width=True)

st.subheader("4 · Explorador de predicción (descuento por recencia)")
c1, c2 = st.columns(2)
lam = c1.slider("λ (olvido por día)", 0.0, 0.05, 0.0, 0.005)
region = c2.selectbox("Región", ["(todas)","AMBA","Centro","NOA","NEA","Cuyo","Patagonia"])
rparam = None if region == "(todas)" else region
st.dataframe(q("select * from predecir_shares('intencion_voto', :c, :l, 5.0, :r, null)",
               {"c": "2026-09-26", "l": lam, "r": rparam}), use_container_width=True)
```

- [ ] **Step 3: Smoke test de queries (no interactivo)**

```bash
/tmp/tpi_bdd_g10/.venv/bin/python -m pip install -q -r dashboard/requirements.txt
/tmp/tpi_bdd_g10/.venv/bin/python - <<'PY'
from sqlalchemy import create_engine, text
from src.config import POSTGRES_URL
with create_engine(POSTGRES_URL).connect() as c:
    for sql in ["select * from predecir_shares('intencion_voto','2026-09-26',0.0,5.0)",
                "select * from segmentar_respuestas('intencion_voto','2024-01-01','2026-12-31','region')"]:
        assert len(c.execute(text(sql)).all()) > 0
print("dashboard queries OK")
PY
```
Expected: `dashboard queries OK`.

- [ ] **Step 4: Arrancar local (verificación manual)**

Run: `/tmp/tpi_bdd_g10/.venv/bin/python -m streamlit run dashboard/app.py`
Expected: levanta sin errores, 4 elementos renderizan. Cerrar tras verificar.

- [ ] **Step 5: Commit**

```bash
git add dashboard/
git commit -m "feat: dashboard BI streamlit con 4 elementos sobre supabase"
```

---

## Phase 9 — Documento + sandbox (no-código)

> Prosa/manual, sin TDD. Checklist para cerrar la monografía y los ejercicios individuales.

### Task 11: Redactar secciones ancladas en lo implementado
- [ ] **Diseño DW** — esquema estrella: grano fact `(response_id, question_id)`; dims surveys/questions/answer_options/time/respondents; auditoría `etl_process_executions`; diagrama.
- [ ] **Arquitectura/Infra** — diagrama Mongo Atlas (OLTP) → ETL (GitHub Actions) → Postgres Supabase (OLAP) → Streamlit (BI). Nube = nota 10.
- [ ] **CRUD con ETL** — upsert dims (`on_conflict_do_update`), insert idempotente facts (`on_conflict_do_nothing`), auditoría; seed vs ETL incremental.
- [ ] **Búsquedas 1/2 claves** — `sql/busquedas.sql` con salida.
- [ ] **Minería segmentación** — `segmentar_respuestas` por región/NSE con salida (patrones), explicar uso.
- [ ] **Minería predicción** — modelo Dirichlet-Multinomial descontado (prior + evidencia pesada por recencia → media posterior + IC), salida λ=0 vs λ>0 y con filtro región.
- [ ] **Motores SQL/NoSQL (TODOs)** — proveedor (MongoDB Inc. / Supabase Inc.), licencia, descarga (Atlas/Supabase free; local: Mongo Community + Postgres), organización.
- [ ] **Seguridad** — contingencia (backups), control de acceso (roles, `.env` fuera del repo, rotar credenciales), concientización.
- [ ] **Escenario** — la promesa de segmentar por edad/NSE/región ahora SÍ existe → coherente.

### Task 12: Sandbox para ejercicios individuales
- [ ] **SQL** — SQL editor de Supabase + 2-3 queries ejemplo (join, agregación, llamada a función).
- [ ] **NoSQL** — Atlas / `mongosh` + 2-3 queries (`find` filtro, `aggregate $group`, proyección) sobre surveys/responses/respondents.

### Task 13: Higiene de seguridad (credenciales)
- [ ] Las credenciales de Supabase y Atlas se compartieron en texto plano durante el desarrollo. **Rotar** ambas al terminar el TP y cargarlas como GitHub Secrets.

---

## Self-Review (cobertura vs consigna)

| Requisito | Task |
|---|---|
| Diseño DW (estrella, infra) | 11 |
| CRUD con ETL + explicación | 5, 6, 11 |
| Búsqueda 1 y 2 claves | 11 (sql hecho) |
| Minería segmentación | 8, 11 |
| Minería predicción | 9, 11 |
| Dashboard ≥4 elementos | 10 |
| Implementación nube (10) | 6, 10 |
| Sandbox SQL + NoSQL | 12 |
| Motores/licencias/descarga | 11 |
| Seguridad | 11, 13 |

Sin placeholders de código: tasks 2-10 traen código completo + comandos con salida esperada. Tasks 11-13 son entregables de prosa/manual.

**Orden obligado:** Task 1 (push) primero para no perder trabajo. Task 7 (re-seed) ANTES de 8-10 (funciones y dashboard dependen de `dim_respondents` poblada + correlación).
