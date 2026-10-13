# Operación · qué hacer cuando algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| Correo / issue **«Incidencias de carga»** con «La carga se ha interrumpido» | Un paso del pipeline ha fallado (código o configuración) | Abrir el enlace de la ejecución, ver el paso en rojo. La app sigue con los datos de la última carga buena. Corregir y lanzar *Actions → Pipeline ILOSTAT → Run workflow*. La issue se cierra sola con la siguiente carga sin fallos. |
| Issue **«Incidencias de carga»**: «No se han publicado los datos de hoy: no superan el control de calidad» | Falta una tabla de la app, está vacía o pierde más de la mitad de sus filas | La app sigue con la carga anterior. Ver qué tabla indica la issue y `ilostat_carga.csv` (rama `calidad`). Si la caída es legítima, lanzar a mano el pipeline con «Caída de filas máxima» más alta (p. ej. 0.9). |
| Issue **«Incidencias de carga»** con indicadores «ANTERIOR» | La API de ILOSTAT no respondía o cambió su formato | Si se repite varios días: lanzar *Actions → Exploración ILOSTAT* y comparar el formato con `pipeline/ilostat.py`. |
| Aviso «Control de calidad: faltan países» | ILOSTAT no tiene aún el último año de algún país | Normal en los primeros meses del año. Ese año no hay dato de la UE hasta que estén los 27 (página «Estado de los datos»). |
| La app dice **«No se han podido cargar los datos: acceso denegado»** | Ha caducado `ILO_DATOS_TOKEN` | Crear token nuevo (solo lectura, Contents, solo este repositorio) y cambiarlo en *Streamlit → Settings → Secrets*. |
| Falla **«Pruebas de la app»** tras un cambio | El cambio rompe una página | No publicar hasta que esté en verde; el log dice qué página y por qué. |
| Falla **«Mantener la app activa»** | App caída o privada | Abrir la app; si está dormida, despertarla; comprobar que sigue pública en *Share*. |
| La app muestra un dato raro | Revisión de ILOSTAT o cambio de encuesta en un país | Página **«Estado de los datos»**: encuesta usada por país y años; contrastar con ilostat.ilo.org. |

Calendario: renovar `ILO_DATOS_TOKEN` antes de su fecha de caducidad (apuntarla al crearlo).
