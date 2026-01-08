import time
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import glob
import sys

# Aseguramos que python encuentre los archivos
sys.path.append(os.getcwd()) 

# Cargar variables desde .env (MERCAT_USER, MERCAT_PASS, CHROME_HEADLESS, etc.)
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from data.robotMercat import RobotMercat
from data.config_reportes import REPORTES_CONFIG
from application.procesamiento import AnalistaDeDatos
from application.analista_operacional import AnalistaOperacional

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Dashboard C&C", layout="wide", page_icon="☕")

# --- FUNCIONES UTILITARIAS ---
def obtener_archivos_disponibles():
    ruta = os.path.join("data", "reportes")
    if not os.path.exists(ruta): return []
    files = [f for f in os.listdir(ruta) if f.endswith(('.csv', '.xlsx'))]
    files.sort(key=lambda x: os.path.getctime(os.path.join(ruta, x)), reverse=True)
    return files

def cargar_df(nombre_archivo):
    try:
        ruta = os.path.join("data", "reportes", nombre_archivo)
        if nombre_archivo.endswith('.csv'):
            df = pd.read_csv(ruta)
        else:
            df = pd.read_excel(ruta)
        df = df.dropna(axis=1, how='all')
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        return df
    except Exception as e:
        st.error(f"Error leyendo {nombre_archivo}: {e}")
        return None

def obtener_coordenadas_mesas():
    """
    Retorna un diccionario con las coordenadas X,Y de cada mesa según el plano del restaurante.
    Coordenadas normalizadas (0-100) para facilitar el escalado.
    """
    return {
        # Fila superior (barra y mesas altas S1, S2, S3)
        "S1": (25, 90),
        "S2": (40, 90),
        "S3": (55, 90),
        
        # Mesas laterales derechas (C1-C6)
        "C1": (85, 85),
        "C2": (85, 78),
        "C3": (85, 71),
        "C4": (85, 64),
        "C5": (85, 57),
        "C6": (85, 50),
        
        # Mesa central (S4)
        "S4": (50, 70),
        
        # Mesas izquierda alta (S5 y otra)
        "S5": (35, 55),
        "S8": (50, 55),
        
        # Área central-baja
        "4": (45, 35),
        "3": (60, 35),
        "2": (70, 35),
        "1": (80, 35),
        
        # Mesas inferiores
        "B1": (25, 20),
        "B2": (25, 12),
        "B3": (25, 5),
    }

def renderizar_mapa_mesas(df_mesas):
    """
    Crea una visualización 2D del restaurante con las mesas posicionadas según el plano físico.
    
    Args:
        df_mesas: DataFrame con columnas Mesa_Real, Ocupaciones, Ticket_Promedio, Facturacion_Total
    
    Returns:
        Plotly figure
    """
    if df_mesas is None or df_mesas.empty:
        return None
    
    coords = obtener_coordenadas_mesas()
    
    # Agregar coordenadas al dataframe
    df_plot = df_mesas.copy()
    df_plot["X"] = df_plot["Mesa_Real"].map(lambda m: coords.get(str(m), (50, 50))[0])
    df_plot["Y"] = df_plot["Mesa_Real"].map(lambda m: coords.get(str(m), (50, 50))[1])
    
    # Mesas no mapeadas (usar posiciones aleatorias en zona inferior)
    import numpy as np
    sin_coords = df_plot[(df_plot["X"] == 50) & (df_plot["Y"] == 50)]
    if not sin_coords.empty:
        np.random.seed(42)
        for idx in sin_coords.index:
            df_plot.at[idx, "X"] = np.random.uniform(10, 90)
            df_plot.at[idx, "Y"] = np.random.uniform(5, 25)
    
    # Crear figura con scatter
    fig = go.Figure()
    
    # Normalizar tamaños para mejor visualización
    size_scale = 100 / df_plot["Ocupaciones"].max() if df_plot["Ocupaciones"].max() > 0 else 1
    
    fig.add_trace(go.Scatter(
        x=df_plot["X"],
        y=df_plot["Y"],
        mode="markers+text",
        marker=dict(
            size=df_plot["Ocupaciones"] * size_scale * 0.8,  # Tamaño proporcional a ocupación
            color=df_plot["Ticket_Promedio"],  # Color por ticket promedio
            colorscale="RdYlGn",  # Rojo (bajo) -> Amarillo -> Verde (alto)
            showscale=True,
            colorbar=dict(title="Ticket Bs"),
            line=dict(width=2, color="white"),
            sizemode="diameter"
        ),
        text=df_plot["Mesa_Real"],
        textposition="middle center",
        textfont=dict(size=10, color="white", family="Arial Black"),
        hovertemplate="<b>Mesa %{text}</b><br>" +
                      "Ocupaciones: %{customdata[0]}<br>" +
                      "Ticket Prom: Bs %{customdata[1]:,.0f}<br>" +
                      "Total: Bs %{customdata[2]:,.0f}<br>" +
                      "<extra></extra>",
        customdata=df_plot[["Ocupaciones", "Ticket_Promedio", "Facturacion_Total"]].values
    ))
    
    # Layout que simula el plano del restaurante
    fig.update_layout(
        title="Mapa de Ocupación del Restaurante",
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[-5, 105]
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[-5, 105],
            scaleanchor="x",
            scaleratio=1
        ),
        plot_bgcolor="rgb(240, 240, 240)",
        height=600,
        showlegend=False
    )
    
    # Agregar áreas del restaurante (opcional, para contexto)
    fig.add_shape(type="rect", x0=0, y0=80, x1=70, y1=100, 
                  fillcolor="rgba(200, 200, 200, 0.2)", line=dict(width=0),
                  layer="below", name="Barra")
    
    return fig

# ==============================================================================
#                                   SIDEBAR
# ==============================================================================
with st.sidebar:
    st.image("./images/CoffeeAndCompany_Marca-06.png", caption="C&C Cafetería")
    st.title("🎛️ Navegación")
    
    modo_app = st.radio("Módulo:", 
        ["🤖 Robot", "📊 Análisis Individual", "🔗 Análisis Maestro (Fusión)"],
        index=1
    )
    
    st.divider()
    
    if modo_app == "🤖 Robot":
        st.subheader("Descargar Reporte")
        with st.form("form_robot"):
            opciones = list(REPORTES_CONFIG.keys())
            tipo = st.selectbox("Reporte", opciones)
            c1, c2 = st.columns(2)
            from datetime import date, timedelta
            hoy = date.today()
            hace_7_dias = hoy - timedelta(days=7)
            fini = c1.date_input("Desde", value=hace_7_dias)
            ffin = c2.date_input("Hasta", value=hoy)
            nombre = st.text_input("Nombre:", value=f"{tipo}_{fini.strftime('%d%m')}")
            limpiar = st.checkbox("Borrar previos", value=False)
            
            if st.form_submit_button("⬇️ Ejecutar"):
                try:
                    folder = os.path.join(os.getcwd(), "data", "reportes")
                    if not os.path.exists(folder): os.makedirs(folder)
                    bot = RobotMercat(folder)
                    if limpiar: bot.limpiar_carpeta_descargas()
                    # Credenciales desde variables de entorno
                    user = os.environ.get("MERCAT_USER")
                    pwd = os.environ.get("MERCAT_PASS")
                    if not user or not pwd:
                        st.error("Faltan variables de entorno MERCAT_USER y MERCAT_PASS.")
                        st.stop()
                    bot.login(user, pwd)
                    params = {
                        "fecha_inicio": fini.strftime("%d/%m/%Y"),
                        "fecha_fin": ffin.strftime("%d/%m/%Y"),
                        "sucursal": "1087", "con_factura": "", "anulado": ""
                    }
                    bot.descargar_reporte(REPORTES_CONFIG[tipo], params)
                    bot.renombrar_ultimo_archivo(nombre)
                    bot.cerrar()
                    st.success(f"✅ {nombre} descargado.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    archivos = obtener_archivos_disponibles()
    st.caption(f"Archivos: {len(archivos)}")

# ==============================================================================
#                           MODO 1: ANÁLISIS INDIVIDUAL
# ==============================================================================
if modo_app == "📊 Análisis Individual":
    st.header("📊 Análisis Detallado")
    
    if not archivos:
        st.warning("No hay archivos.")
        st.stop()
        
    archivo_sel = st.selectbox("Selecciona archivo:", archivos)
    
    if archivo_sel:
        df_raw = cargar_df(archivo_sel)
        if df_raw is not None:
            # Detección
            tipo = "OTRO"
            if "Detalle" in df_raw.columns: tipo = "VENTAS"
            elif "Creado el" in df_raw.columns: tipo = "INDICE"
            
            # Instancia Analista Base
            analista = AnalistaDeDatos(df_raw, tipo)
            st.caption(f"Tipo: {tipo} | Filas: {len(df_raw)}")
            
            # -------------------------------------------------------
            #                     REPORTE VENTAS
            # -------------------------------------------------------
            if tipo == "VENTAS":
                # KPIs globales
                kpis = analista.get_kpis_financieros()
                monto_alquiler = analista.get_kpi_alquileres()
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Ventas Operativas", f"Bs {kpis.get('Ventas Totales',0):,.0f}", help="Venta de productos (Sin alquileres)")
                c2.metric("Ticket Promedio", f"Bs {kpis.get('Ticket Promedio',0):,.0f}")
                c3.metric("Transacciones", kpis.get('Transacciones',0))
                c4.metric("Descuentos", f"Bs {kpis.get('Total Descuentos',0):,.0f}")

                c5, c6, c7, c8 = st.columns(4)
                c5.metric("Pendientes", f"Bs {kpis['Ventas Pendientes']:,.0f}")
                c6.metric("Consumo Interno", f"Bs {kpis['Consumo Interno']:,.0f}")
                c7.metric("Ingreso Yango (Alquiler)", f"Bs {monto_alquiler:,.0f}", delta_color="off", help="Membresías e Insumos facturados aparte")
                c8.metric("Cobranza (%)", f"{kpis['Ratio Pagado']*100:,.1f}%")

                st.divider()

                # Precomputos y helpers para las nuevas vistas por canal
                df_productos = analista.analizar_productos()
                df_global_valid = analista._excluir_alquiler(analista.df.copy())
                if "Es_Valido" in df_global_valid.columns:
                    df_global_valid = df_global_valid[df_global_valid["Es_Valido"] == True]
                total_ventas_validas = df_global_valid["Monto total"].sum()

                CANAL_ALIASES = {
                    "Mesa y Recojo": ["MESA", "RECOJO", "RETIRO", "PICKUP", "PARA LLEVAR"],
                    "Interno": ["INTERNO"],
                    "PedidosYa": ["PEDIDOSYA", "PEDIDOS YA", "PEDIDOS-YA"],
                    "Yango": ["YANGO"]
                }

                def filtrar_por_canal(df_base, alias_list, incluir_alquiler=False):
                    df_tmp = df_base.copy()
                    if not incluir_alquiler:
                        df_tmp = analista._excluir_alquiler(df_tmp)
                    if "Es_Valido" in df_tmp.columns:
                        df_tmp = df_tmp[df_tmp["Es_Valido"] == True]
                    if "Tipo_Norm" in df_tmp.columns:
                        tipos = df_tmp["Tipo_Norm"].fillna("").str.upper()
                    else:
                        tipos = df_tmp["Tipo de orden"].fillna("").str.upper()
                    mask = tipos.apply(lambda t: any(alias in t for alias in alias_list))
                    return df_tmp[mask]

                def filtrar_productos_por_canal(df_prod, alias_list):
                    if df_prod is None or df_prod.empty:
                        return pd.DataFrame()
                    tipos = df_prod["Tipo Orden"].fillna("").str.upper()
                    mask = tipos.apply(lambda t: any(alias in t for alias in alias_list))
                    return df_prod[mask]

                def render_tab_canal(nombre, alias_list, incluir_alquiler=False, permitir_internos=False):
                    df_canal = filtrar_por_canal(analista.df, alias_list, incluir_alquiler=incluir_alquiler)
                    df_prod_canal = filtrar_productos_por_canal(df_productos, alias_list)

                    # Los internos vienen marcados como no venta real; para mostrar sus KPIs los habilitamos
                    if permitir_internos and not df_canal.empty:
                        df_canal = df_canal.copy()
                        df_canal["Es_Venta_Real"] = df_canal["Es_Valido"]

                    if df_canal.empty:
                        st.info("No hay datos válidos para este canal.")
                        return

                    kpi_canal = AnalistaDeDatos(df_canal, "VENTAS").get_kpis_financieros()
                    share = (kpi_canal.get("Ventas Totales", 0) / total_ventas_validas) if total_ventas_validas else 0

                    k1, k2, k3, k4, k5 = st.columns(5)
                    k1.metric("Ventas Totales", f"Bs {kpi_canal.get('Ventas Totales',0):,.0f}", f"{share*100:,.1f}% del total")
                    k2.metric("Ticket Promedio", f"Bs {kpi_canal.get('Ticket Promedio',0):,.0f}")
                    k3.metric("Transacciones", kpi_canal.get('Transacciones',0))
                    k4.metric("Descuentos", f"Bs {kpi_canal.get('Total Descuentos',0):,.0f}")
                    k5.metric("Pendientes", f"Bs {kpi_canal.get('Ventas Pendientes',0):,.0f}")

                    st.markdown("### Top 15 productos más vendidos")
                    if not df_prod_canal.empty:
                        top_base = df_prod_canal.groupby("Producto_Base")["Cantidad"].sum().nlargest(15).reset_index()
                        fig_top = px.bar(top_base, x="Cantidad", y="Producto_Base", orientation="h", text_auto=True, color="Cantidad")
                        st.plotly_chart(fig_top, use_container_width=True)
                    else:
                        st.info("Sin productos detallados para este canal.")

                    st.markdown("### Variantes y modificadores")
                    if not df_prod_canal.empty:
                        c_var, c_mod = st.columns(2)

                        with c_var:
                            productos_disponibles = sorted(df_prod_canal["Producto_Base"].unique())
                            prod_sel = st.selectbox("Producto", productos_disponibles, key=f"prod_{nombre}")
                            df_sel = df_prod_canal[df_prod_canal["Producto_Base"] == prod_sel]
                            total_prod = df_sel["Cantidad"].sum()
                            variantes = df_sel.groupby("Variante")["Cantidad"].sum().reset_index()
                            variantes["Porcentaje"] = variantes["Cantidad"] / total_prod * 100 if total_prod else 0
                            if not variantes.empty:
                                fig_var = px.pie(variantes, values="Cantidad", names="Variante", title=f"Variantes de {prod_sel}", hole=0.45)
                                st.plotly_chart(fig_var, use_container_width=True)
                                st.dataframe(variantes, hide_index=True, use_container_width=True)
                            else:
                                st.info("Sin variantes registradas para este producto.")

                        with c_mod:
                            mods = df_prod_canal[df_prod_canal["Variante"] != "Original/Sin Cambios"]
                            if not mods.empty:
                                top_mods = mods.groupby("Variante")["Cantidad"].sum().nlargest(10).reset_index()
                                fig_mod = px.bar(top_mods, x="Cantidad", y="Variante", title="Modificadores más comunes", color_discrete_sequence=["#FF6692"])
                                st.plotly_chart(fig_mod, use_container_width=True)
                            else:
                                st.info("No hay modificadores distintos al original.")
                    else:
                        st.info("Sin detalle de productos para analizar variantes.")

                    st.markdown("### Productos comprados juntos")
                    if not df_prod_canal.empty:
                        pedidos = df_prod_canal.groupby("Id_Venta")["Producto_Base"].apply(lambda s: tuple(sorted(set([p for p in s.dropna()]))))
                        pedidos = pedidos[pedidos.apply(len) > 1]
                        combos = pedidos.value_counts().head(5).reset_index()
                        combos.columns = ["Pedido", "Veces"]
                        combos["Pedido"] = combos["Pedido"].apply(lambda t: " + ".join(t))
                        if not combos.empty:
                            st.write("Top 5 pedidos completos:")
                            st.dataframe(combos, hide_index=True, use_container_width=True)
                        else:
                            st.info("No hay pedidos con múltiples productos en este canal.")
                    else:
                        st.info("Sin detalle de productos para analizar combos.")

                    reglas = AnalistaDeDatos(df_canal, "VENTAS").basket_analysis(top_n=10, min_support=2)
                    if reglas is not None:
                        reglas["Pareja"] = reglas.apply(lambda r: f"{str(r['item_a']).title()} + {str(r['item_b']).title()}", axis=1)
                        st.write("Top 10 parejas de productos más solicitados")
                        st.dataframe(reglas[["Pareja", "count", "support", "conf_a->b", "conf_b->a"]], hide_index=True, use_container_width=True)
                    else:
                        st.info("No se identificaron parejas frecuentes en este canal.")

                    st.markdown("### Frecuencia de pedidos")
                    c_h, c_d = st.columns(2)
                    if "Hora_Num" in df_canal.columns:
                        horas = df_canal.groupby("Hora_Num")["Id"].nunique().reset_index().rename(columns={"Id": "Pedidos"})
                        c_h.plotly_chart(px.bar(horas, x="Hora_Num", y="Pedidos", title="Cantidad de pedidos por hora"), use_container_width=True)
                    else:
                        c_h.info("No hay información horaria disponible.")

                    if "Dia_Semana" in df_canal.columns:
                        orden_dias = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                        dias = df_canal.groupby("Dia_Semana")["Id"].nunique().reindex(orden_dias).dropna().reset_index().rename(columns={"Id": "Pedidos"})
                        c_d.plotly_chart(px.bar(dias, x="Dia_Semana", y="Pedidos", title="Cantidad de pedidos por día"), use_container_width=True)
                    else:
                        c_d.info("No hay información de día disponible.")

                pestanas = st.tabs([
                    "🪑 Mesa y Recojo",
                    "🏢 Interno",
                    "🛵 PedidosYa",
                    "🚚 Yango",
                    "💳 Pagos",
                    "🧑‍🍳 Meseros"
                ])

                with pestanas[0]:
                    render_tab_canal("Mesa y Recojo", CANAL_ALIASES["Mesa y Recojo"])

                with pestanas[1]:
                    render_tab_canal("Interno", CANAL_ALIASES["Interno"], permitir_internos=True)

                with pestanas[2]:
                    render_tab_canal("PedidosYa", CANAL_ALIASES["PedidosYa"])

                with pestanas[3]:
                    render_tab_canal("Yango", CANAL_ALIASES["Yango"], incluir_alquiler=True)

                with pestanas[4]:
                    analisis_pagos = analista.analisis_pagos_avanzado()

                    if analisis_pagos:
                        c_p1, c_p2 = st.columns(2)

                        with c_p1:
                            st.subheader("Distribución por Cantidad de Ventas")
                            fig_p = px.pie(analisis_pagos["general"], names="Métodos de pago", values="Transacciones", hole=0.4)
                            st.plotly_chart(fig_p, use_container_width=True)

                        with c_p2:
                            st.subheader("Ticket Promedio por Método")
                            fig_tp = px.bar(analisis_pagos["general"], x="Métodos de pago", y="Ticket_Promedio", 
                                            color="Ticket_Promedio", title="¿Quién gasta más?")
                            st.plotly_chart(fig_tp, use_container_width=True)

                        if analisis_pagos["por_tipo_orden"] is not None:
                            st.subheader("Métodos de Pago por Canal (Tipo de Orden)")
                            df_melt = analisis_pagos["por_tipo_orden"].melt(id_vars="Métodos de pago", var_name="Canal", value_name="Transacciones")
                            fig_stack = px.bar(df_melt, x="Canal", y="Transacciones", color="Métodos de pago", 
                                            title="Preferencia de Pago según Canal", barmode="stack")
                            st.plotly_chart(fig_stack, use_container_width=True)

                        with st.expander("Ver Tabla Financiera Detallada"):
                            st.dataframe(analisis_pagos["general"].style.format({"Venta_Total": "Bs {:,.2f}", "Ticket_Promedio": "Bs {:,.2f}"}))
                    else:
                        st.info("No se encontraron datos de métodos de pago.")

                with pestanas[5]:
                    meseros_df = analista.performance_meseros()
                    if meseros_df is not None and not meseros_df.empty:
                        st.subheader("Recaudación por mesero")
                        st.dataframe(
                            meseros_df,
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "Total_Vendido": st.column_config.NumberColumn("Total Vendido", format="Bs %,.0f"),
                                "Ordenes_Totales": st.column_config.NumberColumn("Órdenes", format="%d"),
                                "Anulaciones": st.column_config.NumberColumn("Anulaciones", format="%d"),
                                "% Anulacion": st.column_config.NumberColumn("% Anulación", format="%.1f%%")
                            }
                        )
                    else:
                        st.info("No hay datos de meseros disponibles.")
            # -------------------------------------------------------
            #                     REPORTE INDICE
            # -------------------------------------------------------
            elif tipo == "INDICE":
                st.info("Reporte Operativo Detectado. Usando AnalistaOperacional en modo individual.")
                
                # Usamos la clase Operacional aunque sea solo un archivo
                ops = AnalistaOperacional(df_ventas=None, df_indice=df_raw)
                
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("⏱️ Velocidad (Creado -> Pagado)")
                    kpis_vel, df_vel = ops.kpis_velocidad()
                    if kpis_vel:
                        st.metric("Tiempo Promedio", f"{kpis_vel['Tiempo Promedio Global']:.1f} min")
                        st.metric("Ticket Más Lento", f"{kpis_vel['Ticket Más Lento']:.1f} min")
                        st.plotly_chart(px.histogram(df_vel, x="Minutos_Servicio"), use_container_width=True)
                    else: st.warning("Faltan columnas de fecha en este reporte.")
                
                with c2:
                    st.subheader("🪑 Ocupación de Mesas")
                    hm = ops.heatmap_mesas()
                    if hm is not None:
                        fig = renderizar_mapa_mesas(hm)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("No se pudo generar el mapa de mesas.")
                    else: st.warning("No hay información de mesas.")
            
            else:
                st.warning("Formato desconocido.")
                st.dataframe(df_raw)

# ==============================================================================
#                           MODO 2: ANÁLISIS MAESTRO
# ==============================================================================
elif modo_app == "🔗 Análisis Maestro (Fusión)":
    st.header("🔗 Fusión de Datos: Ventas + Operaciones")
    
    if len(archivos) < 2:
        st.error("Se requieren al menos 2 archivos.")
        st.stop()

    c1, c2 = st.columns(2)
    # Filtros de ayuda
    f_v = [f for f in archivos if "ventas" in f.lower()] or archivos
    f_i = [f for f in archivos if "indice" in f.lower()] or archivos
    
    file_v = c1.selectbox("Archivo VENTAS:", f_v, key="m_v")
    file_i = c2.selectbox("Archivo ÍNDICE:", f_i, key="m_i")
    
    if st.button("🚀 Fusionar"):
        df_v = cargar_df(file_v)
        df_i = cargar_df(file_i)
        
        if df_v is not None and df_i is not None:
            ops = AnalistaOperacional(df_v, df_i)
            st.success(f"Fusión exitosa: {len(ops.df_maestro)} registros combinados.")
            
            tab_v, tab_m = st.tabs(["⏱️ Velocidad por Canal", "🪑 Rentabilidad Mesas"])
            
            with tab_v:
                kpis, df_vel = ops.kpis_velocidad()
                if kpis:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Global", f"{kpis['Tiempo Promedio Global']:.1f} min")
                    m2.metric("Mesa", f"{kpis.get('Promedio Mesa',0):.1f} min")
                    m3.metric("Delivery", f"{kpis.get('Promedio Delivery',0):.1f} min")
                    st.plotly_chart(px.box(df_vel, x="Tipo_Orden", y="Minutos_Servicio", points="all"), use_container_width=True)
            
            with tab_m: # Tab Mesas en Fusión
                hm = ops.heatmap_mesas()
                if hm is not None:
                    c_map1, c_map2 = st.columns([2, 1])
                    
                    with c_map1:
                        st.subheader("Mapa de Ocupación del Restaurante")
                        fig_map = renderizar_mapa_mesas(hm)
                        if fig_map:
                            st.plotly_chart(fig_map, use_container_width=True)
                        else:
                            st.warning("No se pudo generar el mapa.")
                    
                    with c_map2:
                        st.subheader("Top Mesas (Por Visitas)")
                        st.dataframe(
                            hm[['Mesa_Real', 'Ocupaciones', 'Ticket_Promedio']].head(15)
                            .style.format({"Ticket_Promedio": "Bs {:,.2f}"})
                        )
                        
                        st.markdown("---")
                        st.caption("💡 **Leyenda del Mapa:**")
                        st.caption("• **Tamaño**: Cantidad de visitas")
                        st.caption("• **Color**: Ticket promedio (Rojo=Bajo, Verde=Alto)")
                else:
                    st.warning("No se encontraron datos de mesas.")

# ==============================================================================
#                           MODO 0: PANTALLA ROBOT
# ==============================================================================
elif modo_app == "🤖 Robot Descargas":
    st.info("👈 Configura la descarga en el panel izquierdo.")
    st.image("https://media.giphy.com/media/L1R1TV7J2Zbu6qPiOE/giphy.gif", width=300) # Un toque visual
    
    with st.expander("Ver historial de archivos"):
        df_files = pd.DataFrame({"Archivos en sistema": archivos})
        st.dataframe(df_files, use_container_width=True)