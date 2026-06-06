import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.linkextractors import IGNORED_EXTENSIONS # <--- NUEVO
import os
import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

# Quitamos 'pdf' de la lista negra por defecto de Scrapy
EXTENSIONES_PERMITIDAS = [ext for ext in IGNORED_EXTENSIONS if ext != 'pdf']

def limpiar_texto(texto_bruto):
    if not texto_bruto: return ""
    return re.sub(r'\s+', ' ', texto_bruto).strip()

def cargar_dominios_permitidos():
    ruta_archivo = os.path.join(os.path.dirname(__file__), 'dominios.txt')
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            return [linea.strip() for linea in f if linea.strip()]
    except FileNotFoundError:
        return ['boe.es', 'administracion.gob.es', 'poderjudicial.es']

def amputar_parametros_basura(url):
    parsed = urlparse(url)
    
    # 1. ESCUDO ESTRICTO PARA EL BOE: Solo permitimos el documento principal (ID)
    if 'boe.es' in parsed.netloc and 'act.php' in parsed.path:
        params = parse_qs(parsed.query)
        if 'id' in params:
            new_query = urlencode({'id': params['id'][0]})
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', new_query, ''))
            
    # 2. ESCUDO GENÉRICO PARA EL RESTO DE WEBS OFICIALES
    # Lista negra de parámetros que no aportan contenido legal, solo desvían a la araña
    parametros_basura = [
        'idprovincia', 'sessionid', 'phpsessid', 'sid', 
        'lang', 'idioma', 'id_idioma', 
        'utm_source', 'utm_medium', 'utm_campaign', 
        'page', 'pag', 'tn', 'bj', 'pestania'
    ]
    
    if parsed.query:
        # Extraemos todos los parámetros de la URL
        params = parse_qs(parsed.query)
        
        # Filtramos y nos quedamos SOLO con los que NO están en la lista negra
        params_limpios = {k: v for k, v in params.items() if k.lower() not in parametros_basura}
        
        # Reconstruimos la URL con los parámetros limpios (doseq=True mantiene bien las listas)
        new_query = urlencode(params_limpios, doseq=True) 
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
        
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
                allow=(r'/tramites/', r'/leyes/', r'/sede/', r'/disposiciones/', r'\.pdf$'), # <--- AÑADIDO .pdf
                deny=idiomas_cooficiales + basura_web,
                deny_extensions=EXTENSIONES_PERMITIDAS, # <--- USAMOS NUESTRA LISTA
                process_value=amputar_parametros_basura
            ), 
            callback='parse_documento',
            follow=True,
            process_request='asignar_prioridad_alta'
        ),
        Rule(
            LinkExtractor(
                deny=idiomas_cooficiales + basura_web,
                deny_extensions=EXTENSIONES_PERMITIDAS, # <--- USAMOS NUESTRA LISTA
                process_value=amputar_parametros_basura
            ),
            callback='parse_documento',
            follow=True,
            process_request='asignar_prioridad_normal'
        )
    )

    def calcular_bonus_url(self, url):
        if 'boe.es/buscar/act.php' in url: return 50
        if re.search(r'202[0-9]', url): return 20  
        return 0

    def asignar_prioridad_alta(self, request, response):
        request.priority = 10 + self.calcular_bonus_url(request.url)
        return request

    def asignar_prioridad_normal(self, request, response):
        request.priority = 0 + self.calcular_bonus_url(request.url)
        return request

    def parse_documento(self, response):
        # 🚨 DESVÍO RÁPIDO: SI ES UN PDF, AL BUZÓN Y SALIMOS 🚨
        es_pdf = response.url.lower().endswith('.pdf') or b'application/pdf' in response.headers.get('Content-Type', b'')
        if es_pdf:
            dominio = response.url.split('/')[2]
            # Solo guardamos PDFs del Poder Judicial (puedes añadir más si quieres)
            if 'poderjudicial.es' in dominio:
                yield {
                    'tipo_item': 'pdf_pendiente',
                    'url': response.url,
                    'dominio': dominio
                }
            return

        # --- A PARTIR DE AQUÍ, SOLO LLEGA HTML ---
        url_canonica = response.css('link[rel="canonical"]::attr(href)').get() or response.url 
        textos_brutos = response.css('p::text, div.texto::text, article::text, main::text').getall()
        texto_unido = ' '.join(textos_brutos)
        titulo_limpio = limpiar_texto(response.css('title::text').get(default='Sin título'))
        
        texto_limpio = limpiar_texto(texto_unido)
        titulo_minusculas = titulo_limpio.lower()
        texto_minusculas = texto_limpio.lower()

        errores = ['404', 'no encontrada', 'no existe', 'error', 'page not found']
        if any(e in titulo_minusculas for e in errores): return
        if "utilizamos cookies" in texto_minusculas and len(texto_limpio) < 800: return

        if len(texto_limpio) > 500:
            yield {
                'url': response.url,
                'url_canonica': url_canonica,
                'titulo': titulo_limpio,
                'dominio': response.url.split('/')[2],
                'contenido': texto_limpio, 
                'html_crudo': response.text, 
                'longitud_caracteres': len(texto_limpio) 
            }
