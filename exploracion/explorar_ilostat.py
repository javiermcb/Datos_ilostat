#!/usr/bin/env python3
"""
exploracion/explorar_ilostat.py — Comprueba qué ofrece ILOSTAT antes de diseñar el pipeline (formato, códigos, cobertura).

Prueba varias formas de descarga de cada indicador candidato y escribe en resultados/exploracion/:
  descargas.csv   indicador, método, estado HTTP, bytes, columnas
  cobertura.csv   indicador, método, país, fuente, sexo, classif1, años (mín–máx, nº)
  muestra_<id>.csv primeras filas tal cual
Uso: python exploracion/explorar_ilostat.py
"""
import csv, gzip, io, json, sys, urllib.request
from pathlib import Path

SALIDA = Path(__file__).resolve().parent.parent / "resultados" / "exploracion"
UE27 = ["AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN", "FRA", "DEU", "GRC", "HUN", "IRL", "ITA", "LVA",
        "LTU", "LUX", "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "ESP", "SWE"]
INDICADORES = ["POP_XWAP_SEX_AGE_NB_A", "EAP_TEAP_SEX_AGE_NB_A", "UNE_TUNE_SEX_AGE_NB_A",
               "POP_2POP_SEX_AGE_NB_A", "EAP_2EAP_SEX_AGE_NB_A", "UNE_2UNE_SEX_AGE_NB_A",
               "EAP_2WAP_SEX_AGE_RT_A", "UNE_2EAP_SEX_AGE_RT_A", "EAP_DWAP_SEX_AGE_RT_A", "UNE_DEAP_SEX_AGE_RT_A"]
METODOS = {
    "api_csv": "https://rplumber.ilo.org/data/indicator/?id={id}&ref_area={areas}&timefrom=2015&format=.csv",
    "bulk_csv_gz": "https://rplumber.ilo.org/files/website/bulk/indicator/{id}.csv.gz",
}
UA = {"User-Agent": "Mozilla/5.0 datos-ilostat-exploracion/1.0", "Accept-Encoding": "identity"}


def bajar(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
            return r.status, r.read(), r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:500], ""
    except Exception as e:
        return f"{type(e).__name__}: {e}"[:200], b"", ""


def filas_csv(b):
    if b[:2] == b"\x1f\x8b":
        b = gzip.decompress(b)
    texto = b.decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(texto)))


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    desc, cob = [], []
    # índice de indicadores (para saber qué ids existen)
    for nombre, url in {"toc_csv": "https://rplumber.ilo.org/metadata/toc/indicator/?lang=en&format=.csv",
                        "toc_json": "https://rplumber.ilo.org/metadata/toc/indicator/?lang=en"}.items():
        st, b, ct = bajar(url)
        print(f"[{nombre}] {st} {len(b)} bytes {ct}")
        print("  inicio:", b[:300])
        if st == 200 and b:
            (SALIDA / f"{nombre}.txt").write_bytes(b)
    areas = "+".join(UE27)
    for ind in INDICADORES:
        for metodo, plantilla in METODOS.items():
            url = plantilla.format(id=ind, areas=areas)
            st, b, ct = bajar(url)
            cols, n = "", 0
            if st == 200 and b:
                try:
                    filas = filas_csv(b)
                    n = len(filas)
                    cols = "|".join(filas[0].keys()) if filas else ""
                    (SALIDA / f"muestra_{ind}_{metodo}.csv").write_text(
                        "\n".join([",".join(filas[0].keys())] + [",".join(str(v) for v in f.values()) for f in filas[:40]]) if filas else "",
                        encoding="utf-8")
                    otros = sorted({f.get("ref_area", "") for f in filas} - set(UE27))
                    grupos = {}
                    for f in filas:
                        if f.get("ref_area") in UE27 or metodo == "api_csv":
                            k = (f.get("ref_area"), f.get("source"), f.get("sex"), f.get("classif1"))
                            grupos.setdefault(k, set()).add(f.get("time"))
                    for (ra, so, sx, c1), anyos in sorted(grupos.items(), key=lambda x: tuple(str(y) for y in x[0])):
                        cob.append([ind, metodo, ra, so, sx, c1, min(anyos), max(anyos), len(anyos)])
                    print(f"[{ind} {metodo}] {n} filas, columnas: {cols}")
                    print(f"   ref_area fuera de UE27 (primeros 60): {otros[:60]}")
                    print(f"   ejemplo: {json.dumps(filas[0], ensure_ascii=False) if filas else ''}")
                except Exception as e:
                    print(f"[{ind} {metodo}] no se puede leer: {e}; inicio: {b[:200]}")
            else:
                print(f"[{ind} {metodo}] {st} {b[:200]}")
            desc.append([ind, metodo, st, len(b), ct, n, cols])
    with open(SALIDA / "descargas.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";"); w.writerow(["indicador", "metodo", "estado", "bytes", "tipo", "filas", "columnas"]); w.writerows(desc)
    with open(SALIDA / "cobertura.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["indicador", "metodo", "ref_area", "source", "sex", "classif1", "anyo_min", "anyo_max", "n_anyos"]); w.writerows(cob)
    # resumen de cobertura en el log: por indicador y método, países con Total/15+ y último año
    print("\n=== Resumen (sex=SEX_T, classif1 con 'YGE15' o 'TOTAL') ===")
    for ind in INDICADORES:
        for metodo in METODOS:
            sel = [c for c in cob if c[0] == ind and c[1] == metodo and c[4] == "SEX_T" and ("YGE15" in (c[5] or "") or "TOTAL" in (c[5] or ""))]
            if sel:
                paises = sorted({c[2] for c in sel})
                print(f"{ind} {metodo}: {len(paises)} áreas · fuentes {sorted({c[3] for c in sel})[:6]} · classif1 {sorted({c[5] for c in sel})[:4]}"
                      f" · último año mín {min(c[7] for c in sel)} máx {max(c[7] for c in sel)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
