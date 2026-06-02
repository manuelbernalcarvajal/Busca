import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import os
import re

def limpiar_texto(texto_bruto):
    if not texto_bruto:
        return ""
    # 1. Reemplazamos cualquier combinación de saltos de línea (\n), 
    # tabulaciones (\t) o múltiples espacios por UN SOLO espacio.
    texto_limpio = re.sub(r'\s+', ' ', texto_bruto)
    
    # 2. Quitamos espacios al principio y al final
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
        # 1. Extraemos todo el texto posible de párrafos, divs de texto, artículos, etc.
        textos_brutos = response.css('p::text, div.texto::text, article::text, span::text').getall()
        
        # 2. Lo unimos todo
        texto_unido = ' '.join(textos_brutos)
        
        # 3. ¡Lo pasamos por la lavadora!
        texto_limpio = limpiar_texto(texto_unido)
        titulo_limpio = limpiar_texto(response.css('title::text').get(default='Sin título'))
        
        # Subimos el límite a 200 caracteres para asegurarnos de que no 
        # guardamos páginas vacías o que solo dicen "Aceptar cookies"
        if len(texto_limpio) > 200:
            yield {
                'url': response.url,
                'titulo': titulo_limpio,
                'dominio': response.url.split('/')[2],
                'contenido': texto_limpio,
                # Podemos añadir un campo extra para saber la longitud y auditar luego
                'longitud_caracteres': len(texto_limpio) 
            }
