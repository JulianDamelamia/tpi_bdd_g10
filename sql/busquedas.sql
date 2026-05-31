-- =====================================================================
-- BUSQUEDAS sobre el Datawarehouse (lo pide la consigna)
-- =====================================================================

-- ---------------------------------------------------------------------
-- Busqueda por UNA clave
-- ---------------------------------------------------------------------
-- Traer una encuesta puntual por su PK (survey_id).
select *
from dim_surveys
where survey_id = 'survey_0001';

-- ---------------------------------------------------------------------
-- Busqueda por DOS claves
-- ---------------------------------------------------------------------
-- La fact tiene clave compuesta (response_id, question_id) -> uq_fact_response_question.
-- Buscamos la respuesta exacta de un encuestado a una pregunta.
select *
from fact_survey_responses
where response_id = 'resp_0001_001'
  and question_id = 'survey_0001_q01';
