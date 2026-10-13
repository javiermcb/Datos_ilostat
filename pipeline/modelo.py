#!/usr/bin/env python3
"""
pipeline/modelo.py — Construye el modelo a partir de la capa normalizada (DuckDB).

Entradas:  datos/normalizado/ilostat_valores.csv (ilostat.py), datos/qa/ilostat_carga.csv
           pipeline/config/indicadores.csv, areas.csv
Salidas:   datos/modelo/fact_ilostat.parquet          una fila por indicador, área, sexo y año (países, Iberia y UE)
           datos/modelo/dim_area.parquet              países de la UE y agregados (Iberia, UE)
           datos/modelo/dim_indicador.parquet         qué es cada indicador y hasta qué año llega
           datos/modelo/marts/mart_comparativa.parquet  población, fuerza laboral, desempleados y tasas por área, sexo y año
           (y los mismos en .csv) · datos/ilostat.duckdb para consultas SQL
QA:        datos/qa/fuentes_elegidas.csv  fuente de ILOSTAT usada en cada país (si hay varias, una sola por país)
           datos/qa/ue_incompleta.csv     años en los que falta algún país (sin dato de UE ese año)
           datos/qa/resumen_fuentes.csv   filas y periodo de cada tabla publicada

Agregados (elaboración propia, no son cifras de la OIT):
  Iberia = España + Portugal · UE = suma de los 27 países, solo en los años en que están los 27.
  Tasas: actividad = fuerza laboral / población 15+; paro = desempleados / fuerza laboral.
Uso:  python pipeline/modelo.py      (requiere: pip install duckdb)
"""
import sys
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
CFG = RAIZ / "pipeline" / "config"
DATOS = RAIZ / "datos"


def main(datos=DATOS, cfg=CFG):
    norm, modelo, qa = datos / "normalizado", datos / "modelo", datos / "qa"
    (modelo / "marts").mkdir(parents=True, exist_ok=True); qa.mkdir(parents=True, exist_ok=True)
    db = datos / "ilostat.duckdb"
    if db.exists():
        db.unlink()
    con = duckdb.connect(str(db))

    con.execute(f"""CREATE TABLE valores AS SELECT indicador_id, area_id, fuente, sexo, CAST(anyo AS INTEGER) AS anyo,
                    CAST(valor AS DOUBLE) AS valor, estado_obs, nota_fuente
                    FROM read_csv('{norm / "ilostat_valores.csv"}', header=true, all_varchar=true)""")
    con.execute(f"CREATE TABLE cfg_ind AS SELECT * FROM read_csv('{cfg / 'indicadores.csv'}', header=true, delim=';', all_varchar=true)")
    con.execute(f"""CREATE TABLE dim_area AS SELECT area_id, nombre, tipo, ue27 = '1' AS ue27, iberia = '1' AS iberia
                    FROM read_csv('{cfg / 'areas.csv'}', header=true, delim=';', all_varchar=true)""")
    n_ue = con.execute("SELECT count(*) FROM dim_area WHERE ue27").fetchone()[0]
    n_ib = con.execute("SELECT count(*) FROM dim_area WHERE iberia").fetchone()[0]

    # 1) una sola fuente por país (ILOSTAT puede dar varias encuestas para el mismo país): la que cubre más indicadores,
    #    luego la que llega a un año más reciente y luego la que tiene más datos. Así las tasas usan siempre la misma encuesta.
    con.execute("""
    CREATE TABLE fuentes_elegidas AS
    WITH r AS (
        SELECT area_id, fuente, count(DISTINCT indicador_id) AS indicadores, max(anyo) AS ultimo_anyo, min(anyo) AS primer_anyo,
               count(*) AS datos
        FROM valores GROUP BY ALL
    )
    SELECT *, row_number() OVER (PARTITION BY area_id ORDER BY indicadores DESC, ultimo_anyo DESC, datos DESC, fuente) = 1 AS elegida,
           count(*) OVER (PARTITION BY area_id) AS fuentes_disponibles
    FROM r
    """)

    # 2) datos por país con la fuente elegida
    con.execute("""
    CREATE TABLE fact_pais AS
    SELECT v.indicador_id, c.clave AS indicador, v.area_id, v.sexo, v.anyo, v.valor, v.fuente, v.estado_obs,
           1 AS n_paises, false AS es_agregado
    FROM valores v JOIN fuentes_elegidas f ON f.area_id = v.area_id AND f.fuente = v.fuente AND f.elegida
    JOIN cfg_ind c USING (indicador_id)
    """)

    # 3) agregados: Iberia y UE, solo cuando están todos sus países (si falta uno, la suma no sería comparable)
    con.execute(f"""
    CREATE TABLE fact_agregado AS
    SELECT indicador_id, indicador, 'IBERIA' AS area_id, sexo, anyo, sum(valor) AS valor, 'Suma de países' AS fuente,
           '' AS estado_obs, count(*) AS n_paises, true AS es_agregado
    FROM fact_pais JOIN dim_area USING (area_id) WHERE iberia GROUP BY ALL HAVING count(*) = {n_ib}
    UNION ALL
    SELECT indicador_id, indicador, 'UE27', sexo, anyo, sum(valor), 'Suma de países', '', count(*), true
    FROM fact_pais JOIN dim_area USING (area_id) WHERE ue27 GROUP BY ALL HAVING count(*) = {n_ue}
    """)
    con.execute(f"""COPY (
        SELECT k.indicador_id, k.sexo, k.anyo, count(p.area_id) AS paises_con_dato,
               string_agg(a.area_id, ',' ORDER BY a.area_id) FILTER (WHERE p.area_id IS NULL) AS faltan
        FROM (SELECT DISTINCT indicador_id, sexo, anyo FROM fact_pais) k
        CROSS JOIN (SELECT area_id FROM dim_area WHERE ue27) a
        LEFT JOIN fact_pais p ON p.indicador_id = k.indicador_id AND p.sexo = k.sexo AND p.anyo = k.anyo AND p.area_id = a.area_id
        GROUP BY ALL HAVING count(p.area_id) < {n_ue} ORDER BY ALL
    ) TO '{qa / "ue_incompleta.csv"}' (HEADER, DELIMITER ';')""")

    con.execute("CREATE TABLE fact_ilostat AS SELECT * FROM fact_pais UNION ALL SELECT * FROM fact_agregado")

    # 4) tabla lista para el panel: una fila por área, sexo y año con las tres magnitudes y las tasas
    con.execute("""
    CREATE TABLE mart_comparativa AS
    WITH p AS (
        PIVOT (SELECT area_id, sexo, anyo, indicador, valor FROM fact_ilostat) ON indicador IN ('poblacion', 'fuerza_laboral', 'desempleados')
        USING first(valor)
    )
    SELECT p.anyo, p.sexo, p.area_id, a.nombre AS area, a.tipo,
           p.poblacion, p.fuerza_laboral, p.desempleados,
           round(100 * p.fuerza_laboral / nullif(p.poblacion, 0), 2) AS tasa_actividad,
           round(100 * p.desempleados / nullif(p.fuerza_laboral, 0), 2) AS tasa_paro,
           round(100 * p.poblacion / nullif(ue.poblacion, 0), 2) AS cuota_ue_poblacion,
           round(100 * p.fuerza_laboral / nullif(ue.fuerza_laboral, 0), 2) AS cuota_ue_fuerza_laboral,
           round(100 * p.desempleados / nullif(ue.desempleados, 0), 2) AS cuota_ue_desempleados
    FROM p JOIN dim_area a USING (area_id)
    LEFT JOIN p ue ON ue.area_id = 'UE27' AND ue.sexo = p.sexo AND ue.anyo = p.anyo
    ORDER BY p.anyo, p.sexo, p.area_id
    """)

    con.execute("""
    CREATE TABLE dim_indicador AS
    SELECT c.indicador_id, c.clave AS indicador, c.nombre, c.tema, c.unidad, c.nota, 'OIT (ILOSTAT)' AS organismo,
           'https://rplumber.ilo.org/data/indicator/?id=' || c.indicador_id || '&format=.csv' AS url_api,
           min(f.anyo) AS anyo_min, max(f.anyo) AS anyo_max, max(f.anyo) FILTER (WHERE f.area_id = 'UE27') AS anyo_max_ue
    FROM cfg_ind c LEFT JOIN fact_ilostat f ON f.indicador_id = c.indicador_id GROUP BY ALL ORDER BY c.indicador_id
    """)

    # 5) exportar
    tablas = {"fact_ilostat": modelo, "dim_area": modelo, "dim_indicador": modelo, "mart_comparativa": modelo / "marts"}
    for t, carpeta in tablas.items():
        con.execute(f"COPY {t} TO '{carpeta / (t + '.parquet')}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        con.execute(f"COPY {t} TO '{carpeta / (t + '.csv')}' (HEADER, DELIMITER ';')")

    # 6) QA
    con.execute(f"COPY (SELECT * FROM fuentes_elegidas ORDER BY area_id, NOT elegida, fuente) TO '{qa / 'fuentes_elegidas.csv'}' (HEADER, DELIMITER ';')")
    con.execute(f"""COPY (
        SELECT 'fact_ilostat' AS tabla, count(*) AS filas, min(anyo)::VARCHAR AS desde, max(anyo)::VARCHAR AS hasta FROM fact_ilostat
        UNION ALL SELECT 'mart_comparativa', count(*), min(anyo)::VARCHAR, max(anyo)::VARCHAR FROM mart_comparativa
        UNION ALL SELECT 'mart_comparativa (UE)', count(*), min(anyo)::VARCHAR, max(anyo)::VARCHAR FROM mart_comparativa WHERE area_id = 'UE27'
    ) TO '{qa / "resumen_fuentes.csv"}' (HEADER, DELIMITER ';')""")
    n = con.execute("SELECT count(*) FROM fact_ilostat").fetchone()[0]
    ue = con.execute("SELECT max(anyo) FROM fact_ilostat WHERE area_id = 'UE27'").fetchone()[0]
    varias = con.execute("SELECT count(*) FROM fuentes_elegidas WHERE elegida AND fuentes_disponibles > 1").fetchone()[0]
    print(f"fact_ilostat: {n} filas · último año con la UE completa: {ue} · países con varias fuentes: {varias}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
