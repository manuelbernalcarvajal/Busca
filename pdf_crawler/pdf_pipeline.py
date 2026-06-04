import requests
import os
import hashlib
from datetime import datetime

class PdfPipeline:
    
    def __init__(self):
        self.meilisearch_url = os.getenv('MEILISEARCH_URL', 'http://meilisearch:7700')
        self.meilisearch_key = os.getenv('MEILISEARCH_KEY', 'SuperSecreta123')
        self.indice = 'documentos_legales'
        self.configurado = False

    def configurar_indice(self, spider):
        headers = {'Authorization': f'Bearer {self.meilisearch_key}'}
        config = {
            "filterableAttributes": ["categoria", "dominio", "origen_id", "estado_ia"],
            "sortableAttributes": ["fecha_indexacion"]
        }
        requests.patch(
            f"{self.meilisearch_url}/indexes/{self.indice}/settings", 
            headers=headers, json=config
        )
        self.configurado = True
        spider.logger.info("⚙️ Índice configurado para PDFs.")

    def process_item(self, item, spider):
        if not self.configurado:
            self.configurar_indice(spider)
            
        # 1. EL ESCUDO ANTI-MONOPOLIO (Hash Padre)
        identidad_base = f"{item['dominio']}_{item['titulo']}"
        origen_id = hashlib.md5(identidad_base.encode('utf-8')).hexdigest()
        
        # 2. Troceado con Ventana Deslizante (Ideal para PDFs planos)
        textos_troceados = self.trocear_texto_inteligente(item['contenido'])
        
        documentos_a_enviar = []
        fecha_indexacion = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        
        for indice, texto_chunk in enumerate(textos_troceados):
            if not texto_chunk.strip(): continue
            
            # 3. Hash del fragmento
            firma_chunk = f"{identidad_base}_chunk_{indice}"
            chunk_id = hashlib.md5(firma_chunk.encode('utf-8')).hexdigest()
            
            doc_chunk = {
                'id': chunk_id,
                'origen_id': origen_id, 
                'url': item['url'],
                'dominio': item['dominio'],
                'categoria': 'Poder Judicial',
                'titulo': item['titulo'], 
                'contenido': texto_chunk,
                'orden_lectura': indice + 1, 
                'fecha_indexacion': fecha_indexacion,
                # ❌ ELIMINADA LA LÍNEA DE _vectors: {"default": None} ❌
                'estado_ia': 'pendiente' 
            }
            documentos_a_enviar.append(doc_chunk)

        if documentos_a_enviar:
            url_api = f"{self.meilisearch_url}/indexes/{self.indice}/documents"
            try:
                headers = {'Authorization': f'Bearer {self.meilisearch_key}', 'Content-Type': 'application/json'}
                respuesta = requests.post(url_api, headers=headers, json=documentos_a_enviar, timeout=15)
                
                # 👇 EL CHIVATO DE ERRORES RECUPERADO 👇
                if respuesta.status_code not in [200, 202]:
                    spider.logger.error(f"❌ Meilisearch rechazó el PDF: {respuesta.text}")
                else:
                    spider.logger.info(f"✅ Enviados {len(documentos_a_enviar)} chunks del PDF: {item['titulo'][:30]}")
                    
            except Exception as e:
                spider.logger.error(f"🔌 Error de conexión con Meilisearch: {e}")
                
        return item

    def trocear_texto_inteligente(self, texto, max_chars=1200, overlap=250):
        if not texto: return []
        palabras = texto.split()
        chunks = []
        chunk_actual = []
        longitud_actual = 0
        
        i = 0
        while i < len(palabras):
            palabra = palabras[i]
            chunk_actual.append(palabra)
            longitud_actual += len(palabra) + 1 
            
            if longitud_actual >= max_chars or i == len(palabras) - 1:
                chunks.append(" ".join(chunk_actual))
                while chunk_actual and longitud_actual > overlap:
                    palabra_eliminada = chunk_actual.pop(0)
                    longitud_actual -= (len(palabra_eliminada) + 1)
            i += 1
            
        return chunks
