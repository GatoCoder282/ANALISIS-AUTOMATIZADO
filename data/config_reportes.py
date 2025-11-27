# config_reportes.py

REPORTES_CONFIG = {
    "Indice_Mercat": {
        "nombre": "Índice Mercat (Listado de Ordenes)",
        "url": "https://www.mercat.bo/admin/pos_orders/list",
        # Mapeo de campos: 'nombre_parametro_tu_app': 'selector_selenium'
        "campos": {
            "sucursal": {"by": "name", "valor": "shop_id", "tipo": "select"},
            "fecha_inicio": {"by": "name", "valor": "from", "tipo": "text"},
            "fecha_fin": {"by": "name", "valor": "to", "tipo": "text"},
            "con_factura": {"by": "name", "valor": "with_invoice", "tipo": "select"},
            "estado": {"by": "name", "valor": "status", "tipo": "select"},
            "anulado": {"by": "name", "valor": "nullified", "tipo": "select"},
            # Agrega aquí más campos si los necesitas en el futuro
        },
        # Botón Generar (Refresca la tabla)
        "btn_generar": "//button[contains(@class, 'generate_report')]",
        # Botón CSV (Descarga real)
        "btn_descargar_csv": "//button[contains(@class, 'buttons-csv')]"
    },
    
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
    }
}