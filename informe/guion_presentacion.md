# Guión y Estructura de Presentación (30 Minutos - Online)

## Reglas Generales para la Presentación Online
*   **El modelo "Chofer Único":** Solo UN integrante (el que tenga mejor internet y PC) comparte pantalla toda la presentación. Los demás relatan.
*   **Transiciones fluidas:** El Chofer tiene todo abierto previamente (Slides, VS Code con fuente grande, Navegador con Streamlit).
*   **Manejo del tiempo:** Estrictos 6 minutos máximo por persona. Usen un cronómetro visible.

---

## Bloque 1: El Escenario y la Estrategia (5 min) | *Integrante 1*
**Modo Visual:** 100% Slides.

**Puntos Críticos a Cubrir:**
*   **Introducción:** Presentar a "Inteligencia Colectiva" (consultora de opinión pública).
*   **El Problema:** La ingesta masiva de encuestas de múltiples canales (IVR, Web) que cambian constantemente de formato y cantidad de preguntas.
*   **La Solución:** Justificar la decisión de una arquitectura "Políglota" híbrida.
*   **Visual a usar:** Slide con el **Diagrama de Infraestructura** (Las 3 zonas: Extracción, Transformación, Presentación).

## Bloque 2: Arquitectura y Motores (5 min) | *Integrante 2*
**Modo Visual:** 100% Slides (con capturas claras).

**Puntos Críticos a Cubrir:**
*   **Data Lake (NoSQL):** Explicar por qué usamos **MongoDB Atlas**. Mencionar el concepto clave: *Esquema Flexible (schema-less)* para absorber encuestas cambiantes.
*   **Visual a usar:** Captura de pantalla grande de un documento JSON de MongoDB mostrando su estructura anidada.
*   **Data Warehouse (SQL):** Explicar por qué usamos **PostgreSQL (Supabase)** para la capa analítica. Mencionar el rigor de las consultas estructuradas.
*   **Cierre del bloque:** "Usamos el motor correcto para el trabajo correcto".

## Bloque 3: Modelado y la Magia del Hash (7 min) | *Integrante 3*
**Modo Visual:** Slides (Diagramas y Snippets de Código).

**Puntos Críticos a Cubrir:**
*   **Diseño Analítico:** Mostrar el **Diagrama de Entidad-Relación (DER)**. Explicar brevemente que es un modelo híbrido (Copo de Nieve para mantener jerarquías, pero usado como Estrella en la tabla de hechos).
*   **El Perfilado Determinístico:** (Este es el punto para lucirse). Explicar cómo usan el **Hash SHA-256** sobre el ID del encuestado para generar perfiles demográficos reales y consistentes sin base de datos intermedia, simulando privacidad.
*   **Visual a usar:** Un *snippet* (recorte de código resaltado) del archivo `src/demographics.py` dentro de la slide.
*   **Auditoría:** Mencionar rápidamente la tabla `etl_process_executions`.

## Bloque 4: El Corazón Técnico: El ETL (5 min) | *Integrante 4*
**Modo Visual:** Slides -> Transición en vivo al IDE (VS Code).

**Puntos Críticos a Cubrir:**
*   **Visual a usar (Slide):** El **Diagrama de Flujo del ETL**. Explicar cómo el script extrae, aplana el JSON y lo cruza con el hash.
*   **Transición:** El Chofer cambia la pantalla a VS Code (`src/etl_mongo_to_postgres.py`).
*   **Idempotencia:** Mostrar en el código la cláusula `ON CONFLICT DO UPDATE / DO NOTHING`. Explicar por qué es vital para que el script pueda correr mil veces sin duplicar datos.
*   **Minería (Teoría):** Mencionar rápidamente que la lógica pesada (segmentación, bayesiano) se delegó a funciones dentro del motor de PostgreSQL para no saturar el servidor.

## Bloque 5: La Gran Demo y Cierre (8 min) | *Integrante 5*
**Modo Visual:** 100% Demo en Vivo (Navegador).

**Puntos Críticos a Cubrir:**
*   **Transición:** El Chofer cambia al Dashboard de Streamlit (`localhost:8501`).
*   **El Producto Final:** Relatar cómo el Data Warehouse alimenta este Data Mart.
*   **Interacción en vivo:** Pedirle al Chofer que interactúe:
    *   Mostrar la predicción Bayesiana de intención de voto.
    *   Mostrar el Pie Chart de segmentación regional (explicando que consume la función SQL `segmentar_respuestas`).
    *   Mover el slider del parámetro "Lambda" (olvido por recencia) para demostrar la conexión en tiempo real con la base de datos predictiva.
*   **Cierre:** Conclusión de cómo la arquitectura resuelve el problema del cliente planteado en el Bloque 1.
