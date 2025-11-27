import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import glob

class RobotMercat:
    def __init__(self, download_folder):
        self.download_folder = download_folder
        
        options = webdriver.ChromeOptions()
        prefs = {
            "download.default_directory": self.download_folder,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.wait = WebDriverWait(self.driver, 15) # 15 seg de espera máxima

    def login(self, usuario, password):
        """Inicia sesión en el ERP"""
        try:
            print("🔵 Iniciando sesión...")
            self.driver.get("https://www.mercat.bo/users/sign_in")
            
            # Usamos IDs fijos del login que me diste antes (o user_login si ese es el real)
            # Nota: En tu código anterior usaste las constantes USUARIO como ID, cuidado ahí.
            # Basado en tu html anterior, el ID suele ser 'user_login'
            user_field = self.wait.until(EC.element_to_be_clickable((By.ID, "user_login")))
            user_field.clear()
            user_field.send_keys(usuario)
            
            pass_field = self.driver.find_element(By.ID, "user_password")
            pass_field.clear()
            pass_field.send_keys(password)
            
            btn_ingresar = self.driver.find_element(By.NAME, "commit")
            btn_ingresar.click()
            
            print("✅ Login enviado.")
            # Esperar a que cargue la siguiente página (buscando un elemento del dashboard o simplemente esperando un poco)
            time.sleep(3) 
            
        except Exception as e:
            print(f"❌ Error en Login: {e}")

    def _llenar_campo(self, selector_info, valor_a_ingresar):
        """Método auxiliar robusto para llenar campos"""
        tipo_selector = getattr(By, selector_info['by'].upper()) 
        selector_valor = selector_info['valor']
        
        # Esperamos que el elemento exista
        elemento = self.wait.until(EC.presence_of_element_located((tipo_selector, selector_valor)))
        
        if selector_info['tipo'] == 'text':
            # ESTRATEGIA 1: Limpiar y escribir (La normal)
            try:
                elemento.clear()
                elemento.send_keys(valor_a_ingresar)
                
                # ESTRATEGIA 2: Forzar valor con JS (Si el datepicker es rebelde)
                # Esto sobreescribe el valor interno del input directamente
                self.driver.execute_script("arguments[0].value = arguments[1];", elemento, valor_a_ingresar)
                
                # Opcional: Disparar evento 'change' para que la página sepa que cambió
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", elemento)
                
            except Exception as e:
                print(f"⚠️ Error escribiendo en {selector_valor}, intentando solo JS...")
                self.driver.execute_script("arguments[0].value = arguments[1];", elemento, valor_a_ingresar)

        elif selector_info['tipo'] == 'select':
            # ... (El código del select se mantiene igual) ...
            select = Select(elemento)
            try:
                select.select_by_value(str(valor_a_ingresar))
            except:
                select.select_by_visible_text(str(valor_a_ingresar))

    def descargar_reporte(self, config_reporte, parametros):
        """
        config_reporte: El diccionario de config_reportes.py
        parametros: Diccionario con los valores que quieres filtrar. Ej:
                    {'fecha_inicio': '01/11/2025', 'sucursal': '1087'}
        """
        try:
            print(f"🔵 Navegando a: {config_reporte['nombre']}...")
            self.driver.get(config_reporte['url'])
            
            # 1. Llenar todos los filtros recibidos
            print("⚙️ Aplicando filtros...")
            campos_config = config_reporte['campos']
            
            for clave, valor in parametros.items():
                if clave in campos_config:
                    self._llenar_campo(campos_config[clave], valor)
                else:
                    print(f"⚠️ Advertencia: El campo '{clave}' no existe en la configuración de este reporte.")

            # 2. Click en GENERAR
            print("🔄 Generando vista previa...")
            # Esperamos a que el botón exista en el DOM
            btn_generar = self.wait.until(EC.presence_of_element_located((By.XPATH, config_reporte['btn_generar'])))
            
            # Hacemos scroll hasta el botón por si acaso (ayuda visual)
            self.driver.execute_script("arguments[0].scrollIntoView();", btn_generar)
            time.sleep(1) # Pequeña pausa para que el scroll termine
            
            # EL TRUCO DE MAGIA: Clic vía JavaScript (Ignora footers y overlays)
            self.driver.execute_script("arguments[0].click();", btn_generar)
            
            # Esperar a que la tabla se recargue.
            self._esperar_barra_progreso()

            # 3. Click en CSV (Descarga real)
            print("⬇️ Descargando CSV...")
            btn_csv = self.wait.until(EC.presence_of_element_located((By.XPATH, config_reporte['btn_descargar_csv'])))
            
            # También usamos JS aquí por si el footer también tapa este botón
            self.driver.execute_script("arguments[0].scrollIntoView();", btn_csv)
            self.driver.execute_script("arguments[0].click();", btn_csv)
            
            # Espera de descarga
            print("⏳ Esperando archivo...")
            self._esperar_descarga_archivo() # (Opcional: ver punto 3 abajo)
            print(f"✅ {config_reporte['nombre']} procesado.")
            
        except Exception as e:
            print(f"❌ Error en proceso: {e}")

    def cerrar(self):
        self.driver.quit()

    def limpiar_carpeta_descargas(self):
        """Borra todos los archivos .csv o .xlsx de la carpeta data para evitar confusiones"""
        print("🧹 Limpiando carpeta de descargas...")
        # Busca patrones de archivos
        archivos = glob.glob(os.path.join(self.download_folder, "*.*"))
        
        for archivo in archivos:
            try:
                # Solo borramos si no es un script de python (por seguridad)
                if not archivo.endswith(".py"): 
                    os.remove(archivo)
                    print(f"   - Eliminado: {os.path.basename(archivo)}")
            except Exception as e:
                print(f"   ! No se pudo borrar {archivo}: {e}")
        print("✨ Carpeta limpia.")


    def renombrar_ultimo_archivo(self, nuevo_nombre_base):
        """
        Busca el CSV más reciente y lo renombra de forma segura.
        Espera a que desaparezcan los temporales.
        """
        try:
            # 1. Esperar estabilidad (máximo 10 seg extra)
            # Esperamos a que NO haya archivos .crdownload o .tmp recientes
            tiempo_espera = 0
            archivo_reciente = None
            
            while tiempo_espera < 10:
                lista_archivos = glob.glob(os.path.join(self.download_folder, "*"))
                if not lista_archivos:
                    time.sleep(1)
                    tiempo_espera += 1
                    continue

                # Tomamos el más nuevo
                archivo_reciente = max(lista_archivos, key=os.path.getctime)
                
                # Si es temporal, esperamos
                if archivo_reciente.endswith('.crdownload') or archivo_reciente.endswith('.tmp'):
                    print(f"⏳ Descarga en curso ({os.path.basename(archivo_reciente)})... esperando.")
                    time.sleep(1)
                    tiempo_espera += 1
                else:
                    # ¡Es un archivo firme! Salimos del bucle
                    break

            if not archivo_reciente: return None

            # 2. Construir nombre nuevo FORZANDO .csv
            # Limpiamos el nombre de caracteres inválidos
            nombre_limpio = "".join(c for c in nuevo_nombre_base if c.isalnum() or c in (' ', '_', '-')).strip()
            nuevo_nombre = f"{nombre_limpio}.csv" # <--- FORZAMOS .csv AQUÍ
            nueva_ruta = os.path.join(self.download_folder, nuevo_nombre)
            
            # 3. Reemplazo seguro (Windows a veces bloquea si existe)
            if os.path.exists(nueva_ruta):
                try:
                    os.remove(nueva_ruta)
                except PermissionError:
                    print(f"⚠️ El archivo {nuevo_nombre} está abierto, no se puede sobrescribir.")
                    return None

            # Esperar un microsegundo para liberar el lock del sistema de archivos
            time.sleep(0.5)
            os.rename(archivo_reciente, nueva_ruta)
            
            print(f"🏷️ Renombrado final: {nuevo_nombre}")
            return nuevo_nombre
            
        except Exception as e:
            print(f"⚠️ Error al renombrar: {e}")
            return None
        
    def _esperar_barra_progreso(self):
        """
        Vigila la barra de progreso hasta que llegue al 100%
        """
        try:
            # 1. Esperar a que la barra aparezca (máximo 3 seg)
            # Usamos un wait corto aquí porque la barra debería salir casi de inmediato tras el click
            wait_barra = WebDriverWait(self.driver, 5) 
            
            barra = wait_barra.until(EC.visibility_of_element_located((By.CLASS_NAME, "progress-bar")))
            print("⏳ Procesando reporte (Barra detectada)...")

            # 2. Esperar hasta que 'aria-valuenow' sea '100'
            # Le damos más tiempo (ej: 60 seg) porque el reporte puede ser pesado
            wait_proceso = WebDriverWait(self.driver, 60)
            
            wait_proceso.until(lambda d: 
                barra.get_attribute("aria-valuenow") == "100"
            )
            
            print("✅ Procesamiento al 100%.")
            
            # Pequeña pausa de seguridad para que la animación termine y habilite botones
            time.sleep(1) 

        except Exception as e:
            # Si entra aquí, puede ser que el reporte fue tan rápido que la barra ni se vio
            # o que tardó demasiado.
            print("⚡ El reporte cargó rápido o no se detectó barra de progreso.")

    def _esperar_descarga_archivo(self, timeout=30):
        """Espera hasta que aparezca un archivo nuevo en la carpeta que no sea .crdownload"""
        print("Sniffeando carpeta de descargas...")
        tiempo_inicio = time.time()
        
        while time.time() - tiempo_inicio < timeout:
            archivos = os.listdir(self.download_folder)
            # Buscamos archivos que NO sean temporales de chrome (.crdownload)
            archivos_validos = [f for f in archivos if not f.endswith('.crdownload') and f.endswith('.csv')]
            
            if archivos_validos:
                return True
            time.sleep(1) # Chequear cada segundo
            
        print("⚠️ Tiempo de espera de descarga agotado.")
        return False