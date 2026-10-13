"""Modelo: una fuente por país, agregados Iberia y UE (solo con todos los países) y tasas (datos sintéticos, sin red)."""
import csv

import duckdb

import ilostat
import modelo

PAISES = [r["area_id"] for r in ilostat.leer_cfg("areas.csv") if r["tipo"] == "País"]


def _normalizado(tmp_path, filas):
    p = tmp_path / "normalizado" / "ilostat_valores.csv"
    p.parent.mkdir(parents=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["indicador_id", "area_id", "fuente", "sexo", "anyo", "valor", "estado_obs", "nota_fuente"])
        w.writerows(filas)


def _datos(anyos=(2024, 2025), falta=None):
    filas = []
    for a in anyos:
        for p in PAISES:
            if (p, a) == falta:
                continue
            filas += [["POP_XWAP_SEX_AGE_NB_A", p, "BA:1", "Total", a, 100, "", ""],
                      ["EAP_TEAP_SEX_AGE_NB_A", p, "BA:1", "Total", a, 60, "", ""],
                      ["UNE_TUNE_SEX_AGE_NB_A", p, "BA:1", "Total", a, 6, "", ""]]
    # segunda encuesta en España, solo con población: no debe elegirse ni sumarse dos veces
    filas.append(["POP_XWAP_SEX_AGE_NB_A", "ESP", "BA:9", "Total", 2025, 999, "", ""])
    return filas


def _mart(tmp_path):
    """{(area_id, anyo): fila} del mart (sexo Total), sin pandas (el pipeline solo instala duckdb)."""
    r = duckdb.sql(f"SELECT * FROM '{tmp_path / 'modelo' / 'marts' / 'mart_comparativa.parquet'}' WHERE sexo = 'Total'")
    return {(f["area_id"], f["anyo"]): f for f in (dict(zip(r.columns, x)) for x in r.fetchall())}


def test_agregados_y_tasas(tmp_path):
    _normalizado(tmp_path, _datos())
    modelo.main(tmp_path)
    m = _mart(tmp_path)
    assert m[("UE27", 2025)]["poblacion"] == 100 * len(PAISES)
    assert m[("IBERIA", 2025)]["poblacion"] == 200
    assert m[("ESP", 2025)]["poblacion"] == 100  # la otra encuesta no se usa
    assert m[("UE27", 2025)]["tasa_actividad"] == 60
    assert m[("IBERIA", 2025)]["tasa_paro"] == 10
    assert m[("IBERIA", 2025)]["cuota_ue_poblacion"] == round(100 * 2 / len(PAISES), 2)


def test_sin_ue_si_falta_un_pais(tmp_path):
    _normalizado(tmp_path, _datos(falta=("MLT", 2025)))
    modelo.main(tmp_path)
    m = _mart(tmp_path)
    assert ("UE27", 2025) not in m and ("UE27", 2024) in m
    falta = (tmp_path / "qa" / "ue_incompleta.csv").read_text(encoding="utf-8")
    assert "MLT" in falta and "2025" in falta
