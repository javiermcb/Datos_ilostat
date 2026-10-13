# App Streamlit · Iberia frente a la UE (ILOSTAT)

Lee los Parquet que genera el pipeline (`pipeline/`) y los consulta con DuckDB. Sin registro de acceso.

## Páginas

| Página | Contenido |
|---|---|
| Panel | Población (peso de Iberia en la UE), Fuerza laboral (tasa de actividad) y Desempleo (tasa de paro), Iberia frente a la UE, con barras de UE, España y Portugal |
| Evolución | Tasas de paro y de actividad por año y peso de Iberia en la UE |
| Países de la UE | Los 27 países ordenados por el indicador elegido, con España y Portugal resaltados |
| Datos y descargas | Tablas del modelo con filtros y descarga CSV |
| Estado de los datos | Última carga, estado de cada indicador, años sin UE completa y encuesta usada en cada país |

Filtros (barra lateral, comunes a todas las páginas): año (solo años con los 27 países) y género (Todos, Hombres, Mujeres).

## Ejecutar en local

```bash
pip install -r requirements.txt
ILO_DATOS=/ruta/al/modelo streamlit run app.py
```

`ILO_DATOS` (variable de entorno o secreto de Streamlit) puede ser una carpeta local con `<tabla>.parquet` y
`marts/<tabla>.parquet` o una URL base con la misma estructura (cada fichero se descarga una vez y se refresca cada 6 horas).
Sin `ILO_DATOS` se usa `../datos/modelo`. Si el repositorio es privado, `ILO_DATOS_TOKEN` = token de GitHub
*fine-grained* con **Contents: Read-only** solo en este repositorio.

## Pruebas

`tests/test_paginas.py` abre cada página con la muestra `resultados/dev_modelo` (datos reales de una carga) y falla si
alguna da error. Se ejecuta en GitHub Actions (`app_pruebas.yml`) en cada cambio de la app. En local:

```bash
pip install pytest
python -m pytest tests -q
```

## Despliegue

Ver `docs/puesta_en_marcha.md`.
