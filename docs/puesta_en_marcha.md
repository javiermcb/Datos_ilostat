# Puesta en marcha

1. **Fusionar en `main`.** El pipeline solo publica desde `main`. Al fusionar, se ejecuta y crea las ramas
   `datos-modelo` (Parquet para la app) y `calidad` (informes). También se puede lanzar en *Actions → Pipeline ILOSTAT → Run workflow*.
2. **Repositorio público.** Streamlit Community Cloud solo permite una app privada por espacio de trabajo; con el
   repositorio público la app es pública y la app lee los datos sin token.
3. **Desplegar la app** en share.streamlit.io: repositorio `javiermcb/Datos_ilostat`, rama `main`, fichero
   `streamlit_app/app.py`. Secretos:

   ```toml
   ILO_DATOS = "https://raw.githubusercontent.com/javiermcb/Datos_ilostat/datos-modelo/modelo/"
   ```
4. **Mantenerla despierta.** El workflow «Mantener la app activa» visita https://datos-ilostar.streamlit.app/ cada 4 horas.
   Si la URL cambia, crear la variable `ILO_APP_URL` (*Settings → Secrets and variables → Actions → Variables*) con la nueva.
