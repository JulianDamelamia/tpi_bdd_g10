"""Dashboard BI — consultora Inteligencia Colectiva.

Organizado en pestañas: intención de voto, imagen de gobierno, prioridades,
muestra/demografía y un explorador de predicción bayesiana.
"""
import html
import json
import sys
import pathlib

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.config import POSTGRES_URL

st.set_page_config(page_title="Inteligencia Colectiva — BI", layout="wide")
engine = create_engine(POSTGRES_URL)


@st.cache_data
def _load_geojson():
    """Polígonos de las 24 provincias (GADM nivel 1, propiedad NAME_1)."""
    path = pathlib.Path(__file__).resolve().parent / "argentina_provincias.geojson"
    return json.loads(path.read_text())


ARG_GEOJSON = _load_geojson()

CORTE = "2026-09-26"
POSITIVAS = ("Muy buena", "Buena")
NEGATIVAS = ("Mala", "Muy mala")


@st.cache_data(ttl=300)
def q(sql: str, params: dict | None = None) -> pd.DataFrame:
    with engine.connect() as c:
        return pd.read_sql(text(sql), c, params=params or {})


def saldo_imagen(df: pd.DataFrame, grupo: str) -> pd.DataFrame:
    """De un df con [grupo, option_text, n] calcula saldo = %positiva - %negativa."""
    df = df.copy()
    df["signo"] = df["option_text"].apply(
        lambda t: "pos" if t in POSITIVAS else ("neg" if t in NEGATIVAS else "neutro")
    )
    piv = df.pivot_table(index=grupo, columns="signo", values="n", aggfunc="sum", fill_value=0)
    total = piv.sum(axis=1)
    out = pd.DataFrame({grupo: piv.index})
    out["saldo"] = ((piv.get("pos", 0) - piv.get("neg", 0)) / total * 100).values
    return out


st.title("Inteligencia Colectiva — Tablero de Opinión Pública")

tab_voto, tab_imagen, tab_prio, tab_muestra, tab_pred = st.tabs(
    ["Intención de voto", "Imagen de gobierno", "Prioridades", "Muestra", "Predicción"]
)

# ===================== TAB 1 — INTENCIÓN DE VOTO =====================
with tab_voto:
    st.subheader("Predicción bayesiana del share por partido")
    pred = q("select * from predecir_shares('intencion_voto', :c, 0.0, 5.0)", {"c": CORTE})
    fig = go.Figure()
    fig.add_bar(
        x=pred["opcion"], y=pred["share_pred"],
        error_y=dict(type="data", array=pred["ic_alto"] - pred["share_pred"],
                     arrayminus=pred["share_pred"] - pred["ic_bajo"]),
    )
    fig.update_layout(yaxis_title="share % (con intervalo de credibilidad 95%)")
    st.plotly_chart(fig, use_container_width=True)

    voto_reg = q("""
        select r.region, o.option_text opcion, count(*) n
        from fact_survey_responses f
        join dim_questions q on f.question_id=q.question_id
        join dim_answer_options o on f.option_id=o.option_id
        join dim_respondents r on f.respondent_id=r.respondent_id
        where q.category='intencion_voto' group by 1,2""")
    piv = voto_reg.pivot_table(index="region", columns="opcion", values="n", fill_value=0)
    pct = piv.div(piv.sum(axis=1), axis=0) * 100

    # mapa: provincias rellenas — color = partido ganador de su región, intensidad = share
    PROV_REGION = {
        "Ciudad de Buenos Aires": "AMBA", "Buenos Aires": "AMBA",
        "Córdoba": "Centro", "Santa Fe": "Centro", "Entre Ríos": "Centro", "La Pampa": "Centro",
        "Jujuy": "NOA", "Salta": "NOA", "Tucumán": "NOA", "Catamarca": "NOA",
        "La Rioja": "NOA", "Santiago del Estero": "NOA",
        "Misiones": "NEA", "Corrientes": "NEA", "Chaco": "NEA", "Formosa": "NEA",
        "Mendoza": "Cuyo", "San Juan": "Cuyo", "San Luis": "Cuyo",
        "Neuquén": "Patagonia", "Río Negro": "Patagonia", "Chubut": "Patagonia",
        "Santa Cruz": "Patagonia", "Tierra del Fuego": "Patagonia",
    }
    mapa = pd.DataFrame({
        "region": pct.index,
        "ganador": pct.idxmax(axis=1).values,
        "share": pct.max(axis=1).round(1).values,
        "total": piv.sum(axis=1).values,
    })
    # cada provincia hereda el resultado de su región
    prov = (
        pd.DataFrame({"provincia": list(PROV_REGION), "region": list(PROV_REGION.values())})
        .merge(mapa, on="region", how="left")
    )
    # un color base por partido; se aclara hacia el blanco cuanto menor es el share
    partidos = sorted(mapa["ganador"].unique())
    base = {p: px.colors.qualitative.Plotly[i % 10] for i, p in enumerate(partidos)}
    smin, smax = prov["share"].min(), prov["share"].max()

    def _shade(share, party):
        r, g, b = px.colors.hex_to_rgb(base[party])
        t = 0.40 + 0.60 * (((share - smin) / (smax - smin)) if smax > smin else 1.0)
        return f"rgb({int(255 + (r - 255) * t)},{int(255 + (g - 255) * t)},{int(255 + (b - 255) * t)})"

    prov["color"] = [_shade(s, p) for s, p in zip(prov["share"], prov["ganador"])]

    st.markdown("**Partido ganador por provincia** — color = partido, intensidad = % del ganador en su región")
    # choropleth_map (MapLibre, planar) en vez de choropleth (geo, esférico):
    # los polígonos GADM tienen winding que rompe el render esférico (rellena todo el globo)
    fig_map = px.choropleth_map(
        prov, geojson=ARG_GEOJSON, locations="provincia",
        featureidkey="properties.NAME_1", color="provincia",
        color_discrete_map=dict(zip(prov["provincia"], prov["color"])),
        hover_name="provincia",
        hover_data={"provincia": False, "region": True, "ganador": True,
                    "share": True, "total": True},
        center={"lat": -40, "lon": -65}, zoom=3.0,
        map_style="white-bg", opacity=1.0,
    )
    fig_map.update_layout(height=560, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
    st.plotly_chart(fig_map, use_container_width=True)
    # html.escape: los nombres de partido vienen de la DB (option_text) y se inyectan
    # en unsafe_allow_html -> escapar para evitar XSS almacenado
    leyenda = " &nbsp; ".join(
        f"<span style='display:inline-block;width:12px;height:12px;background:{base[p]};"
        f"border-radius:2px;margin-right:5px'></span>{html.escape(str(p))}" for p in partidos
    )
    st.markdown(f"<div style='font-size:0.85rem;color:#666'>{leyenda}</div>",
                unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Voto por región (% dentro de cada región)**")
        st.plotly_chart(
            px.imshow(pct.round(1), text_auto=True, aspect="auto", color_continuous_scale="Blues"),
            use_container_width=True)
    voto_nse = q("""
        select r.nse, o.option_text opcion, count(*) n
        from fact_survey_responses f
        join dim_questions q on f.question_id=q.question_id
        join dim_answer_options o on f.option_id=o.option_id
        join dim_respondents r on f.respondent_id=r.respondent_id
        where q.category='intencion_voto' group by 1,2""")
    with col2:
        st.markdown("**Voto por nivel socioeconómico**")
        st.plotly_chart(px.bar(voto_nse, x="nse", y="n", color="opcion", barmode="group"),
                        use_container_width=True)

# ===================== TAB 2 — IMAGEN DE GOBIERNO =====================
with tab_imagen:
    st.subheader("Evolución mensual de la imagen de gobierno")
    modo = st.radio("Vista", ["Desglosado", "Combinado (saldo de imagen)"], horizontal=True)
    serie = q("""
        select t.year, t.month_number, o.option_text, count(*) n
        from fact_survey_responses f
        join dim_questions q on f.question_id=q.question_id
        join dim_answer_options o on f.option_id=o.option_id
        join dim_time t on f.date_key=t.date_key
        where q.category='imagen_gobierno'
        group by 1,2,3 order by 1,2""")
    serie["periodo"] = serie["year"].astype(str) + "-" + serie["month_number"].astype(str).str.zfill(2)
    if modo == "Desglosado":
        st.plotly_chart(px.line(serie, x="periodo", y="n", color="option_text"),
                        use_container_width=True)
    else:
        s = saldo_imagen(serie, "periodo")
        figs = px.line(s, x="periodo", y="saldo")
        figs.update_layout(yaxis_title="saldo de imagen (% positiva − % negativa)")
        figs.add_hline(y=0, line_dash="dot", line_color="gray")
        st.plotly_chart(figs, use_container_width=True)

    col1, col2 = st.columns(2)
    img_nse = q("""
        select r.nse, o.option_text, count(*) n
        from fact_survey_responses f
        join dim_questions q on f.question_id=q.question_id
        join dim_answer_options o on f.option_id=o.option_id
        join dim_respondents r on f.respondent_id=r.respondent_id
        where q.category='imagen_gobierno' group by 1,2""")
    with col1:
        st.markdown("**Saldo de imagen por NSE** (cuanto más bajo, más crítico)")
        sn = saldo_imagen(img_nse, "nse")
        st.plotly_chart(px.bar(sn, x="nse", y="saldo", color="saldo",
                               color_continuous_scale="RdYlGn",
                               range_color=[-80, 80]), use_container_width=True)
    img_reg = q("""
        select r.region, o.option_text, count(*) n
        from fact_survey_responses f
        join dim_questions q on f.question_id=q.question_id
        join dim_answer_options o on f.option_id=o.option_id
        join dim_respondents r on f.respondent_id=r.respondent_id
        where q.category='imagen_gobierno' group by 1,2""")
    with col2:
        st.markdown("**Saldo de imagen por región**")
        sr = saldo_imagen(img_reg, "region")
        st.plotly_chart(px.bar(sr, x="region", y="saldo", color="saldo",
                               color_continuous_scale="RdYlGn",
                               range_color=[-80, 80]), use_container_width=True)

# ===================== TAB 3 — PRIORIDADES =====================
with tab_prio:
    st.subheader("Prioridades de la agenda pública")
    prio = q("""
        select o.option_text prioridad, count(*) n
        from fact_survey_responses f
        join dim_questions q on f.question_id=q.question_id
        join dim_answer_options o on f.option_id=o.option_id
        where q.category='prioridad_publica' group by 1 order by 2 desc""")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Ranking general**")
        st.plotly_chart(px.bar(prio, x="prioridad", y="n", color="prioridad"),
                        use_container_width=True)
    prio_reg = q("""
        select r.region, o.option_text prioridad, count(*) n
        from fact_survey_responses f
        join dim_questions q on f.question_id=q.question_id
        join dim_answer_options o on f.option_id=o.option_id
        join dim_respondents r on f.respondent_id=r.respondent_id
        where q.category='prioridad_publica' group by 1,2""")
    pr = prio_reg.pivot_table(index="region", columns="prioridad", values="n", fill_value=0)
    prp = pr.div(pr.sum(axis=1), axis=0) * 100
    with col2:
        st.markdown("**Prioridad por región (%)**")
        st.plotly_chart(px.imshow(prp.round(1), text_auto=True, aspect="auto",
                                  color_continuous_scale="Oranges"), use_container_width=True)

# ===================== TAB 4 — MUESTRA / DEMOGRAFÍA =====================
with tab_muestra:
    st.subheader("Composición de la muestra")
    col1, col2, col3 = st.columns(3)
    with col1:
        reg = q("select region, count(*) n from dim_respondents group by 1 order by 1")
        st.plotly_chart(px.pie(reg, names="region", values="n", title="Por región"),
                        use_container_width=True)
    with col2:
        eta = q("select grupo_etario, count(*) n from dim_respondents group by 1 order by 1")
        st.plotly_chart(px.bar(eta, x="grupo_etario", y="n", title="Por grupo etario"),
                        use_container_width=True)
    with col3:
        gen = q("select genero, count(*) n from dim_respondents group by 1 order by 1")
        st.plotly_chart(px.pie(gen, names="genero", values="n", title="Por género"),
                        use_container_width=True)

    col4, col5 = st.columns(2)
    with col4:
        fuente = q("select source fuente, count(*) n from fact_survey_responses group by 1 order by 2 desc")
        st.plotly_chart(px.bar(fuente, x="fuente", y="n", color="fuente",
                               title="Respuestas por canal"), use_container_width=True)
    with col5:
        vol = q("""select t.year, t.month_number, count(*) n
            from fact_survey_responses f join dim_time t on f.date_key=t.date_key
            group by 1,2 order by 1,2""")
        vol["periodo"] = vol["year"].astype(str) + "-" + vol["month_number"].astype(str).str.zfill(2)
        st.plotly_chart(px.area(vol, x="periodo", y="n", title="Volumen de respuestas por mes"),
                        use_container_width=True)

# ===================== TAB 5 — PREDICCIÓN (EXPLORADOR) =====================
with tab_pred:
    st.subheader("Explorador de predicción bayesiana")
    st.caption("Subí λ para que la predicción pondere más lo reciente: la banda de error se ensancha "
               "cuando hay menos datos frescos.")
    c1, c2, c3 = st.columns(3)
    categoria = c1.selectbox("Pregunta", ["intencion_voto", "imagen_gobierno", "prioridad_publica"])
    lam = c2.slider("λ (olvido por día)", 0.0, 0.05, 0.0, 0.005)
    region = c3.selectbox("Región", ["(todas)", "AMBA", "Centro", "NOA", "NEA", "Cuyo", "Patagonia"])
    rparam = None if region == "(todas)" else region
    expl = q("select * from predecir_shares(:cat, :c, :l, 5.0, :r, null)",
             {"cat": categoria, "c": CORTE, "l": lam, "r": rparam})
    figp = go.Figure()
    figp.add_bar(
        x=expl["opcion"], y=expl["share_pred"],
        error_y=dict(type="data", array=expl["ic_alto"] - expl["share_pred"],
                     arrayminus=expl["share_pred"] - expl["ic_bajo"]),
    )
    figp.update_layout(yaxis_title="share % (con IC 95%)")
    st.plotly_chart(figp, use_container_width=True)
    st.dataframe(expl, use_container_width=True)
