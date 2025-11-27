from time import time
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import glob
import sys
# Aseguramos que python encuentre los archivos si están en la misma carpeta
sys.path.append(os.getcwd()) 

from data.robotMercat import RobotMercat
from data.config_reportes import REPORTES_CONFIG
from procesamiento import AnalistaDeDatos

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Dashboard C&C", layout="wide")

# --- FUNCIONES DE TUS NOTEBOOKS (BACKEND) ---
# Traídas directamente de tu Indice_Mercat.ipynb
def limpiar_columnas_unnamed(df: pd.DataFrame):
    df = df.dropna(axis=1, how='all')
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    return df

def transformar_fechas(df: pd.DataFrame):
    if "Creado el" in df.columns:
        df["Creado el"] = pd.to_datetime(df["Creado el"], errors="coerce", dayfirst=True)
        df["Fecha"] = df["Creado el"].dt.date
        df["Hora"] = df["Creado el"].dt.hour
    return df

# Traídas de AnalisisPan.ipynb
def detectar_pan(producto: str):
    tipos_pan = ["Pan Blanco", "Pan Integral", "Pan de orégano y aceituna", "Pan de tomate y albahaca"]
    if not isinstance(producto, str): return None
    for pan in tipos_pan:
        if pan.lower() in producto.lower():
            return pan
    return "Sin Especificar"

# --- CARGA DE DATOS ---
def cargar_datos():
    try:
        # Busca el archivo más reciente en data/reportes
        ruta_busqueda = os.path.join("data", "reportes", "*.csv")
        archivos = glob.glob(ruta_busqueda)
        
        if not archivos:
            return None, None # Retorna (df, nombre_archivo)

        ultimo_archivo = max(archivos, key=os.path.getctime)
        nombre_archivo = os.path.basename(ultimo_archivo)
        
        # Leemos el archivo
        df = pd.read_csv(ultimo_archivo)
        
        # Limpieza básica común
        df = limpiar_columnas_unnamed(df)
        
        # Intentamos transformar fechas si existen columnas candidatas
        # (Tu función transformar_fechas ya maneja si la columna no existe)
        df = transformar_fechas(df)
        
        return df, nombre_archivo
        
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None, None
# --- INTERFAZ GRÁFICA (FRONTEND) ---

# --- BARRA LATERAL DE CONTROL ---
with st.sidebar:
    st.image("https://via.placeholder.com/150", caption="C&C Cafetería")
    st.title("🎛️ Centro de Mando")
    
    # --- SECCIÓN 1: EL ROBOT (Descargas) ---
    with st.expander("🤖 Descargar Nuevo Reporte", expanded=True):
        with st.form("form_robot"):
            # 1. Configuración
            opciones_reportes = list(REPORTES_CONFIG.keys())
            tipo_reporte = st.selectbox("Tipo de Reporte", opciones_reportes)
            
            col1, col2 = st.columns(2)
            fecha_inicio = col1.date_input("Desde", value=pd.to_datetime("today").date().replace(day=1))
            fecha_fin = col2.date_input("Hasta", value=pd.to_datetime("today").date())
            
            # 2. GESTIÓN DE ARCHIVOS (¡LO NUEVO!)
            st.markdown("---")
            # Etiqueta personalizada para no perderse
            etiqueta_default = f"{tipo_reporte}_{fecha_inicio.strftime('%Y%m')}"
            nombre_personalizado = st.text_input("Guardar como:", value=etiqueta_default, help="Nombre para identificar este archivo luego")
            
            f_ini_str = fecha_inicio.strftime("%d/%m/%Y")
            f_fin_str = fecha_fin.strftime("%d/%m/%Y")
            # Checkbox de limpieza (Desmarcado por defecto para permitir múltiples)
            limpiar_antes = st.checkbox("🗑️ Borrar archivos anteriores", value=False, help="Marca esto si quieres limpiar la carpeta antes de descargar")

            boton_actualizar = st.form_submit_button("⬇️ Ejecutar Descarga")

    # --- LÓGICA DE EJECUCIÓN ---
    if boton_actualizar:
        status_box = st.empty() # Caja para mensajes de estado
        status_box.info("⏳ Iniciando Robot... Por favor espere.")
        
        try:
            # A. Preparar rutas
            carpeta_reportes = os.path.join(os.getcwd(), "data", "reportes")
            if not os.path.exists(carpeta_reportes):
                os.makedirs(carpeta_reportes)
            
            # B. Instanciar Robot
            bot = RobotMercat(carpeta_reportes)
            
            # C. Login (Idealmente usa st.secrets para no hardcodear contraseñas)
            # Por ahora usa tus variables, pero luego te enseño a ocultarlas
            USUARIO = "diegomvaldez19@gmail.com"
            PASSWORD = "Gatovaldez8Mercat"

            if limpiar_antes:
                bot.limpiar_carpeta_descargas()
            
            bot.login(USUARIO, PASSWORD)
            
            # D. Preparar Parámetros
            # Aquí mapeamos los inputs de Streamlit a lo que espera el ERP
            parametros = {
                "fecha_inicio": f_ini_str,
                "fecha_fin": f_fin_str,
                "sucursal": "1087", # C&C
                # Puedes agregar más lógica aquí si añades más filtros al form
                "con_factura": "", # Todos por defecto
                "anulado": ""
            }
            
            # E. Descargar
            config_seleccionada = REPORTES_CONFIG[tipo_reporte]
            bot.descargar_reporte(config_seleccionada, parametros)
            bot.renombrar_ultimo_archivo(nombre_personalizado)
            
            bot.cerrar()
            st.success(f"✅ Guardado como: {nombre_personalizado}")
            st.rerun()
            
          
            
        except Exception as e:
            status_box.error(f"❌ Error del Robot: {e}")
            if 'bot' in locals(): bot.cerrar()

        # --- SECCIÓN 2: SELECTOR DE ARCHIVOS (¡CRUCIAL!) ---
    st.divider()
    st.subheader("📂 Archivos Disponibles")
    
    # Buscamos todos los archivos en la carpeta
    ruta_reportes = os.path.join("data", "reportes")
    if not os.path.exists(ruta_reportes): os.makedirs(ruta_reportes)
        
    archivos_disponibles = [f for f in os.listdir(ruta_reportes) if f.endswith(('.csv', '.xlsx'))]
    
    # Ordenamos por fecha de creación (más nuevo arriba)
    archivos_disponibles.sort(key=lambda x: os.path.getctime(os.path.join(ruta_reportes, x)), reverse=True)
    
    if archivos_disponibles:
        # El usuario elige cuál ver
        archivo_seleccionado = st.selectbox(
            "Selecciona para analizar:", 
            archivos_disponibles,
            index=0 # Por defecto selecciona el primero (el más nuevo)
        )
        
        # Botón para borrar el archivo seleccionado (Mantenimiento)
        if st.button("🗑️ Eliminar Seleccionado"):
            os.remove(os.path.join(ruta_reportes, archivo_seleccionado))
            st.rerun()
    else:
        archivo_seleccionado = None
        st.info("No hay reportes guardados.")

df_raw, nombre_archivo = cargar_datos()

if archivo_seleccionado:
    ruta_completa = os.path.join("data", "reportes", archivo_seleccionado)
    
    try:
        # Leemos el archivo seleccionado
        df_raw = pd.read_csv(ruta_completa)
        # (Aquí aplicas tus funciones de limpieza básicas que ya tienes)
        df_raw = limpiar_columnas_unnamed(df_raw) 
        
        # Detectamos tipo (igual que antes)
        if "Detalle" in df_raw.columns:
            tipo_reporte_detectado = "VENTAS"
        elif "Creado el" in df_raw.columns:
            tipo_reporte_detectado = "INDICE"
        else:
            tipo_reporte_detectado = "OTRO"
        
        # Instanciamos el Analista
        analista = AnalistaDeDatos(df_raw, tipo_reporte_detectado)
        
        # ... AQUI COMIENZA TU DASHBOARD DE SIEMPRE ...
        st.header(f"📊 Análisis de: {archivo_seleccionado}")
        st.caption(f"Tipo detectado: {tipo_reporte} | Registros: {len(df_raw)}")
# --- BLOQUE DE DIAGNÓSTICO (BORRAR LUEGO) ---
        with st.expander("🕵️‍♂️ Ver Columnas Detectadas (Debug)"):
            st.write("Columnas encontradas en el CSV:")
            st.write(df_raw.columns.tolist())
            st.write("¿Existe 'Detalle'?", "Detalle" in df_raw.columns)
            st.write("¿Existe 'Monto total'?", "Monto total" in df_raw.columns)
            st.write("¿Existe 'Creado el'?", "Creado el" in df_raw.columns)
        # -----
    # --- DASHBOARD DE VENTAS (El más completo) ---
        if tipo_reporte_detectado == "VENTAS":
            
            # A. KPIS PRINCIPALES
            kpis = analista.get_kpis_financieros()
            if kpis:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Ventas Netas", f"Bs {kpis['Ventas Totales']:,.2f}")
                c2.metric("Ticket Promedio", f"Bs {kpis['Ticket Promedio']:,.2f}")
                c3.metric("Transacciones", kpis['Transacciones'])
                c4.metric("Descuentos Dados", f"Bs {kpis['Total Descuentos']:,.2f}")
                st.divider()

            # B. PESTAÑAS DE ANÁLISIS
            tab_prod, tab_tiempos, tab_meseros, tab_pagos = st.tabs([
                "🍩 Productos Top", "⏰ Tiempos y Calor", "busts_in_silhouette: Equipo", "💳 Pagos"
            ])
            
            # 1. ANÁLISIS DE PRODUCTOS (Usando Regex)
            with tab_prod:
                df_prods = analista.analizar_productos()
                if df_prods is not None and not df_prods.empty:
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.subheader("Top 10 Productos Más Vendidos")
                        top_10 = df_prods.groupby("Producto")["Cantidad"].sum().nlargest(10).reset_index()
                        fig_prod = px.bar(top_10, x="Cantidad", y="Producto", orientation='h', text_auto=True, color="Cantidad")
                        st.plotly_chart(fig_prod, use_container_width=True)
                    
                    with col2:
                        st.subheader("Por Tipo de Orden")
                        # Filtro rápido para ver qué productos salen más por delivery vs mesa
                        tipo_filtro = st.selectbox("Filtrar por:", df_prods["Tipo Orden"].unique())
                        top_filtro = df_prods[df_prods["Tipo Orden"] == tipo_filtro].groupby("Producto")["Cantidad"].sum().nlargest(5)
                        st.table(top_filtro)
                else:
                    st.warning("No se pudieron extraer productos. Verifica la columna 'Detalle'.")

            # 2. ANÁLISIS TEMPORAL
            with tab_tiempos:
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Ventas por Hora (Mapa de Calor)")
                    df_horas = analista.df[analista.df["Es_Valido"]==True].groupby("Hora_Num")["Monto total"].sum().reset_index()
                    fig_hora = px.bar(df_horas, x="Hora_Num", y="Monto total", title="Horas Pico de Venta")
                    st.plotly_chart(fig_hora, use_container_width=True)
                
                with col2:
                    st.subheader("Días de la Semana")
                    orden_dias = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    df_dias = analista.df[analista.df["Es_Valido"]==True].groupby("Dia_Semana")["Monto total"].mean().reindex(orden_dias).reset_index()
                    fig_dias = px.bar(df_dias, x="Dia_Semana", y="Monto total", title="Venta Promedio por Día")
                    st.plotly_chart(fig_dias, use_container_width=True)

            # 3. ANÁLISIS DE MESEROS
            with tab_meseros:
                df_meseros = analista.performance_meseros()
                if df_meseros is not None:
                    st.subheader("Rendimiento del Personal")
                    
                    # Gráfico combinado: Barras (Ventas) y Línea (% Anulación)
                    # Esto es avanzado en Plotly, usamos scatter y bar
                    import plotly.graph_objects as go
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=df_meseros["Mesero"], y=df_meseros["Total_Vendido"], name="Ventas (Bs)",
                        marker_color='green'
                    ))
                    fig.add_trace(go.Scatter(
                        x=df_meseros["Mesero"], y=df_meseros["% Anulacion"], name="% Anulación",
                        yaxis="y2", mode='lines+markers', line=dict(color='red')
                    ))
                    
                    fig.update_layout(
                        title="Ventas vs Calidad Operativa (% Anulaciones)",
                        yaxis=dict(title="Ventas (Bs)"),
                        yaxis2=dict(title="% Anulaciones", overlaying="y", side="right")
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    with st.expander("Ver tabla detallada de meseros"):
                        st.dataframe(df_meseros)

            # 4. MÉTODOS DE PAGO
            with tab_pagos:
                df_fp = analista.metodos_pago_complejos()
                if df_fp is not None:
                    st.subheader("Frecuencia de Métodos de Pago")
                    fig_fp = px.pie(df_fp, names=df_fp.columns[0], values="Frecuencia", hole=0.4)
                    st.plotly_chart(fig_fp)

        # --- LÓGICA PARA OTROS REPORTES ---
        elif tipo_reporte_detectado == "INDICE":
            st.info("Análisis simplificado para Índice (Se recomienda usar Ventas para más detalle).")
            st.dataframe(analista.df.head())
            
        else:
            st.warning("Formato de reporte no reconocido para análisis avanzado.")
            st.dataframe(df_raw)
    except Exception as e:
        st.error(f"No se pudo leer el archivo {archivo_seleccionado}: {e}")

else:
    # ESTE ES EL BLOQUE "ELSE" QUE RESTAURA LA SUBIDA MANUAL
    
    st.warning("⚠️ No se encontraron datos recientes en la carpeta 'data/reportes'.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("🤖 **Opción 1: Usar el Robot**\n\nVe a la barra lateral (izquierda), elige las fechas y dale a 'Descargar'.")

    with col2:
        st.info("📂 **Opción 2: Subida Manual**\n\nSi ya tienes el archivo descargado, súbelo aquí:")
        
        uploaded_file = st.file_uploader("Arrastra tu reporte aquí", type=['csv', 'xlsx'])
        
        if uploaded_file:
            # 1. Asegurar que la carpeta existe
            carpeta_destino = os.path.join(os.getcwd(), "data", "reportes")
            if not os.path.exists(carpeta_destino):
                os.makedirs(carpeta_destino)
            
            # 2. Limpieza preventiva (opcional, para no mezclar manual con robot)
            # Si quieres que lo manual reemplace a lo anterior, borra todo antes
            files = glob.glob(os.path.join(carpeta_destino, "*"))
            for f in files:
                try: os.remove(f)
                except: pass

            # 3. Guardar el archivo subido
            ruta_final = os.path.join(carpeta_destino, uploaded_file.name)
            with open(ruta_final, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.success(f"✅ Archivo '{uploaded_file.name}' cargado. Actualizando...")
            time.sleep(1) # Dar tiempo al sistema de archivos
            st.rerun()