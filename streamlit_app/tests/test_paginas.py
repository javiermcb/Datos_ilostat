"""
Prueba de humo de la app: abre cada página con la muestra del modelo (resultados/dev_modelo) y falla si alguna
lanza una excepción o muestra un error. Se ejecuta en GitHub Actions en cada cambio de streamlit_app/ (app_pruebas.yml).

En local:  cd streamlit_app && python -m pytest tests -q
"""
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent
os.environ.setdefault("ILO_DATOS", str(APP.parent / "resultados" / "dev_modelo"))
PAGINAS = sorted(p.name for p in (APP / "paginas").glob("*.py"))


@pytest.mark.parametrize("genero", ["Todos", "Mujeres"])
@pytest.mark.parametrize("pagina", PAGINAS)
def test_pagina_sin_errores(pagina, genero, monkeypatch):
    monkeypatch.chdir(APP)
    at = AppTest.from_file(str(APP / "app.py"), default_timeout=120)
    at.run()
    at.selectbox(key="genero").set_value(genero).run()
    at.switch_page(f"paginas/{pagina}").run()
    errores = [e.value for e in at.exception]
    assert not errores, f"{pagina}: {errores[0] if errores else ''}"
    assert not at.error, f"{pagina}: {[e.value for e in at.error]}"


def test_panel_muestra_las_tres_magnitudes(monkeypatch):
    monkeypatch.chdir(APP)
    at = AppTest.from_file(str(APP / "app.py"), default_timeout=120).run()
    html = " ".join(m.value for m in at.markdown)
    for t in ("Población", "Fuerza Laboral", "Desempleo", "Iberia", "UE"):
        assert t in html
    assert at.selectbox(key="anyo").value is not None
