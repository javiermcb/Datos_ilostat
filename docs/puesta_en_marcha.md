# Puesta en marcha

1. **Fusionar en `main`.** El pipeline solo publica desde `main`. Al fusionar, se ejecuta y crea las ramas
   `datos-modelo` (Parquet para la app) y `calidad` (informes). También se puede lanzar en *Actions → Pipeline ILOSTAT → Run workflow*.
2. **Permisos de Actions.** *Settings → Actions → General → Workflow permissions*: «Read and write permissions»
   (el pipeline escribe las ramas `datos-modelo` y `calidad` y abre issues).
3. **Token de lectura para la app** (el repositorio es privado). GitHub → *Settings → Developer settings →
   Fine-grained tokens*: solo este repositorio, permiso **Contents: Read-only**. Apuntar la fecha de caducidad.
4. **Desplegar la app** en share.streamlit.io: repositorio `javiermcb/Datos_ilostat`, rama `main`, fichero
   `streamlit_app/app.py`. Secretos:

   ```toml
   ILO_DATOS = "https://raw.githubusercontent.com/javiermcb/Datos_ilostat/datos-modelo/modelo/"
   ILO_DATOS_TOKEN = "github_pat_..."
   ```
5. **Mantenerla despierta.** *Settings → Secrets and variables → Actions → Variables*: crear `ILO_APP_URL` con la URL
   de la app. Sin esa variable, el workflow «Mantener la app activa» no hace nada.
