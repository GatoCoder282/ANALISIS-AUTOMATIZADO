import os
from robotMercat import RobotMercat
from config_reportes import REPORTES_CONFIG

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# Credenciales desde .env (MERCAT_USER, MERCAT_PASS)
USUARIO = os.environ.get("MERCAT_USER")
PASSWORD = os.environ.get("MERCAT_PASS")

def probar_descarga():
    # Carpeta donde se guardarán los archivos
    carpeta_data = os.path.join(os.getcwd(), "data", "reportes")
    if not os.path.exists(carpeta_data):
        os.makedirs(carpeta_data)

    bot = RobotMercat(carpeta_data)
    
    # Esto asegura que la carpeta esté vacía antes de empezar
    bot.limpiar_carpeta_descargas()

    # 1. Login
    if not USUARIO or not PASSWORD:
        raise RuntimeError("Faltan MERCAT_USER o MERCAT_PASS en .env")
    bot.login(USUARIO, PASSWORD)
    
    # 2. Definir qué queremos descargar
    # REPORTE 1: Indice Mercat
    params_indice = {
        "fecha_inicio": "26/11/2025",
        "fecha_fin": "26/11/2025",
        "sucursal": "1087", # ID de C&C que viste en el HTML
        "estado": "pagado" # Ejemplo de filtro opcional
    }
    
    # REPORTE 2: Ventas
    params_ventas = {
        "fecha_inicio": "01/11/2025",
        "fecha_fin": "30/11/2025",
        "sucursal": "1087",
        "con_factura": "true" # Segun el HTML value="true" es Sí
    }

    # 3. Ejecutar descargas
    # Prueba con el Indice
    bot.descargar_reporte(REPORTES_CONFIG["Indice_Mercat"], params_indice)
    
    # Prueba con Ventas
    # bot.descargar_reporte(REPORTES_CONFIG["Ventas"], params_ventas)
    
    # 4. Cerrar
    bot.cerrar()

if __name__ == "__main__":
    probar_descarga()