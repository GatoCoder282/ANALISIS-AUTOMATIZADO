import pandas as pd
import numpy as np

class AnalistaOperacional:
    def __init__(self, df_ventas=None, df_indice=None):
        # Permitimos que cualquiera de los dos sea None para flexibilidad
        self.df_ventas = self._preparar_ventas(df_ventas)
        self.df_indice = self._preparar_indice(df_indice)
        self.df_maestro = self._fusionar_y_validar()

    def _preparar_ventas(self, df):
        """Limpia y prepara el dataframe de Ventas"""
        if df is None: return None
        df = df.copy()
        # Limpieza básica si no viene limpia
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # Estandarizar
        if "Número" in df.columns: df = df.rename(columns={"Número": "Ticket_ID"})
        if "Tipo de orden" in df.columns: df = df.rename(columns={"Tipo de orden": "Tipo_Orden"})
        if "Monto total" in df.columns: df = df.rename(columns={"Monto total": "Monto_Ventas"})
        
        # Fechas para cruce
        if "Fecha" in df.columns:
             # Asumimos que ya viene formateada o es string
             df["Dia_Join"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors='coerce').dt.date
        return df

    def _preparar_indice(self, df):
        if df is None: return None
        df = df.copy()
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

        # Mapeo de columnas (Índice) -> Nombres Estandarizados
        rename_map = {
            "Número": "ticket_id", "Numero": "ticket_id",
            "Tipo": "tipo_orden_idx",
            "Mesa": "mesa",
            "Estado": "estado_idx",
            "Monto total": "monto",
            "Creado el": "creado_el",
            "Pagado el": "pagado_el",
            "Anulado": "anulado"
        }
        df = df.rename(columns=rename_map)

        # Fechas: convertir a datetime con nombres estandarizados adicionales
        for col in ["creado_el", "pagado_el"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

        # Normalizaciones adicionales para compatibilidad con el maestro
        # Crear columnas en el formato que el resto del código espera
        if "creado_el" in df.columns:
            df["Creado_DT"] = df["creado_el"]
            df["fecha_dia"] = df["creado_el"].dt.date
            df["Dia_Join"] = df["creado_el"].dt.date  # mismo nombre que usa ventas
        if "pagado_el" in df.columns:
            df["Pagado_DT"] = df["pagado_el"]

        # Ticket id: asegurar Ticket_ID (mayúsculas) para fusión con ventas
        if "ticket_id" in df.columns and "Ticket_ID" not in df.columns:
            df["Ticket_ID"] = df["ticket_id"]
        # Mesa: crear Mesa_Real si no existe (heatmap espera Mesa_Real)
        if "mesa" in df.columns and "Mesa_Real" not in df.columns:
            df["Mesa_Real"] = df["mesa"]

        # Limpieza numérica (por si acaso el índice trae Bs o comas)
        if "monto" in df.columns:
            if df["monto"].dtype == 'object':
                df["monto"] = df["monto"].astype(str).str.replace(r'[^\d.-]', '', regex=True)
            df["monto"] = pd.to_numeric(df["monto"], errors='coerce').fillna(0)

        # Normalizar anulado a boolean si existe
        if "anulado" in df.columns:
            df["anulado"] = df["anulado"].astype(str).str.lower().isin(["sí", "si", "true", "yes", "1"])

        return df

    def _fusionar_y_validar(self):
        """Fusión inteligente"""
        # Si falta uno, devolvemos el que hay (adaptado)
        if self.df_ventas is None: return self.df_indice
        if self.df_indice is None: return self.df_ventas

        # Asegurar claves de fusión en ambos lados (Ticket_ID, Dia_Join)
        left = self.df_ventas.copy()
        right = self.df_indice.copy()

        # Normalizar nombres alternativos
        if "ticket_id" in left.columns and "Ticket_ID" not in left.columns:
            left["Ticket_ID"] = left["ticket_id"]
        if "ticket_id" in right.columns and "Ticket_ID" not in right.columns:
            right["Ticket_ID"] = right["ticket_id"]

        if "fecha_dia" in left.columns and "Dia_Join" not in left.columns:
            left["Dia_Join"] = left["fecha_dia"]
        if "fecha_dia" in right.columns and "Dia_Join" not in right.columns:
            right["Dia_Join"] = right["fecha_dia"]

        # Si ventas trae "Fecha" como string, intentar convertir a date en Dia_Join ya en _preparar_ventas
        try:
            df_merged = pd.merge(
                left,
                right,
                on=["Ticket_ID", "Dia_Join"],
                how="left",
                suffixes=("", "_idx")
            )
            return df_merged
        except Exception as e:
            print(f"Error en fusión: {e}")
            # Intento alternativo: merge solo por Ticket_ID si Dia_Join no está alineado
            try:
                df_merged = pd.merge(left, right, on=["Ticket_ID"], how="left", suffixes=("", "_idx"))
                print("Fusión alternativa por Ticket_ID aplicada.")
                return df_merged
            except Exception as e2:
                print(f"Error en fusión alternativa: {e2}")
                return self.df_ventas

    def kpis_velocidad(self):
        """Calcula tiempos de servicio (Requiere columnas de Índice)"""
        df = self.df_maestro.copy()
        if "Creado_DT" not in df.columns or "Pagado_DT" not in df.columns:
            return None, None

        df["Minutos_Servicio"] = (df["Pagado_DT"] - df["Creado_DT"]).dt.total_seconds() / 60
        # Filtro lógica negocio: Tiempos positivos y menores a 5 horas (300 min)
        df = df[(df["Minutos_Servicio"] >= 0) & (df["Minutos_Servicio"] < 300)]
        
        if df.empty: return None, None

        kpis = {
            "Tiempo Promedio Global": df["Minutos_Servicio"].mean(),
            "Ticket Más Rápido": df["Minutos_Servicio"].min(),
            "Ticket Más Lento": df["Minutos_Servicio"].max()
        }
        
        # Si existe Tipo de Orden, desglosamos
        if "Tipo_Orden" in df.columns:
            kpis["Promedio Mesa"] = df[df["Tipo_Orden"] == "Mesa"]["Minutos_Servicio"].mean()
            kpis["Promedio Delivery"] = df[df["Tipo_Orden"] == "Delivery"]["Minutos_Servicio"].mean()
        elif "Tipo_Orden_Indice" in df.columns: # Fallback a columna de Indice
             kpis["Promedio Mesa"] = df[df["Tipo_Orden_Indice"] == "Mesa"]["Minutos_Servicio"].mean()
             
        return kpis, df

    def heatmap_mesas(self):
        """
        Analiza ocupación de mesas basada en CONTEO de visitas.
        Filtra solo lo anulado (operativamente no cuenta), pero incluye todo lo demás.
        """
        df = self.df_maestro.copy()
        if "Mesa_Real" not in df.columns: return None

        # 1. Limpieza de datos nulos o genéricos
        # Eliminamos filas donde no hay mesa asignada
        df_mesas = df.dropna(subset=["Mesa_Real"])
        
        # 2. Filtro Operativo
        # Queremos contar "veces que consumieron", por lo tanto excluimos solo los ANULADOS.
        # (Todo lo que sea 'Pagado', 'Pendiente', con o sin factura, cuenta como ocupación).
        if "anulado" in df_mesas.columns:
            # Normalizar a string para comparar seguro
            df_mesas = df_mesas[~df_mesas["anulado"].astype(str).str.lower().isin(["sí", "si", "true", "yes"])]

        # 3. Agrupación
        stats = df_mesas.groupby("Mesa_Real").agg(
            Ocupaciones=('ticket_id', 'nunique'),      # Conteo de visitas únicas
            Facturacion_Total=('monto', 'sum'),        # Total dinero
            Ticket_Promedio=('monto', 'mean')          # Promedio por visita
        ).reset_index()
        
        # Ordenar por Ocupación (lo más importante ahora)
        return stats.sort_values("Ocupaciones", ascending=False)