-- Porcentaje de imagen negativa por region.
-- DENSE_RANK ordena las regiones desde la mas critica.

with imagen_por_region as (
    select
        r.region,
        count(*) as respuestas,
        count(*) filter (
            where o.option_text in ('Mala', 'Muy mala')
        ) as respuestas_negativas
    from fact_survey_responses f
    join dim_questions q
        on q.question_id = f.question_id
    join dim_answer_options o
        on o.option_id = f.option_id
    join dim_respondents r
        on r.respondent_id = f.respondent_id
    where q.category = 'imagen_gobierno'
    group by r.region
)
select
    dense_rank() over (
        order by respuestas_negativas * 100.0 / respuestas desc
    ) as posicion,
    region,
    respuestas,
    respuestas_negativas,
    round(respuestas_negativas * 100.0 / respuestas, 2) as imagen_negativa_pct
from imagen_por_region
order by posicion, region;
