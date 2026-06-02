import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import os
import re

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
        return ['boe.es']

class GobSpider(CrawlSpider):
    name = 'gob_spider'
    allowed_domains = cargar_dominios_permitidos()
    
    start_urls = [
        'https://administracion.gob.es/pag_Home/atencionCiudadana/SedesElectronicas-y-Webs-Publicas.html',
        'https://www.boe.es'
    ]

    # Diccionario de idiomas para denegar en las reglas principales
    idiomas_cooficiales = (r'/ca/', r'/eu/', r'/gl/', r'/va/', r'/es-ca/', r'/es-eu/', r'/es-gl/')
    basura_web = (r'/contacto', r'/aviso-legal', r'/accesibilidad', r'/mapa-web')

    rules = (
        # REGLA 1: VIP (+10 Puntos) -> Trámites y Leyes en Español
        Rule(
            LinkExtractor(
                allow=(r'/tramites/', r'/leyes/', r'/sede/', r'/disposiciones/'), 
                deny=idiomas_cooficiales + basura_web
            ), 
            callback='parse_documento',
            follow=True,
            process_request='prioridad_alta'
        ),
        
        # REGLA 2: NORMAL (0 Puntos) -> Resto de la web en Español
        Rule(
            LinkExtractor(
                deny=idiomas_cooficiales + basura_web
            ),
            callback='parse_documento',
            follow=True,
            process_request='prioridad_normal'
        ),

        # REGLA 3: ÚLTIMO MONO (-10 Puntos) -> Idiomas cooficiales
        Rule(
            LinkExtractor(
                allow=idiomas_cooficiales
            ),
            callback='parse_documento',
            follow=True,
            process_request='prioridad_baja'
        ),
    )

    # --- Funciones de asignación de prioridad ---
    def prioridad_alta(self, request, response):
        request.priority = 10
        return request

    def prioridad_normal(self, request, response):
        request.priority = 0
        return request

    def prioridad_baja(self, request, response):
        request.priority = -10
        return request

    # --- Procesamiento del texto ---
    def parse_documento(self, response):
        textos_brutos = response.css('p::text, div.texto::text, article::text, span::text').getall()
        texto_unido = ' '.join(textos_brutos)
        
        texto_limpio = limpiar_texto(texto_unido)
        titulo_limpio = limpiar_texto(response.css('title::text').get(default='Sin título'))
        
        if len(texto_limpio) > 200:
            yield {
                'url': response.url,
                'titulo': titulo_limpio,
                'dominio': response.url.split('/')[2],
                'contenido': texto_limpio,
                'longitud_caracteres': len(texto_limpio) 
            }
