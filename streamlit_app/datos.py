"""
datos.py — Acceso a los datos del modelo ILOSTAT (Parquet) para la app.

Origen de los datos (por orden):
  1. variable de entorno o secreto de Streamlit ILO_DATOS: carpeta local o URL base que contenga
     <tabla>.parquet y marts/<tabla>.parquet (p. ej. https://raw.githubusercontent.com/<usuario>/<repo>/datos-modelo/modelo/).
     Si el repositorio es privado, ILO_DATOS_TOKEN = token de GitHub con permiso de lectura de contenidos.
  2. ../datos/modelo (modelo generado en local por el pipeline)
Con una URL, cada fichero se descarga una vez a una carpeta temporal y se vuelve a descargar cada 6 horas.
Todas las consultas son SQL de DuckDB sobre vistas con el nombre de cada tabla.
"""
import os, tempfile, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent
CACHE = Path(tempfile.gettempdir()) / "ilostat_datos"
TTL = 6 * 3600
_ERRORES = {}  # {tabla: motivo} de la última carga (compartido por todas las sesiones, como la conexión)

TABLAS = ["dim_area", "dim_indicador", "fact_ilostat", "marts/mart_comparativa"]
# las cachés (conexión y consultas) llevan esta firma en la clave: al añadir una tabla, la app la carga al publicar el código
# en vez de seguir con la conexión antigua (sin la tabla) hasta que caduque la caché
FIRMA = "|".join(TABLAS)


def _ajuste(nombre):
    """Variable de entorno o secreto de Streamlit."""
    valor = os.environ.get(nombre)
    if not valor:
        try:
            valor = st.secrets.get(nombre)
        except Exception:
            valor = None
    return valor


def origen():
    return _ajuste("ILO_DATOS") or str(RAIZ.parent / "datos" / "modelo")


def _abrir(url, timeout):
    """Descarga una URL. Con ILO_DATOS_TOKEN (repositorio privado), una URL raw.githubusercontent.com/<dueño>/<repo>/<rama>/<ruta>
    se pide a la API de contenidos de GitHub con el token (lectura de contenidos)."""
    cab = {"User-Agent": "datos-ilostat-app"}
    token = _ajuste("ILO_DATOS_TOKEN")
    if token and url.startswith("https://raw.githubusercontent.com/"):
        dueno, repo, rama, ruta = url.removeprefix("https://raw.githubusercontent.com/").split("/", 3)
        url = f"https://api.github.com/repos/{dueno}/{repo}/contents/{ruta}?ref={rama}"
        cab |= {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.raw+json"}
    return urllib.request.urlopen(urllib.request.Request(url, headers=cab), timeout=timeout)


def _motivo(e):
    """Texto corto para el aviso de la app según el error de descarga."""
    import urllib.error
    if isinstance(e, urllib.error.HTTPError):
        if e.code in (401, 403):
            return f"acceso denegado (HTTP {e.code}): el token ILO_DATOS_TOKEN no es válido o ha caducado"
        if e.code == 404:
            return "no encontrado (HTTP 404): revisa la URL ILO_DATOS o que el token tenga acceso al repositorio"
        return f"HTTP {e.code}"
    return f"{type(e).__name__}: {e}"[:160]


def _ruta_local(base, rel):
    """(ruta local del fichero <rel>.parquet o None, error o None), descargándolo si el origen es una URL."""
    if not base.startswith("http"):
        p = Path(base) / f"{rel}.parquet"
        return (p, None) if p.exists() else (None, f"no existe {p}")
    destino = CACHE / f"{rel}.parquet"
    if destino.exists() and time.time() - destino.stat().st_mtime < TTL:
        return destino, None
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        url = base.rstrip("/") + f"/{rel}.parquet"
        with _abrir(url, 120) as r:
            tmp = destino.with_suffix(".tmp")
            tmp.write_bytes(r.read())
            tmp.replace(destino)
        return destino, None
    except Exception as e:
        # si falla, la última copia descargada (si la hay)
        return (destino if destino.exists() else None), _motivo(e)


def _extra(base, nombre):
    """alertas.csv, metadatos.json… junto a los Parquet."""
    if not base.startswith("http"):
        p = Path(base) / nombre
        return p.read_bytes() if p.exists() else None
    try:
        with _abrir(base.rstrip("/") + "/" + nombre, 60) as r:
            return r.read()
    except Exception:
        return None


def conexion():
    return _conexion(FIRMA)


@st.cache_resource(ttl=TTL, show_spinner="Cargando los datos…")
def _conexion(firma):  # sin «_» delante: Streamlit no usa en la clave los argumentos que empiezan por «_»
    base = origen()
    con = duckdb.connect()
    disponibles, faltan = [], []
    # descargas en paralelo: con una URL, la primera carga baja varios ficheros
    with ThreadPoolExecutor(max_workers=8) as ex:
        rutas = dict(zip(TABLAS, ex.map(lambda rel: _ruta_local(base, rel), TABLAS)))
    errores = {rel.split("/")[-1]: err for rel, (_, err) in rutas.items() if err}
    for rel in TABLAS:
        p = rutas[rel][0]
        nombre = rel.split("/")[-1]
        if p is None:
            faltan.append(nombre); continue
        con.execute(f"CREATE VIEW {nombre} AS SELECT * FROM read_parquet('{p.as_posix()}')")
        disponibles.append(nombre)
    alertas = _extra(base, "alertas.csv")
    if alertas:
        p = CACHE / "alertas.csv"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(alertas)
        con.execute(f"CREATE VIEW alertas AS SELECT * FROM read_csv('{p.as_posix()}', delim=';', header=true, all_varchar=true)")
        disponibles.append("alertas")
    _ERRORES.clear(); _ERRORES.update(errores)
    return con, disponibles, faltan


def errores_descarga():
    """{tabla: motivo} de las descargas que han fallado en la última carga de datos (con o sin copia anterior)."""
    conexion()
    return dict(_ERRORES)


def hay(*tablas):
    _, disp, _ = conexion()
    return all(t in disp for t in tablas)


def q(sql, params=None):
    """Consulta SQL -> DataFrame. Si una tabla no está disponible devuelve un DataFrame vacío."""
    return _q(sql, params, FIRMA)


@st.cache_data(ttl=TTL, show_spinner=False)
def _q(sql, params, firma):
    con, _, _ = conexion()
    try:
        return con.execute(sql, params or []).df()
    except duckdb.CatalogException:
        return pd.DataFrame()


@st.cache_data(ttl=TTL, show_spinner=False)
def metadatos():
    """metadatos.json del modelo: fecha de generación y filas por tabla."""
    import json
    m = _extra(origen(), "metadatos.json")
    try:
        return json.loads(m) if m else {}
    except Exception:
        return {}


def fecha_carga():
    return metadatos().get("generado")


@st.cache_data(ttl=TTL, show_spinner=False)
def csv_extra(nombre):
    """CSV de calidad publicado junto al modelo (fuentes_carga.csv, resumen_fuentes.csv…), separador ';'."""
    import io
    b = _extra(origen(), nombre)
    if not b:
        return pd.DataFrame()
    try:
        return pd.read_csv(io.BytesIO(b), sep=";", dtype=str).fillna("")
    except Exception:
        return pd.DataFrame()


def periodos():
    """[(fuente, año)]: hasta qué año llega cada dato en esta carga (para el pie de las páginas)."""
    return _periodos(FIRMA)


@st.cache_data(ttl=TTL, show_spinner=False)
def _periodos(firma):
    d = q("""SELECT a.nombre, max(m.anyo) FROM mart_comparativa m JOIN dim_area a USING (area_id)
             WHERE m.area_id IN ('ESP', 'PRT', 'UE27') AND m.desempleados IS NOT NULL AND m.sexo = 'Total'
             GROUP BY a.nombre ORDER BY a.nombre""")
    return [(f"ILOSTAT · {n}", str(int(a))) for n, a in d.itertuples(index=False)] if not d.empty else []


AREAS_PANEL = ["UE27", "IBERIA", "ESP", "PRT"]


def anyos():
    """Años con la UE completa (los 27 países), del más reciente al más antiguo."""
    d = q("SELECT DISTINCT anyo FROM mart_comparativa WHERE area_id = 'UE27' AND desempleados IS NOT NULL ORDER BY anyo DESC")
    return [int(x) for x in d.anyo] if not d.empty else []


def comparativa(sexo="Total", areas=None):
    """mart_comparativa de un sexo (y de unas áreas)."""
    areas = areas or AREAS_PANEL
    return q(f"SELECT * FROM mart_comparativa WHERE sexo = ? AND area_id IN ({', '.join('?' * len(areas))}) ORDER BY anyo, area_id",
             [sexo, *areas])
