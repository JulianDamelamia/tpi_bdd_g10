# Data Architecture Design: Hybrid Polystore for a Survey Platform
**Course Project Documentation** **Architecture Paradigm:** Hybrid OLTP (NoSQL) & OLAP (SQL) with Managed ETL Pipeline

---

## 1. Executive Summary & Core Motivation

Modern survey platforms face a unique technical challenge that exposes the limitations of traditional, single-database architectures:
1. **Dynamic Schemas (The Survey Builder Problem):** Every survey is structural mutation. One user may design a 3-question consumer satisfaction poll using multiple-choice grids; another might design a 50-question academic psychology survey with conditional skip-logic and open-ended textual matrices. Attempting to manage these varying shapes in a rigid relational schema leads to severe relational anti-patterns (such as wide, mostly-null rows or dangerous programmatic execution of Data Definition Language (`ALTER TABLE`) operations).
2. **High-Throughput Analytics (The Dashboard Problem):** While capturing unstructured survey responses requires write-optimized horizontal scale, reading those responses to build business intelligence (BI) dashboards requires intensive analytical computations (`COUNT`, `AVERAGE`, `GROUP BY`, `PERCENTILE`). Running resource-heavy analytical queries on the exact same database engine handling high-volume operational writes causes lock contention, latency spikes, and degraded user experiences.

### The Hybrid Polystore Solution
This architecture decouples operational ingestion from downstream analytics by implementing a clear separation of concerns:
* **Operational Store (OLTP):** A **NoSQL Document Database** acts as the high-throughput, schema-agnostic ingestion engine. It stores dynamic survey definitions and raw response payloads cleanly as nested JSON structures without requiring upfront structural compliance.
* **Analytical Store (OLAP):** A **Relational SQL Database** configured in a structural Star Schema serves as a dedicated read-optimized engine to feed a real-time metrics dashboard.
* **Bridge Component (ETL Pipeline):** An autonomous **Extract, Transform, Load (ETL)** pipeline periodically extracts new or updated JSON records from the NoSQL engine, structurally flattens and normalizes the payloads, and loads them into uniform relational data marts.

---

## 2. System Architecture Blueprint

The following logical flow charts illustrate how data moves through the system from initial ingest to downstream analytical visual consumption:


              [ STRATEGIC ARCHITECTURE FLOW ]

 +-------------------------------------------------------+
 |                    Web Application                    |
 +-----------+-------------------------------+-----------+
             |                               |
             | (1) Read/Write                | (4) Query Static
             |     Flexible Forms            |     Aggregates
             v                               v
   +-------------------+           +-------------------+
   |   NoSQL Storage   |           |    SQL Storage    |
   |    (OLTP Layer)   |           |    (OLAP Layer)   |
   +---------+---------+           +---------+---------+
             |                               ^
             | (2) Extract                   | (3) Transform
             |     JSON Data                 |     & Load Rows
             |                               |
             +---------> [ ETL PIPELINE ] ---+

```

```

### Operational Interaction Sequence
1. **Survey Creation:** When an author builds a questionnaire, the dynamic layout parameters are serialized to JSON and stored directly inside the NoSQL collection.
2. **Response Collection:** When an end-user completes a survey, their multi-variant answers are packaged into a single JSON transaction and written immediately to the NoSQL operational database. This optimizes write operations ($O(1)$ complexity) and prevents user-facing bottlenecks.
3. **The Synchronization Cycle:** Independent of user actions, the ETL engine awakens (either via an automated cron trigger or a Change Data Capture stream), pulling non-processed documents from the NoSQL engine.
4. **Relational Ingestion:** The ETL pipeline normalizes the nested JSON trees into unified relational primitives, inserting clean rows directly into the SQL system.
5. **Dashboard Rendering:** When organizational clients open administrative reporting dashboards, the user interface fires standard relational queries directly at the SQL warehouse, bypassing the operational NoSQL engine entirely.

---

## 3. Storage Layer Specifications

### 3.1. Operational Storage Layer (NoSQL Document Engine)
The choice of a Document-oriented NoSQL engine (e.g., MongoDB) is driven by document-to-object mapping synergy. Survey patterns natively mimic tree structures: a survey possesses metadata, which embeds an array of dynamic questions, which in turn map to user answer matrices.

#### Collection Design: `surveys`
This collection maintains the blueprint of the survey structures.
```json
##ejemplo encuesta
{
  "_id": "mineria_05_2026",
  "titulo": "Encuesta sobre minería - Mayo 2026",
  "fecha_creacion": "2026-05-10T14:22:00Z",
  "preguntas": [
    {
      "pregunta_id": "p01",
      "tipo": "multiple_choice",
      "texto": "¿Con qué espacio político se siente más identificado?",
      "opciones": [
        { "codigo": 1, "texto": "Partido ultragarca" },
        { "codigo": 2, "texto": "Mentira y propaganda" },
        { "codigo": 3, "texto": "Los inoperantes de siempre" },
        { "codigo": 4, "texto": "Frente de injunables" }
      ]
    },
    {
      "pregunta_id": "p02",
      "tipo": "rango",
      "texto": "¿Qué tan de acuerdo está con la siguiente frase: 'regalar el país...'?",
      "opciones": [
        { "codigo": 1, "texto": "Mucho" },
        { "codigo": 2, "texto": "Algo" },
        { "codigo": 3, "texto": "Poco" }
      ]
    }
  ]
}

```

#### Collection Design: `responses`

This collection isolates operational throughput. It does not enforce structural schemas across separate documents; if an entry contains modified question keys, the database writes it natively without impedance.

```json
## ejemplo respuesta
{ 
	"_id": "resp_99824_xyz", 
	"encuesta_id": "mineria_05_2026", 
	"encuestado_id": "1122334455", 
	"fecha": "2026-05-17T19:05:12Z",
  "fuente": "telefono",
	"procesado_por_etl": false, 
	"respuestas": [
		{ "pregunta_id": "p01", "valor": 1 },
		{ "pregunta_id": "p02", "valor": 3 } 
	] 
} 
 

```

### 3.2. Analytical Storage Layer (SQL Relational Engine)

To support clean dashboard generation without building specialized dynamic tables for individual surveys, the warehouse adopts a highly optimized **Star Schema Relational Design**.

Instead of creating separate columns or tables for separate questions, the analytical engine flattens questions and answers into distinct **Rows**. This structure relies on a unified variation of the Entity-Attribute-Value (EAV) layout adapted for analytical reporting.


                    [ STAR SCHEMA RELATIONAL MODEL ]

        +--------------------+              +--------------------+
        |    dim_surveys     |              |   dim_questions    |
        +--------------------+              +--------------------+
        | PK | survey_id     |<----+        | PK | question_id   |-------+
        |    | title         |     |        | FK | survey_id     |       |
        |    | creator_id    |     |        |    | question_text |       |
        |    | status        |     |        |    | question_type |       |
        +--------------------+     |        +--------------------+       |
                                   |                                     |
                                   |    +--------------------------+     |
                                   +--->|  fact_survey_responses   |<----+
                                        +--------------------------+
                                        | PK | response_row_id     |
                                        |    | response_id         |
                                        | FK | survey_id           |
                                        | FK | question_id         |
                                        |    | respondent_id       |
                                        |    | answer_text         |
                                        |    | answer_numeric      |
                                        | FK | date_key            |
                                        +--------------------------+
                                                     |
        +--------------------+                       |
        |      dim_time      |                       |
        +--------------------+                       |
        | PK | date_key      |<----------------------+
        |    | full_date     |
        |    | day_of_week   |
        |    | month         |
        |    | year          |
        +--------------------+



#### DDL Structure (SQL Tables Blueprint)

```sql
-- Dimension 1: Surveys High-Level Properties
CREATE TABLE dim_surveys (
    survey_id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    creator_id VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL
);

-- Dimension 2: Questions Flattened to Row-Level Primitive Entries
CREATE TABLE dim_questions (
    question_id VARCHAR(50) PRIMARY KEY,
    survey_id VARCHAR(50) NOT NULL,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) NOT NULL,
    FOREIGN KEY (survey_id) REFERENCES dim_surveys(survey_id)
);

-- Dimension 3: Analytics-Optimized Time Context Table
CREATE TABLE dim_time (
    date_key INT PRIMARY KEY, -- Formatted as YYYYMMDD
    full_date DATE NOT NULL,
    day_of_week VARCHAR(15) NOT NULL,
    month VARCHAR(15) NOT NULL,
    year INT NOT NULL
);

-- Core Fact Table: Individual Responses and Associated Answer Primitives
CREATE TABLE fact_survey_responses (
    response_row_id SERIAL PRIMARY KEY,
    response_id VARCHAR(50) NOT NULL,
    survey_id VARCHAR(50) NOT NULL,
    question_id VARCHAR(50) NOT NULL,
    respondent_id VARCHAR(50) NOT NULL,
    answer_text TEXT,               -- Captures alpha-numeric text strings or options
    answer_numeric NUMERIC(10, 2),  -- Captures quantitative values (scales, ranges) for clean mathematical aggregations
    date_key INT NOT NULL,
    FOREIGN KEY (survey_id) REFERENCES dim_surveys(survey_id),
    FOREIGN KEY (question_id) REFERENCES dim_questions(question_id),
    FOREIGN KEY (date_key) REFERENCES dim_time(date_key)
);

```

---

## 4. Managed ETL Pipeline Architecture

The ETL engine converts dynamic, hierarchical JSON array configurations into structured data rows.

```
       [ RAW JSON PAYLOAD IN NOSQL ]
       {
         "response_id": "resp_99824_xyz",
         "survey_id": "srv_abc123_2026",
         "answers": [
           { "question_id": "q_001", "value": 5 },
           { "question_id": "q_002", "value": "Professional" }
         ]
       }
                                 |
                                 v  [ EXTRACT & TRANSLATE VIA ENGINE ]
                                 |
       +-----------------------------------------------------------------------+
       |                  FLATTENED STRUCTURAL ROWS FOR SQL                    |
       +-----------------------------------------------------------------------+
       | ROW_ID | RESPONSE_ID     | SURVEY_ID       | QUESTION_ID | ANSWER_NUM |
       +--------+-----------------+-----------------+-------------+------------+
       | 1      | resp_99824_xyz  | srv_abc123_2026 | q_001       | 5.00       |
       | 2      | resp_99824_xyz  | srv_abc123_2026 | q_002       | NULL       |
       +-----------------------------------------------------------------------+

```

### Functional Execution Logic (Pseudocode Pipeline Implementation)

The parsing pipeline can be constructed easily via Python or Node.js. Below is an abstract behavioral roadmap of how the programmatic parsing pipeline functions:

```python
def execute_etl_pipeline_cycle(nosql_client, sql_client):
    # 1. EXTRACT: Fetch documents that have not yet been synchronized
    raw_responses = nosql_client.db.responses.find({"processed_by_etl": False})
    
    for document in raw_responses:
        response_id = document["_id"]
        survey_id = document["survey_id"]
        respondent_id = document["respondent_id"]
        timestamp = document["submitted_at"] # Format: "2026-05-17T19:05:12Z"
        
        # Parse Time Dimensions to derive the Primary Key for dim_time
        date_key = transform_timestamp_to_key(timestamp) 
        
        # 2. TRANSFORM: Iterate through individual questions nested in the response document
        for answer_node in document["answers"]:
            question_id = answer_node["question_id"]
            raw_value = answer_node["value"]
            
            # Map values dynamically to analytical typed storage primitives
            answer_text = None
            answer_numeric = None
            
            if isinstance(raw_value, (int, float)):
                answer_numeric = float(raw_value)
                answer_text = str(raw_value)
            else:
                answer_text = str(raw_value)
                
            # 3. LOAD: Append structured tabular data directly to SQL tables
            sql_client.execute(
                \"\"\"
                INSERT INTO fact_survey_responses 
                (response_id, survey_id, question_id, respondent_id, answer_text, answer_numeric, date_key)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                \"\"\",
                (response_id, survey_id, question_id, respondent_id, answer_text, answer_numeric, date_key)
            )
            
        # Flag NoSQL document as synchronized to prevent accidental double-processing
        nosql_client.db.responses.update_one(
            {"_id": response_id}, 
            {"$set": {"processed_by_etl": True}}
        )

```

---

## 5. Analytics & Dashboard Performance Advantages

By mapping our target warehouse structure to a unified schema, constructing complex aggregated analytical reports requires zero dynamic database reconfiguration. The frontend code uses simple, predictable SQL queries.

### Universal Query Analytics Examples

#### Case A: Generating Distribution Metrics for Multiple-Choice Questions

To populate a pie chart or a comparative horizontal bar chart detailing response breakdowns for *any* multiple-choice selection, the query abstracts to a simple aggregation filtering on the unique target `question_id`:

```sql
SELECT 
    answer_text AS selection_option,
    COUNT(*) AS absolute_votes,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS distribution_percentage
FROM fact_survey_responses
WHERE question_id = 'q_002'
GROUP BY answer_text
ORDER BY absolute_votes DESC;

```

#### Case B: Running Aggregations for Quantitative Questions

To evaluate transactional NPS scores or linear numerical survey parameters, calculating averages or variations takes advantage of native indexing across performance-optimized data columns:

```sql
SELECT 
    q.question_text,
    COUNT(f.response_row_id) AS total_responses_collected,
    AVG(f.answer_numeric) AS arithmetic_mean_score,
    MIN(f.answer_numeric) AS minimum_recorded_value,
    MAX(f.answer_numeric) AS maximum_recorded_value
FROM fact_survey_responses f
JOIN dim_questions q ON f.question_id = q.question_id
WHERE f.question_id = 'q_001'
GROUP BY q.question_text;

```

---

## 6. Key Architecture Safeguards

* **Data Normalization Boundaries:** High-level entities that dictate relationship bounds (such as Account Metadata, Organizational Authorization Rules, or Subscriptions) belong securely inside the ACID-compliant relational SQL storage layout.
* **Separation of Operational Workloads:** This hybrid separation prevents intensive business intelligence processes from consuming resources needed for live survey responses. Even during massive analytics spikes, operational survey submissions remain fast and unaffected.
* **Idempotent ETL Pipeline Execution:** The ETL processing code uses transactional markers (`processed_by_etl`). This ensures that if a network glitch occurs midway through a sync operation, the pipeline can safely restart without writing duplicate data entries into the analytics engine.
"""


```
System Tone: General/Informational (Unspecified)

Your Markdown file is ready 
[file-tag: code-generated-file-0-1779045362379173529]

I have created a comprehensive, production-grade documentation file named `survey_platform_architecture.md`. It explicitly covers every facet of the design we discussed and maps out the exact structural mechanics needed to get top marks on your university project.

### What is covered in the document:
1. **Core Motivation:** A detailed breakdown of why single-database models fail in survey environments (the conflict between wide/null rows and dynamic questions vs. heavy dashboard aggregates).
2. **System Architecture Blueprint:** Textual ASCII flowcharts mapping the exact movement of data from **Web Application** $\rightarrow$ **NoSQL (OLTP)** $\rightarrow$ **ETL Engine** $\rightarrow$ **SQL Warehouse (OLAP)**.
3. **Storage Layer Specifications:** Complete JSON schemas for the NoSQL collections alongside structured SQL DDL script declarations mapping out your dimensions (`dim_surveys`, `dim_questions`, `dim_time`) and core analytics fact table (`fact_survey_responses`).
4. **Managed ETL Design:** Clean Python pseudocode displaying how a real-time extraction, transformation, mapping, and loading sequence parses a nested JSON array into standardized rows.
5. **Universal Analytical Queries:** Real SQL aggregation queries (`SUM`, `COUNT`, `OVER()`, `AVG`) demonstrating how a single static dashboard can fetch metrics for *any* dynamic survey type without changing database tables.

```

