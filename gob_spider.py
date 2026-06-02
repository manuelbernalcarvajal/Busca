import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import os

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

    # Configuración exclusiva para hacer pruebas seguras
    custom_settings = {
        'CLOSESPIDER_PAGECOUNT': 10, # Se detendrá tras 10 páginas para que no sature tu servidor en la primera prueba
        'FEEDS': {
            'resultados.json': {
                'format': 'json',
                'encoding': 'utf8',
                'indent': 4,
            }
        }
    }

    def parse_documento(self, response):
        texto_pagina = ' '.join(response.css('p::text, div.texto::text').getall()).strip()
        
        if len(texto_pagina) > 100:
            yield {
                'url': response.url,
                'titulo': response.css('title::text').get(default='Sin título').strip(),
                'dominio': response.url.split('/')[2],
                'contenido': texto_pagina
            }
