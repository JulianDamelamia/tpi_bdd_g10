# TRABAJO PRÁCTICO INTEGRADOR DE BASE DE DATOS
## Sistemas de gestión de base de datos Políglota

### 1. Presentación del Escenario

#### 1.1. Empresa
Representamos al equipo de Datos de la consultora de opinión pública **Inteligencia Colectiva**. Esta empresa se dedica a realizar encuestas mediante llamados telefónicos (IVR) y por formularios online (web y apps).

#### 1.2. Situación a Implementar/Solucionar
Nuestra tarea es desarrollar la infraestructura necesaria para almacenar, procesar y explotar los datos recolectados de múltiples fuentes. Se busca implementar una estructura de datos eficiente y ordenada para el guardado de las respuestas, considerando variables propias del negocio: multiplicidad de cuestionarios, y el hecho de que cada cuestionario tiene una cantidad y tipo de preguntas distintas, con cantidades y tipos de respuestas posibles diferentes. El objetivo final es presentar tableros concisos con estadísticas relevantes para el cliente (tendencias de opinión, segmentación por edad, nivel socioeconómico, región, etc.) y ofrecer proyecciones predictivas.

#### 1.3. Justificación
El flujo de datos del negocio tiene dos etapas claramente diferenciadas:
1. **Ingesta masiva:** Recolección de respuestas "crudas" y no estructuradas de múltiples canales.
2. **Análisis agregativo:** Transformación de esos datos en un formato estructurado para la toma de decisiones, BI y predicciones.
Por esto, justificamos una arquitectura híbrida y políglota: MongoDB para la flexibilidad operativa (OLTP) y PostgreSQL para la rigurosidad analítica (OLAP/Data Warehouse).

---

### 2. Presentación de los motores SQL y NoSQL

#### 2.1. MongoDB (NoSQL)
*   **Empresa/Organización:** MongoDB Inc.
*   **Justificación de Elección:** Utilizaremos MongoDB para almacenar los datos "crudos" (encuestas y respuestas). Su modelo de documentos (JSON/BSON) encaja perfectamente con nuestra lógica de negocio, ya que las encuestas cambian constantemente en estructura. MongoDB permite almacenar jerarquías complejas sin necesidad de migraciones de esquema (schema-less). Descartamos bases clave-valor o columnares puras porque necesitamos filtrar datos por identificadores internos (encuesta, encuestado).
*   **Tipo de Licencia:** Server Side Public License (SSPL) - Libre para uso general, con opciones Enterprise de pago (MongoDB Atlas).
*   **Cómo conseguirlo:** Se puede descargar desde `mongodb.com/try/download/community` para instalación local, levantar mediante Docker (`docker pull mongo`), o utilizar su versión gestionada en la nube (MongoDB Atlas).

#### 2.2. PostgreSQL (SQL)
*   **Empresa/Organización:** PostgreSQL Global Development Group.
*   **Justificación de Elección:** Elegido como motor para nuestro Data Warehouse. Postgres destaca por su robustez, soporte completo de transacciones ACID, y su capacidad de manejar funciones analíticas complejas directamente en el motor (minerías de datos, ventanas, segmentación matemática). En este proyecto se utiliza a través de **Supabase**, lo que facilita su despliegue en la nube.
*   **Tipo de Licencia:** Licencia PostgreSQL (similar a BSD/MIT) - Open Source y completamente gratuito.
*   **Cómo conseguirlo:** Descarga local en `postgresql.org/download/`, uso mediante contenedores Docker (`docker pull postgres`), o en servicios DBaaS como Supabase, AWS RDS, o Google Cloud SQL.

---

### 3. Diseño del Datawarehouse

#### 3.1. Arquitectura BI
La arquitectura consta de tres capas que siguen los estándares modernos de Ingeniería de Datos:
1.  **Data Lake (Capa de Extracción):** Representada por **MongoDB**. Es el repositorio donde aterrizan los datos "crudos" y no estructurados de las encuestas en formato JSON. Su flexibilidad permite almacenar cualquier tipo de cuestionario sin pérdida de información.
2.  **Data Warehouse (Capa de Transformación y Carga):** Representada por **PostgreSQL**. Es el repositorio central donde los datos, tras pasar por el proceso ETL (`src/etl_mongo_to_postgres.py`), son limpiados, tipificados y organizados bajo un modelo relacional en estrella.
3.  **Explotación:** Representada por el **Dashboard de Streamlit**. Esta capa consume subconjuntos específicos del Data Warehouse (orientados a temas como Intención de Voto o Imagen de Gestión) para la visualización y toma de decisiones.

#### 3.2. Motor Seleccionado
PostgreSQL 15+ (vía Supabase / Local).

#### 3.3. Modelado de Datos
El modelo implementado es un **Modelo en Estrella (Star Schema)**, optimizado para consultas de agregación masiva.
*   **Tabla de Hechos:** `fact_survey_responses` (Un registro por cada respuesta a una pregunta individual, granularidad máxima).
*   **Tablas de Dimensiones:**
    *   `dim_surveys` (Datos de la encuesta).
    *   `dim_questions` (Metadata de la pregunta).
    *   `dim_answer_options` (Opciones de respuesta válidas).
    *   `dim_respondents` (Perfiles demográficos: región, NSE, edad, género).
    *   `dim_time` (Dimensión temporal para análisis histórico).
*   **Tabla de Auditoría:** `etl_process_executions` (Registra cada ejecución del proceso ETL, tiempos de inicio/fin, estado y cantidad de registros procesados para asegurar la trazabilidad del sistema).
*   *(Nota de diseño: El perfil del encuestado en `dim_respondents` se genera mediante un **Perfilado Determinístico vía Hash SHA-256**, lo que permite derivar atributos consistentes a partir del ID sin necesidad de almacenar datos personales sensibles).*

#### 3.4. Infraestructura usada
*(Espacio reservado para Diagramas y Máquinas - El grupo debe insertar imágenes aquí. Arquitectura conceptual: App/IVR -> MongoDB -> Python ETL Cron -> PostgreSQL -> Streamlit Dashboard).*

---

### 4. Operaciones sobre el Datawarehouse (CRUD y ETL)

El proceso **ETL** principal se ejecuta de forma incremental. Lee documentos desde MongoDB, los transforma y los carga (Upsert) en PostgreSQL.

#### 4.1. Creación e Inserción (El proceso ETL)
El script extrae las respuestas de Mongo por lotes.
*   **Dimensiones:** Se actualizan mediante la cláusula `ON CONFLICT DO UPDATE` (Upsert). Si entra una encuesta nueva, se crea; si ya existe, se actualizan sus metadatos (título, estado).
*   **Hechos:** Se insertan en `fact_survey_responses` mediante `ON CONFLICT DO NOTHING`. Si por un fallo el ETL vuelve a leer el mismo documento de Mongo, la restricción de unicidad (`uq_fact_response_question`) previene datos duplicados en el Data Warehouse.

#### 4.2. Actualización
Principalmente se refleja en las tablas de dimensiones. Por ejemplo, si el `status` de un documento de encuesta en Mongo cambia de "active" a "closed", en la siguiente corrida del ETL, la instrucción `ON CONFLICT DO UPDATE` en `dim_surveys` modificará el registro existente.

#### 4.3. Eliminación
En un entorno Data Warehouse (OLAP) tradicional, los datos rara vez se eliminan (soft-deletes). Sin embargo, para entornos de prueba, el repositorio cuenta con un script de "Reset" (`seed.py`) que ejecuta un `DROP TABLE` y `DROP DATABASE` tanto en Mongo como Postgres para limpiar el entorno.

#### 4.4. Búsquedas
*   **Búsqueda por 1 Clave:** Obtener todas las respuestas de una encuesta específica (`SELECT * FROM fact_survey_responses WHERE survey_id = 'survey_0001'`).
*   **Búsqueda por 2 Claves:** Buscar respuestas de una categoría específica en un año particular (Ej: `SELECT f.* FROM fact_survey_responses f JOIN dim_questions q ON f.question_id = q.question_id JOIN dim_time t ON f.date_key = t.date_key WHERE q.category = 'imagen_gobierno' AND t.year = 2025`).

---

### 5. Minería de Datos (Implementado vía SQL Functions)

El proyecto utiliza la capacidad analítica de PostgreSQL para realizar minería in-database, evitando transferir millones de filas a la capa de la aplicación.

#### 5.1. Función Dinámica de Segmentación
Se implementó la función SQL `segmentar_respuestas(p_categoria, p_desde, p_hasta, p_dimension)`.
*   **Uso:** Permite agrupar las respuestas de una categoría (ej. "intencion_voto") en un rango de fechas, segmentándolas dinámicamente por criterios demográficos (como "region" o "nse" - Nivel Socioeconómico).
*   **Explicación:** La función realiza un JOIN dinámico evaluando la dimensión seleccionada, contando la cantidad de votos u opiniones por cada segmento. Esto es vital para el negocio para entender cómo vota el norte del país vs. la capital, sin tener que escribir consultas complejas manualmente cada vez.

#### 5.2. Función Dinámica de Predicción
Se implementó la función SQL `predecir_shares(p_categoria, p_fecha_corte, p_lambda, p_prior_weight)`.
*   **Uso:** Aplica una predicción bayesiana para calcular la intención de voto o imagen política futura.
*   **Explicación:** Utiliza un parámetro `p_lambda` para aplicar un "decaimiento exponencial" (recency bias), dándole más peso a las respuestas recientes que a las antiguas. Combina esto con una distribución a priori (`p_prior_weight`) para generar no solo un porcentaje predicho, sino un intervalo de credibilidad (limite alto y bajo). Es un uso puro de matemáticas estadísticas delegadas directamente al motor SQL.

---

### 6. Implementar un DashBoard BI

Se desarrolló un Dashboard interactivo utilizando **Streamlit** y **Plotly** (`dashboard/app.py`), el cual cumple con el requerimiento de presentar al menos 4 elementos de información conectados al Data Warehouse:

1.  **Intención de Voto (Predicción Bayesiana):** Un gráfico de barras con barras de error que muestra la predicción de resultados electorales consumiendo la función SQL `predecir_shares`.
2.  **Segmentación Geográfica:** Un gráfico circular (Pie Chart) que consume la función `segmentar_respuestas` para mostrar la proporción de respuestas categorizadas por región.
3.  **Evolución Temporal:** Un gráfico de líneas que traza la serie de tiempo de la imagen del gobierno mes a mes, uniendo la tabla de hechos con la dimensión de tiempo (`dim_time`).
4.  **Explorador Interactivo:** Un panel dinámico con selectores (sliders y dropdowns) que permite al usuario modificar la tasa de "olvido" (parámetro lambda) y filtrar por región en tiempo real, observando cómo se recalcula el modelo matemático en pantalla.

---

### Apéndice: Dimensionamiento y Seguridad

**Dimensionamiento Estimado:**
Un documento máximo en MongoDB (80 preguntas a 20.000 encuestados) pesa ~100MB. En PostgreSQL, modelado en estrella, esto representa ~1.6 millones de filas en la tabla de hechos. Asumiendo ~30 bytes por fila más las tablas de dimensiones, esto se traduce en ~50MB por encuesta almacenada. Con un disco estándar de 100GB, la infraestructura soporta años de operaciones ininterrumpidas a máxima capacidad sin requerir sharding complejo.

**Seguridad:**
*   Control de Acceso: El sistema utiliza variables de entorno (`.env`) para asegurar que las credenciales no se expongan en el código fuente.
*   En producción (Supabase), se aplican políticas RLS (Row Level Security) y se diferencian roles (ej. un usuario de solo lectura para el Dashboard BI y un usuario con permisos de escritura para el proceso ETL).
