-- =====================================================================
-- FUNCION DINAMICA DE PREDICCION (Bayesiana, multi-opcion)
-- =====================================================================
-- Predice el "share" (proporcion de votos/preferencia) de cada opcion de
-- una pregunta, con su intervalo de credibilidad.
--
-- Modelo: Dirichlet-Multinomial con descuento por recencia.
--   - Arrancamos con un prior: cada opcion empieza con alpha0/K de creencia
--     previa (K = cantidad de opciones). Sin datos, todas quedan parejas.
--   - Cada respuesta observada suma evidencia a la opcion elegida, PERO
--     pesada por que tan vieja es: peso = exp(-lambda * dias_de_antiguedad).
--     Respuestas viejas pesan menos -> filtro Bayesiano descontado.
--   - Posterior de cada opcion:  alpha_k = alpha0/K + suma_de_pesos_k
--   - Share predicho (media posterior) = alpha_k / sum(alpha)
--   - Incertidumbre: cada opcion marginaliza a una Beta(alpha_k, A-alpha_k);
--     usamos su desvio y una aprox normal para el intervalo 95%.
--
-- parametros:
--   p_categoria   -> pregunta a predecir ('intencion_voto', etc)
--   p_fecha_corte -> predecimos "al dia X" (solo usa respuestas <= esa fecha)
--   p_lambda      -> velocidad de olvido por dia (0 = no descuenta nada)
--   p_alpha0      -> fuerza total del prior (mas alto = mas conservador)
--   p_region      -> filtro opcional: solo encuestados de esa region (null = todas)
--   p_nse         -> filtro opcional: solo encuestados de ese NSE (null = todos)
-- =====================================================================

-- drop de la firma vieja (4 args) para evitar ambiguedad con la nueva (6 args con defaults)
drop function if exists predecir_shares(text, date, numeric, numeric);

create or replace function predecir_shares(
    p_categoria   text,
    p_fecha_corte date,
    p_lambda      numeric default 0.0,
    p_alpha0      numeric default 5.0,
    p_region      text default null,
    p_nse         text default null
)
returns table (
    opcion         text,     -- la opcion (ej. partido)
    peso_efectivo  numeric,  -- evidencia acumulada con descuento
    conteo_crudo   bigint,   -- respuestas sin pesar (referencia)
    share_pred     numeric,  -- media posterior, en %
    ic_bajo        numeric,  -- limite inferior intervalo credibilidad 95%, en %
    ic_alto        numeric   -- limite superior, en %
)
language plpgsql
as $$
begin

    return query
    with
    -- todas las opciones posibles de la categoria (asi aparecen aunque tengan 0 votos)
    opts as (
        select distinct o.option_text::text as opcion
        from dim_answer_options o
        join dim_questions q on o.question_id = q.question_id
        where q.category = p_categoria
    ),
    k as ( select count(*)::numeric as n from opts ),
    -- respuestas observadas hasta la fecha de corte, con su peso por recencia
    obs as (
        select
            o.option_text as opcion,
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
    -- acumulamos peso y conteo crudo por opcion (left join para no perder opciones sin datos)
    agg as (
        select
            op.opcion,
            coalesce(sum(ob.w), 0)   as w_sum,
            count(ob.opcion)         as raw_cnt
        from opts op
        left join obs ob on ob.opcion = op.opcion
        group by op.opcion
    ),
    -- posterior: prior uniforme (alpha0/K) + evidencia pesada
    post as (
        select
            a.opcion,
            a.raw_cnt,
            a.w_sum,
            (p_alpha0 / (select n from k)) + a.w_sum as alpha_k
        from agg a
    ),
    tot as ( select sum(alpha_k) as a_total from post )
    select
        p.opcion,
        round(p.w_sum, 4)                                         as peso_efectivo,
        p.raw_cnt::bigint                                         as conteo_crudo,
        round(100 * p.alpha_k / t.a_total, 2)                     as share_pred,
        round(100 * greatest(
            p.alpha_k / t.a_total
            - 1.96 * sqrt( p.alpha_k * (t.a_total - p.alpha_k)
                           / (t.a_total * t.a_total * (t.a_total + 1)) ),
            0), 2)                                                as ic_bajo,
        round(100 * least(
            p.alpha_k / t.a_total
            + 1.96 * sqrt( p.alpha_k * (t.a_total - p.alpha_k)
                           / (t.a_total * t.a_total * (t.a_total + 1)) ),
            1), 2)                                                as ic_alto
    from post p, tot t
    order by share_pred desc;

end;
$$;


-- ejemplos:
-- sin descuento, todas las regiones:
-- select * from predecir_shares('intencion_voto', '2026-09-26', 0.0, 5.0);
-- con descuento fuerte (pondera lo reciente):
-- select * from predecir_shares('intencion_voto', '2026-09-26', 0.02, 5.0);
-- filtrando por region:
-- select * from predecir_shares('intencion_voto', '2026-09-26', 0.0, 5.0, 'AMBA', null);
