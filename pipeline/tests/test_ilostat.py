"""Lectura de la configuración y del CSV de ILOSTAT (sin red)."""
import pytest

import ilostat

CAB = "ref_area,source,indicator,sex,classif1,time,obs_value,obs_status,note_classif,note_indicator,note_source\n"


def test_configuracion_valida():
    ind = ilostat.leer_cfg("indicadores.csv")
    assert ind and ilostat.validar(ind) is None
    areas = ilostat.leer_cfg("areas.csv")
    assert sum(r["ue27"] == "1" for r in areas) == 27
    assert {r["area_id"] for r in areas if r["iberia"] == "1"} == {"ESP", "PRT"}


def test_validar_detecta_repetidos_y_columnas_de_mas():
    assert "repetidos" in ilostat.validar([{"indicador_id": "A"}, {"indicador_id": "A"}])
    assert "sobran columnas" in ilostat.validar([{"indicador_id": "B", None: ["x"]}])


def test_normaliza_solo_15_y_mas_y_sexos():
    b = (CAB + 'ESP,BA:2244,POP_XWAP_SEX_AGE_NB,SEX_T,AGE_YTHADULT_YGE15,2025,"41000.5",,,,R1:1\n'
         "ESP,BA:2244,POP_XWAP_SEX_AGE_NB,SEX_F,AGE_YTHADULT_YGE15,2025,21000,,,,\n"
         "ESP,BA:2244,POP_XWAP_SEX_AGE_NB,SEX_T,AGE_YTHADULT_Y15-24,2025,5000,,,,\n"
         "ESP,BA:2244,POP_XWAP_SEX_AGE_NB,SEX_O,AGE_YTHADULT_YGE15,2025,1,,,,\n"
         "USA,BA:1,POP_XWAP_SEX_AGE_NB,SEX_T,AGE_YTHADULT_YGE15,2025,1,,,,\n"
         "PRT,BA:2252,POP_XWAP_SEX_AGE_NB,SEX_T,AGE_YTHADULT_YGE15,2025,,,,,\n").encode()
    d = ilostat.normalizar(ilostat.leer_csv(b), {"ESP", "PRT"})
    assert d == [("ESP", "BA:2244", "Total", 2025, 41000.5, "", "R1:1"), ("ESP", "BA:2244", "Mujeres", 2025, 21000.0, "", "")]


def test_respuesta_de_error_no_se_acepta():
    with pytest.raises(ValueError):
        ilostat.leer_csv(b'{"error":"deprecated or invalid dataset id=X"}')
