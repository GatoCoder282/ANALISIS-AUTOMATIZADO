import pandas as pd
import numpy as np
import re

class AnalistaDeDatos:
    def __init__(self, df, tipo_reporte):
        self.raw_df = df
        self.tipo = tipo_reporte
        self.df = self._limpiar_y_estandarizar()

    def _limpiar_y_estandarizar(self):
        """
        Limpieza y Estandarización según el tipo de reporte.
        """
        df = self.raw_df.copy()
        
        # 1. Limpieza General
        df = df.dropna(axis=1, how='all')
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # 2. Limpieza Numérica General (Quitar símbolos si hay)
        cols_money = ["Monto total", "Subtotal", "Descuento", "Tarifa delivery", "Monto factura"]
        for col in cols_money:
            if col in df.columns:
                # Si viene como string 'Bs 1,200.50', lo limpiamos
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.replace(r'[^\d.-]', '', regex=True)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 3. Lógica Específica
        if self.tipo == "VENTAS":
            # Unir Fecha y Hora
            if "Fecha" in df.columns and "Hora" in df.columns:
                # Asumiendo formato DD/MM/YYYY
                df["Fecha_DT"] = pd.to_datetime(
                    df["Fecha"] + " " + df["Hora"], 
                    format="%d/%m/%Y %H:%M", 
                    errors='coerce',
                    dayfirst=True
                )
            
            # REGLA DE NEGOCIO: Ventas Válidas
            # "Pagado" (Cuidado con mayúsculas/minúsculas) y "Válido"
            # Normalizamos a mayúsculas para evitar errores
            df["Estado_Norm"] = df["Estado"].astype(str).str.upper()
            df["Validez_Norm"] = df["Validez"].astype(str).str.upper()
            df["Tipo_Norm"] = df["Tipo de orden"].astype(str).str.upper()

            df["Es_Valido"] = (df["Estado_Norm"] == "PAGADO") & (df["Validez_Norm"] == "VÁLIDO")
            
            # REGLA: Excluir consumo interno para métricas financieras reales
            df["Es_Venta_Real"] = df["Es_Valido"] & (df["Tipo_Norm"] != "INTERNO")
            
        elif self.tipo == "INDICE":
            if "Creado el" in df.columns:
                df["Fecha_DT"] = pd.to_datetime(df["Creado el"], dayfirst=True, errors='coerce')
            
            # Normalización para Indice
            if "Estado" in df.columns:
                 df["Estado_Norm"] = df["Estado"].astype(str).str.upper()
            
            # En Indice, "Anulado" es una columna "Sí/No"
            if "Anulado" in df.columns:
                df["Es_Valido"] = (df["Estado_Norm"] == "PAGADO") & (df["Anulado"] == "No")
            else:
                df["Es_Valido"] = df["Estado_Norm"] == "PAGADO"

        # Columnas derivadas de tiempo
        if "Fecha_DT" in df.columns:
            df["Dia"] = df["Fecha_DT"].dt.date
            df["Hora_Num"] = df["Fecha_DT"].dt.hour
            # Ordenar días de la semana correctamente
            df["Dia_Semana"] = df["Fecha_DT"].dt.day_name()

        return df

    def get_kpis_financieros(self):
        """Cálculo de KPIs con reglas de negocio estrictas"""
        if "Es_Venta_Real" not in self.df.columns:
            return {}
            
        # Solo ventas reales (Pagadas, Válidas, No Interno)
        df_real = self.df[self.df["Es_Venta_Real"] == True]
        
        total_ventas = df_real["Monto total"].sum()
        num_transacciones = len(df_real)
        ticket_promedio = total_ventas / num_transacciones if num_transacciones > 0 else 0
        
        # Para el KPI de descuentos, usamos todas las válidas (incluso internos pueden tener descuento)
        df_validas = self.df[self.df["Es_Valido"] == True]
        
        return {
            "Ventas Totales": total_ventas,
            "Transacciones": num_transacciones,
            "Ticket Promedio": ticket_promedio,
            "Total Descuentos": df_validas["Descuento"].sum()
        }

    def analizar_productos(self):
        """
        Desglosa la columna 'Detalle' usando Regex para '1x Producto' o '1× Producto'
        """
        if self.tipo != "VENTAS" or "Detalle" not in self.df.columns:
            return None

        # Solo analizamos ventas válidas (incluyendo internos para saber consumo)
        df_analisis = self.df[self.df["Es_Valido"] == True].copy()
        
        items_vendidos = []
        
        # Regex: Busca un número, seguido de 'x' o '×', espacios, y el nombre
        # Detiene la búsqueda antes del siguiente número+x o el final
        patron = r'(\d+)\s*[x×]\s*(.+?)(?=\s\d+\s*[x×]|$)'

        for _, row in df_analisis.iterrows():
            detalle = str(row["Detalle"])
            # Buscamos todas las coincidencias en el string
            matches = re.findall(patron, detalle)
            
            for cantidad, producto in matches:
                items_vendidos.append({
                    "Producto": producto.strip(),
                    "Cantidad": int(cantidad),
                    "Fecha": row["Dia"],
                    "Hora": row["Hora_Num"],
                    "Tipo Orden": row.get("Tipo de orden", "Desconocido"),
                    "Mesero": row.get("Mesero", "Sin Asignar"),
                    "Id_Venta": row["Id"]
                })
        
        return pd.DataFrame(items_vendidos)

    def performance_meseros(self):
        """Analiza ventas y anulaciones por mesero"""
        if "Mesero" not in self.df.columns: return None
        
        # Llenar nulos en mesero
        df = self.df.copy()
        df["Mesero"] = df["Mesero"].fillna("Sin Asignar")
        
        resumen = df.groupby("Mesero").agg(
            # Suma solo si es venta real
            Total_Vendido=pd.NamedAgg(column="Monto total", aggfunc=lambda x: x[df.loc[x.index, "Es_Venta_Real"]].sum()),
            Ordenes_Totales=pd.NamedAgg(column="Id", aggfunc="count"),
            # Cuenta anulados (Validez = ANULADO)
            Anulaciones=pd.NamedAgg(column="Validez", aggfunc=lambda x: (x.astype(str).str.upper() == "ANULADO").sum())
        ).reset_index()
        
        # Evitar división por cero
        resumen["% Anulacion"] = np.where(
            resumen["Ordenes_Totales"] > 0,
            (resumen["Anulaciones"] / resumen["Ordenes_Totales"]) * 100,
            0
        )
        return resumen.sort_values("Total_Vendido", ascending=False)
    
    def metodos_pago_complejos(self):
        """Desglosa pagos mixtos 'Efectivo, QR'"""
        if "Métodos de pago" not in self.df.columns: return None
        
        # Solo ventas válidas
        df_pagos = self.df[self.df["Es_Valido"] == True]["Métodos de pago"].dropna()
        
        # Separar por coma y limpiar espacios
        todos_los_pagos = []
        for pago in df_pagos:
            metodos = [m.strip() for m in pago.split(',')]
            todos_los_pagos.extend(metodos)
            
        return pd.Series(todos_los_pagos).value_counts().reset_index(name="Frecuencia").rename(columns={"index": "Metodo"})

    def analisis_mesas(self):
        """
        Analiza ocupación de mesas (Reporte Ventas tiene 'Tipo de orden'='Mesa' pero no el nombre de la mesa.
        El reporte INDICE sí tiene la columna 'Mesa'.
        Si estamos en VENTAS, solo podemos contar cuántas fueron en mesa vs delivery).
        """
        if self.tipo == "INDICE" and "Mesa" in self.df.columns:
            df_mesas = self.df[self.df["Es_Valido"]==True]
            return df_mesas["Mesa"].value_counts().reset_index(name="Ocupaciones").rename(columns={"index": "Mesa"})
        
        elif self.tipo == "VENTAS" and "Tipo de orden" in self.df.columns:
            # Retornamos distribución por canal (Mesa, Delivery, etc)
            return self.df[self.df["Es_Valido"]==True]["Tipo de orden"].value_counts().reset_index(name="Cantidad")
        
        return None