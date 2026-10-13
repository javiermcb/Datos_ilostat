"""
graficos.py — Gráficos Altair con un mismo estilo: dona, barras horizontales y líneas.

Un color fijo por área en todas las páginas (UE, Iberia, España, Portugal) y el resto de países en gris.
Textos en azul marino rgb(0, 20, 90). Números con formato español (1.234,5).
"""
import altair as alt
import pandas as pd
import streamlit as st

TEXTO, TEXTO_SUAVE = "#00145A", "#4a5585"
COLOR = {"UE27": "#00145A", "IBERIA": "#E8000B", "ESP": "#2457F5", "PRT": "#C5DCDC"}
MEDIA = "#F28C28"  # líneas de media de la UE: naranja, distinto de los colores de las áreas
RESTO = "#E3E6EE"  # resto de países: más claro que Portugal para no confundirlos
NOMBRE = {"UE27": "UE", "IBERIA": "Iberia", "ESP": "España", "PRT": "Portugal"}
LOCALE = {"number": {"decimal": ",", "thousands": ".", "grouping": [3], "currency": ["", " €"]}}


def es(x, d=1, suf=""):
    """1234.5 -> '1.234,5'."""
    if x is None or pd.isna(x):
        return "–"
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".") + suf


def millones(miles):
    """Miles de personas -> '12,6M'."""
    return es(miles / 1000, 1, "M")


def es_movil():
    try:
        ua = st.context.headers.get("User-Agent", "") or ""
    except Exception:
        return False
    return any(k in ua for k in ("Mobi", "Android", "iPhone"))


def _cfg(ch):
    return (ch.configure(locale=LOCALE, font="system-ui, -apple-system, Segoe UI, sans-serif")
              .configure_axis(grid=False, domainColor="#c3c2b7", labelColor=TEXTO_SUAVE, titleColor=TEXTO_SUAVE,
                              labelFontSize=12, titleFontSize=11, tickColor="#c3c2b7")
              .configure_view(stroke=None)
              .configure_legend(orient="top", title=None, labelFontSize=12, symbolType="square", labelColor=TEXTO))


def mostrar(ch):
    st.altair_chart(_cfg(ch), width="stretch", theme=None)


def leyenda(items):
    """Cuadrado de color + texto, en línea: [(color, texto), ...]."""
    html = "".join(f"<span style='display:inline-flex;align-items:center;margin-right:1.4rem;font-size:1.05rem;color:{TEXTO}'>"
                   f"<span style='width:14px;height:14px;background:{c};display:inline-block;margin-right:0.45rem'></span>{t}</span>"
                   for c, t in items)
    st.markdown(f"<div style='text-align:center;margin:0.2rem 0 0.8rem 0'>{html}</div>", unsafe_allow_html=True)


def dona(partes, alto=234, centro=None):
    """partes: [(etiqueta, valor, color)]. Dona con el porcentaje de cada parte en el tooltip y un texto en el centro."""
    d = pd.DataFrame(partes, columns=["parte", "valor", "color"])
    if d.empty or d.valor.isna().any():
        st.info("Sin datos para este año.")
        return
    d["pct"] = 100 * d.valor / d.valor.sum()
    d["orden"] = range(len(d))
    radio = 72  # tamaño fijo y pequeño, con margen: no se corta ni por arriba ni en columnas estrechas
    ch = alt.Chart(d).mark_arc(innerRadius=46, outerRadius=radio, stroke="#ffffff", strokeWidth=1).encode(
        theta=alt.Theta("valor:Q", stack=True), order=alt.Order("orden:Q"),
        color=alt.Color("color:N", scale=None),
        tooltip=[alt.Tooltip("parte:N", title=""), alt.Tooltip("pct:Q", format=",.1f", title="%")])
    if centro:
        ch += alt.Chart(pd.DataFrame({"t": [centro]})).mark_text(fontSize=15, fontWeight="bold", color=COLOR["IBERIA"]).encode(text="t:N")
    mostrar(ch.properties(height=alto))


def barras_areas(d, col, alto_fila=78, media=None):
    """Barras horizontales por área (d con area_id y la columna en miles), en el orden de d y con la cifra en millones.
    media: valor de la media de la UE por país (total UE / 27), como línea discontinua de referencia."""
    d = d.dropna(subset=[col]).copy()
    if d.empty:
        st.info("Sin datos para este año.")
        return
    d["area"] = d.area_id.map(NOMBRE)
    d["color"] = d.area_id.map(COLOR)
    d["etiqueta"] = d[col].map(millones)
    orden = d.area.tolist()
    base = alt.Chart(d).encode(y=alt.Y("area:N", sort=orden, title=None, axis=alt.Axis(domain=False, ticks=False, labelPadding=8)),
                               x=alt.X(f"{col}:Q", title=None, axis=None, scale=alt.Scale(domainMax=float(d[col].max()) * 1.35)))
    b = base.mark_bar(height=max(10, alto_fila - 20)).encode(
        color=alt.Color("color:N", scale=None),
        tooltip=[alt.Tooltip("area:N", title=""), alt.Tooltip("etiqueta:N", title="Personas")])
    t = base.mark_text(align="left", dx=5, fontSize=12, color=TEXTO_SUAVE).encode(text="etiqueta:N")
    capas = b + t
    if media is not None and media == media:
        m = pd.DataFrame({"media": [media], "t": [f"Media UE por país: {millones(media)}"]})
        regla = alt.Chart(m).encode(x=alt.X("media:Q", title=None), tooltip=[alt.Tooltip("t:N", title="")])
        capas += regla.mark_rule(color=MEDIA, strokeDash=[5, 4], strokeWidth=2.5)
        capas += regla.mark_text(align="left", baseline="bottom", dx=4, dy=-2, y=0, fontSize=11, fontWeight="bold", color=MEDIA).encode(text="t:N")
    mostrar(capas.properties(height=alto_fila * len(d)))


def lineas(d, x, y, serie, fmt=",.1f", titulo=None, alto=340, nombres=None):
    """Líneas por área con sus colores fijos. nombres: etiquetas de la leyenda distintas de NOMBRE."""
    if d.empty:
        st.info("Sin datos en esta carga.")
        return
    d = d.copy()
    nombres = {**NOMBRE, **(nombres or {})}
    d["Área"] = d[serie].map(nombres).fillna(d[serie])
    areas = [a for a in COLOR if nombres[a] in set(d["Área"])]
    ch = alt.Chart(d).mark_line(point=True, strokeWidth=2.5).encode(
        x=alt.X(f"{x}:O", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(f"{y}:Q", title=titulo, axis=alt.Axis(format=fmt), scale=alt.Scale(zero=False)),
        color=alt.Color("Área:N", sort=[nombres[a] for a in areas],
                        scale=alt.Scale(domain=[nombres[a] for a in areas], range=[COLOR[a] for a in areas]),
                        legend=alt.Legend(labelLimit=400)),
        tooltip=[alt.Tooltip("Área:N"), alt.Tooltip(f"{x}:O", title="Año"), alt.Tooltip(f"{y}:Q", format=fmt, title=titulo or y)])
    mostrar(ch.properties(height=alto))


def ranking(d, cat, val, color, fmt=",.1f", titulo=None, ref=None, ref_texto="Media UE"):
    """Barras horizontales ordenadas de mayor a menor; color: columna con el color de cada barra. ref: línea vertical (p. ej. la UE)."""
    if d.empty:
        st.info("Sin datos para este año.")
        return
    orden = d.sort_values(val, ascending=False)[cat].tolist()
    base = alt.Chart(d).encode(y=alt.Y(f"{cat}:N", sort=orden, title=None), x=alt.X(f"{val}:Q", title=titulo, axis=alt.Axis(format=fmt)))
    capas = base.mark_bar(cornerRadiusEnd=3, height=14).encode(
        color=alt.Color(f"{color}:N", scale=None),
        tooltip=[alt.Tooltip(f"{cat}:N", title=""), alt.Tooltip(f"{val}:Q", format=fmt, title=titulo or val)])
    capas += base.mark_text(align="left", dx=4, fontSize=11, color=TEXTO).encode(text=alt.Text(f"{val}:Q", format=fmt))
    if ref is not None:
        etiqueta = f"{ref_texto}: {es(ref, 1 if fmt.endswith('.1f') else 0)}"
        r = alt.Chart(pd.DataFrame({"media": [ref], "t": [etiqueta]})).encode(x=alt.X("media:Q", title=None), tooltip=[alt.Tooltip("t:N", title="")])
        capas += r.mark_rule(color=MEDIA, strokeDash=[5, 4], strokeWidth=2.5)
        capas += r.mark_text(align="left", baseline="bottom", dx=4, y=-4, fontSize=11, fontWeight="bold", color=MEDIA).encode(text="t:N")
    mostrar(capas.properties(height=22 * len(d)))
