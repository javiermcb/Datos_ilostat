"""Los 27 países de la UE ordenados por el indicador elegido, con España y Portugal resaltados y la UE como referencia."""
import streamlit as st

import datos
import graficos as g

SEXO = {"Todos": "Total", "Hombres": "Hombres", "Mujeres": "Mujeres"}
anyo, genero = st.session_state.get("anyo"), st.session_state.get("genero", "Todos")
st.title("Países de la UE")
MEDIDAS = {"Tasa de paro (%)": "tasa_paro", "Tasa de actividad (%)": "tasa_actividad",
           "Desempleados (miles)": "desempleados", "Fuerza laboral (miles)": "fuerza_laboral", "Población 15+ (miles)": "poblacion"}
medida = st.radio("Indicador", list(MEDIDAS), horizontal=True)
col = MEDIDAS[medida]
st.caption(f"Año {anyo} · {genero} · la línea discontinua es el valor de la UE (solo en las tasas).")
d = datos.q("SELECT m.*, a.tipo FROM mart_comparativa m JOIN dim_area a USING (area_id) WHERE m.anyo = ? AND m.sexo = ?",
            [anyo, SEXO[genero]]) if anyo else None
if d is None or d.empty:
    st.info("Sin datos en esta carga.")
    st.stop()
paises = d[d.tipo == "País"].dropna(subset=[col]).copy()
paises["color"] = paises.area_id.map(g.COLOR).fillna(g.RESTO)
ue = d.loc[d.area_id == "UE27", col]
tasa = col.startswith("tasa")
g.ranking(paises, "area", col, "color", fmt=",.1f" if tasa else ",.0f", titulo=medida, ref=ue.iloc[0] if tasa and not ue.empty else None)
