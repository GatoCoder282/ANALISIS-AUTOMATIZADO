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
    Coordenadas normalizadas (0-130 en X, 0-100 en Y) alineadas al plano físico:
    - Balcón exterior: B1-B5
    - Salón interior: S1-S6
    - Cubículos: C1-C5
    - Barra: P1-P2
    - Sala privada: SALA (agregado de todas las variantes "SALA")
    """
    return {
        # Balcón exterior
        "B1": (12, 86),
        "B2": (12, 74),
        "B3": (12, 58),
        "B4": (12, 46),
        "B5": (12, 34),

        # Salón interior
        "S1": (50, 84),
        "S2": (64, 84),
        "S3": (78, 84),
        "S4": (66, 62),
        "S5": (52, 46),
        "S6": (68, 46),

        # Cubículos
        "C1": (96, 72),
        "C2": (96, 62),
        "C3": (96, 52),
        "C4": (96, 42),
        "C5": (96, 32),
        "C6": (96, 22),  # Agregado C6 que aparece en el CSV

        # Barra
        "P1": (58, 32),
        "P2": (72, 32),

        # Sala privada (consolida todas las salas)
        "SALA": (120, 64),
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
    df_plot["X"] = df_plot["Mesa_Real"].map(lambda m: coords.get(str(m), (None, None))[0])
    df_plot["Y"] = df_plot["Mesa_Real"].map(lambda m: coords.get(str(m), (None, None))[1])
    # Asegurar tipo numérico flotante para evitar FutureWarning por asignación
    try:
        df_plot["X"] = pd.to_numeric(df_plot["X"], errors="coerce").astype(float)
        df_plot["Y"] = pd.to_numeric(df_plot["Y"], errors="coerce").astype(float)
    except Exception:
        pass
    df_plot = df_plot.dropna(subset=["X", "Y"])
    if df_plot.empty:
        return None
    
    # Crear figura con scatter
    fig = go.Figure()
    
    # Normalizar tamaños para mejor visualización
    max_ocup = df_plot["Ocupaciones"].max() if df_plot["Ocupaciones"].max() > 0 else 1
    df_plot["_size"] = 14 + (df_plot["Ocupaciones"] / max_ocup) * 32
    
    fig.add_trace(go.Scatter(
        x=df_plot["X"],
        y=df_plot["Y"],
        mode="markers+text",
        marker=dict(
            size=df_plot["_size"],
            color=df_plot["Ticket_Promedio"],
            colorscale="Viridis",
            showscale=True,
            colorbar=dict(title="Ticket Bs", thickness=12, outlinewidth=0, len=0.5),
            line=dict(width=1, color="#0b1221"),
            sizemode="diameter",
            opacity=0.9
        ),
        text=df_plot["Mesa_Real"],
        textposition="middle center",
        textfont=dict(size=11, color="#e5e7eb", family="Arial Black"),
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
            range=[-5, 130]
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[0, 100],
            scaleanchor="x",
            scaleratio=1
        ),
        plot_bgcolor="#0b1221",
        paper_bgcolor="#0b1221",
        font=dict(color="#e5e7eb"),
        height=640,
        showlegend=False,
        margin=dict(l=10, r=10, t=50, b=10)
    )
    
    # Zonas de contexto (suaves, bajo las burbujas)
    fig.add_shape(type="rect", x0=0, y0=20, x1=24, y1=90,
                  fillcolor="rgba(255,255,255,0.04)", line=dict(color="#6b7280", width=0.5), layer="below")
    fig.add_shape(type="rect", x0=24, y0=20, x1=105, y1=90,
                  fillcolor="rgba(255,255,255,0.03)", line=dict(color="#4b5563", width=0.4), layer="below")
    fig.add_shape(type="rect", x0=50, y0=26, x1=78, y1=36,
                  fillcolor="rgba(255,255,255,0.06)", line=dict(color="#9ca3af", width=0.3), layer="below")
    fig.add_shape(type="rect", x0=88, y0=28, x1=104, y1=76,
                  fillcolor="rgba(255,255,255,0.04)", line=dict(color="#6b7280", width=0.5), layer="below")
    fig.add_shape(type="rect", x0=105, y0=42, x1=130, y1=86,
                  fillcolor="rgba(255,255,255,0.02)", line=dict(color="#9ca3af", width=0.4), layer="below")
    fig.add_annotation(x=12, y=92, text="Balcón", showarrow=False, font=dict(size=11, color="#cbd5e1"))
    fig.add_annotation(x=64, y=94, text="Salón", showarrow=False, font=dict(size=11, color="#cbd5e1"))
    fig.add_annotation(x=96, y=78, text="Cubículos", showarrow=False, font=dict(size=11, color="#cbd5e1"))
    fig.add_annotation(x=66, y=24, text="Barra", showarrow=False, font=dict(size=11, color="#cbd5e1"))
    fig.add_annotation(x=118, y=88, text="Sala", showarrow=False, font=dict(size=11, color="#cbd5e1"))
    
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
                    "Mesa": ["MESA", "EN LOCAL", "DINE IN"],
                    "Recojo": ["RECOJO", "RETIRO", "PICKUP", "PARA LLEVAR"],
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
                        fig_top.update_layout(yaxis=dict(autorange="reversed"))
                        st.plotly_chart(fig_top, width='stretch', key=f"fig_top_{nombre}")
                    else:
                        st.info("Sin productos detallados para este canal.")

                    
                    st.markdown("### Variantes") # Ya no "y modificadores" si quitaste esa parte

                    if not df_prod_canal.empty:
                        # 1. El selector de producto queda arriba (ancho completo)
                        productos_disponibles = sorted(df_prod_canal["Producto_Base"].unique())
                        prod_sel = st.selectbox("Producto", productos_disponibles, key=f"prod_{nombre}")
                        
                        # 2. Procesamiento de datos
                        df_sel = df_prod_canal[df_prod_canal["Producto_Base"] == prod_sel]
                        total_prod = df_sel["Cantidad"].sum()
                        variantes = df_sel.groupby("Variante")["Cantidad"].sum().reset_index()
                        variantes["Porcentaje"] = variantes["Cantidad"] / total_prod * 100 if total_prod else 0

                        if not variantes.empty:
                            # 3. AQUÍ CREAMOS LAS COLUMNAS: Gráfico (Izquierda) | Tabla (Derecha)
                            # El array [2, 1] le da más espacio al gráfico (2/3) y menos a la tabla (1/3)
                            col_grafico, col_tabla = st.columns([2, 1]) 

                            with col_grafico:
                                fig_var = px.pie(variantes, values="Cantidad", names="Variante", 
                                                title=f"Distribución de {prod_sel}", hole=0.45)
                                # Opcional: poner la leyenda abajo si molesta a los lados
                                # fig_var.update_layout(legend=dict(orientation="h", y=-0.1))
                                st.plotly_chart(fig_var, use_container_width=True, key=f"fig_var_{nombre}")

                            with col_tabla:
                                # Agregué un margen superior o un título pequeño para que no se vea desalineado
                                st.write(f"**Total: {total_prod}**") 
                                st.dataframe(
                                    variantes[["Variante", "Cantidad", "Porcentaje"]], 
                                    hide_index=True, 
                                    use_container_width=True,
                                    height=300 # Opcional: fuerza una altura similar al gráfico si hay pocas filas
                                )
                        else:
                            st.info("Sin variantes registradas para este producto.")

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

                    reglas = AnalistaDeDatos(df_canal, "VENTAS").basket_analysis(top_n=20, min_support=2)
                    if reglas is not None:
                        reglas["Pareja"] = reglas.apply(lambda r: f"{str(r['item_a']).title()} + {str(r['item_b']).title()}", axis=1)
                        st.write("Top 20 parejas de productos más solicitados")
                        st.dataframe(reglas[["Pareja", "count", "support", "conf_a->b", "conf_b->a"]], hide_index=True, use_container_width=True)
                    else:
                        st.info("No se identificaron parejas frecuentes en este canal.")

                    st.markdown("### Frecuencia de pedidos")
                    c_h, c_d = st.columns(2)
                    if "Hora_Num" in df_canal.columns:
                        horas = df_canal.groupby("Hora_Num")["Id"].nunique().reset_index().rename(columns={"Id": "Pedidos"})
                        c_h.plotly_chart(px.bar(horas, x="Hora_Num", y="Pedidos", title="Cantidad de pedidos por hora"), width='stretch', key=f"freq_hora_{nombre}")
                    else:
                        c_h.info("No hay información horaria disponible.")

                    if "Dia_Semana" in df_canal.columns:
                        orden_dias = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                        dias = df_canal.groupby("Dia_Semana")["Id"].nunique().reindex(orden_dias).dropna().reset_index().rename(columns={"Id": "Pedidos"})
                        c_d.plotly_chart(px.bar(dias, x="Dia_Semana", y="Pedidos", title="Cantidad de pedidos por día"), width='stretch', key=f"freq_dia_{nombre}")
                    else:
                        c_d.info("No hay información de día disponible.")

                    st.markdown("### Venta total (monto) por hora y día")
                    c_vh, c_vd = st.columns(2)
                    if "Hora_Num" in df_canal.columns:
                        ventas_hora = df_canal.groupby("Hora_Num")["Monto total"].sum().reset_index().rename(columns={"Monto total": "Venta_Total"})
                        c_vh.plotly_chart(px.bar(ventas_hora, x="Hora_Num", y="Venta_Total", title="Venta total por hora (Bs)", text_auto=True), width='stretch', key=f"venta_hora_{nombre}")
                    else:
                        c_vh.info("No hay información horaria disponible.")

                    if "Dia_Semana" in df_canal.columns:
                        ventas_dia = df_canal.groupby("Dia_Semana")["Monto total"].sum().reindex(orden_dias).dropna().reset_index().rename(columns={"Monto total": "Venta_Total"})
                        c_vd.plotly_chart(px.bar(ventas_dia, x="Dia_Semana", y="Venta_Total", title="Venta total por día (Bs)", text_auto=True), width='stretch', key=f"venta_dia_{nombre}")
                    else:
                        c_vd.info("No hay información de día disponible.")

                    st.markdown("### Ticket promedio por hora y día")
                    c_th, c_td = st.columns(2)
                    if "Hora_Num" in df_canal.columns:
                        ticket_hora = df_canal.groupby("Hora_Num").agg(
                            Monto_Total=("Monto total", "sum"),
                            Pedidos=("Id", "nunique")
                        ).reset_index()
                        ticket_hora["Ticket_Promedio"] = ticket_hora["Monto_Total"] / ticket_hora["Pedidos"]
                        c_th.plotly_chart(px.bar(ticket_hora, x="Hora_Num", y="Ticket_Promedio", title="Ticket promedio por hora (Bs)", text_auto=True), width='stretch', key=f"ticket_hora_{nombre}")
                    else:
                        c_th.info("No hay información horaria disponible.")

                    if "Dia_Semana" in df_canal.columns:
                        ticket_dia = df_canal.groupby("Dia_Semana").agg(
                            Monto_Total=("Monto total", "sum"),
                            Pedidos=("Id", "nunique")
                        ).reindex(orden_dias).dropna().reset_index()
                        ticket_dia["Ticket_Promedio"] = ticket_dia["Monto_Total"] / ticket_dia["Pedidos"]
                        c_td.plotly_chart(px.bar(ticket_dia, x="Dia_Semana", y="Ticket_Promedio", title="Ticket promedio por día (Bs)", text_auto=True), width='stretch', key=f"ticket_dia_{nombre}")
                    else:
                        c_td.info("No hay información de día disponible.")

                    # Análisis detallado por día de la semana
                    st.markdown("### Análisis por día de la semana")
                    if "Dia_Semana" in df_canal.columns and "Hora_Num" in df_canal.columns:
                        # Mapeo de nombres en inglés a español para mejor UX
                        dias_map = {
                            'Monday': 'Lunes',
                            'Tuesday': 'Martes',
                            'Wednesday': 'Miércoles',
                            'Thursday': 'Jueves',
                            'Friday': 'Viernes',
                            'Saturday': 'Sábado',
                            'Sunday': 'Domingo'
                        }
                        dias_disponibles = [d for d in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'] 
                                           if d in df_canal["Dia_Semana"].values]
                        
                        if dias_disponibles:
                            dia_seleccionado = st.selectbox(
                                "Selecciona un día:", 
                                dias_disponibles,
                                format_func=lambda x: dias_map.get(x, x),
                                key=f"dia_sel_{nombre}"
                            )
                            
                            # Filtrar datos del día seleccionado
                            df_dia = df_canal[df_canal["Dia_Semana"] == dia_seleccionado].copy()
                            
                            if not df_dia.empty:
                                # Calcular totales de la semana para porcentaje
                                pedidos_semana = df_canal["Id"].nunique()
                                monto_semana = df_canal["Monto total"].sum()
                                
                                # KPIs del día
                                pedidos_dia = df_dia["Id"].nunique()
                                monto_dia = df_dia["Monto total"].sum()
                                ticket_prom_dia = monto_dia / pedidos_dia if pedidos_dia > 0 else 0
                                
                                # Porcentajes respecto a la semana
                                porc_pedidos = (pedidos_dia / pedidos_semana * 100) if pedidos_semana > 0 else 0
                                porc_monto = (monto_dia / monto_semana * 100) if monto_semana > 0 else 0
                                
                                k_d1, k_d2, k_d3 = st.columns(3)
                                k_d1.metric(
                                    f"Pedidos ({dias_map.get(dia_seleccionado, dia_seleccionado)})", 
                                    pedidos_dia,
                                    f"{porc_pedidos:.1f}% de la semana"
                                )
                                k_d2.metric("Ticket Promedio", f"Bs {ticket_prom_dia:,.0f}")
                                k_d3.metric(
                                    "Monto Total", 
                                    f"Bs {monto_dia:,.0f}",
                                    f"{porc_monto:.1f}% de la semana"
                                )
                                
                                # Análisis por hora del día seleccionado
                                st.markdown(f"#### Pedidos por hora - {dias_map.get(dia_seleccionado, dia_seleccionado)}")
                                horas_dia = df_dia.groupby("Hora_Num").agg({
                                    "Id": "nunique",
                                    "Monto total": "sum"
                                }).reset_index()
                                horas_dia.columns = ["Hora", "Pedidos", "Monto"]
                                horas_dia["Ticket_Promedio"] = horas_dia["Monto"] / horas_dia["Pedidos"]
                                horas_dia = horas_dia.sort_values("Hora")
                                
                                # Gráfico de pedidos por hora
                                fig_hora_dia = px.bar(
                                    horas_dia, 
                                    x="Hora", 
                                    y="Pedidos",
                                    title=f"Distribución horaria - {dias_map.get(dia_seleccionado, dia_seleccionado)}",
                                    text_auto=True,
                                    color="Pedidos",
                                    color_continuous_scale="Blues"
                                )
                                st.plotly_chart(fig_hora_dia, use_container_width=True, key=f"hora_dia_{nombre}")
                                
                                # Análisis por turno
                                st.markdown("#### Análisis por Turno")
                                df_dia["Turno"] = df_dia["Hora_Num"].apply(lambda h: "Mañana (00:00-14:00)" if h < 14 else "Tarde (14:00-00:00)")
                                
                                turnos = df_dia.groupby("Turno").agg({
                                    "Id": "nunique",
                                    "Monto total": "sum"
                                }).reset_index()
                                turnos.columns = ["Turno", "Pedidos", "Monto"]
                                turnos["Ticket_Promedio"] = turnos["Monto"] / turnos["Pedidos"]
                                
                                # Calcular porcentajes respecto al total del día
                                turnos["Porc_Pedidos"] = (turnos["Pedidos"] / pedidos_dia * 100) if pedidos_dia > 0 else 0
                                turnos["Porc_Monto"] = (turnos["Monto"] / monto_dia * 100) if monto_dia > 0 else 0
                                
                                # Asegurar orden: Mañana primero
                                turnos = turnos.sort_values("Turno", ascending=True)
                                
                                # Mostrar métricas por turno
                                col_turnos = st.columns(len(turnos))
                                for idx, (_, turno_row) in enumerate(turnos.iterrows()):
                                    with col_turnos[idx]:
                                        st.markdown(f"**{turno_row['Turno']}**")
                                        st.metric(
                                            "Pedidos", 
                                            f"{int(turno_row['Pedidos'])}",
                                            f"{turno_row['Porc_Pedidos']:.1f}% del día"
                                        )
                                        st.metric("Ticket Promedio", f"Bs {turno_row['Ticket_Promedio']:,.0f}")
                                        st.metric(
                                            "Monto Total", 
                                            f"Bs {turno_row['Monto']:,.0f}",
                                            f"{turno_row['Porc_Monto']:.1f}% del día"
                                        )
                                
                                # Tabla detallada de turnos
                                with st.expander("Ver tabla detallada por turno"):
                                    st.dataframe(
                                        turnos[["Turno", "Pedidos", "Porc_Pedidos", "Monto", "Porc_Monto", "Ticket_Promedio"]].style.format({
                                            "Pedidos": "{:,.0f}",
                                            "Porc_Pedidos": "{:.1f}%",
                                            "Monto": "Bs {:,.2f}",
                                            "Porc_Monto": "{:.1f}%",
                                            "Ticket_Promedio": "Bs {:,.2f}"
                                        }),
                                        hide_index=True,
                                        use_container_width=True
                                    )
                            else:
                                st.info(f"No hay datos para {dias_map.get(dia_seleccionado, dia_seleccionado)}.")
                        else:
                            st.info("No hay datos de días de la semana disponibles.")
                    else:
                        st.info("No hay información suficiente para análisis por día.")

                    # Análisis mensual por canal
                    st.markdown(f"### Resumen de ventas por mes - {nombre}")
                    if "Fecha_DT" in df_canal.columns:
                        df_mes_canal = df_canal.copy()
                        df_mes_canal["Mes"] = df_mes_canal["Fecha_DT"].dt.to_period("M").astype(str)
                        
                        ventas_mes_canal = df_mes_canal.groupby("Mes").agg({
                            "Id": "nunique",
                            "Monto total": "sum"
                        }).reset_index()
                        ventas_mes_canal.columns = ["Mes", "Transacciones", "Monto_Total"]
                        ventas_mes_canal["Ticket_Promedio"] = ventas_mes_canal["Monto_Total"] / ventas_mes_canal["Transacciones"]
                        ventas_mes_canal = ventas_mes_canal.sort_values("Mes")
                        
                        if not ventas_mes_canal.empty:
                            col_m1, col_m2 = st.columns(2)
                            
                            with col_m1:
                                fig_mes_trans = px.bar(
                                    ventas_mes_canal, 
                                    x="Mes", 
                                    y="Transacciones", 
                                    title=f"Transacciones por mes - {nombre}", 
                                    text_auto=True,
                                    color="Transacciones"
                                )
                                st.plotly_chart(fig_mes_trans, use_container_width=True, key=f"ventas_mes_trans_{nombre}")
                            
                            with col_m2:
                                fig_mes_monto = px.bar(
                                    ventas_mes_canal, 
                                    x="Mes", 
                                    y="Monto_Total", 
                                    title=f"Monto recaudado por mes - {nombre} (Bs)", 
                                    text_auto=".0f",
                                    color="Monto_Total",
                                    color_continuous_scale="Greens"
                                )
                                st.plotly_chart(fig_mes_monto, use_container_width=True, key=f"ventas_mes_monto_{nombre}")
                            
                            fig_mes_ticket = px.line(
                                ventas_mes_canal, 
                                x="Mes", 
                                y="Ticket_Promedio", 
                                title=f"Evolución del ticket promedio - {nombre} (Bs)",
                                markers=True,
                                text="Ticket_Promedio"
                            )
                            fig_mes_ticket.update_traces(texttemplate='Bs %{text:,.0f}', textposition="top center")
                            st.plotly_chart(fig_mes_ticket, use_container_width=True, key=f"ventas_mes_ticket_{nombre}")
                            
                            with st.expander("Ver tabla detallada por mes"):
                                st.dataframe(
                                    ventas_mes_canal.style.format({
                                        "Transacciones": "{:,.0f}",
                                        "Monto_Total": "Bs {:,.2f}",
                                        "Ticket_Promedio": "Bs {:,.2f}"
                                    }),
                                    hide_index=True,
                                    use_container_width=True
                                )
                        else:
                            st.info(f"No hay transacciones mensuales para {nombre}.")
                    else:
                        st.info("No hay información de fecha para agrupar por mes.")

                pestanas = st.tabs([
                    "🪑 Mesa",
                    "🥡 Recojo",
                    "🏢 Interno",
                    "🛵 PedidosYa",
                    "🚚 Yango",
                    "💳 Pagos",
                    "🧑‍🍳 Meseros",
                    "📊 Total"
                ])

                with pestanas[0]:
                    render_tab_canal("Mesa", CANAL_ALIASES["Mesa"])

                with pestanas[1]:
                    render_tab_canal("Recojo", CANAL_ALIASES["Recojo"])    

                with pestanas[2]:
                    render_tab_canal("Interno", CANAL_ALIASES["Interno"], permitir_internos=True)

                with pestanas[3]:
                    render_tab_canal("PedidosYa", CANAL_ALIASES["PedidosYa"])

                with pestanas[4]:
                    render_tab_canal("Yango", CANAL_ALIASES["Yango"], incluir_alquiler=True)

                with pestanas[5]:
                    analisis_pagos = analista.analisis_pagos_avanzado()

                    if analisis_pagos:
                        c_p1, c_p2 = st.columns(2)

                        with c_p1:
                            st.subheader("Distribución por Cantidad de Ventas")
                            fig_p = px.pie(analisis_pagos["general"], names="Métodos de pago", values="Transacciones", hole=0.4)
                            st.plotly_chart(fig_p, width='stretch', key="pagos_pie")

                        with c_p2:
                            st.subheader("Ticket Promedio por Método")
                            fig_tp = px.bar(analisis_pagos["general"], x="Métodos de pago", y="Ticket_Promedio", 
                                            color="Ticket_Promedio", title="¿Quién gasta más?")
                            st.plotly_chart(fig_tp, width='stretch', key="pagos_ticket")

                        if analisis_pagos["por_tipo_orden"] is not None:
                            st.subheader("Métodos de Pago por Canal (Tipo de Orden)")
                            df_melt = analisis_pagos["por_tipo_orden"].melt(id_vars="Métodos de pago", var_name="Canal", value_name="Transacciones")
                            fig_stack = px.bar(df_melt, x="Canal", y="Transacciones", color="Métodos de pago", 
                                            title="Preferencia de Pago según Canal", barmode="stack")
                            st.plotly_chart(fig_stack, width='stretch', key="pagos_stack")

                        with st.expander("Ver Tabla Financiera Detallada"):
                            st.dataframe(
                                analisis_pagos["general"].style.format({
                                    "Venta_Total": "Bs {:,.2f}",
                                    "Ticket_Promedio": "Bs {:,.2f}",
                                    "Venta_Facturada": "Bs {:,.2f}",
                                    "%_Facturado": "{:.1f}%"
                                })
                            )
                    else:
                        st.info("No se encontraron datos de métodos de pago.")

                with pestanas[6]:
                    meseros_df = analista.performance_meseros()
                    if meseros_df is not None and not meseros_df.empty:
                        mesero_norm = (
                            meseros_df["Mesero"]
                            .astype(str)
                            .str.replace(r"\s+", " ", regex=True)
                            .str.strip()
                            .str.lower()
                            .str.normalize("NFKD")
                            .str.encode("ascii", errors="ignore")
                            .str.decode("utf-8")
                        )
                        meseros_df = meseros_df[mesero_norm != "pedro triveno"]
                    if meseros_df is not None and not meseros_df.empty:
                        st.subheader("Recaudación y Eficiencia por Mesero")
                        
                        # Mostrar KPIs generales si hay datos de horas trabajadas
                        if "Horas_Trabajadas" in meseros_df.columns:
                            total_horas = meseros_df["Horas_Trabajadas"].sum()
                            total_ventas = meseros_df["Total_Vendido"].sum()
                            total_ordenes = meseros_df["Ordenes_Totales"].sum()
                            
                            col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
                            col_kpi1.metric("Horas Totales", f"{total_horas:,.1f} hrs")
                            col_kpi2.metric("Ventas Totales", f"Bs {total_ventas:,.0f}")
                            col_kpi3.metric("Órdenes Totales", f"{total_ordenes:,.0f}")
                            col_kpi4.metric("Promedio por Hora", f"Bs {total_ventas/total_horas:,.0f}/hr" if total_horas > 0 else "N/A")
                            
                            st.markdown("---")
                        
                        # Configurar columnas según datos disponibles
                        if "Horas_Trabajadas" in meseros_df.columns:
                            column_config = {
                                "Total_Vendido": st.column_config.NumberColumn("Total Vendido", format="$%.0f"),
                                "Ordenes_Totales": st.column_config.NumberColumn("Órdenes", format="%d"),
                                "Anulaciones": st.column_config.NumberColumn("Anulaciones", format="%d"),
                                "% Anulacion": st.column_config.NumberColumn("% Anulación", format="%.1f%%"),
                                "Horas_Trabajadas": st.column_config.NumberColumn("Horas Trabajadas", format="%.1f"),
                                "Ventas_por_Hora": st.column_config.NumberColumn("Ventas/Hora", format="$%.0f", help="Eficiencia: Ventas generadas por hora trabajada"),
                                "Ordenes_por_Hora": st.column_config.NumberColumn("Órdenes/Hora", format="%.1f", help="Productividad: Órdenes atendidas por hora"),
                                "Ticket_Promedio": st.column_config.NumberColumn("Ticket Promedio", format="$%.0f", help="Valor promedio por orden")
                            }
                        else:
                            column_config = {
                                "Total_Vendido": st.column_config.NumberColumn("Total Vendido", format="$%.0f"),
                                "Ordenes_Totales": st.column_config.NumberColumn("Órdenes", format="%d"),
                                "Anulaciones": st.column_config.NumberColumn("Anulaciones", format="%d"),
                                "% Anulacion": st.column_config.NumberColumn("% Anulación", format="%.1f%%"),
                                "Ticket_Promedio": st.column_config.NumberColumn("Ticket Promedio", format="$%.0f")
                            }
                        
                        st.dataframe(
                            meseros_df,
                            hide_index=True,
                            use_container_width=True,
                            column_config=column_config
                        )
                        
                        # Visualizaciones adicionales si hay métricas de eficiencia
                        if "Ventas_por_Hora" in meseros_df.columns and "Ordenes_por_Hora" in meseros_df.columns:
                            st.markdown("### Análisis de Eficiencia")
                            
                            col_chart1, col_chart2 = st.columns(2)
                            
                            with col_chart1:
                                # Top 5 por ventas por hora
                                top_ventas_hora = meseros_df.nlargest(5, "Ventas_por_Hora")
                                fig_ventas = px.bar(
                                    top_ventas_hora,
                                    x="Ventas_por_Hora",
                                    y="Mesero",
                                    orientation="h",
                                    title="Top 5: Ventas por Hora Trabajada",
                                    text_auto=".0f",
                                    color="Ventas_por_Hora",
                                    color_continuous_scale="Greens"
                                )
                                fig_ventas.update_layout(yaxis=dict(autorange="reversed"))
                                st.plotly_chart(fig_ventas, use_container_width=True, key="ventas_hora_meseros")
                            
                            with col_chart2:
                                # Top 5 por órdenes por hora
                                top_ordenes_hora = meseros_df.nlargest(5, "Ordenes_por_Hora")
                                fig_ordenes = px.bar(
                                    top_ordenes_hora,
                                    x="Ordenes_por_Hora",
                                    y="Mesero",
                                    orientation="h",
                                    title="Top 5: Órdenes por Hora Trabajada",
                                    text_auto=".1f",
                                    color="Ordenes_por_Hora",
                                    color_continuous_scale="Blues"
                                )
                                fig_ordenes.update_layout(yaxis=dict(autorange="reversed"))
                                st.plotly_chart(fig_ordenes, use_container_width=True, key="ordenes_hora_meseros")
                    else:
                        st.info("No hay datos de meseros disponibles.")

                with pestanas[7]:
                    st.markdown("### 📊 Análisis Total (Todas las órdenes válidas)")
                    st.info("Este análisis incluye: Mesa, Recojo, Delivery (PedidosYa, Yango), Interno. Excluye: Alquileres y órdenes anuladas.")
                    
                    # Filtrar todas las órdenes válidas excluyendo alquileres
                    df_total = analista._excluir_alquiler(analista.df.copy())
                    if "Es_Valido" in df_total.columns:
                        df_total = df_total[df_total["Es_Valido"] == True]
                    
                    # Obtener productos totales
                    df_productos_total = df_productos.copy() if df_productos is not None and not df_productos.empty else pd.DataFrame()
                    
                    if not df_total.empty:
                        kpi_total = AnalistaDeDatos(df_total, "VENTAS").get_kpis_financieros()

                        k1, k2, k3, k4, k5 = st.columns(5)
                        k1.metric("Ventas Totales", f"Bs {kpi_total.get('Ventas Totales',0):,.0f}", "100% del total")
                        k2.metric("Ticket Promedio", f"Bs {kpi_total.get('Ticket Promedio',0):,.0f}")
                        k3.metric("Transacciones", kpi_total.get('Transacciones',0))
                        k4.metric("Descuentos", f"Bs {kpi_total.get('Total Descuentos',0):,.0f}")
                        k5.metric("Pendientes", f"Bs {kpi_total.get('Ventas Pendientes',0):,.0f}")

                        st.markdown("### Top 15 productos más vendidos (Todos los canales)")
                        if not df_productos_total.empty:
                            top_base = df_productos_total.groupby("Producto_Base")["Cantidad"].sum().nlargest(15).reset_index()
                            fig_top = px.bar(top_base, x="Cantidad", y="Producto_Base", orientation="h", text_auto=True, color="Cantidad")
                            fig_top.update_layout(yaxis=dict(autorange="reversed"))
                            st.plotly_chart(fig_top, use_container_width=True, key="fig_top_total")
                        else:
                            st.info("Sin productos detallados.")

                        st.markdown("### Variantes")
                        if not df_productos_total.empty:
                            productos_disponibles = sorted(df_productos_total["Producto_Base"].unique())
                            prod_sel = st.selectbox("Producto", productos_disponibles, key="prod_total")
                            
                            df_sel = df_productos_total[df_productos_total["Producto_Base"] == prod_sel]
                            total_prod = df_sel["Cantidad"].sum()
                            variantes = df_sel.groupby("Variante")["Cantidad"].sum().reset_index()
                            variantes["Porcentaje"] = variantes["Cantidad"] / total_prod * 100 if total_prod else 0

                            if not variantes.empty:
                                col_grafico, col_tabla = st.columns([2, 1]) 

                                with col_grafico:
                                    fig_var = px.pie(variantes, values="Cantidad", names="Variante", 
                                                    title=f"Distribución de {prod_sel}", hole=0.45)
                                    st.plotly_chart(fig_var, use_container_width=True, key="fig_var_total")

                                with col_tabla:
                                    st.write(f"**Total: {total_prod}**") 
                                    st.dataframe(
                                        variantes[["Variante", "Cantidad", "Porcentaje"]], 
                                        hide_index=True, 
                                        use_container_width=True,
                                        height=300
                                    )
                            else:
                                st.info("Sin variantes registradas para este producto.")
                        else:
                            st.info("Sin detalle de productos para analizar variantes.")

                        st.markdown("### Productos comprados juntos")
                        if not df_productos_total.empty:
                            pedidos = df_productos_total.groupby("Id_Venta")["Producto_Base"].apply(lambda s: tuple(sorted(set([p for p in s.dropna()]))))
                            pedidos = pedidos[pedidos.apply(len) > 1]
                            combos = pedidos.value_counts().head(5).reset_index()
                            combos.columns = ["Pedido", "Veces"]
                            combos["Pedido"] = combos["Pedido"].apply(lambda t: " + ".join(t))
                            if not combos.empty:
                                st.write("Top 5 pedidos completos:")
                                st.dataframe(combos, hide_index=True, use_container_width=True)
                            else:
                                st.info("No hay pedidos con múltiples productos.")
                        else:
                            st.info("Sin detalle de productos para analizar combos.")

                        reglas = AnalistaDeDatos(df_total, "VENTAS").basket_analysis(top_n=20, min_support=2)
                        if reglas is not None:
                            reglas["Pareja"] = reglas.apply(lambda r: f"{str(r['item_a']).title()} + {str(r['item_b']).title()}", axis=1)
                            st.write("Top 20 parejas de productos más solicitados")
                            st.dataframe(reglas[["Pareja", "count", "support", "conf_a->b", "conf_b->a"]], hide_index=True, use_container_width=True)
                        else:
                            st.info("No se identificaron parejas frecuentes.")

                        st.markdown("### Frecuencia de pedidos")
                        c_h, c_d = st.columns(2)
                        if "Hora_Num" in df_total.columns:
                            horas = df_total.groupby("Hora_Num")["Id"].nunique().reset_index().rename(columns={"Id": "Pedidos"})
                            c_h.plotly_chart(px.bar(horas, x="Hora_Num", y="Pedidos", title="Cantidad de pedidos por hora"), use_container_width=True, key="freq_hora_total")
                        else:
                            c_h.info("No hay información horaria disponible.")

                        if "Dia_Semana" in df_total.columns:
                            orden_dias = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                            dias = df_total.groupby("Dia_Semana")["Id"].nunique().reindex(orden_dias).dropna().reset_index().rename(columns={"Id": "Pedidos"})
                            c_d.plotly_chart(px.bar(dias, x="Dia_Semana", y="Pedidos", title="Cantidad de pedidos por día"), use_container_width=True, key="freq_dia_total")
                        else:
                            c_d.info("No hay información de día disponible.")

                        st.markdown("### Venta total (monto) por hora y día")
                        c_vh, c_vd = st.columns(2)
                        if "Hora_Num" in df_total.columns:
                            ventas_hora = df_total.groupby("Hora_Num")["Monto total"].sum().reset_index().rename(columns={"Monto total": "Venta_Total"})
                            c_vh.plotly_chart(px.bar(ventas_hora, x="Hora_Num", y="Venta_Total", title="Venta total por hora (Bs)", text_auto=True), use_container_width=True, key="venta_hora_total")
                        else:
                            c_vh.info("No hay información horaria disponible.")

                        if "Dia_Semana" in df_total.columns:
                            ventas_dia = df_total.groupby("Dia_Semana")["Monto total"].sum().reindex(orden_dias).dropna().reset_index().rename(columns={"Monto total": "Venta_Total"})
                            c_vd.plotly_chart(px.bar(ventas_dia, x="Dia_Semana", y="Venta_Total", title="Venta total por día (Bs)", text_auto=True), use_container_width=True, key="venta_dia_total")
                        else:
                            c_vd.info("No hay información de día disponible.")

                        st.markdown("### Ticket promedio por hora y día")
                        c_th, c_td = st.columns(2)
                        if "Hora_Num" in df_total.columns:
                            ticket_hora = df_total.groupby("Hora_Num").agg(
                                Monto_Total=("Monto total", "sum"),
                                Pedidos=("Id", "nunique")
                            ).reset_index()
                            ticket_hora["Ticket_Promedio"] = ticket_hora["Monto_Total"] / ticket_hora["Pedidos"]
                            c_th.plotly_chart(px.bar(ticket_hora, x="Hora_Num", y="Ticket_Promedio", title="Ticket promedio por hora (Bs)", text_auto=True), use_container_width=True, key="ticket_hora_total")
                        else:
                            c_th.info("No hay información horaria disponible.")

                        if "Dia_Semana" in df_total.columns:
                            ticket_dia = df_total.groupby("Dia_Semana").agg(
                                Monto_Total=("Monto total", "sum"),
                                Pedidos=("Id", "nunique")
                            ).reindex(orden_dias).dropna().reset_index()
                            ticket_dia["Ticket_Promedio"] = ticket_dia["Monto_Total"] / ticket_dia["Pedidos"]
                            c_td.plotly_chart(px.bar(ticket_dia, x="Dia_Semana", y="Ticket_Promedio", title="Ticket promedio por día (Bs)", text_auto=True), use_container_width=True, key="ticket_dia_total")
                        else:
                            c_td.info("No hay información de día disponible.")

                        # Análisis detallado por día de la semana
                        st.markdown("### Análisis por día de la semana")
                        if "Dia_Semana" in df_total.columns and "Hora_Num" in df_total.columns:
                            dias_map = {
                                'Monday': 'Lunes',
                                'Tuesday': 'Martes',
                                'Wednesday': 'Miércoles',
                                'Thursday': 'Jueves',
                                'Friday': 'Viernes',
                                'Saturday': 'Sábado',
                                'Sunday': 'Domingo'
                            }
                            dias_disponibles = [d for d in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'] 
                                               if d in df_total["Dia_Semana"].values]
                            
                            if dias_disponibles:
                                dia_seleccionado = st.selectbox(
                                    "Selecciona un día:", 
                                    dias_disponibles,
                                    format_func=lambda x: dias_map.get(x, x),
                                    key="dia_sel_total"
                                )
                                
                                df_dia = df_total[df_total["Dia_Semana"] == dia_seleccionado].copy()
                                
                                if not df_dia.empty:
                                    # Calcular totales de la semana para porcentaje
                                    pedidos_semana = df_total["Id"].nunique()
                                    monto_semana = df_total["Monto total"].sum()
                                    
                                    pedidos_dia = df_dia["Id"].nunique()
                                    monto_dia = df_dia["Monto total"].sum()
                                    ticket_prom_dia = monto_dia / pedidos_dia if pedidos_dia > 0 else 0
                                    
                                    # Porcentajes respecto a la semana
                                    porc_pedidos = (pedidos_dia / pedidos_semana * 100) if pedidos_semana > 0 else 0
                                    porc_monto = (monto_dia / monto_semana * 100) if monto_semana > 0 else 0
                                    
                                    k_d1, k_d2, k_d3 = st.columns(3)
                                    k_d1.metric(
                                        f"Pedidos ({dias_map.get(dia_seleccionado, dia_seleccionado)})", 
                                        pedidos_dia,
                                        f"{porc_pedidos:.1f}% de la semana"
                                    )
                                    k_d2.metric("Ticket Promedio", f"Bs {ticket_prom_dia:,.0f}")
                                    k_d3.metric(
                                        "Monto Total", 
                                        f"Bs {monto_dia:,.0f}",
                                        f"{porc_monto:.1f}% de la semana"
                                    )
                                    
                                    st.markdown(f"#### Pedidos por hora - {dias_map.get(dia_seleccionado, dia_seleccionado)}")
                                    horas_dia = df_dia.groupby("Hora_Num").agg({
                                        "Id": "nunique",
                                        "Monto total": "sum"
                                    }).reset_index()
                                    horas_dia.columns = ["Hora", "Pedidos", "Monto"]
                                    horas_dia["Ticket_Promedio"] = horas_dia["Monto"] / horas_dia["Pedidos"]
                                    horas_dia = horas_dia.sort_values("Hora")
                                    
                                    fig_hora_dia = px.bar(
                                        horas_dia, 
                                        x="Hora", 
                                        y="Pedidos",
                                        title=f"Distribución horaria - {dias_map.get(dia_seleccionado, dia_seleccionado)}",
                                        text_auto=True,
                                        color="Pedidos",
                                        color_continuous_scale="Blues"
                                    )
                                    st.plotly_chart(fig_hora_dia, use_container_width=True, key="hora_dia_total")
                                    
                                    st.markdown("#### Análisis por Turno")
                                    df_dia["Turno"] = df_dia["Hora_Num"].apply(lambda h: "Mañana (00:00-14:00)" if h < 14 else "Tarde (14:00-00:00)")
                                    
                                    turnos = df_dia.groupby("Turno").agg({
                                        "Id": "nunique",
                                        "Monto total": "sum"
                                    }).reset_index()
                                    turnos.columns = ["Turno", "Pedidos", "Monto"]
                                    turnos["Ticket_Promedio"] = turnos["Monto"] / turnos["Pedidos"]
                                    
                                    # Calcular porcentajes respecto al total del día
                                    turnos["Porc_Pedidos"] = (turnos["Pedidos"] / pedidos_dia * 100) if pedidos_dia > 0 else 0
                                    turnos["Porc_Monto"] = (turnos["Monto"] / monto_dia * 100) if monto_dia > 0 else 0
                                    
                                    turnos = turnos.sort_values("Turno", ascending=True)
                                    
                                    col_turnos = st.columns(len(turnos))
                                    for idx, (_, turno_row) in enumerate(turnos.iterrows()):
                                        with col_turnos[idx]:
                                            st.markdown(f"**{turno_row['Turno']}**")
                                            st.metric(
                                                "Pedidos", 
                                                f"{int(turno_row['Pedidos'])}",
                                                f"{turno_row['Porc_Pedidos']:.1f}% del día"
                                            )
                                            st.metric("Ticket Promedio", f"Bs {turno_row['Ticket_Promedio']:,.0f}")
                                            st.metric(
                                                "Monto Total", 
                                                f"Bs {turno_row['Monto']:,.0f}",
                                                f"{turno_row['Porc_Monto']:.1f}% del día"
                                            )
                                    
                                    with st.expander("Ver tabla detallada por turno"):
                                        st.dataframe(
                                            turnos[["Turno", "Pedidos", "Porc_Pedidos", "Monto", "Porc_Monto", "Ticket_Promedio"]].style.format({
                                                "Pedidos": "{:,.0f}",
                                                "Porc_Pedidos": "{:.1f}%",
                                                "Monto": "Bs {:,.2f}",
                                                "Porc_Monto": "{:.1f}%",
                                                "Ticket_Promedio": "Bs {:,.2f}"
                                            }),
                                            hide_index=True,
                                            use_container_width=True
                                        )
                                else:
                                    st.info(f"No hay datos para {dias_map.get(dia_seleccionado, dia_seleccionado)}.")
                            else:
                                st.info("No hay datos de días de la semana disponibles.")
                        else:
                            st.info("No hay información suficiente para análisis por día.")

                        # Análisis mensual GLOBAL (solo en Total)
                        st.markdown("### Resumen de ventas por mes (Global)")
                        if "Fecha_DT" in df_total.columns:
                            df_mes = df_total.copy()
                            df_mes["Mes"] = df_mes["Fecha_DT"].dt.to_period("M").astype(str)
                            
                            # Agregar análisis completo: transacciones, monto y ticket promedio
                            ventas_mes = df_mes.groupby("Mes").agg({
                                "Id": "nunique",
                                "Monto total": "sum"
                            }).reset_index()
                            ventas_mes.columns = ["Mes", "Transacciones", "Monto_Total"]
                            ventas_mes["Ticket_Promedio"] = ventas_mes["Monto_Total"] / ventas_mes["Transacciones"]
                            ventas_mes = ventas_mes.sort_values("Mes")
                            
                            if not ventas_mes.empty:
                                col_m1, col_m2 = st.columns(2)
                                
                                with col_m1:
                                    fig_mes_trans = px.bar(
                                        ventas_mes, 
                                        x="Mes", 
                                        y="Transacciones", 
                                        title="Transacciones por mes (Todos los canales)", 
                                        text_auto=True,
                                        color="Transacciones"
                                    )
                                    st.plotly_chart(fig_mes_trans, use_container_width=True, key="ventas_por_mes_trans_global")
                                
                                with col_m2:
                                    fig_mes_monto = px.bar(
                                        ventas_mes, 
                                        x="Mes", 
                                        y="Monto_Total", 
                                        title="Monto total recaudado por mes (Bs)", 
                                        text_auto=".0f",
                                        color="Monto_Total",
                                        color_continuous_scale="Greens"
                                    )
                                    st.plotly_chart(fig_mes_monto, use_container_width=True, key="ventas_por_mes_monto_global")
                                
                                # Gráfico de ticket promedio
                                fig_mes_ticket = px.line(
                                    ventas_mes, 
                                    x="Mes", 
                                    y="Ticket_Promedio", 
                                    title="Evolución del ticket promedio por mes (Bs)",
                                    markers=True,
                                    text="Ticket_Promedio"
                                )
                                fig_mes_ticket.update_traces(texttemplate='Bs %{text:,.0f}', textposition="top center")
                                st.plotly_chart(fig_mes_ticket, use_container_width=True, key="ventas_por_mes_ticket_global")
                                
                                # Tabla detallada
                                with st.expander("Ver tabla detallada por mes"):
                                    st.dataframe(
                                        ventas_mes.style.format({
                                            "Transacciones": "{:,.0f}",
                                            "Monto_Total": "Bs {:,.2f}",
                                            "Ticket_Promedio": "Bs {:,.2f}"
                                        }),
                                        hide_index=True,
                                        use_container_width=True
                                    )
                            else:
                                st.info("No hay transacciones para calcular el resumen mensual.")
                        else:
                            st.info("No hay información de fecha para agrupar por mes.")
                    else:
                        st.info("No hay datos válidos para análisis total.")
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
                        st.plotly_chart(px.histogram(df_vel, x="Minutos_Servicio"), width='stretch', key="hist_vel")
                    else: st.warning("Faltan columnas de fecha en este reporte.")
                
                with c2:
                    st.subheader("🪑 Ocupación de Mesas")
                    hm = ops.heatmap_mesas()
                    if hm is not None:
                        fig = renderizar_mapa_mesas(hm)
                        if fig:
                            st.plotly_chart(fig, width='stretch', key="map_indice")
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
                    st.plotly_chart(px.box(df_vel, x="Tipo_Orden", y="Minutos_Servicio", points="all"), width='stretch', key="box_vel_maestro")
            
            with tab_m: # Tab Mesas en Fusión
                hm = ops.heatmap_mesas()
                if hm is not None:
                    c_map1, c_map2 = st.columns([2, 1])
                    
                    with c_map1:
                        st.subheader("Mapa de Ocupación del Restaurante")
                        fig_map = renderizar_mapa_mesas(hm)
                        if fig_map:
                            st.plotly_chart(fig_map, width='stretch', key="map_maestro")
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