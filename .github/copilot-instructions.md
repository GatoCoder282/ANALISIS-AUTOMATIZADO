# Copilot Instructions for C&C Analytics Dashboard

## Project Overview
A Streamlit dashboard for C&C Cafetería analyzing sales and operations data from Mercat ERP. The app has two core modules:
1. **Robot Module**: Selenium-based automated downloader for Mercat reports
2. **Analytics Module**: Sales and operational analysis with KPIs, visualizations, and restaurant floor heatmaps

## Architecture & Data Flow

### Three-Layer Processing Pipeline
```
data/ → application/ → dashboards/
```

1. **Data Layer** (`data/`):
   - `robotMercat.py`: Selenium automation for downloading CSV reports from Mercat ERP
   - `config_reportes.py`: Report definitions with URLs, form fields, and button XPaths for 3 report types (Índice, Ventas, Por_Producto)
   - `reportes/`: Downloaded CSV/XLSX files storage

2. **Application Layer** (`application/`):
   - `procesamiento.py`: `AnalistaDeDatos` class - primary data cleaning/standardization for VENTAS and INDICE report types
   - `analista_operacional.py`: `AnalistaOperacional` class - fuses Ventas + Índice DataFrames for cross-analysis (e.g., service speed metrics)
   - `dataframe_creator.py`: Helper utilities

3. **Dashboard Layer** (`dashboards/`):
   - `app.py`: Main Streamlit app with 3 modes: Robot, Individual Analysis, Maestro (Fusion) Analysis

### Critical Data Transformation Pattern
Reports arrive raw from Mercat and undergo standardization:
- Money columns cleaned: `str.replace(r'[^\d.-]', '')` → `pd.to_numeric()`
- Datetime handling: `pd.to_datetime()` with `dayfirst=True` (Bolivia format: dd/mm/yyyy)
- Boolean flags: `Es_Valido`, `Es_Venta_Real`, `Es_Interno`, `Es_Alquiler` (excludes Yango membership fees)
- Mesa/Table normalization: `Mesa_Real` column for restaurant floor mapping

**Alquiler Exclusion Logic** (in `procesamiento.py`):
```python
patron_yango = r"\d[x×]\s*Cuota de membresía por Oficina C&C \(|1[x×]\s*Entrega de insumos \("
df["Es_Alquiler"] = df["Detalle"].str.contains(patron_yango, regex=True, case=False)
df["Es_Venta_Real"] = df["Es_Valido"] & (df["Tipo_Norm"] != "INTERNO") & (~df["Es_Alquiler"])
```
This ensures rental income (Yango memberships) is tracked separately from operational sales.

## Developer Workflows

### Local Development
```powershell
# Setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Environment variables (required for Robot module)
$env:MERCAT_USER = "your_username"
$env:MERCAT_PASS = "your_password"
$env:CHROME_HEADLESS = "false"  # Use "true" for production

# Run
streamlit run dashboards/app.py --server.port 8501
```

### Testing
```powershell
pytest -q  # Runs tests in tests/analista_test.py
```

### Robot Module Testing
Use `data/main.py` for standalone robot testing:
```python
bot = RobotMercat(carpeta_data)
bot.login(USUARIO, PASSWORD)
bot.descargar_reporte(REPORTES_CONFIG["Ventas"], params_ventas)
bot.renombrar_ultimo_archivo("custom_name")
```

## Project-Specific Conventions

### Mesa/Table Coordinates System
Restaurant floor visualization uses hardcoded 2D coordinates (0-130 X, 0-100 Y) in `obtener_coordenadas_mesas()`:
- **Balcón (B1-B5)**: Outdoor balcony section at X=12
- **Salón (S1-S6)**: Main indoor dining at X=50-78
- **Cubículos (C1-C6)**: Private booths at X=96
- **Barra (P1-P2)**: Bar seating at Y=32
- **SALA**: Consolidated private room at (120, 64)

When adding new tables, update coordinates in `dashboards/app.py:obtener_coordenadas_mesas()`.

### Report Type Detection
Files auto-detect type via column presence:
```python
if "Detalle" in df.columns: tipo = "VENTAS"
elif "Creado el" in df.columns: tipo = "INDICE"
```

### Selenium Stability Patterns
The robot uses explicit waits and fallback strategies:
```python
# Prefer execute_script for clicks (avoids overlay issues)
self.driver.execute_script("arguments[0].click();", element)

# Use webdriver-manager for local dev, system chromedriver in production
system_chromedriver = shutil.which('chromedriver')
if system_chromedriver:
    self.driver = webdriver.Chrome(service=Service(system_chromedriver), options=options)
```

### Column Name Variations
Multiple sources mean inconsistent names. The codebase handles aliases:
- Ticket ID: `Número`, `Numero`, `ticket_id`, `Ticket_ID`
- Amount: `Monto total`, `monto`, `Monto_Ventas`
- Date: `Fecha`, `Creado el`, `creado_el`, `Fecha_DT`, `Creado_DT`

Always check both raw and normalized names when debugging.

## Key Integration Points

### Maestro Fusion (Cross-Report Analysis)
`AnalistaOperacional` merges Ventas + Índice on `["Ticket_ID", "Dia_Join"]`:
```python
df_merged = pd.merge(left, right, on=["Ticket_ID", "Dia_Join"], how="left", suffixes=("", "_idx"))
```
This enables velocity metrics (time from `Creado_DT` to `Pagado_DT`) and cross-validation.

### Deployment Configurations
- **Streamlit Cloud**: Set `MERCAT_USER`, `MERCAT_PASS` as Secrets (headless mode may not work)
- **Render**: Uses `Dockerfile` with Chrome stable, `render.yaml` auto-detected, port 10000
- **Hugging Face**: Dashboard only (Selenium unsupported)

### Chrome Headless Control
`CHROME_HEADLESS` env var (default: `"true"`):
- Production: `--headless=new` for server environments
- Local dev: Set to `"false"` to watch browser automation

## Common Pitfalls

1. **Missing Environment Variables**: Robot fails silently if `MERCAT_USER`/`MERCAT_PASS` undefined. Always check with `os.environ.get()` and raise clear errors.

2. **FutureWarning on Mesa Coordinates**: Explicitly cast to float to avoid pandas warnings:
   ```python
   df_plot["X"] = pd.to_numeric(df_plot["X"], errors="coerce").astype(float)
   ```

3. **Date Format Consistency**: Bolivia uses dd/mm/yyyy. Always use `dayfirst=True` in `pd.to_datetime()`.

4. **Report Type Mismatch**: Some metrics require Índice data (e.g., `Creado_DT`, `Pagado_DT`). Check for column existence before calculating velocity KPIs.

5. **Unnamed Columns**: Raw CSVs have `Unnamed: X` columns. Always strip: `df = df.loc[:, ~df.columns.str.contains('^Unnamed')]`

## File Organization Patterns

- **Report CSVs**: Store in `data/reportes/` with descriptive names like `Reporte_de_ventas_Mercat_ENERO_2026.csv`
- **Menu Data**: Static reference files in `data/menu/` (e.g., `menuEnero2026.csv`)
- **Images**: Brand assets in `images/` (e.g., `CoffeeAndCompany_Marca-06.png`)

## References
- Mercat Report URLs: See `data/config_reportes.py` for exact endpoints
- Streamlit deployment docs: https://aka.ms/vscode-instructions-docs
- Key analysis logic: [application/procesamiento.py](application/procesamiento.py), [application/analista_operacional.py](application/analista_operacional.py)
