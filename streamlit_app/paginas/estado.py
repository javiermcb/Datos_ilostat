import pandas as pd
import streamlit as st

import datos

st.title("Estado de los datos")
st.caption("Qué indicadores se actualizaron en la última carga diaria, hasta qué año llega cada uno y si la app ha podido "
           "descargarlos. Un indicador que falla un día no deja la tabla vacía: se usa su última carga buena.")

carga = datos.fecha_carga()
st.metric("Última carga del pipeline", carga or "desconocida")

errores = datos.errores_descarga()
if errores:
    st.subheader("Descargas fallidas en la app")
    st.warning("La app no ha podido descargar estas tablas en su último refresco; muestra la copia anterior si la tenía.")
    st.dataframe(pd.DataFrame(sorted(errores.items()), columns=["Tabla", "Motivo"]), hide_index=True, width="stretch")

ESTADOS = {"OK": "✅ Actualizado", "ANTERIOR": "🟠 Última carga buena (la API falló)", "AVISO": "🟡 Actualizado con avisos",
           "ERROR": "🔴 Sin datos"}

st.subheader("Indicadores de ILOSTAT")
I = datos.csv_extra("ilostat_carga.csv")
if I.empty:
    st.info("Esta carga no incluye el informe de carga (se publica a partir de la próxima carga del pipeline).")
else:
    I["Estado"] = I.estado.map(ESTADOS).fillna(I.estado)
    st.dataframe(I[["indicador_id", "tema", "Estado", "datos", "paises", "anyo_min", "anyo_max", "error"]].rename(
        columns={"indicador_id": "Indicador", "tema": "Tema", "datos": "Datos", "paises": "Países", "anyo_min": "Desde",
                 "anyo_max": "Hasta", "error": "Detalle"}), hide_index=True, width="stretch")

st.subheader("Años sin el total de la UE")
U = datos.csv_extra("ue_incompleta.csv")
if U.empty:
    st.caption("Todos los años descargados tienen los 27 países (o el informe no está en esta carga).")
else:
    st.caption("En estos años falta algún país, así que no se calcula la UE.")
    st.dataframe(U, hide_index=True, width="stretch")

st.subheader("Encuesta de ILOSTAT usada en cada país")
F = datos.csv_extra("fuentes_elegidas.csv")
if not F.empty:
    st.caption("Si ILOSTAT da varias encuestas para un país, se usa una sola (la que cubre más indicadores y llega más lejos).")
    st.dataframe(F, hide_index=True, width="stretch")

st.subheader("Periodo que cubre cada tabla")
R = datos.csv_extra("resumen_fuentes.csv")
meta = datos.metadatos().get("ficheros", {})
if not R.empty:
    st.dataframe(R, hide_index=True, width="stretch")
elif meta:
    st.dataframe(pd.DataFrame([{"Tabla": k, "Filas": v.get("filas")} for k, v in meta.items()]), hide_index=True, width="stretch")
