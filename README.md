# C&C Dashboard (Streamlit)

Aplicación de análisis en Streamlit con dos módulos:
- Robot de descarga de reportes desde Mercat (Selenium)
- Dashboards de análisis de ventas y operación

## Estructura y entrada
- Archivos de reporte en `data/reportes/` (`.csv` o `.xlsx`)
- App principal en `dashboards/app.py`

## Variables de entorno
Definir antes de ejecutar:
- `MERCAT_USER`: usuario para Mercat (solo si usas el Robot)
- `MERCAT_PASS`: contraseña para Mercat (solo si usas el Robot)
- `STREAMLIT_SERVER_PORT` (opcional): puerto del servidor, por defecto 8501

En Windows PowerShell:
```powershell
$env:MERCAT_USER = "tu_usuario"
$env:MERCAT_PASS = "tu_password"
$env:STREAMLIT_SERVER_PORT = "8501"
```

## Instalación
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecución local
```powershell
streamlit run dashboards/app.py --server.port $env:STREAMLIT_SERVER_PORT
```

## Despliegue
### Opción 1: Streamlit Cloud
- Subir el repo y configurar los Secrets:
  - `MERCAT_USER`, `MERCAT_PASS`
- Consideración: el módulo Robot requiere navegador (Chrome) y puede no funcionar en entornos serverless sin soporte de navegador.

### Opción 2: Render (Docker)
- Ya incluí `Dockerfile` y `render.yaml` listos.
- Variables de entorno: `MERCAT_USER`, `MERCAT_PASS` (secrets), `CHROME_HEADLESS=true`.
- Puerto: Render usa 10000 en esta configuración.

Pasos:
1. Conecta tu repo a Render.
2. Crea un servicio Web con “Use Docker” y Render detectará `render.yaml`.
3. En “Environment”, agrega secrets:
   - `MERCAT_USER` y `MERCAT_PASS` (sin sync, inserta los valores en Render).
4. Deploy. La app quedará en `https://<tu-servicio>.onrender.com`.

### Opción 3: Hugging Face Spaces (Gradio/Streamlit)
- Funciona para el dashboard; el Robot puede no estar soportado por restricciones de navegador.

## Notas del Robot (Selenium)
- En producción, usa `--headless` en Chrome y valida que el host soporte Chromium.
- El robot descarga a `data/reportes/`; asegúrate de permisos de escritura.
- Evita guardar credenciales en código; usa variables de entorno/secrets.
 - `CHROME_HEADLESS` controla el modo headless (default: `true`).

## Tests
```powershell
pytest -q
```
