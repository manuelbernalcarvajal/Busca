import requests
import re
import os

class ProcesadorGobiernoPipeline:
    
    def __init__(self):
        # Configuraremos estas variables de entorno luego en el docker-compose
        self.meilisearch_url = os.getenv('MEILISEARCH_URL', 'http://meilisearch:7700')
        self.meilisearch_key = os.getenv('MEILISEARCH_KEY', 'masterKeySecreta123')
        self.indice = 'documentos_legales'

    def process_item(self, item, spider):
        # --- FASE 1: PRECLASIFICACIÓN (Tu motor ligero) ---
        item['categoria'] = self.clasificar(item['url'], item['titulo'], item['contenido'])

        # --- FASE 2: ENVIAR A MEILISEARCH (La API) ---
        self.enviar_a_meilisearch(item, spider)
        
        return item

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
        
        url_api = f"{self.meilisearch_url}/indexes/{self.indice}/documents"
        
        try:
            # Hacemos la llamada POST a la API de Meilisearch
            respuesta = requests.post(url_api, headers=headers, json=[item], timeout=5)
            if respuesta.status_code not in [200, 202]:
                spider.logger.error(f"❌ Error al enviar a Meilisearch: {respuesta.text}")
        except Exception as e:
            spider.logger.error(f"🔌 Error de conexión con Meilisearch: {e}")
