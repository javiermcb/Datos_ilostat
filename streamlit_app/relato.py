"""
relato.py — Piezas comunes de las páginas: estilo, resumen en cifras y pie con el último año de cada dato.
"""
from html import escape

import streamlit as st

CSS = """<style>
.il-titulo{font-size:2.6rem;font-weight:800;color:#00145A;text-align:center;line-height:1.15;margin:0.6rem 0 0.3rem 0}
.il-sub{font-size:1.25rem;color:#4a5585;text-align:center;margin:0 0 0.4rem 0}
.il-nota{color:#4a5585;font-size:0.85rem}
.il-resumen{border-left:4px solid #00145A;background:#F2F4FA;border-radius:8px;padding:0.6rem 1rem;margin:0.2rem 0 1rem 0}
.il-resumen ul{margin:0.1rem 0 0 1.1rem;padding:0}
.il-resumen li{margin:0.15rem 0;line-height:1.4}
.il-pie{border-top:1px solid #dfe3f0;margin-top:2rem;padding-top:0.6rem;color:#4a5585;font-size:0.8rem;line-height:1.9}
.il-pie span{display:inline-block;border:1px solid #dfe3f0;border-radius:999px;padding:0 0.55rem;margin:0 0.25rem 0.25rem 0;background:#fff;white-space:nowrap}
.il-pie b{color:#00145A;font-weight:600}
</style>"""


def estilo():
    st.markdown(CSS, unsafe_allow_html=True)


def titulo(texto, sub=None):
    estilo()
    st.markdown(f"<div class='il-titulo'>{escape(texto)}</div>" + (f"<div class='il-sub'>{escape(sub)}</div>" if sub else ""),
                unsafe_allow_html=True)


def nota(texto):
    st.markdown(f"<div class='il-nota'>{escape(texto)}</div>", unsafe_allow_html=True)


def resumen(puntos):
    lis = "".join(f"<li>{escape(p)}</li>" for p in puntos if p)
    if lis:
        estilo()
        st.markdown(f"<div class='il-resumen'><b>En resumen</b><ul>{lis}</ul></div>", unsafe_allow_html=True)


def pie_periodos(periodos):
    if not periodos:
        return
    chips = "".join(f"<span>{escape(n)}: <b>{escape(p)}</b></span>" for n, p in periodos)
    st.markdown("<div class='il-pie'>Último año publicado por ILOSTAT en esta carga:<br>" + chips + "</div>", unsafe_allow_html=True)
