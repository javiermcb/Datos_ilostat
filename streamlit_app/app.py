"""
Datos ILOSTAT · España, Portugal, Iberia y UE (app de Streamlit).

Arranque en local:   streamlit run app.py
Datos: ver datos.py (ILO_DATOS = carpeta o URL con los Parquet del modelo que genera el pipeline cada día).
"""
import streamlit as st

st.set_page_config(page_title="Mercado laboral · Iberia vs UE", page_icon="📊", layout="wide")

import recarga  # noqa: E402

recarga.comprobar()  # tras publicar código nuevo, recarga graficos, datos... (Streamlit Cloud guarda la versión antigua)

import datos  # noqa: E402
import graficos as g  # noqa: E402

nav = st.navigation([
    st.Page("paginas/panel.py", title="Panel", icon=":material/dashboard:", default=True),
    st.Page("paginas/evolucion.py", title="Evolución", icon=":material/trending_up:"),
    st.Page("paginas/paises.py", title="Países de la UE", icon=":material/public:"),
    st.Page("paginas/datos_descarga.py", title="Datos y descargas", icon=":material/download:"),
    st.Page("paginas/estado.py", title="Estado de los datos", icon=":material/fact_check:"),
], position="top")

_, disponibles, faltan = datos.conexion()
errores = datos.errores_descarga()

with st.sidebar:
    st.header("Filtros")
    anyos = datos.anyos()
    if anyos:
        st.selectbox("Selecciona el año", anyos, key="anyo",
                     help="Años con datos de los 27 países de la UE (sin los 27, el total de la UE no sería comparable).")
    st.selectbox("Selecciona el género", ["Todos", "Hombres", "Mujeres"], key="genero")
    st.header("Leyenda")
    for area in ("UE27", "IBERIA", "ESP", "PRT"):
        st.markdown(f"<div style='display:flex;align-items:center;margin:0.35rem 0;font-size:1.05rem'>"
                    f"<span style='width:16px;height:16px;background:{g.COLOR[area]};display:inline-block;margin-right:0.6rem'></span>"
                    f"{g.NOMBRE[area]}</div>", unsafe_allow_html=True)
    st.divider()
    carga = datos.fecha_carga()
    if carga:
        st.caption(f"Datos de la carga del {carga}")
    if faltan:
        st.caption(f"Tablas no disponibles en esta carga: {', '.join(faltan)}")
    st.caption("Elaboración propia con datos de ILOSTAT (Organización Internacional del Trabajo), encuestas de población "
               "activa de cada país, personas de 15 años o más. Iberia (España + Portugal), UE (suma de los 27 países) y las "
               "tasas son cálculos propios, no cifras oficiales. La OIT no participa en esta herramienta ni la respalda.")

if errores and not disponibles:
    # sin ninguna tabla: casi siempre es el token o la URL; se dice en claro en vez de mostrar páginas vacías
    st.error("No se han podido cargar los datos: " + sorted(set(errores.values()))[0])
    st.stop()
if errores:
    st.sidebar.warning(f"{len(errores)} tablas no se han podido actualizar (se muestra la última copia descargada, "
                       "si la hay). Detalle en «Estado de los datos».")

nav.run()

import relato  # noqa: E402

relato.estilo()
relato.pie_periodos(datos.periodos())
