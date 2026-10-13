"""Tablas del modelo con descarga en CSV."""
import streamlit as st

import datos

st.title("Datos y descargas")
st.caption("Tablas que publica el pipeline cada día laborable. Valores en miles de personas; tasas y cuotas en %.")
TABLAS = {"Comparativa por área, sexo y año (mart_comparativa)": "SELECT * FROM mart_comparativa ORDER BY anyo DESC, sexo, area_id",
          "Datos por indicador, área, sexo y año (fact_ilostat)": "SELECT * FROM fact_ilostat ORDER BY anyo DESC, indicador, area_id, sexo",
          "Indicadores (dim_indicador)": "SELECT * FROM dim_indicador",
          "Áreas (dim_area)": "SELECT * FROM dim_area"}
nombre = st.selectbox("Tabla", list(TABLAS))
d = datos.q(TABLAS[nombre])
if d.empty:
    st.info("Tabla no disponible en esta carga.")
    st.stop()
if "area_id" in d.columns and "anyo" in d.columns:
    c = st.columns(2)
    areas = c[0].multiselect("Áreas", sorted(d.area_id.unique()), default=[a for a in ("UE27", "IBERIA", "ESP", "PRT") if a in set(d.area_id)])
    anyos = c[1].multiselect("Años", sorted(d.anyo.unique(), reverse=True))
    if areas:
        d = d[d.area_id.isin(areas)]
    if anyos:
        d = d[d.anyo.isin(anyos)]
st.dataframe(d, hide_index=True, width="stretch")
st.download_button("Descargar CSV", d.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                   file_name=TABLAS[nombre].split("FROM ")[1].split()[0] + ".csv", mime="text/csv")
