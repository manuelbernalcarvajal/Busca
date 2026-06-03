import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.linkextractors import IGNORED_EXTENSIONS
import os
import re
import io
from pypdf import PdfReader # ¡Nuestro lector de PDFs en RAM!
from urllib.parse import urlparse, urlunparse

# 1. Le decimos a Scrapy que deje de ignorar los PDFs por defecto
EXTENSIONES_PERMITIDAS = [ext for ext in IGNORED_EXTENSIONS if ext != 'pdf']

def limpiar_texto(texto_bruto):
    if not texto_bruto:
        return ""
    texto_limpio = re.sub(r'\s+', ' ', texto_bruto)
    return texto_limpio.strip()

def cargar_dominios_permitidos():
    ruta_archivo = os.path.join(os.path.dirname(__file__), 'dominios.txt')
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            return [linea.strip() for linea in f if linea.strip()]
    except FileNotFoundError:
        return ['boe.es', 'poderjudicial.es']

def amputar_parametros_basura(url):
    """
    Destruye parámetros inútiles de las URLs antes de que Scrapy las visite.
    """
    parsed = urlparse(url)
    
    # Si la URL es del Poder Judicial o del BOE y tiene el parámetro '?idProvincia='
    if 'idProvincia=' in parsed.query:
        # Reconstruimos la URL EXACTA pero dejando la 'query' (los parámetros) en blanco
        url_limpia = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, '', parsed.fragment))
        return url_limpia
        
    # Aquí puedes añadir más basura conocida en el futuro
    # if 'source=twitter' in parsed.query: ...
    
    return url

class GobSpider(CrawlSpider):
    name = 'gob_spider'
    allowed_domains = cargar_dominios_permitidos()
    
    # 1. Ponemos PRIMERO tus páginas VIP (El BOE, los directorios...)
    start_urls = [
        'https://administracion.gob.es/pag_Home/atencionCiudadana/SedesElectronicas-y-Webs-Publicas.html',
        'https://www.boe.es',
        'https://www.poderjudicial.es',
        'https://www.tribunalconstitucional.es/es/Paginas/default.aspx'
    ] + [f"https://{dominio}" for dominio in allowed_domains]

    idiomas_cooficiales = (r'/ca/', r'/eu/', r'/gl/', r'/va/', r'/es-ca/', r'/es-eu/', r'/es-gl/')
    basura_web = (r'/contacto', r'/aviso-legal', r'/accesibilidad', r'/mapa-web')

    rules = (
        # Añadimos deny_extensions para que SÍ siga los enlaces .pdf
        Rule(
            LinkExtractor(
                allow=(r'/tramites/', r'/leyes/', r'/sede/', r'/disposiciones/', r'\.pdf$'), 
                deny=idiomas_cooficiales + basura_web,
                deny_extensions=EXTENSIONES_PERMITIDAS,
                process_value=amputar_parametros_basura  # <--- EL FRANCOTIRADOR 🔫
            ), 
            callback='parse_documento',
            follow=True,
            process_request='asignar_prioridad_alta'
        ),
        
        Rule(
            LinkExtractor(
                deny=idiomas_cooficiales + basura_web,
                deny_extensions=EXTENSIONES_PERMITIDAS,
                process_value=amputar_parametros_basura  # <--- EL FRANCOTIRADOR 🔫
            ),
            callback='parse_documento',
            follow=True,
            process_request='asignar_prioridad_normal'
        ),

        Rule(
            LinkExtractor(
                allow=idiomas_cooficiales,
                deny_extensions=EXTENSIONES_PERMITIDAS
                process_value=amputar_parametros_basura  # <--- EL FRANCOTIRADOR 🔫
            ),
            callback='parse_documento',
            follow=True,
            process_request='asignar_prioridad_baja'
        ),
    )

    # --- MOTOR DE PRIORIDADES (El clasificador de años) ---
    def calcular_bonus_ano(self, url):
        # Busca años en la URL
        if re.search(r'202[0-9]', url):
            return 20  # +20 para cosas de esta década (2020-2029)
        elif re.search(r'201[0-9]', url):
            return 5   # +5 para la década pasada (2010-2019)
        elif re.search(r'19[0-9]{2}', url):
            return -20 # -20 para cosas del milenio pasado (1900-1999)
        return 0

    def asignar_prioridad_alta(self, request, response):
        request.priority = 10 + self.calcular_bonus_ano(request.url)
        return request

    def asignar_prioridad_normal(self, request, response):
        request.priority = 0 + self.calcular_bonus_ano(request.url)
        return request

    def asignar_prioridad_baja(self, request, response):
        # Los idiomas cooficiales siempre castigados, sean del año que sean
        request.priority = -10 
        return request

   # --- LECTOR HÍBRIDO (HTML y PDF) ---
    def parse_documento(self, response):
        # 1. Comprobamos si es un PDF (por extensión o por cabecera del servidor)
        es_pdf = response.url.lower().endswith('.pdf') or b'application/pdf' in response.headers.get('Content-Type', b'')

        if es_pdf:
            try:
                # Leemos el PDF directamente desde la RAM
                lector = PdfReader(io.BytesIO(response.body))
                texto_unido = " ".join([page.extract_text() for page in lector.pages if page.extract_text()])
                titulo_limpio = response.url.split('/')[-1] 
            except Exception as e:
                self.logger.error(f"❌ Error leyendo PDF en RAM ({response.url}): {e}")
                return
        else:
            # 2. Si es una web normal (HTML)
            # Quitamos los 'span::text' porque suelen arrastrar menús y basura
            textos_brutos = response.css('p::text, div.texto::text, article::text, main::text').getall()
            texto_unido = ' '.join(textos_brutos)
            titulo_limpio = limpiar_texto(response.css('title::text').get(default='Sin título'))
        
        texto_limpio = limpiar_texto(texto_unido)
        
        # =========================================================
        # 🧠 EL SENTIDO COMÚN (Filtros Anti-Basura)
        # =========================================================
        titulo_minusculas = titulo_limpio.lower()
        texto_minusculas = texto_limpio.lower()

        # A) Filtro Anti-Soft 404 (Páginas de error disfrazadas)
        errores = ['404', 'no encontrada', 'no existe', 'error', 'page not found']
        if any(e in titulo_minusculas for e in errores):
            self.logger.info(f"🗑️ Basura descartada (Error 404 oculto): {response.url}")
            return

        # B) Filtro Anti-Monstruo de las Galletas
        # Si menciona cookies y el texto total es corto, es que solo capturó el banner
        if "utilizamos cookies" in texto_minusculas and len(texto_limpio) < 800:
            self.logger.info(f"🍪 Basura descartada (Solo capturó banner de Cookies): {response.url}")
            return

        # C) Nivel de exigencia general
        # Un documento legal de verdad tiene mucha letra. Subimos el límite a 500 caracteres.
        if len(texto_limpio) > 500:
            yield {
                'url': response.url,
                'titulo': titulo_limpio,
                'dominio': response.url.split('/')[2],
                'contenido': texto_limpio,
                'longitud_caracteres': len(texto_limpio) 
            }
        else:
            self.logger.info(f"🤏 Descartado por corto ({len(texto_limpio)} chars): {response.url}")
