-- =====================================================================
-- FUNCION DINAMICA DE SEGMENTACION
-- =====================================================================
-- Agrupa las respuestas de una pregunta (categoria) y te dice cuantas
-- cayeron en cada grupo y que % representan.
-- Es "dinamica" porque cambiando los parametros te da segmentos distintos.
--
-- parametros:
--   p_categoria   -> que pregunta miramos: 'intencion_voto', 'imagen_gobierno', 'prioridad_publica'
--   p_fecha_desde -> desde cuando
--   p_fecha_hasta -> hasta cuando
--   p_dimension   -> por que eje agrupamos: 'opcion', 'fuente' o 'mes'
-- =====================================================================

create or replace function segmentar_respuestas(
    p_categoria   text,
    p_fecha_desde date,
    p_fecha_hasta date,
    p_dimension   text
)
returns table (
    segmento   text,     -- nombre del grupo (opcion elegida, fuente, o mes)
    cantidad   bigint,    -- cuantas respuestas hay en ese grupo
    porcentaje numeric    -- % sobre el total filtrado
)
language plpgsql
as $$
begin

    -- chequeo de que la dimension sea valida
    if p_dimension not in ('opcion', 'fuente', 'mes') then
        raise exception 'la dimension % no vale, usa: opcion / fuente / mes', p_dimension;
    end if;

    return query
    with base as (
        select
            (case p_dimension
                when 'opcion' then o.option_text
                when 'fuente' then f.source
                when 'mes'    then t.month
            end)::text as segmento
        from fact_survey_responses f
        join dim_questions      q on f.question_id = q.question_id
        join dim_time           t on f.date_key    = t.date_key
        left join dim_answer_options o on f.option_id = o.option_id
        where q.category = p_categoria
          and t.full_date between p_fecha_desde and p_fecha_hasta
    )
    select
        b.segmento,
        count(*)::bigint as cantidad,
        round( count(*) * 100.0 / nullif((select count(*) from base), 0), 2) as porcentaje
    from base b
    group by b.segmento
    order by cantidad desc;

end;
$$;


-- ejemplos:
-- select * from segmentar_respuestas('intencion_voto', '2024-01-01', '2026-12-31', 'opcion');
-- select * from segmentar_respuestas('intencion_voto', '2024-01-01', '2026-12-31', 'fuente');
-- select * from segmentar_respuestas('imagen_gobierno','2024-01-01', '2026-12-31', 'mes');
