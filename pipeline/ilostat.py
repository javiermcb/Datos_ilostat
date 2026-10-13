#!/usr/bin/env python3
"""
pipeline/ilostat.py — Ingesta de indicadores de ILOSTAT (API pública de la OIT, CSV) a la capa normalizada.

Lee pipeline/config/indicadores.csv y areas.csv y, por cada indicador:
  1. BRUTO       datos/raw/ilostat/<id>.csv            respuesta tal cual de la API (los 27 países de la UE)
  2. NORMALIZADO datos/normalizado/ilostat_valores.csv una fila por dato (país, fuente, sexo, año), 15 años o más
  3. QA          datos/qa/ilostat_carga.csv            estado, filas, países y años de cada indicador
Si un indicador falla y existe su última descarga buena (datos/raw/ilostat/<id>.csv, conservada en caché), se reutiliza
y se marca como ANTERIOR, con la fecha de esa carga (datos/estado_cargas.json).

API: https://rplumber.ilo.org/data/indicator/?id=<id>&ref_area=<A+B+...>&timefrom=<año>&format=.csv
Uso:  python pipeline/ilostat.py [--indicadores POP_XWAP_SEX_AGE_NB_A] [--desde 2010]
Solo librería estándar. Un indicador que falla no para los demás.
"""
import argparse, csv, io, sys, time, urllib.parse, urllib.request
from pathlib import Path

import estado

RAIZ = Path(__file__).resolve().parent.parent
CFG = RAIZ / "pipeline" / "config"
DATOS = RAIZ / "datos"
API = "https://rplumber.ilo.org/data/indicator/?id={id}&ref_area={areas}&timefrom={desde}&format=.csv"
UA = {"User-Agent": "Mozilla/5.0 datos-ilostat-pipeline/1.0"}
COLUMNAS = {"ref_area", "source", "indicator", "sex", "classif1", "time", "obs_value"}
EDAD = "AGE_YTHADULT_YGE15"  # 15 años o más (comprobado en la exploración: está en los 27 países)
SEXOS = {"SEX_T": "Total", "SEX_M": "Hombres", "SEX_F": "Mujeres"}


def leer_cfg(nombre):
    with open(CFG / nombre, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def validar(indicadores):
    """Error de configuración de indicadores.csv, o None si está bien."""
    ids = [r["indicador_id"] for r in indicadores]
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    if repetidos:
        return f"indicadores repetidos {repetidos}"
    malos = [r["indicador_id"] for r in indicadores if None in r]  # un ';' dentro de un texto desplaza las columnas
    if malos:
        return f"sobran columnas en {malos} (¿un ';' dentro del nombre o la nota?)"
    return None


def get(url, intentos=3):
    for i in range(intentos):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
                return r.read()
        except Exception:
            if i == intentos - 1:
                raise
            time.sleep(5 * (i + 1))


def leer_csv(b):
    """Filas del CSV de ILOSTAT. Error si la respuesta no es el CSV esperado (p. ej. un JSON de error de la API)."""
    texto = b.decode("utf-8-sig")
    filas = list(csv.DictReader(io.StringIO(texto)))
    faltan = COLUMNAS - set(filas[0].keys() if filas else [])
    if not filas or faltan:
        raise ValueError(f"respuesta inesperada (faltan columnas {sorted(faltan)}): {texto[:200]}")
    return filas


def normalizar(filas, paises):
    """Solo 15 años o más, los tres sexos y los países configurados. [(ref_area, source, sexo, año, valor, obs_status, nota)]"""
    out = []
    for f in filas:
        if f["classif1"] != EDAD or f["sex"] not in SEXOS or f["ref_area"] not in paises:
            continue
        try:
            valor = float(f["obs_value"])
            anyo = int(f["time"])
        except (TypeError, ValueError):
            continue  # dato sin valor (confidencial, no disponible)
        out.append((f["ref_area"], f["source"], SEXOS[f["sex"]], anyo, valor, f.get("obs_status", ""), f.get("note_source", "")))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indicadores", nargs="+")
    ap.add_argument("--desde", type=int, default=2010)
    a = ap.parse_args()

    indicadores = [r for r in leer_cfg("indicadores.csv") if not a.indicadores or r["indicador_id"] in a.indicadores]
    error = validar(indicadores)
    if error:
        sys.exit(f"indicadores.csv: {error}")
    paises = [r["area_id"] for r in leer_cfg("areas.csv") if r["tipo"] == "País"]
    for d in ("raw/ilostat", "normalizado", "qa"):
        (DATOS / d).mkdir(parents=True, exist_ok=True)

    fv = open(DATOS / "normalizado" / "ilostat_valores.csv", "w", newline="", encoding="utf-8")
    wv = csv.writer(fv)
    wv.writerow(["indicador_id", "area_id", "fuente", "sexo", "anyo", "valor", "estado_obs", "nota_fuente"])
    qa, ok = [], []
    for ind in indicadores:
        iid, t0 = ind["indicador_id"], time.time()
        url = API.format(id=iid, areas=urllib.parse.quote("+".join(paises), safe="+"), desde=a.desde)
        crudo = DATOS / "raw" / "ilostat" / f"{iid}.csv"
        situacion, nota = "OK", ""
        try:
            b = get(url)
            filas = leer_csv(b)
            crudo.write_bytes(b)
            ok.append(f"ilostat:{iid}")
        except Exception as e:
            error = f"{type(e).__name__}: {e}"[:250]
            if crudo.exists():  # última descarga buena, conservada en caché entre ejecuciones
                filas = leer_csv(crudo.read_bytes())
                situacion, nota = "ANTERIOR", f"{error} · se usa la última carga buena ({estado.ultima_ok(f'ilostat:{iid}')})"
            else:
                qa.append([iid, ind["tema"], "ERROR", "", "", "", "", f"{time.time() - t0:.0f}s", error])
                print(f"[{iid}] ERROR {e}")
                continue
        datos = normalizar(filas, set(paises))
        for d in datos:
            wv.writerow([iid, *d])
        anyos = [d[3] for d in datos]
        n_paises = len({d[0] for d in datos})
        if situacion == "OK" and n_paises < len(paises):
            situacion = "AVISO"
            nota = f"faltan países: {sorted(set(paises) - {d[0] for d in datos})}"
        qa.append([iid, ind["tema"], situacion, len(datos), n_paises, min(anyos, default=""), max(anyos, default=""),
                   f"{time.time() - t0:.0f}s", nota])
        print(f"[{iid}] {situacion} {len(datos)} datos, {n_paises} países, {min(anyos, default='')} – {max(anyos, default='')}")
        time.sleep(1)
    estado.marcar_ok(ok)
    fv.close()
    with open(DATOS / "qa" / "ilostat_carga.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["indicador_id", "tema", "estado", "datos", "paises", "anyo_min", "anyo_max", "tiempo", "error"])
        w.writerows(qa)
    errores = sum(1 for q in qa if q[2] == "ERROR")
    print(f"{len(qa) - errores} indicadores con datos, {errores} con error")
    return 1 if errores == len(qa) else 0


if __name__ == "__main__":
    sys.exit(main())
