#!/usr/bin/env python3
"""
pipeline/publicacion.py — Prepara la carpeta que se publica en la rama datos-modelo (la que lee la app).

Entrada:  datos/modelo/*.parquet|csv (modelo.py), datos/qa/ilostat_carga.csv, datos/qa/alertas.csv
Salida:   datos/publicar/
            README.md              qué hay, fecha de actualización y último año de cada indicador
            modelo/                los Parquet y CSV del modelo + indicadores.csv + alertas.csv
            modelo/metadatos.json  fecha de generación, filas por tabla e indicadores no actualizados
Uso:      python pipeline/publicacion.py [--repo usuario/repositorio]
"""
import argparse, csv, json, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
MODELO, PUB = RAIZ / "datos" / "modelo", RAIZ / "datos" / "publicar"
CFG = RAIZ / "pipeline" / "config"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="USUARIO/REPOSITORIO")
    a = ap.parse_args()

    if PUB.exists():
        shutil.rmtree(PUB)
    (PUB / "modelo").mkdir(parents=True)
    for f in MODELO.iterdir():
        (shutil.copytree if f.is_dir() else shutil.copy2)(f, PUB / "modelo" / f.name)
    shutil.copy2(CFG / "indicadores.csv", PUB / "modelo" / "indicadores.csv")
    alertas = RAIZ / "datos" / "qa" / "alertas.csv"
    if alertas.exists():
        shutil.copy2(alertas, PUB / "modelo" / "alertas.csv")

    con = duckdb.connect()
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    tablas = {}
    for p in sorted(MODELO.glob("*.parquet")) + sorted(MODELO.glob("marts/*.parquet")):
        n = con.execute(f"SELECT count(*) FROM '{p}'").fetchone()[0]
        tablas[str(p.relative_to(MODELO).with_suffix(""))] = {"filas": n, "bytes_parquet": p.stat().st_size}
    indicadores = con.execute(f"""SELECT indicador_id, nombre, anyo_min, anyo_max, anyo_max_ue
                                  FROM '{MODELO / "dim_indicador.parquet"}' ORDER BY indicador_id""").fetchall()
    incidencias = []
    q = RAIZ / "datos" / "qa" / "ilostat_carga.csv"
    if q.exists():
        with open(q, encoding="utf-8") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                if r["estado"] in ("ANTERIOR", "ERROR"):
                    incidencias.append({"tabla": r["indicador_id"], "estado": r["estado"], "detalle": r["error"][:300]})
    meta = {"generado": ahora, "ficheros": tablas, "incidencias_carga": incidencias,
            "indicadores": [{"indicador_id": i, "nombre": n, "anyo_min": a0, "anyo_max": a1, "anyo_max_ue": ue}
                            for i, n, a0, a1, ue in indicadores]}
    (PUB / "modelo" / "metadatos.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    miles = lambda n: f"{n:,}".replace(",", ".")
    ficheros = "\n".join(f"| `modelo/{k}.parquet` | {miles(v['filas'])} | {v['bytes_parquet'] / 1e3:.0f} kB |" for k, v in tablas.items())
    filas = "\n".join(f"| `{i}` | {n} | {a0}–{a1} | {ue or ''} |" for i, n, a0, a1, ue in indicadores)
    aviso = ""
    if incidencias:
        aviso = "\n> **Indicadores no actualizados en esta carga** (se mantiene su última versión buena, o no hay datos):\n" + "\n".join(
            f"> - `{i['tabla']}` · {i['estado']} · {i['detalle']}" for i in incidencias) + "\n"
    (PUB / "README.md").write_text(f"""# Datos ILOSTAT · España, Portugal, Iberia y UE

Modelo de datos generado automáticamente a partir de **ILOSTAT** (Organización Internacional del Trabajo).
**Última actualización: {ahora}.**
{aviso}
## Ficheros

| Fichero | Filas | Tamaño |
|---|---|---|
{ficheros}

Cada tabla está también en CSV (`;` como separador). `modelo/metadatos.json` indica la fecha de generación y las filas
de cada tabla. URL base: `https://raw.githubusercontent.com/{a.repo}/datos-modelo/modelo/`

`fact_ilostat` mezcla magnitudes: filtra siempre por `indicador` y `sexo` antes de sumar `valor` (miles de personas).
Iberia (España + Portugal) y UE (suma de los 27 países, solo en años con los 27) son agregados de elaboración propia.

## Indicadores

| Indicador | Nombre | Años | Último año con la UE completa |
|---|---|---|---|
{filas}

Fuente: OIT, ILOSTAT, API pública `rplumber.ilo.org/data/indicator`.
""", encoding="utf-8")
    print(f"Publicación preparada en {PUB} ({len(tablas)} tablas)")


if __name__ == "__main__":
    sys.exit(main())
