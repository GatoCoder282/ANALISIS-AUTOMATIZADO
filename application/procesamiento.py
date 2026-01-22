import pandas as pd
import numpy as np
import re
import itertools
from collections import Counter

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
        
        # 2. Limpieza Numérica
        cols_money = ["Monto total", "Subtotal", "Descuento", "Tarifa delivery", "Monto factura"]
        for col in cols_money:
            if col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.replace(r'[^\d.-]', '', regex=True)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 3. Lógica Específica
        if self.tipo == "VENTAS":
            if "Fecha" in df.columns and "Hora" in df.columns:
                df["Fecha_DT"] = pd.to_datetime(
                    df["Fecha"] + " " + df["Hora"], 
                    format="%d/%m/%Y %H:%M", 
                    errors='coerce',
                    dayfirst=True
                )
            
            # Normalización de estados
            df["Estado_Norm"] = df["Estado"].astype(str).str.upper()
            df["Validez_Norm"] = df["Validez"].astype(str).str.upper()
            df["Tipo_Norm"] = df["Tipo de orden"].astype(str).str.upper()

            # -------------------------------------------------------
            # NUEVO: LÓGICA DE EXCLUSIÓN DE YANGO / ALQUILER
            # -------------------------------------------------------
            if "Detalle" in df.columns:
                # Buscamos patrones específicos al inicio del string
                # Nota: Manejamos tanto 'x' como '×' por si acaso
                patron_yango = r"\d[x×]\s*Cuota de membresía por Oficina C&C \(|1[x×]\s*Entrega de insumos \("
                
                df["Es_Alquiler"] = df["Detalle"].astype(str).str.contains(patron_yango, regex=True, case=False)
            else:
                df["Es_Alquiler"] = False

            df["Es_Valido"] = (df["Estado_Norm"] == "PAGADO") & (df["Validez_Norm"] == "VÁLIDO")
            df["Es_Venta_Real"] = df["Es_Valido"] & (df["Tipo_Norm"] != "INTERNO") & (~df["Es_Alquiler"])
            df["Es_Interno"] = df["Es_Valido"] & (df["Tipo_Norm"] == "INTERNO")
            df["Es_Valido_Pago_Pendiente"] = (df["Estado_Norm"] != "PAGADO") & (df["Validez_Norm"] == "VÁLIDO")
            
        elif self.tipo == "INDICE":
            if "Creado el" in df.columns:
                df["Fecha_DT"] = pd.to_datetime(df["Creado el"], dayfirst=True, errors='coerce')
            
            if "Estado" in df.columns: df["Estado_Norm"] = df["Estado"].astype(str).str.upper()
    
            if "Anulado" in df.columns:
                df["Es_Valido"] = (df["Estado_Norm"] == "PAGADO") & (df["Anulado"].astype(str).str.upper() == "NO")
            else:
                df["Es_Valido"] = df["Estado_Norm"] == "PAGADO"

        if "Fecha_DT" in df.columns:
            df["Dia"] = df["Fecha_DT"].dt.date
            df["Hora_Num"] = df["Fecha_DT"].dt.hour
            df["Dia_Semana"] = df["Fecha_DT"].dt.day_name()

        return df

    # --- NUEVO MÉTODO PARA VER EL DATO AISLADO ---
    def get_kpi_alquileres(self):
        """Retorna el monto total de Membresías Yango (separado de la venta operativa)"""
        if "Es_Alquiler" not in self.df.columns: return 0
        
        # Solo sumamos si es válido (Pagado)
        alquileres = self.df[(self.df["Es_Alquiler"] == True) & (self.df["Es_Valido"] == True)]
        return alquileres["Monto total"].sum()
    
    def _excluir_alquiler(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Excluye filas marcadas como Es_Alquiler (Yango / alquiler) de un DataFrame.
        Devuelve copia del df filtrado. Si la columna no existe devuelve el df tal cual.
        """
        if df is None:
            return df
        if "Es_Alquiler" in df.columns:
            mask = df["Es_Alquiler"].astype(bool)
            if mask.any():
                return df.loc[~mask].copy()
        return df

    def get_kpis_financieros(self):
        """Cálculo de KPIs con reglas de negocio estrictas"""
        if "Es_Venta_Real" not in self.df.columns:
            return {}
        # trabajamos sobre copia y excluimos alquileres
        df = self._excluir_alquiler(self.df.copy())
        # --- BASES DE FILTRADO ---
        df_real       = df[df["Es_Venta_Real"]]             # Ventas reales, pagadas, válidas
        df_validas    = df[df["Es_Valido"]]                 # Para descuentos
        df_internas   = df[df["Es_Interno"]]                # Ventas internas válidas
        df_pendientes = df[df["Es_Valido_Pago_Pendiente"]]  # Válidas pero con pago pendiente
        
        
        total_ventas = df_real.get("Monto total", pd.Series(dtype=float)).sum()
        num_transacciones = len(df_real)
        ticket_promedio = total_ventas / num_transacciones if num_transacciones > 0 else 0
        total_descuentos = df_validas["Descuento"].sum()
        total_pendiente = df_pendientes["Monto total"].sum()
        total_interno = df_internas["Monto total"].sum() if not df_internas.empty else 0
        total_pagado = total_ventas
        ratio_pagado = total_pagado / (total_pagado + total_pendiente) if (total_pagado + total_pendiente) > 0 else 0

        
        return {
            "Ventas Totales": total_ventas,
            "Transacciones": num_transacciones,
            "Ticket Promedio": ticket_promedio,
            "Total Descuentos": total_descuentos,
            "Ventas Pendientes": total_pendiente,
            "Consumo Interno": total_interno,
            "Ratio Pagado": ratio_pagado,
            }

    def analizar_productos(self):
        """
        Desglosa la columna 'Detalle' separando Producto Base de sus Variantes.
        """
        if self.tipo != "VENTAS" or "Detalle" not in self.df.columns:
            return None

        # 1. Preparar DF
        df_analisis = self._excluir_alquiler(self.df.copy())
        df_analisis = df_analisis[df_analisis["Es_Valido"] == True].copy()
        
        items_vendidos = []
        
        # 2. NUEVO REGEX AVANZADO
        # Grupo 1: Cantidad
        # Grupo 2: Producto Base (hasta encontrar ':', '.', '(' o el final)
        # Grupo 3: Variantes (Opcional, lo que sigue después de los separadores)
        # Lookahead: Se detiene antes del siguiente "1x" o el final de la línea
        patron_item = r'(\d+)\s*[x×]\s*(.+?)(?=\s+\d+\s*[x×]|$)'

        # --- PASO 2: PATRÓN DE LIMPIEZA DE NOMBRE ---
        # Separa "Cappuccino (Leche almendra)" en "Cappuccino" y "Leche almendra"
        # Corta en ':', '(', o '.'
        patron_variante = r'^([^(:.]+)(?:[\(:\.]\s*(.+?)\)?)?$'

        for _, row in df_analisis.iterrows():
            detalle = str(row["Detalle"]).replace("\n", " ") # Limpiar saltos de línea
            
            # Paso 1: Encontrar todos los items en el string gigante
            matches_items = re.findall(patron_item, detalle)
            
            for cantidad, nombre_sucio in matches_items:
                nombre_sucio = nombre_sucio.strip()
                
                # Paso 2: Diseccionar el nombre sucio
                match_var = re.search(patron_variante, nombre_sucio)
                
                if match_var:
                    p_base = match_var.group(1).strip().title()
                    # Si hay grupo 2 (variante), lo usamos, sino es Original
                    p_var = match_var.group(2).strip() if match_var.group(2) else "Original/Sin Cambios"
                else:
                    # Fallback por si acaso (raro)
                    p_base = nombre_sucio.title()
                    p_var = "Original/Sin Cambios"

                # Nombre completo legible
                p_completo = f"{p_base} ({p_var})" if p_var != "Original/Sin Cambios" else p_base

                items_vendidos.append({
                    "Producto_Base": p_base,
                    "Variante": p_var,
                    "Producto_Completo": p_completo,
                    "Cantidad": int(cantidad),
                    "Producto": p_base, # Retrocompatibilidad con funciones viejas que usaban 'Producto'
                    "Fecha": row.get("Dia"),
                    "Hora": row.get("Hora_Num"),
                    "Tipo Orden": row.get("Tipo de orden", "Desconocido"),
                    "Mesero": row.get("Mesero", "Sin Asignar"),
                    "Id_Venta": row.get("Id")
                })
        
        if not items_vendidos:
            return None
            
        return pd.DataFrame(items_vendidos)

    def performance_meseros(self):
        """Analiza ventas y anulaciones por mesero"""
        if "Mesero" not in self.df.columns: return None
        # trabajar sobre copia excluyendo alquileres
        df = self._excluir_alquiler(self.df.copy())
        
        # Llenar nulos en mesero
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
    
    def analisis_pagos_avanzado(self):
        """
        Desglose profundo de Métodos de Pago:
        1. General: Transacciones, Total, Ticket Promedio.
        2. Por Tipo de Orden: Cruzar Metodo vs Canal (Mesa, Delivery, etc).
        """
        # Usamos solo ventas válidas y excluimos alquileres
        df = self._excluir_alquiler(self.df.copy())
        df = df[df["Es_Valido"] == True].copy()
        
        if "Métodos de pago" not in df.columns: return None

        # NOTA: Para Ticket Promedio financiero correcto, NO separamos pagos mixtos 
        # (ej: "Efectivo, QR" se trata como una categoría única "Mixto" o se deja tal cual
        # para no duplicar el monto al calcular promedios).
        
        # 1. Tabla General (Agrupada por Método exacto)
        general = df.groupby("Métodos de pago").agg(
            Transacciones=("Id", "nunique"),
            Venta_Total=("Monto total", "sum"),
            Ticket_Promedio=("Monto total", "mean")
        ).reset_index().sort_values("Venta_Total", ascending=False)

        # 2. Matriz por Tipo de Orden (Crosstab)
        # Filas: Método, Columnas: Tipo de Orden, Valores: Cantidad de Transacciones
        if "Tipo de orden" in df.columns:
            matriz_tipo = pd.crosstab(
                df["Métodos de pago"], 
                df["Tipo de orden"]
            ).reset_index()
        else:
            matriz_tipo = None

        return {
            "general": general,
            "por_tipo_orden": matriz_tipo
        }
    
    def metodos_pago_complejos(self):
        """Desglosa pagos mixtos 'Efectivo, QR'"""
        if "Métodos de pago" not in self.df.columns: return None
        
        # Solo ventas válidas
        df_pagos = self._excluir_alquiler(self.df.copy())
        df_pagos = df_pagos[df_pagos["Es_Valido"] == True]["Métodos de pago"].dropna()
        
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
            df_mesas = self._excluir_alquiler(self.df.copy())
            df_mesas = df_mesas[df_mesas["Es_Valido"]==True]
            return df_mesas["Mesa"].value_counts().reset_index(name="Ocupaciones").rename(columns={"index": "Mesa"})
        
        elif self.tipo == "VENTAS" and "Tipo de orden" in self.df.columns:
            dfv = self._excluir_alquiler(self.df.copy())
            return dfv[dfv["Es_Valido"]==True]["Tipo de orden"].value_counts().reset_index(name="Cantidad")
        
        return None

    def build_master_df(self, df_indice=None):
        """
        Construye un DataFrame maestro normalizado con columnas clave:
        ticket_id, fecha_hora, producto (si aplica), precio, mesero, mesa, tipo_orden,
        estado, cliente, metodo_pago, descuento, anulacion
        """
        df = self.df.copy()
        # Normalizaciones defensivas
        # Ticket id
        for col in ["Id", "Número", "Ticket_ID"]:
            if col in df.columns:
                df["ticket_id"] = df[col]
                break
        # Fecha/hora
        if "Fecha_DT" in df.columns:
            df["fecha_hora"] = df["Fecha_DT"]
        elif "Creado el" in df.columns:
            df["fecha_hora"] = pd.to_datetime(df["Creado el"], dayfirst=True, errors='coerce')
        elif "Fecha" in df.columns and "Hora" in df.columns:
            df["fecha_hora"] = pd.to_datetime(df["Fecha"] + " " + df["Hora"], dayfirst=True, errors='coerce', format="%d/%m/%Y %H:%M")
        # Cliente
        for col in ["Cliente", "Cliente Nombre", "Nombre Cliente"]:
            if col in df.columns:
                df["cliente"] = df[col]
                break
        # Mesero, mesa, tipo, estado, metodo pago, monto, descuento, anulacion
        df["mesero"] = df["Mesero"] if "Mesero" in df.columns else df.get("Mesero", None)
        df["mesa"] = df.get("Mesa", df.get("Mesa_Real", None))
        df["tipo_orden"] = df.get("Tipo de orden", df.get("Tipo_Norm", df.get("Tipo", None)))
        df["estado"] = df.get("Estado", df.get("Estado_Norm", None))
        df["metodo_pago"] = df.get("Métodos de pago", df.get("Metodo de pago", None))
        # Montos
        amt_cols = ["Monto total", "Monto_Ventas", "Monto"]
        for c in amt_cols:
            if c in df.columns:
                df["monto"] = pd.to_numeric(df[c], errors='coerce').fillna(0)
                break
        if "Descuento" in df.columns:
            df["descuento"] = pd.to_numeric(df["Descuento"], errors='coerce').fillna(0)
        # Anulado
        if "Anulado" in df.columns:
            df["anulado"] = df["Anulado"].astype(str).str.lower().isin(["sí", "si", "true", "yes"])
        elif "Validez" in df.columns:
            df["anulado"] = df["Validez"].astype(str).str.upper() == "ANULADO"
        # Estado de pago pendiente
        df["pendiente_pago"] = df.get("Estado", "").astype(str).str.lower().isin(["pendiente", "por pagar", "pending"])
        # Si me dieron índice lo uno por ticket_id/fecha
        if df_indice is not None:
            # también excluir alquileres en ventas antes de unir con índice
            df = self._excluir_alquiler(df)
            idx = df_indice.copy()
            # intentar un join por ticket y día
            if "Creado_DT" in idx.columns:
                idx["fecha_dia"] = pd.to_datetime(idx["Creado_DT"], dayfirst=True, errors='coerce').dt.date
            if "fecha_hora" in df.columns:
                df["fecha_dia"] = pd.to_datetime(df["fecha_hora"], dayfirst=True, errors='coerce').dt.date
            if "ticket_id" in df.columns and "Ticket_ID" in idx.columns:
                merged = pd.merge(df, idx, left_on=["ticket_id","fecha_dia"], right_on=["Ticket_ID","fecha_dia"], how="left", suffixes=("","_idx"))
                return merged
        return df

    def basket_analysis(self, top_n=20, min_support=2):
        """
        Análisis de mercado simple: pares de productos que ocurren juntos.
        ACTUALIZADO: Usa regex robusto con \s+ para separar items.
        """
        if "Detalle" not in self.df.columns and "producto" not in self.df.columns:
            return None

        # Construir lista de transacciones (lista de sets de productos)
        tx_items = []

        if "Detalle" in self.df.columns:
            patron = r'(\d+)\s*[x×]\s*(.+?)(?=\s+\d+\s*[x×]|$)' 
            df_valid = self._excluir_alquiler(self.df.copy())
            grouped = df_valid[df_valid["Es_Valido"]==True].groupby("Id")["Detalle"].agg(lambda s: "   ".join(s.dropna().astype(str)))
            
            for detalle in grouped:
                matches = re.findall(patron, str(detalle))
                items = [m[1].strip().lower() for m in matches if m[1].strip()]
                
                if items:
                    tx_items.append(list(set(items)))
        else:
            df_valid = self._excluir_alquiler(self.df.copy())
            grouped = df_valid[df_valid["Es_Valido"]==True].groupby("ticket_id")["producto"].agg(lambda s: list(set(s.dropna().astype(str).str.lower())))
            tx_items = grouped.tolist()

        pair_counts = Counter()
        item_counts = Counter()
        
        for items in tx_items:
            for it in items:
                item_counts[it] += 1
            for a,b in itertools.combinations(sorted(items),2):
                pair_counts[(a,b)] += 1
        
        total_tx = len(tx_items)
        if total_tx == 0:
            return None
            
        rows = []
        for (a,b),cnt in pair_counts.most_common(top_n):
            support = (cnt / total_tx) * 100
            conf_a = (cnt / item_counts[a]) * 100 if item_counts[a] else 0
            conf_b = (cnt / item_counts[b]) * 100 if item_counts[b] else 0
            
            if cnt >= min_support: 
                rows.append({
                    "item_a": a, "item_b": b, "count": cnt, 
                    "support": support, "conf_a->b": conf_a, "conf_b->a": conf_b
                })
                
        return pd.DataFrame(rows)

    def market_basket_rules(self, min_support=0.01, min_confidence=0.3, max_len=3, top_n=50):
        """
        Apriori-like rules generator (simple, puro Python).
        Devuelve reglas con soporte, confianza y lift ordenadas por lift.
        Requiere columna 'Detalle' (o 'producto' con transaction_id 'ticket_id').
        """
        # 1) Construir transacciones (lista de sets)
        tx_items = []
        if "Detalle" in self.df.columns:
            patron = r'(\d+)\s*[x×]\s*(.+?)(?=\s\d+\s*[x×]|$)'
            df_valid = self._excluir_alquiler(self.df.copy())
            grouped = df_valid[df_valid["Es_Valido"]==True].groupby("Id")["Detalle"].agg(lambda s: " ||| ".join(s.dropna().astype(str)))
            for detalle in grouped:
                matches = re.findall(patron, str(detalle))
                items = [m[1].strip().lower() for m in matches if m[1].strip()]
                if items:
                    tx_items.append(sorted(set(items)))
        elif "producto" in self.df.columns and "ticket_id" in self.df.columns:
            df_valid = self._excluir_alquiler(self.df.copy())
            grouped = df_valid[df_valid["Es_Valido"]==True].groupby("ticket_id")["producto"].agg(lambda s: list(set(s.dropna().astype(str).str.lower())))
            tx_items = [sorted(x) for x in grouped.tolist() if x]

        if not tx_items:
            return None

        N = len(tx_items)

        # 2) contar itemsets por tamaño
        itemset_counts = {}
        for k in range(1, max_len+1):
            counts = Counter()
            for items in tx_items:
                if len(items) < k: continue
                for combo in itertools.combinations(items, k):
                    counts[tuple(sorted(combo))] += 1
            itemset_counts[k] = counts

        # 3) generar reglas a partir de itemsets de tamaño >=2
        rules = []
        for k in range(2, max_len+1):
            for itemset, cnt in itemset_counts.get(k, {}).items():
                support = cnt / N
                if support < min_support:
                    continue
                itemset = tuple(itemset)
                # generar todas las particiones: antecedente -> consecuente
                all_subsets = []
                for r in range(1, len(itemset)):
                    for antecedent in itertools.combinations(itemset, r):
                        consequent = tuple(sorted(set(itemset) - set(antecedent)))
                        antecedent = tuple(sorted(antecedent))
                        cnt_ant = itemset_counts[len(antecedent)].get(antecedent, 0)
                        cnt_cons = itemset_counts[len(consequent)].get(consequent, 0)
                        if cnt_ant == 0: continue
                        confidence = cnt / cnt_ant
                        if confidence < min_confidence: continue
                        # lift = confidence / support(consequent)
                        support_cons = cnt_cons / N if cnt_cons else 0
                        lift = confidence / support_cons if support_cons > 0 else np.nan
                        rules.append({
                            "antecedent": antecedent,
                            "consequent": consequent,
                            "support": support,
                            "confidence": confidence,
                            "lift": lift,
                            "count": cnt
                        })
        if not rules:
            return None
        df_rules = pd.DataFrame(rules)
        # Ordenar y devolver top_n
        df_rules = df_rules.sort_values(["lift","confidence","support"], ascending=[False, False, False]).head(top_n)
        return df_rules.reset_index(drop=True)

    def productos_problematicos(self, top_n=20):
         """
         Identifica productos con mayor cantidad de anulaciones, descuentos y tendencias semanales.
         Requiere columna 'Detalle' para descomponer por producto.
         Retorna dict con tablas: 'anulaciones', 'descuentos', 'tendencia_semanal', 'nunca_vendidos'
         """
         # Extraer items por transacción
         if "Detalle" not in self.df.columns:
             return None
         patron = r'(\d+)\s*[x×]\s*(.+?)(?=\s\d+\s*[x×]|$)'
         rows = []
         # iterar solo ventas válidas y sin alquiler
         df_iter = self._excluir_alquiler(self.df.copy())
         for _, row in df_iter.iterrows():
             detalle = str(row.get("Detalle",""))
             matches = re.findall(patron, detalle)
             for q,p in matches:
                 prod = p.strip().lower()
                 rows.append({
                     "ticket_id": row.get("Id"),
                     "producto": prod,
                     "cantidad": int(q),
                     "monto_ticket": row.get("Monto total", 0),
                     "anulado": (str(row.get("Validez","")).upper() == "ANULADO") or (str(row.get("Anulado","")).lower() in ["sí","si","true","yes"]),
                     "descuento": float(row.get("Descuento", 0) or 0),
                     "fecha": row.get("Fecha_DT", row.get("Creado el", None))
                 })
         if not rows:
             return None
         items_df = pd.DataFrame(rows)
         items_df["fecha"] = pd.to_datetime(items_df["fecha"], errors='coerce')
         items_df["week"] = items_df["fecha"].dt.to_period("W").apply(lambda p: p.start_time.date())

         # Anulaciones por producto
         anulaciones = items_df.groupby("producto").agg(
             anulaciones_count=pd.NamedAgg(column="anulado", aggfunc="sum"),
             ventas_count=pd.NamedAgg(column="ticket_id", aggfunc=lambda s: s.nunique())
         ).reset_index()
         anulaciones["%_anulacion"] = anulaciones["anulaciones_count"] / anulaciones["ventas_count"].replace(0, np.nan) * 100
         anulaciones = anulaciones.sort_values("anulaciones_count", ascending=False).head(top_n)

         # Descuentos por producto (sumado)
         descuentos = items_df.groupby("producto").agg(
             total_descuento=pd.NamedAgg(column="descuento", aggfunc="sum"),
             ventas_count=pd.NamedAgg(column="ticket_id", aggfunc=lambda s: s.nunique())
         ).reset_index().sort_values("total_descuento", ascending=False).head(top_n)

         # Tendencia semanal (últimas N semanas -> pct change)
         weekly = items_df.groupby(["week","producto"])["cantidad"].sum().reset_index()
         pivot = weekly.pivot(index="week", columns="producto", values="cantidad").fillna(0)
         if pivot.empty:
             pct_df = pd.DataFrame()
         else:
             pct = pivot.pct_change().fillna(0)
             # calculamos promedio de cambios absolutos o relativos según prefieras; usamos media simple aquí
             avg_pct = pct.mean().sort_values(ascending=False)
             pct_df = avg_pct.reset_index().rename(columns={0: "avg_weekly_pct_change", "index": "producto"})
             # Asegurar nombres correctos
             pct_df.columns = ["producto", "avg_weekly_pct_change"]

         # productos nunca vendidos: placeholder
         never_sold = []

         return {
             "anulaciones": anulaciones,
             "descuentos": descuentos,
             "tendencia_semanal": pct_df,
             "nunca_vendidos": never_sold
         }

    def vip_products(self, top_pct=0.2):
        """
        Ley de Pareto: productos que generan el top_pct de ventas.
        Retorna tabla con share acumulado y flag VIP.
        """
        # Obtener items con monto; si no hay monto por item, distribuimos monto del ticket proporcionalmente por cantidad
        items = []
        if "Detalle" in self.df.columns:
            patron = r'(\d+)\s*[x×]\s*(.+?)(?=\s\d+\s*[x×]|$)'
            for _, row in self.df.iterrows():
                detalle = str(row.get("Detalle",""))
                matches = re.findall(patron, detalle)
                total_qty = sum(int(m[0]) for m in matches) if matches else 0
                for q,p in matches:
                    prod = p.strip().lower()
                    qty = int(q)
                    monto_ticket = float(row.get("Monto total", 0) or 0)
                    # asignar monto proporcional por cantidad
                    monto_item = (monto_ticket * (qty / total_qty)) if total_qty>0 else 0
                    items.append({"producto": prod, "monto": monto_item})
        elif "producto" in self.df.columns:
            df_iter = self._excluir_alquiler(self.df.copy())
            items = df_iter[["producto","monto"]].rename(columns={"monto":"monto"}).to_dict('records')

        if not items:
            return None

        items_df = pd.DataFrame(items)
        agg = items_df.groupby("producto")["monto"].sum().reset_index().sort_values("monto", ascending=False)
        total = agg["monto"].sum()
        agg["share"] = agg["monto"] / total
        agg["cumsum"] = agg["share"].cumsum()
        # marcar VIPs: primeros productos que suman top_pct del total
        agg["VIP"] = agg["cumsum"] <= top_pct
        return agg
    # ... (resto de métodos de AnalistaDeDatos) ...

    def ventas_por_tiempo(self, agrupacion="D"):
        """
        Agrupa ventas por Día (D) o Hora (H).
        Usado para gráficos de tendencias y horas pico.
        """
        # Trabajamos sobre una copia filtrada (solo ventas válidas)
        df = self.df.copy()
        df = self._excluir_alquiler(df)
        if "Es_Valido" in df.columns:
            df = df[df["Es_Valido"] == True]
            
        if "Fecha_DT" not in df.columns:
            return pd.DataFrame() # Retorna vacío si no hay fechas
        
        if agrupacion == "D":
            # Agrupar por Fecha (Día completo)
            return df.groupby("Dia")["Monto total"].sum().reset_index().rename(columns={"Dia": "Fecha"})
            
        elif agrupacion == "H":
            # Agrupar por Hora (0-23)
            if "Hora_Num" in df.columns:
                return df.groupby("Hora_Num")["Monto total"].sum().reset_index()
            
        return pd.DataFrame()

    def weekly_heatmap(self):
        """
        Crea la matriz para el mapa de calor (Día de la Semana vs Hora).
        Retorna un DataFrame pivoteado.
        """
        df = self.df.copy()
        df = self._excluir_alquiler(df)
        if "Es_Valido" in df.columns:
            df = df[df["Es_Valido"] == True]
            
        if "Dia_Semana" not in df.columns or "Hora_Num" not in df.columns:
            return None
            
        # Crear tabla dinámica: Filas=Hora, Columnas=Día, Valores=Venta Total
        pivot = df.pivot_table(
            index="Hora_Num", 
            columns="Dia_Semana", 
            values="Monto total", 
            aggfunc="sum"
        ).fillna(0)
        
        # Ordenar los días lógicamente (Lunes a Domingo)
        dias_orden = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        # Filtrar solo los días que existen en los datos para no romper nada
        cols_existentes = [d for d in dias_orden if d in pivot.columns]
        pivot = pivot[cols_existentes]
        
        return pivot
    def bcg_matrix(self, weeks_window=4, date_col=None):
        """
        Matriz BCG robusta por producto.
        - weeks_window: tamaño de la ventana reciente y anterior en semanas.
        - date_col: nombre de la columna fecha si no es detectada automáticamente.
        Retorna DataFrame con: producto, rev_recent, rev_prev, growth, revenue_total, category
        """
        df = self._excluir_alquiler(self.df.copy())

        # detectar columna fecha
        if date_col and date_col in df.columns:
            df["__fecha"] = pd.to_datetime(df[date_col], errors="coerce")
        else:
            for c in ["fecha_hora", "Fecha_DT", "Creado_DT", "Creado el", "Fecha"]:
                if c in df.columns:
                    df["__fecha"] = pd.to_datetime(df[c], errors="coerce", dayfirst=True)
                    break
        if "__fecha" not in df.columns or df["__fecha"].isna().all():
            return None

        # construir items por producto (producto columna o parseo de Detalle)
        items = []
        if "producto" in df.columns:
            tmp = df.loc[df.get("Es_Valido", True)==True, ["producto", "__fecha"] + ([ "monto"] if "monto" in df.columns else ["Monto total"] if "Monto total" in df.columns else [])].copy()
            monto_col = "monto" if "monto" in tmp.columns else ("Monto total" if "Monto total" in tmp.columns else None)
            for _, r in tmp.iterrows():
                prod = str(r["producto"]).strip().lower()
                val = float(r[monto_col]) if monto_col else 0.0
                items.append({"producto": prod, "monto": val, "fecha": r["__fecha"]})
        elif "Detalle" in df.columns:
            patron = r'(\d+)\s*[x×]\s*(.+?)(?=\s\d+\s*[x×]|$)'
            df_valid = df[df.get("Es_Valido", True)==True]
            for _, r in df_valid.iterrows():
                detalle = str(r.get("Detalle",""))
                matches = re.findall(patron, detalle)
                total_qty = sum(int(m[0]) for m in matches) if matches else 0
                monto_ticket = float(r.get("monto", r.get("Monto total", 0)) or 0)
                for q,p in matches:
                    prod = p.strip().lower()
                    qty = int(q)
                    monto_item = (monto_ticket * (qty / total_qty)) if total_qty>0 else (monto_ticket if len(matches)==1 else 0)
                    items.append({"producto": prod, "monto": monto_item, "fecha": r["__fecha"]})
        else:
            return None

        items_df = pd.DataFrame(items)
        if items_df.empty:
            return None
        items_df["fecha"] = pd.to_datetime(items_df["fecha"], errors='coerce')
        max_date = items_df["fecha"].max()
        recent_start = max_date - pd.Timedelta(weeks=weeks_window)
        prev_start = recent_start - pd.Timedelta(weeks=weeks_window)

        recent = items_df[items_df["fecha"] > recent_start]
        prev = items_df[(items_df["fecha"] > prev_start) & (items_df["fecha"] <= recent_start)]

        rev_recent = recent.groupby("producto")["monto"].sum().rename("rev_recent")
        rev_prev = prev.groupby("producto")["monto"].sum().rename("rev_prev")

        bcg = pd.concat([rev_recent, rev_prev], axis=1).fillna(0)
        bcg["revenue_total"] = bcg["rev_recent"] + bcg["rev_prev"]

        # growth: manejo defensivo (si prev==0 y recent>0 => growth = large positive number)
        # calculamos growth con protección y marcamos casos con prev==0 y recent>0 con valor grande para que clasifiquen como "growth"
        bcg["growth"] = 0.0
        mask_prev_zero = (bcg["rev_prev"] == 0) & (bcg["rev_recent"] > 0)
        bcg.loc[~mask_prev_zero, "growth"] = (bcg["rev_recent"] - bcg["rev_prev"]) / bcg["rev_prev"].replace({0: np.nan})
        # asignar valor grande razonable para crecimiento desde cero (evita np.inf -> NaN)
        bcg.loc[mask_prev_zero, "growth"] = bcg.loc[mask_prev_zero, "rev_recent"] / 1.0  # escala como "alto" growth (1x of revenue)
        bcg["growth"] = bcg["growth"].replace([np.inf, -np.inf], np.nan)

        # thresholds: mediana robusta (ignorar NaN en growth)
        rev_thresh = bcg["revenue_total"].median() if not bcg["revenue_total"].empty else 0
        growth_thresh = bcg["growth"].median(skipna=True) if not bcg["growth"].dropna().empty else 0

        def classify(row):
            rev = row["revenue_total"]
            gr = row["growth"] if not pd.isna(row["growth"]) else -9999
            if rev >= rev_thresh and gr > growth_thresh:
                return "Star"
            if rev >= rev_thresh and gr <= growth_thresh:
                return "Cash Cow"
            if rev < rev_thresh and gr > growth_thresh:
                return "Question Mark"
            return "Dog"

        bcg["category"] = bcg.apply(classify, axis=1)
        bcg = bcg.reset_index().sort_values(["revenue_total","growth"], ascending=[False, False])
        return bcg
    def recurrence_analysis(self, min_visits=2):
        """
        Identifica clientes recurrentes y métricas de recurrencia.
        Retorna dict con:
         - recurrent_clients: int
         - mean_days_between: float | None
         - visits_per_month_mean: float
         - ticket_prom_new: float
         - ticket_prom_freq: float
         - retention_table: DataFrame (cohort retention rates) o None
        """
        df = self.df.copy()
        # detectar columna cliente
        cliente_col = None
        for c in ["cliente", "Cliente", "Nombre Cliente", "Cliente Nombre"]:
            if c in df.columns:
                cliente_col = c
                break
        if cliente_col is None:
            return None

        # detectar columna fecha/hora
        if "fecha_hora" in df.columns:
            df["fecha_hora"] = pd.to_datetime(df["fecha_hora"], errors="coerce")
        elif "Fecha_DT" in df.columns:
            df["fecha_hora"] = pd.to_datetime(df["Fecha_DT"], errors="coerce")
        elif "Creado el" in df.columns:
            df["fecha_hora"] = pd.to_datetime(df["Creado el"], dayfirst=True, errors="coerce")
        else:
            # si no hay fechas válidas devolvemos None para indicar insuficiente info
            return None

        # trabajar solo con filas que tengan cliente y fecha válida
        df = df.dropna(subset=[cliente_col, "fecha_hora"]).copy()
        if df.empty:
            return None

        # normalizar monto para cálculos de ticket promedio
        monto_col = None
        for m in ["monto", "Monto total", "Monto", "Venta_Total"]:
            if m in df.columns:
                monto_col = m
                break
        if monto_col is None:
            # si no hay monto, creamos columna con 0 para evitar errores
            df["monto_tmp"] = 0.0
            monto_col = "monto_tmp"

        # fecha día (para contar visitas únicas por día)
        df["fecha_dia"] = df["fecha_hora"].dt.date
        # mes periodo
        df["mes_periodo"] = df["fecha_hora"].dt.to_period("M")

        # visitas únicas por cliente (dias distintos)
        visits = df.groupby(cliente_col)["fecha_dia"].nunique().rename("visits")
        recurrent = visits[visits >= min_visits]
        n_recurrent = int(len(recurrent))

        # visitas por mes (promedio por cliente)
        visits_month = df.groupby([cliente_col, "mes_periodo"]).size().groupby(level=0).mean().rename("visits_per_month")
        visits_per_month_mean = float(visits_month.mean()) if not visits_month.empty else 0.0

        # definir clientes frecuentes
        frequent_clients = set(recurrent.index)

        # ticket promedio: calcular ticket promedio por cliente (promedio de montos por ticket)
        # identificamos ticket id si existe
        ticket_id_col = None
        for tid in ["ticket_id", "Id", "Id_Venta", "Ticket_ID"]:
            if tid in df.columns:
                ticket_id_col = tid
                break

        if ticket_id_col:
            # monto por ticket (agregar si hay varias filas por ticket)
            monto_por_ticket = df.groupby([ticket_id_col, cliente_col])[monto_col].sum().reset_index()
            # avg_ticket_by_cliente será una Series indexed por cliente
            avg_ticket_by_cliente = monto_por_ticket.groupby(cliente_col)[monto_col].mean()
            clientes_presentes = list(avg_ticket_by_cliente.index)
            new_clients = [c for c in clientes_presentes if c not in frequent_clients]
            freq_clients = [c for c in clientes_presentes if c in frequent_clients]
            ticket_prom_new = float(avg_ticket_by_cliente.loc[new_clients].mean()) if new_clients else 0.0
            ticket_prom_freq = float(avg_ticket_by_cliente.loc[freq_clients].mean()) if freq_clients else 0.0
        else:
            # fallback: usar promedio por fila (menos preciso)
            df["is_frequent"] = df[cliente_col].isin(frequent_clients)
            ticket_prom_new = float(df[~df["is_frequent"]][monto_col].mean()) if not df[~df["is_frequent"]].empty else 0.0
            ticket_prom_freq = float(df[df["is_frequent"]][monto_col].mean()) if not df[df["is_frequent"]].empty else 0.0

        # frecuencia: días promedio entre visitas para recurrentes
        days_between_means = []
        for c in frequent_clients:
            fechas = sorted(df[df[cliente_col] == c]["fecha_dia"].dropna().unique())
            if len(fechas) >= 2:
                diffs = pd.Series(pd.to_datetime(fechas)).diff().dropna().dt.days
                if not diffs.empty:
                    days_between_means.append(float(diffs.mean()))
        mean_days_between = float(np.mean(days_between_means)) if days_between_means else None

        # Retención: cohort por semana (semana de primera visita)
        df["week"] = df["fecha_hora"].dt.to_period("W").apply(lambda p: p.start_time.date())
        cohort = df.groupby(cliente_col)["week"].min().rename("cohort_week")
        df_cohort = df.merge(cohort, left_on=cliente_col, right_index=True, how="left")
        pivot = df_cohort.groupby(["cohort_week", "week"])[cliente_col].nunique().unstack(fill_value=0)
        if not pivot.empty:
            cohort_sizes = pivot.iloc[:,0]  # first column corresponds to cohort size
            retention = pivot.div(cohort_sizes, axis=0).fillna(0)
        else:
            retention = None

        return {
            "recurrent_clients": n_recurrent,
            "mean_days_between": mean_days_between,
            "visits_per_month_mean": visits_per_month_mean,
            "ticket_prom_new": ticket_prom_new,
            "ticket_prom_freq": ticket_prom_freq,
            "retention_table": retention
        }
    
    def clientes_ballena(self, top_n=10):
        """
        Top clientes por facturación y su porcentaje sobre total.
        Busca columnas alternativas para monto, ticket_id y cliente.
        """
        df = self.df.copy()

        # detectar columna cliente
        cliente_col = next((c for c in ["cliente", "Cliente", "Nombre Cliente", "Cliente Nombre"] if c in df.columns), None)
        if cliente_col is None:
            return None

        # detectar columna monto
        monto_col = next((c for c in ["monto", "Monto total", "Monto", "Venta_Total", "Total"] if c in df.columns), None)
        if monto_col is None:
            df["monto_tmp"] = 0.0
            monto_col = "monto_tmp"

        # detectar columna ticket id
        ticket_col = next((c for c in ["ticket_id", "Ticket_ID", "Id", "ID", "Número", "Numero"] if c in df.columns), None)

        # Agrupación segura: si existe ticket_id usamos nunique, si no usamos conteo por cliente
        if ticket_col is not None:
            agg = df.groupby(cliente_col).agg(
                ventas=(monto_col, "sum"),
                transacciones=(ticket_col, "nunique")
            ).reset_index()
        else:
            agg = df.groupby(cliente_col).agg(
                ventas=(monto_col, "sum"),
                transacciones=(cliente_col, "count")
            ).reset_index()

        total = agg["ventas"].sum() if not agg.empty else 1
        agg["%_sobre_total"] = agg["ventas"] / total * 100
        return agg.sort_values("ventas", ascending=False).head(top_n)
    def control_anulados_y_pendientes(self):
        """
        Reporte de anulados y pendientes: cantidad y monto.
        CORREGIDO: Verifica existencia de columnas antes de filtrar.
        """
        df = self.df.copy()
        
        # 1. Identificar Pendientes de Pago
        # Si la columna ya existe la usamos, sino la calculamos aquí
        if "pendiente_pago" not in df.columns:
            # Lógica para detectar pendientes basada en la columna "Estado"
            if "Estado" in df.columns:
                # Normalizamos a minúsculas para comparar
                estado_norm = df["Estado"].astype(str).str.lower()
                df["pendiente_pago"] = estado_norm.isin(["pendiente", "por pagar", "pending", "pendiente de pago"])
            else:
                # Si no hay columna Estado, asumimos False
                df["pendiente_pago"] = False

        # Ahora sí filtramos de forma segura
        pendientes = df[df["pendiente_pago"] == True]

        # 2. Identificar Anulados
        if "anulado" not in df.columns:
            if "Validez" in df.columns:
                df["anulado"] = df["Validez"].astype(str).str.upper() == "ANULADO"
            elif "Anulado" in df.columns:
                df["anulado"] = df["Anulado"].astype(str).str.lower().isin(["sí", "si", "true", "yes"])
            else:
                df["anulado"] = False
                
        anulados = df[df["anulado"] == True]
        
        # 3. Retornar reporte
        return {
            "anulados_count": len(anulados),
            "anulados_monto": anulados["monto"].sum() if "monto" in anulados.columns and not anulados.empty else 0,
            "pendientes_count": len(pendientes),
            "pendientes_monto": pendientes["monto"].sum() if "monto" in pendientes.columns and not pendientes.empty else 0,
            "pendientes_por_cliente": pendientes.groupby("cliente")["monto"].sum().reset_index() if "cliente" in df.columns and not pendientes.empty else None,
            # Ajuste: "mesa" a veces no existe en ventas, usamos "Tipo de orden" como fallback o None
            "pendientes_por_mesa": pendientes.groupby("mesa")["monto"].sum().reset_index() if "mesa" in df.columns and not pendientes.empty else None
        }