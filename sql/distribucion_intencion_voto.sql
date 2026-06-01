-- Distribucion general de intencion de voto.
-- La funcion de ventana calcula el porcentaje sobre el total.

with votos_por_partido as (
    select
        o.option_text as partido,
        count(*) as votos
    from fact_survey_responses f
    join dim_questions q
        on q.question_id = f.question_id
    join dim_answer_options o
        on o.option_id = f.option_id
    where q.category = 'intencion_voto'
    group by o.option_text
)
select
    partido,
    votos,
    round(votos * 100.0 / sum(votos) over (), 2) as porcentaje
from votos_por_partido
order by votos desc;
