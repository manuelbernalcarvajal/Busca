import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import os
import re
from urllib.parse import urlparse, urlunparse

def limpiar_texto(texto_bruto):
    if not texto_bruto:
        return ""
    return re.sub(r'\s+', ' ', texto_bruto).strip()

def cargar_dominios_permitidos():
    ruta_archivo = os.path.join(os.path.dirname(__file__), 'dominios.txt')
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            return [linea.strip() for linea in f if linea.strip()]
    except FileNotFoundError:
        return ['boe.es', 'administracion.gob.es']

def amputar_parametros_basura(url):
    parsed = urlparse(url)
    # Limpiamos basura conocida
    if 'idProvincia=' in parsed.query:
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, '', parsed.fragment))
    return url

class GobSpider(CrawlSpider):
    name = 'gob_spider'
    allowed_domains = cargar_dominios_permitidos()
    
    start_urls = [
        'https://administracion.gob.es/pag_Home/atencionCiudadana/SedesElectronicas-y-Webs-Publicas.html',
        'https://www.boe.es'
    ] + [f"https://{dominio}" for dominio in allowed_domains]

    idiomas_cooficiales = (r'/ca/', r'/eu/', r'/gl/', r'/va/', r'/es-ca/', r'/es-eu/', r'/es-gl/')
    basura_web = (r'/contacto', r'/aviso-legal', r'/accesibilidad', r'/mapa-web')

    rules = (
        Rule(
            LinkExtractor(
                allow=(r'/tramites/', r'/leyes/', r'/sede/', r'/disposiciones/'), 
                deny=idiomas_cooficiales + basura_web,
                # Scrapy ya ignora PDFs por defecto, pero lo aseguramos
                deny_extensions=['pdf', 'doc', 'docx', 'xls', 'zip', 'rar'],
                process_value=amputar_parametros_basura
            ), 
            callback='parse_documento',
            follow=True,
            process_request='asignar_prioridad_alta'
        ),
        Rule(
            LinkExtractor(
                deny=idiomas_cooficiales + basura_web,
                deny_extensions=['pdf', 'doc', 'docx', 'xls', 'zip', 'rar'],
                process_value=amputar_parametros_basura
            ),
            callback='parse_documento',
            follow=True,
            process_request='asignar_prioridad_normal'
        )
    )

    def calcular_bonus_url(self, url):
        # Prioridad máxima al BOE consolidado
        if 'boe.es/buscar/act.php' in url:
            return 50
        if re.search(r'202[0-9]', url):
            return 20  
        return 0

    def asignar_prioridad_alta(self, request, response):
        request.priority = 10 + self.calcular_bonus_url(request.url)
        return request

    def asignar_prioridad_normal(self, request, response):
        request.priority = 0 + self.calcular_bonus_url(request.url)
        return request

    def parse_documento(self, response):
        # 1. Búsqueda de la Identidad Única (URL Canónica)
        url_canonica = response.css('link[rel="canonical"]::attr(href)').get()
        if not url_canonica:
            url_canonica = response.url 

        # 2. Extracción de textos (Solo HTML)
        textos_brutos = response.css('p::text, div.texto::text, article::text, main::text').getall()
        texto_unido = ' '.join(textos_brutos)
        titulo_limpio = limpiar_texto(response.css('title::text').get(default='Sin título'))
        
        texto_limpio = limpiar_texto(texto_unido)
        titulo_minusculas = titulo_limpio.lower()
        texto_minusculas = texto_limpio.lower()

        # 3. Filtros Anti-Basura
        errores = ['404', 'no encontrada', 'no existe', 'error', 'page not found']
        if any(e in titulo_minusculas for e in errores):
            return

        if "utilizamos cookies" in texto_minusculas and len(texto_limpio) < 800:
            return

        if len(texto_limpio) > 500:
            yield {
                'url': response.url,
                'url_canonica': url_canonica,
                'titulo': titulo_limpio,
                'dominio': response.url.split('/')[2],
                'contenido': texto_limpio, 
                'html_crudo': response.text, # <--- Esencial para el pipeline
                'longitud_caracteres': len(texto_limpio) 
            }
