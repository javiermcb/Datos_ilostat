"""Panel: población, fuerza laboral y desempleo de Iberia frente a la UE en un año y para un sexo."""
import streamlit as st

import datos
import graficos as g
import relato

SEXO = {"Todos": "Total", "Hombres": "Hombres", "Mujeres": "Mujeres"}
anyo, sexo = st.session_state.get("anyo"), SEXO[st.session_state.get("genero", "Todos")]
d = datos.comparativa(sexo)
if d.empty or anyo is None:
    st.info("Sin datos en esta carga. Revisa «Estado de los datos».")
    st.stop()
d = d[d.anyo == anyo].set_index("area_id")
fila = lambda a, c: d.loc[a, c] if a in d.index else None
pct = lambda v: g.es(v, 1, "%")

c = st.columns(3, gap="large")
with c[0]:
    relato.titulo("Población", "% Iberia vs UE")
    cuota = fila("IBERIA", "cuota_ue_poblacion")
    g.leyenda([(g.COLOR["IBERIA"], f"Iberia {g.es(cuota, 0, '%')}"), (g.COLOR["UE27"], f"Resto UE {g.es(100 - cuota, 0, '%') if cuota is not None else '–'}")])
    g.dona([("Iberia", fila("IBERIA", "poblacion"), g.COLOR["IBERIA"]),
            ("Resto de la UE", (fila("UE27", "poblacion") or 0) - (fila("IBERIA", "poblacion") or 0), g.COLOR["UE27"])])
    relato.nota(f"Población de 15 años o más. Iberia: {g.millones(fila('IBERIA', 'poblacion'))} de "
                f"{g.millones(fila('UE27', 'poblacion'))} en la UE.")
with c[1]:
    relato.titulo("Fuerza Laboral", "Tasa de actividad · Iberia vs UE")
    g.leyenda([(g.COLOR["IBERIA"], f"Iberia {pct(fila('IBERIA', 'tasa_actividad'))}"), (g.COLOR["UE27"], f"UE {pct(fila('UE27', 'tasa_actividad'))}")])
    g.barras_areas(d.reindex(["UE27", "ESP", "PRT"]).reset_index(), "fuerza_laboral")
    relato.nota("Personas activas (ocupadas o en paro) de 15 años o más. Tasa: activos / población de 15 años o más.")
with c[2]:
    relato.titulo("Desempleo", "Tasa de paro · Iberia vs UE")
    g.leyenda([(g.COLOR["IBERIA"], f"Iberia {pct(fila('IBERIA', 'tasa_paro'))}"), (g.COLOR["UE27"], f"UE {pct(fila('UE27', 'tasa_paro'))}")])
    g.barras_areas(d.reindex(["UE27", "ESP", "PRT"]).reset_index(), "desempleados")
    relato.nota("Personas desempleadas según la definición de la OIT. Tasa: desempleados / activos.")

st.caption(f"Año {anyo} · {st.session_state.get('genero', 'Todos')} · Fuente: OIT, ILOSTAT. Iberia, UE y tasas: elaboración propia.")
