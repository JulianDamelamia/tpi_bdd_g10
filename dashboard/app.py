"""Dashboard BI — consultora Inteligencia Colectiva. 4 elementos."""
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


@st.cache_data(ttl=300)
def q(sql: str, params: dict | None = None) -> pd.DataFrame:
    with engine.connect() as c:
        return pd.read_sql(text(sql), c, params=params or {})


st.title("Inteligencia Colectiva — Tablero de Opinión Pública")

# Elemento 1: intención de voto con intervalo de credibilidad bayesiano
st.subheader("1 · Intención de voto — predicción bayesiana")
pred = q("select * from predecir_shares('intencion_voto', :c, 0.0, 5.0)", {"c": "2026-09-26"})
fig1 = go.Figure()
fig1.add_bar(
    x=pred["opcion"], y=pred["share_pred"],
    error_y=dict(type="data", array=pred["ic_alto"] - pred["share_pred"],
                 arrayminus=pred["share_pred"] - pred["ic_bajo"]),
)
fig1.update_layout(yaxis_title="share %")
st.plotly_chart(fig1, use_container_width=True)

# Elemento 2: segmentación por región
st.subheader("2 · Segmentación de respuestas por región")
seg = q("select * from segmentar_respuestas('intencion_voto','2024-01-01','2026-12-31','region')")
st.plotly_chart(px.pie(seg, names="segmento", values="cantidad"), use_container_width=True)

# Elemento 3: evolución mensual de imagen de gobierno
st.subheader("3 · Evolución mensual de imagen de gobierno")
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
    st.plotly_chart(px.line(serie, x="periodo", y="n", color="option_text"), use_container_width=True)
else:
    positivas = {"Muy buena", "Buena"}
    negativas = {"Mala", "Muy mala"}
    serie["signo"] = serie["option_text"].apply(
        lambda t: "pos" if t in positivas else ("neg" if t in negativas else "neutro")
    )
    piv = serie.pivot_table(index="periodo", columns="signo", values="n", aggfunc="sum", fill_value=0)
    total = piv.sum(axis=1)
    saldo = ((piv.get("pos", 0) - piv.get("neg", 0)) / total * 100).reset_index(name="saldo")
    fig3 = px.line(saldo, x="periodo", y="saldo")
    fig3.update_layout(yaxis_title="saldo de imagen (% positiva − % negativa)")
    fig3.add_hline(y=0, line_dash="dot", line_color="gray")
    st.plotly_chart(fig3, use_container_width=True)

# Elemento 4: explorador interactivo (slider lambda + filtro region)
st.subheader("4 · Explorador de predicción (descuento por recencia)")
c1, c2 = st.columns(2)
lam = c1.slider("λ (olvido por día)", 0.0, 0.05, 0.0, 0.005)
region = c2.selectbox("Región", ["(todas)", "AMBA", "Centro", "NOA", "NEA", "Cuyo", "Patagonia"])
rparam = None if region == "(todas)" else region
st.dataframe(
    q("select * from predecir_shares('intencion_voto', :c, :l, 5.0, :r, null)",
      {"c": "2026-09-26", "l": lam, "r": rparam}),
    use_container_width=True,
)
