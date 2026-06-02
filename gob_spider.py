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

    rules = (
        Rule(
            LinkExtractor(
                allow=(r'/tramites/', r'/leyes/', r'/sede/', r'/disposiciones/'), 
                deny=(r'/contacto', r'/aviso-legal', r'/accesibilidad') 
            ), 
            callback='parse_documento',
            follow=True 
        ),
        Rule(
            LinkExtractor(),
            callback='parse_documento',
            follow=True
        ),
    )

    # Fíjate cómo "def parse_documento" tiene 4 espacios delante para estar dentro de la clase
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
