import time
import os
import glob
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import shutil

class RobotMercat:
    DEFAULT_WAIT = 20
    PROGRESS_WAIT = 60
    DOWNLOAD_WAIT = 45

    def __init__(self, download_folder):
        # Asegurar folder y usar Path
        self.download_folder = str(Path(download_folder).resolve())
        Path(self.download_folder).mkdir(parents=True, exist_ok=True)

        options = webdriver.ChromeOptions()
        prefs = {
            "download.default_directory": self.download_folder,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # Headless configurable por entorno (default: habilitado en servidores)
        headless = os.environ.get("CHROME_HEADLESS", "true").lower() in ["1", "true", "yes"]
        if headless:
            options.add_argument("--headless=new")

        # Usar chromedriver del sistema si existe (producción), sino webdriver-manager (desarrollo)
        system_chromedriver = shutil.which('chromedriver')
        if system_chromedriver:
            self.driver = webdriver.Chrome(service=Service(system_chromedriver), options=options)
        else:
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.wait = WebDriverWait(self.driver, self.DEFAULT_WAIT)

    def login(self, usuario, password):
        """Inicia sesión en el ERP con espera robusta."""
        try:
            self.driver.get("https://www.mercat.bo/users/sign_in")
            user_field = self.wait.until(EC.element_to_be_clickable((By.ID, "user_login")))
            user_field.clear()
            user_field.send_keys(usuario)

            pass_field = self.wait.until(EC.presence_of_element_located((By.ID, "user_password")))
            pass_field.clear()
            pass_field.send_keys(password)

            btn_ingresar = self.wait.until(EC.element_to_be_clickable((By.NAME, "commit")))
            self.driver.execute_script("arguments[0].click();", btn_ingresar)

            # Espera mínima de transición
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "navbar")))
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"❌ Error en Login: {e}")
            return False


    def _formatear_datetime(self, valor, selector_valor, tipo):
        """Devuelve fecha/hora con extremos para from/to."""
        s = str(valor).strip()
        if tipo == 'datetime':
            if len(s) <= 10:  # solo fecha dd/mm/yyyy
                if 'from' in selector_valor.lower():
                    return f"{s} 00:00"
                if 'to' in selector_valor.lower():
                    return f"{s} 23:59"
        return s
    

    def _llenar_campo(self, selector_info, valor_a_ingresar):
        """Llena campos compatibles con config_reportes.py."""
        by = selector_info.get('by', '').upper()
        selector_valor = selector_info.get('valor', '')
        tipo_campo = selector_info.get('tipo', 'text')

        if not by or not selector_valor:
            print(f"⚠️ Config de campo inválida: {selector_info}")
            return

        tipo_selector = getattr(By, by)

        # Override con valor fijo
        if 'valor_fijo' in selector_info:
            valor_a_ingresar = selector_info['valor_fijo']

        try:
            elemento = self.wait.until(EC.presence_of_element_located((tipo_selector, selector_valor)))

            if tipo_campo in ['date', 'datetime', 'text']:
                valor_fmt = self._formatear_datetime(valor_a_ingresar, selector_valor, tipo_campo if tipo_campo in ['date', 'datetime'] else 'text')

                # Intento normal
                try:
                    elemento.clear()
                    elemento.send_keys(valor_fmt)
                except:
                    pass

                # ESTRATEGIA 2: Forzar valor con JS y disparar eventos
                try:
                    self.driver.execute_script("arguments[0].value = arguments[1];", elemento, valor_fmt)
                    self.driver.execute_script("arguments[0].dispatchEvent(new Event('input'));", elemento)
                    self.driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", elemento)
                except Exception as e:
                    print(f"⚠️ JS set value falló en {selector_valor}: {e}")

                # Cerrar popup del date/datetime picker
                try:
                    self.driver.find_element(By.TAG_NAME, 'body').click()
                except:
                    pass

            elif tipo_campo == 'select':
                select = Select(elemento)
                try:
                    select.select_by_value(str(valor_a_ingresar))
                except:
                    try:
                        select.select_by_visible_text(str(valor_a_ingresar))
                    except:
                        print(f"⚠️ No se pudo seleccionar '{valor_a_ingresar}' en {selector_valor}")

            elif tipo_campo == 'checkbox':
                debe_estar_marcado = str(valor_a_ingresar).lower() in ['true', '1', 'on', 'yes', 'sí', 'si']
                esta_marcado = elemento.is_selected()
                if debe_estar_marcado != esta_marcado:
                    self.driver.execute_script("arguments[0].click();", elemento)

            else:
                print(f"⚠️ Tipo de campo desconocido: {tipo_campo}")

        except Exception as e:
            print(f"⚠️ Error llenando campo {selector_valor}: {e}")

    def _esperar_barra_progreso(self):
        """Espera barra de progreso 100%, tolerante si no aparece."""
        try:
            wait_barra = WebDriverWait(self.driver, 5)
            barra = wait_barra.until(EC.visibility_of_element_located((By.CLASS_NAME, "progress-bar")))
            wait_proceso = WebDriverWait(self.driver, self.PROGRESS_WAIT)
            wait_proceso.until(lambda d: barra.get_attribute("aria-valuenow") == "100")
            time.sleep(0.5)
        except Exception:
            # Puede cargar sin barra
            pass

    def _esperar_descarga_archivo(self, timeout=None, extensiones=('.csv', '.xlsx')):
        """Espera archivo descargado evitando temporales."""
        timeout = timeout or self.DOWNLOAD_WAIT
        inicio = time.time()
        while time.time() - inicio < timeout:
            archivos = os.listdir(self.download_folder)
            validos = [f for f in archivos if (f.endswith(extensiones)) and not f.endswith('.crdownload') and not f.endswith('.tmp')]
            if validos:
                return True
            time.sleep(1)
        print("⚠️ Tiempo agotado esperando archivo.")
        return False

    def descargar_reporte(self, config_reporte, parametros):
        """
        Descarga cualquier reporte definido en data/config_reportes.py.
        - Llena solo los campos presentes en 'campos'.
        - Usa click JS para evitar overlays.
        """
        try:
            self.driver.get(config_reporte['url'])

            # 1) Llenar filtros definidos en la config
            campos_config = config_reporte.get('campos', {})
            for clave_config, info_campo in campos_config.items():
                valor = parametros.get(clave_config, "")
                self._llenar_campo(info_campo, valor)

            # 2) Generar
            btn_generar = self.wait.until(EC.presence_of_element_located((By.XPATH, config_reporte['btn_generar'])))
            self.driver.execute_script("arguments[0].scrollIntoView();", btn_generar)
            time.sleep(0.3)
            self.driver.execute_script("arguments[0].click();", btn_generar)

            self._esperar_barra_progreso()

            # 3) Descargar CSV
            btn_csv = self.wait.until(EC.presence_of_element_located((By.XPATH, config_reporte['btn_descargar_csv'])))
            self.driver.execute_script("arguments[0].scrollIntoView();", btn_csv)
            self.driver.execute_script("arguments[0].click();", btn_csv)

            # 4) Esperar archivo
            # Para "Por_Producto" puede ser .csv o .xlsx según el sitio; aceptamos ambas.
            self._esperar_descarga_archivo(extensiones=('.csv', '.xlsx'))
            return True
        except Exception as e:
            print(f"❌ Error en proceso: {e}")
            return False

    def cerrar(self):
        try:
            self.driver.quit()
        except Exception as e:
            print(f"⚠️ Error cerrando navegador: {e}")

    def limpiar_carpeta_descargas(self):
        """Borra archivos descargados evitando scripts."""
        print("🧹 Limpiando carpeta de descargas...")
        archivos = glob.glob(os.path.join(self.download_folder, "*.*"))
        for archivo in archivos:
            try:
                if not archivo.endswith(".py"):
                    os.remove(archivo)
            except Exception as e:
                print(f"   ! No se pudo borrar {archivo}: {e}")
        print("✨ Carpeta limpia.")

    def renombrar_ultimo_archivo(self, nuevo_nombre_final):
        """
        Renombra el archivo descargado más reciente usando exactamente el nombre proporcionado.
        Si ya existe un archivo con ese nombre, agrega un número secuencial (1), (2), etc.
        """
        try:
            # Esperar hasta tener un archivo completo (no .crdownload/.tmp)
            tiempo_espera = 0
            archivo_reciente = None
            while tiempo_espera < 15:
                lista_archivos = glob.glob(os.path.join(self.download_folder, "*"))
                if not lista_archivos:
                    time.sleep(1); tiempo_espera += 1; continue
                archivo_reciente = max(lista_archivos, key=os.path.getctime)
                if archivo_reciente.endswith(('.crdownload', '.tmp')):
                    time.sleep(1); tiempo_espera += 1
                else:
                    break

            if not archivo_reciente:
                print("⚠️ No se encontró archivo para renombrar.")
                return None

            # Usar exactamente el nombre recibido desde la interfaz (debe incluir extensión .csv/.xlsx)
            destino = os.path.join(self.download_folder, nuevo_nombre_final)

            # Si existe, agregar número secuencial
            if os.path.exists(destino):
                # Separar nombre base y extensión
                nombre_base, extension = os.path.splitext(nuevo_nombre_final)
                contador = 1
                
                # Buscar un nombre disponible
                while os.path.exists(destino):
                    nuevo_nombre_con_numero = f"{nombre_base} ({contador}){extension}"
                    destino = os.path.join(self.download_folder, nuevo_nombre_con_numero)
                    contador += 1
                
                nombre_final_usado = os.path.basename(destino)
                print(f"⚠️ Archivo ya existe. Renombrando a: {nombre_final_usado}")
            else:
                nombre_final_usado = nuevo_nombre_final

            time.sleep(0.5)  # evitar locks en Windows
            os.rename(archivo_reciente, destino)
            print(f"🏷️ Guardado como: {nombre_final_usado}")
            return nombre_final_usado

        except Exception as e:
            print(f"⚠️ Error al renombrar: {e}")
            return None
        