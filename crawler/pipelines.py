import requests
import re
import os
from datetime import datetime

class ProcesadorGobiernoPipeline:
    
    def __init__(self):
        self.meilisearch_url = os.getenv('MEILISEARCH_URL', 'http://meilisearch:7700')
        self.meilisearch_key = os.getenv('MEILISEARCH_KEY', 'SuperSecreta123')
        self.indice = 'documentos_legales'
        self.configurado = False

    def configurar_indice(self, spider):
        # Le decimos a Meilisearch qué campos sirven para Filtrar y Ordenar
        headers = {'Authorization': f'Bearer {self.meilisearch_key}'}
        config = {
            "filterableAttributes": ["categoria", "dominio"],
            "sortableAttributes": ["fecha_web", "fecha_indexacion"]
        }
        requests.patch(
            f"{self.meilisearch_url}/indexes/{self.indice}/settings", 
            headers=headers, json=config
        )
        self.configurado = True
        spider.logger.info("⚙️ Índice de Meilisearch configurado con filtros y fechas.")

    def process_item(self, item, spider):
        if not self.configurado:
            self.configurar_indice(spider)

        item['categoria'] = self.clasificar(item['url'], item['titulo'], item['contenido'])
        
        # Generamos la fecha exacta de "ahora mismo" en formato ISO (UTC)
        item['fecha_indexacion'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        self.enviar_a_meilisearch(item, spider)
        return item

    # ... (El resto de métodos clasificar y enviar_a_meilisearch se quedan igual) ...
    def clasificar(self, url, titulo, contenido):
        texto_total = f"{url} {titulo} {contenido}".lower()
        
        # Reglas lógicas del motor
        if re.search(r'/tramites/|/sede/|cita previa|solicitud|formulario', texto_total):
            return "Tramite/Servicio"
        elif re.search(r'real decreto|ley orgánica|boletín|resolución|disposición', texto_total):
            return "Legislacion/Normativa"
        elif re.search(r'beca|ayuda|subvención|bono', texto_total):
            return "Ayudas/Subvenciones"
        elif re.search(r'sentencia|tribunal|juzgado|jurisprudencia', texto_total):
            return "Poder Judicial"
        else:
            return "Informativo/General"

    def enviar_a_meilisearch(self, item, spider):
        headers = {
            'Authorization': f'Bearer {self.meilisearch_key}',
            'Content-Type': 'application/json'
        }
        
        # Meilisearch necesita que cada documento tenga un ID único. 
        # Usamos la URL limpiándola para que sirva de ID.
        doc_id = re.sub(r'[^a-zA-Z0-9]', '', item['url'])
        item['id'] = doc_id
        
        # 👇 LA MAGIA PARA CALLAR A MEILISEARCH 👇
        item['_vectors'] = {"default": None}
        item['estado_ia'] = 'pendiente'  # <--- NUESTRO TICKET DE TURNO
        
        url_api = f"{self.meilisearch_url}/indexes/{self.indice}/documents"
        
        try:
            # Hacemos la llamada POST a la API de Meilisearch
            respuesta = requests.post(url_api, headers=headers, json=[item], timeout=5)
            if respuesta.status_code not in [200, 202]:
                spider.logger.error(f"❌ Error al enviar a Meilisearch: {respuesta.text}")
        except Exception as e:
            spider.logger.error(f"🔌 Error de conexión con Meilisearch: {e}")
