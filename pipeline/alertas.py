#!/usr/bin/env python3
"""
pipeline/alertas.py — Alertas de la carga: fallos de carga, datos nuevos y cambios fuertes en las tasas.

Entradas: datos/qa/ilostat_carga.csv, datos/modelo/marts/mart_comparativa.parquet,
          resultados/pipeline/ultimos_anyos.csv (carga anterior, de la rama calidad; si no existe, no hay «novedades»)
Salidas:  datos/qa/alertas.csv  (tipo;indicador;territorio;periodo;valor;referencia;mensaje;nivel)
          datos/qa/alertas.md   el mismo contenido para leer
          datos/qa/ultimos_anyos.csv  último año de cada indicador y área (para comparar en la próxima carga)
Niveles:  'aviso' (fallo de carga o cambio de más de UMBRAL_PP puntos en un año) · 'novedad' (año nuevo publicado)
"""
import csv, sys
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
QA = RAIZ / "datos" / "qa"
MART = RAIZ / "datos" / "modelo" / "marts" / "mart_comparativa.parquet"
PREVIO = RAIZ / "resultados" / "pipeline" / "ultimos_anyos.csv"
AREAS = {"ESP": "España", "PRT": "Portugal", "IBERIA": "Iberia", "UE27": "UE"}
UMBRAL_PP = 1.0
CAMPOS = ["tipo", "indicador", "territorio", "periodo", "valor", "referencia", "mensaje", "nivel"]


def leer(p):
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def es(x, d=1):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main():
    QA.mkdir(parents=True, exist_ok=True)
    alertas = []
    for r in leer(QA / "ilostat_carga.csv"):
        if r["estado"] == "ERROR":
            alertas.append(["carga", r["indicador_id"], "", "", "", "", f"Sin datos: {r['error']}", "aviso"])
        elif r["estado"] == "ANTERIOR":
            alertas.append(["carga", r["indicador_id"], "", "", "", "", f"No actualizada en esta carga: {r['error']}", "aviso"])
        elif r["estado"] == "AVISO":
            alertas.append(["carga", r["indicador_id"], "", "", "", "", f"Control de calidad: {r['error']}", "aviso"])

    if MART.exists():
        con = duckdb.connect()
        ultimos = con.execute(f"""SELECT area_id, max(anyo) FILTER (WHERE poblacion IS NOT NULL) AS poblacion,
                                         max(anyo) FILTER (WHERE fuerza_laboral IS NOT NULL) AS fuerza_laboral,
                                         max(anyo) FILTER (WHERE desempleados IS NOT NULL) AS desempleados
                                  FROM '{MART}' WHERE sexo = 'Total' GROUP BY area_id ORDER BY area_id""").fetchall()
        previos = {(r["area_id"], r["indicador"]): r["anyo"] for r in leer(PREVIO)}
        with open(QA / "ultimos_anyos.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";"); w.writerow(["area_id", "indicador", "anyo"])
            for area, *anyos in ultimos:
                for ind, anyo in zip(("poblacion", "fuerza_laboral", "desempleados"), anyos):
                    w.writerow([area, ind, anyo or ""])
                    antes = previos.get((area, ind))
                    if area in AREAS and anyo and antes and int(anyo) > int(antes):
                        alertas.append(["novedad", ind, AREAS[area], str(anyo), "", antes,
                                        f"Nuevo año publicado: {anyo} (antes {antes})", "novedad"])
        # cambios fuertes en el último año de cada área (tasas de actividad y de paro)
        filas = con.execute(f"""
            WITH t AS (SELECT area_id, anyo, tasa_actividad, tasa_paro,
                              lag(tasa_actividad) OVER w AS act_ant, lag(tasa_paro) OVER w AS paro_ant, lag(anyo) OVER w AS anyo_ant
                       FROM '{MART}' WHERE sexo = 'Total' WINDOW w AS (PARTITION BY area_id ORDER BY anyo))
            SELECT area_id, anyo, tasa_actividad, act_ant, tasa_paro, paro_ant FROM t
            WHERE anyo_ant = anyo - 1 AND anyo = (SELECT max(anyo) FROM t t2 WHERE t2.area_id = t.area_id AND t2.tasa_paro IS NOT NULL)
            """).fetchall()
        for area, anyo, act, act_ant, paro, paro_ant in filas:
            if area not in AREAS:
                continue
            for nombre, v, ant in (("Tasa de paro", paro, paro_ant), ("Tasa de actividad", act, act_ant)):
                if v is not None and ant is not None and abs(v - ant) > UMBRAL_PP:
                    alertas.append(["indicador", nombre, AREAS[area], str(anyo), es(v), es(ant),
                                    f"{nombre} {es(v)} % en {anyo}: {'+' if v > ant else ''}{es(v - ant)} puntos en un año", "aviso"])

    with open(QA / "alertas.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";"); w.writerow(CAMPOS); w.writerows(alertas)
    texto = ["# Alertas de la carga", ""] + [f"- [{a[7]}] **{a[1]}** {a[2]} · {a[6]}" for a in alertas]
    (QA / "alertas.md").write_text("\n".join(texto if alertas else ["# Alertas de la carga", "", "Sin alertas."]) + "\n", encoding="utf-8")
    print(f"{len(alertas)} alertas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
