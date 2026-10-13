"""Evolución anual de las tasas de actividad y de paro y del peso de Iberia en la UE."""
import streamlit as st

import datos
import graficos as g
import relato

SEXO = {"Todos": "Total", "Hombres": "Hombres", "Mujeres": "Mujeres"}
genero = st.session_state.get("genero", "Todos")
st.title("Evolución")
st.caption(f"{genero} · personas de 15 años o más · la UE solo aparece en los años con datos de los 27 países.")
d = datos.comparativa(SEXO[genero])
if d.empty:
    st.info("Sin datos en esta carga.")
    st.stop()

ult = d[d.area_id == "UE27"].dropna(subset=["tasa_paro"]).anyo.max()
if ult == ult:  # no es NaN
    u = d[d.anyo == ult].set_index("area_id")
    ib, ue = u.tasa_paro.get("IBERIA"), u.tasa_paro.get("UE27")
    relato.resumen([f"Tasa de paro en {ult}: Iberia {g.es(ib, 1, ' %')} y UE {g.es(ue, 1, ' %')} "
                    f"({g.es(ib - ue, 1)} puntos de diferencia)." if ib is not None and ue is not None else "",
                    f"Tasa de actividad en {ult}: Iberia {g.es(u.tasa_actividad.get('IBERIA'), 1, ' %')} y "
                    f"UE {g.es(u.tasa_actividad.get('UE27'), 1, ' %')}."])

c = st.columns(2)
with c[0]:
    st.subheader("Tasa de paro (%)")
    g.lineas(d.dropna(subset=["tasa_paro"]), "anyo", "tasa_paro", "area_id", titulo="%")
with c[1]:
    st.subheader("Tasa de actividad (%)")
    g.lineas(d.dropna(subset=["tasa_actividad"]), "anyo", "tasa_actividad", "area_id", titulo="%")
st.subheader("Peso de Iberia en la UE (%)")
p = d[d.area_id == "IBERIA"].melt(id_vars=["anyo"], value_vars=["cuota_ue_poblacion", "cuota_ue_fuerza_laboral", "cuota_ue_desempleados"],
                                   var_name="medida", value_name="pct").dropna()
p["medida"] = p.medida.map({"cuota_ue_poblacion": "Población", "cuota_ue_fuerza_laboral": "Fuerza laboral",
                            "cuota_ue_desempleados": "Desempleados"})
if p.empty:
    st.info("Sin datos de la UE completa en esta carga.")
else:
    import altair as alt
    g.mostrar(alt.Chart(p).mark_line(point=True, strokeWidth=2.5).encode(
        x=alt.X("anyo:O", title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y("pct:Q", title="% de la UE", scale=alt.Scale(zero=False)),
        color=alt.Color("medida:N", sort=["Población", "Fuerza laboral", "Desempleados"],
                        scale=alt.Scale(domain=["Población", "Fuerza laboral", "Desempleados"], range=[g.COLOR["UE27"], g.COLOR["ESP"], g.COLOR["IBERIA"]])),
        tooltip=["medida:N", alt.Tooltip("anyo:O", title="Año"), alt.Tooltip("pct:Q", format=",.1f", title="%")]).properties(height=320))
