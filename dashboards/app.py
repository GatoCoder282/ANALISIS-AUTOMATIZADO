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

from data.robotMercat import RobotMercat
from data.config_reportes import REPORTES_CONFIG
from procesamiento import AnalistaDeDatos
from analista_operacional import AnalistaOperacional

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

# ==============================================================================
#                                   SIDEBAR
# ==============================================================================
with st.sidebar:
    st.image("https://via.placeholder.com/150", caption="C&C Cafetería")
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
            fini = c1.date_input("Desde")
            ffin = c2.date_input("Hasta")
            nombre = st.text_input("Nombre:", value=f"{tipo}_{fini.strftime('%d%m')}")
            limpiar = st.checkbox("Borrar previos", value=False)
            
            if st.form_submit_button("⬇️ Ejecutar"):
                try:
                    folder = os.path.join(os.getcwd(), "data", "reportes")
                    if not os.path.exists(folder): os.makedirs(folder)
                    bot = RobotMercat(folder)
                    if limpiar: bot.limpiar_carpeta_descargas()
                    bot.login("diegomvaldez19@gmail.com", "Gatovaldez8Mercat")
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
                # KPIs Header
                kpis = analista.get_kpis_financieros() # Esto ya NO incluye Yango
                monto_alquiler = analista.get_kpi_alquileres() # Esto ES solo Yango
                c1, c2, c3, c4, c5 = st.columns(5)
            
                c1.metric("Ventas Operativas", f"Bs {kpis.get('Ventas Totales',0):,.0f}", help="Venta de productos (Sin alquileres)")
                c2.metric("Ticket Promedio", f"Bs {kpis.get('Ticket Promedio',0):,.0f}")
                c3.metric("Transacciones", kpis.get('Transacciones',0))
                c4.metric("Descuentos", f"Bs {kpis.get('Total Descuentos',0):,.0f}")
                
                # Métrica destacada de Yango
                c5.metric("Ingreso Yango (Alquiler)", f"Bs {monto_alquiler:,.0f}", delta_color="off", help="Membresías e Insumos facturados aparte")
                
                st.divider()
                # Pestañas con TODAS las funciones implementadas
                pestanas = st.tabs([
                    "🍩 Productos", 
                    "🧠 Estrategia (BCG/Pareto)", 
                    "🛒 Combos (Basket)", 
                    "👥 Clientes (Recurrencia)", 
                    "⚠️ Auditoría",
                    "⏰ Tiempos", 
                    "💳 Pagos"
                ])
                
                # 1. Productos Básicos
                with pestanas[0]:
                    df_p = analista.analizar_productos()
                    if df_p is not None:
                        c_a, c_b = st.columns([2,1])
                        with c_a:
                            top = df_p.groupby("Producto")["Cantidad"].sum().nlargest(15).reset_index()
                            st.plotly_chart(px.bar(top, x="Cantidad", y="Producto", orientation='h', title="Top 15 Productos"), use_container_width=True)
                        with c_b:
                            st.subheader("Por Canal")
                            filtro = st.selectbox("Canal:", df_p["Tipo Orden"].unique())
                            top_f = df_p[df_p["Tipo Orden"]==filtro].groupby("Producto")["Cantidad"].sum().nlargest(10)
                            st.table(top_f)
                
                # 2. Estrategia (BCG y Pareto)
                with pestanas[1]:
                    c_bcg, c_par = st.columns(2)
                    with c_bcg:
                        st.subheader("Matriz BCG (Crecimiento vs Ventas)")
                        df_bcg = analista.bcg_matrix()
                        if df_bcg is not None:
                            fig_bcg = px.scatter(df_bcg, x="revenue_total", y="growth", color="category", hover_name="producto", size="revenue_total")
                            st.plotly_chart(fig_bcg, use_container_width=True)
                            with st.expander("Ver datos BCG"): st.dataframe(df_bcg)
                        else: st.info("No hay suficientes datos históricos para BCG.")
                    
                    with c_par:
                        st.subheader("Productos VIP (Ley de Pareto)")
                        df_vip = analista.vip_products()
                        if df_vip is not None:
                            vips = df_vip[df_vip["VIP"]==True]
                            st.metric("Cantidad Productos VIP", len(vips))
                            st.write(f"Estos {len(vips)} productos hacen el 20% de tu venta.")
                            st.dataframe(vips[["share", "cumsum"]].head(len(vips)+5))

                # 3. Market Basket
                with pestanas[2]:
                    st.subheader("Análisis de Canasta (Productos comprados juntos)")
                    mb = analista.market_basket_rules()
                    if mb is not None:
                        st.dataframe(mb, use_container_width=True)
                    else: st.info("No se encontraron patrones fuertes de combinación.")

                # 4. Clientes y Recurrencia
                with pestanas[3]:
                    rec = analista.recurrence_analysis()
                    if rec:
                        cc1, cc2, cc3 = st.columns(3)
                        cc1.metric("Clientes Recurrentes", rec.get('recurrent_clients',0))
                        if rec.get('mean_days_between'):
                            cc2.metric("Frecuencia de Visita", f"Cada {rec['mean_days_between']:.1f} días")
                        cc3.metric("Ticket Recurrente vs Nuevo", f"{rec.get('ticket_prom_freq',0):.1f} vs {rec.get('ticket_prom_new',0):.1f}")
                        
                        st.subheader("Top Clientes Ballena")
                        ballenas = analista.clientes_ballena()
                        if ballenas is not None: st.dataframe(ballenas)

                # 5. Auditoría y Problemas
                with pestanas[4]:
                    col_prob, col_anul = st.columns(2)
                    with col_prob:
                        st.subheader("Productos Problemáticos")
                        probs = analista.productos_problematicos()
                        if probs:
                            st.write("**Más Anulados:**")
                            st.dataframe(probs["anulaciones"].head(5))
                            st.write("**Más Descontados:**")
                            st.dataframe(probs["descuentos"].head(5))
                    
                    with col_anul:
                        st.subheader("Control de Caja")
                        ctrl = analista.control_anulados_y_pendientes()
                        if ctrl:
                            st.metric("Total Anulado", f"Bs {ctrl['anulados_monto']:,.2f}")
                            st.metric("Pendiente de Pago", f"Bs {ctrl['pendientes_monto']:,.2f}")
                            if ctrl['pendientes_por_cliente'] is not None:
                                st.write("Deudores:")
                                st.dataframe(ctrl['pendientes_por_cliente'])

                # 6. Tiempos (Ventas por hora)
                with pestanas[5]:
                    c_t1, c_t2 = st.columns(2)
                    df_h = analista.ventas_por_tiempo("H")
                    if not df_h.empty:
                        c_t1.subheader("Mapa de Calor Horario")
                        c_t1.plotly_chart(px.bar(df_h, x=df_h.columns[0], y="Monto total"), use_container_width=True)
                    
                    heat = analista.weekly_heatmap()
                    if heat is not None:
                        c_t2.subheader("Intensidad Semanal")
                        c_t2.plotly_chart(px.imshow(heat.T, aspect="auto"), use_container_width=True)

                # 7. Pagos
                with pestanas[6]:
                    analisis_pagos = analista.analisis_pagos_avanzado()
                
                    if analisis_pagos:
                        # 1. Gráficos Generales
                        c_p1, c_p2 = st.columns(2)
                        
                        with c_p1:
                            st.subheader("Distribución por Cantidad de Ventas")
                            # Gráfico de Torta basado en Transacciones (No en monto)
                            fig_p = px.pie(analisis_pagos["general"], names="Métodos de pago", values="Transacciones", hole=0.4)
                            st.plotly_chart(fig_p, use_container_width=True)
                            
                        with c_p2:
                            st.subheader("Ticket Promedio por Método")
                            # Gráfico de Barras para ver quién gasta más
                            fig_tp = px.bar(analisis_pagos["general"], x="Métodos de pago", y="Ticket_Promedio", 
                                            color="Ticket_Promedio", title="¿Quién gasta más?")
                            st.plotly_chart(fig_tp, use_container_width=True)

                        # 2. Desglose por Tipo de Orden
                        if analisis_pagos["por_tipo_orden"] is not None:
                            st.subheader("Métodos de Pago por Canal (Tipo de Orden)")
                            # Convertimos la matriz a formato largo para graficar fácil
                            df_melt = analisis_pagos["por_tipo_orden"].melt(id_vars="Métodos de pago", var_name="Canal", value_name="Transacciones")
                            
                            fig_stack = px.bar(df_melt, x="Canal", y="Transacciones", color="Métodos de pago", 
                                            title="Preferencia de Pago según Canal", barmode="stack")
                            st.plotly_chart(fig_stack, use_container_width=True)
                        
                        # Tabla detalle
                        with st.expander("Ver Tabla Financiera Detallada"):
                            st.dataframe(analisis_pagos["general"].style.format({"Venta_Total": "Bs {:,.2f}", "Ticket_Promedio": "Bs {:,.2f}"}))
                    else:
                        st.info("No se encontraron datos de métodos de pago.")
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
                        # medir/colorear por número de ocupaciones (veces que se usó la mesa)
                        color_col = "Ocupaciones" if "Ocupaciones" in hm.columns else (
                                    "Facturacion_Total" if "Facturacion_Total" in hm.columns else None)
                        if color_col:
                            fig = px.treemap(hm, path=['Mesa_Real'], values='Ocupaciones', color=color_col)
                        else:
                            fig = px.treemap(hm, path=['Mesa_Real'], values='Ocupaciones')
                        st.plotly_chart(fig, width='stretch')
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
                        st.subheader("Mapa de Calor: Frecuencia de Uso")
                        # CAMBIO: El tamaño es la ocupación (veces usado), el color es el ticket promedio
                        # Así ves: Mesas muy usadas (Grande) y si gastan mucho o poco (Rojo/Azul)
                        fig_tree = px.treemap(
                            hm, 
                            path=['Mesa_Real'], 
                            values='Ocupaciones', 
                            color='Ticket_Promedio',
                            color_continuous_scale='RdBu', 
                            title="Tamaño = Cantidad Visitas | Color = Ticket Promedio"
                        )
                        st.plotly_chart(fig_tree, use_container_width=True)
                    
                    with c_map2:
                        st.subheader("Top Mesas (Por Visitas)")
                        # Tabla simple ordenada por ocupación
                        st.dataframe(
                            hm[['Mesa_Real', 'Ocupaciones', 'Ticket_Promedio']].head(15)
                            .style.format({"Ticket_Promedio": "Bs {:,.2f}"})
                        )
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