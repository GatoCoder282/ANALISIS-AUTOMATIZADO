# data/config_reportes.py

REPORTES_CONFIG = {
    # -------------------------------------------------------------------------
    # 1. ÍNDICE MERCAT (Base operativa)
    # -------------------------------------------------------------------------
    "Indice_Mercat": {
        "nombre": "Índice Mercat (Listado de Ordenes)",
        "url": "https://www.mercat.bo/admin/pos_orders/list",
        "campos": {
            "sucursal": {"by": "name", "valor": "shop_id", "tipo": "select"},
            "fecha_inicio": {"by": "name", "valor": "from", "tipo": "text"},
            "fecha_fin": {"by": "name", "valor": "to", "tipo": "text"},
            "con_factura": {"by": "name", "valor": "with_invoice", "tipo": "select"},
            "estado": {"by": "name", "valor": "status", "tipo": "select"},
            "anulado": {"by": "name", "valor": "nullified", "tipo": "select"},
        },
        "btn_generar": "//button[contains(@class, 'generate_report')]",
        "btn_descargar_csv": "//button[contains(@class, 'buttons-csv')]"
    },
    
    # -------------------------------------------------------------------------
    # 2. REPORTE DE VENTAS (Base financiera)
    # -------------------------------------------------------------------------
    "Ventas": {
        "nombre": "Reporte de Ventas",
        "url": "https://www.mercat.bo/admin/pos_orders/sales_report",
        "campos": {
            "sucursal": {"by": "name", "valor": "shop_id", "tipo": "select"},
            "fecha_inicio": {"by": "name", "valor": "from", "tipo": "text"},
            "fecha_fin": {"by": "name", "valor": "to", "tipo": "text"},
            "con_factura": {"by": "name", "valor": "with_invoice", "tipo": "select"},
            "referencia": {"by": "name", "valor": "reference_datetime", "tipo": "select"},
            "anulado": {"by": "name", "valor": "nullified", "tipo": "select"},
        },
        "btn_generar": "//button[contains(@class, 'generate_report')]",
        "btn_descargar_csv": "//button[contains(@class, 'buttons-csv')]"
    },

    # -------------------------------------------------------------------------
    # 3. REPORTE POR PRODUCTO (Detallado con horas)
    # -------------------------------------------------------------------------
    "Por_Producto": {
        "nombre": "Reporte por Producto (Lotes)",
        "url": "https://www.mercat.bo/admin/pos_orders/report_by_product_in_batches",
        "campos": {
            "sucursal": {"by": "name", "valor": "shop_id", "tipo": "select"},
            # Nota: Este reporte usa fecha Y HORA en el placeholder (dd/mm/yyyy hh:mm)
            # El robot deberá manejar esto si el input espera ese formato exacto.
            "fecha_inicio": {"by": "name", "valor": "from", "tipo": "datetime"}, 
            "fecha_fin": {"by": "name", "valor": "to", "tipo": "datetime"},
            
            "agrupar_por": {"by": "name", "valor": "group_by", "tipo": "select"},
            "tipo_orden": {"by": "name", "valor": "order_type", "tipo": "select"},
            "intervalo": {"by": "name", "valor": "grouped_by", "tipo": "select"}, # Agrupar por dia/hora
            "ref_fecha": {"by": "name", "valor": "reports[datetime_type]", "tipo": "select"}, # Creado o Pagado
            "facturacion": {"by": "name", "valor": "invoicing", "tipo": "select"},
            "categoria": {"by": "name", "valor": "product_category_id", "tipo": "select"},
            "pendientes": {"by": "name", "valor": "include_pending", "tipo": "checkbox"},
        },
        "btn_generar": "//button[contains(@class, 'generate_report')]",
        "btn_descargar_csv": "//button[contains(@class, 'buttons-csv')]"
    },

    # -------------------------------------------------------------------------
    # 4. FLUJO DE CAJA (Ingresos)
    # -------------------------------------------------------------------------
    "Ingresos": {
        "nombre": "Reporte de Ingresos (Caja)",
        "url": "https://www.mercat.bo/admin/cash_flows/report",
        "campos": {
            "sucursal": {"by": "name", "valor": "shop_id", "tipo": "select"},
            # Aquí forzamos el valor "ingreso" en el select flow_type
            "tipo_flujo": {"by": "name", "valor": "flow_type", "tipo": "select", "valor_fijo": "ingreso"},
            "fecha_inicio": {"by": "name", "valor": "from", "tipo": "text"},
            "fecha_fin": {"by": "name", "valor": "to", "tipo": "text"},
            "supercategoria": {"by": "name", "valor": "product_supercategory_id", "tipo": "select"},
        },
        "btn_generar": "//button[contains(@class, 'generate_report')]",
        "btn_descargar_csv": "//button[contains(@class, 'buttons-csv')]"
    },

    # -------------------------------------------------------------------------
    # 5. FLUJO DE CAJA (Egresos)
    # -------------------------------------------------------------------------
    "Egresos": {
        "nombre": "Reporte de Egresos (Gastos)",
        "url": "https://www.mercat.bo/admin/cash_flows/report",
        "campos": {
            "sucursal": {"by": "name", "valor": "shop_id", "tipo": "select"},
            # Aquí forzamos el valor "egreso"
            "tipo_flujo": {"by": "name", "valor": "flow_type", "tipo": "select", "valor_fijo": "egreso"},
            "fecha_inicio": {"by": "name", "valor": "from", "tipo": "text"},
            "fecha_fin": {"by": "name", "valor": "to", "tipo": "text"},
            "supercategoria": {"by": "name", "valor": "product_supercategory_id", "tipo": "select"},
        },
        "btn_generar": "//button[contains(@class, 'generate_report')]",
        "btn_descargar_csv": "//button[contains(@class, 'buttons-csv')]"
    },

    # -------------------------------------------------------------------------
    # 6. ACUMULADO
    # -------------------------------------------------------------------------
    "Acumulado": {
        "nombre": "Reporte Acumulado General",
        "url": "https://www.mercat.bo/admin/pos_orders/accumulated_report",
        "campos": {
            "sucursal": {"by": "name", "valor": "shop_id", "tipo": "select"},
            "fecha_inicio": {"by": "name", "valor": "from", "tipo": "text"},
            "fecha_fin": {"by": "name", "valor": "to", "tipo": "text"},
        },
        "btn_generar": "//button[contains(@class, 'generate_report')]",
        "btn_descargar_csv": "//button[contains(@class, 'buttons-csv')]"
    },

    # -------------------------------------------------------------------------
    # 7. AÑADIDOS (Extras)
    # -------------------------------------------------------------------------
    "Anadidos": {
        "nombre": "Reporte de Añadidos (Extras)",
        "url": "https://www.mercat.bo/admin/pos_orders/addons_report",
        "campos": {
            "sucursal": {"by": "name", "valor": "shop_id", "tipo": "select"},
            "fecha_inicio": {"by": "name", "valor": "from", "tipo": "text"},
            "fecha_fin": {"by": "name", "valor": "to", "tipo": "text"},
            "incluir_sin_pagar": {"by": "name", "valor": "include_unpaid", "tipo": "checkbox"},
        },
        "btn_generar": "//button[contains(@class, 'generate_report')]",
        "btn_descargar_csv": "//button[contains(@class, 'buttons-csv')]"
    }
}