import requests
import re
import os
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup 
import sqlite3 # <--- NUEVO

class ProcesadorGobiernoPipeline:
    
    def __init__(self):
        self.meilisearch_url = os.getenv('MEILISEARCH_URL', 'http://meilisearch:7700')
        self.meilisearch_key = os.getenv('MEILISEARCH_KEY', 'SuperSecreta123')
        self.indice = 'documentos_legales'
        self.configurado = False
        
        # 👇 CREAMOS EL BUZÓN COMPARTIDO CON EL MINERO 👇
        os.makedirs('datos', exist_ok=True)
        self.conn_cola = sqlite3.connect('datos/cola_pdfs.db')
        self.cursor_cola = self.conn_cola.cursor()
        self.cursor_cola.execute('''
            CREATE TABLE IF NOT EXISTS tareas_pdf (
                url TEXT PRIMARY KEY,
                dominio TEXT,
                estado TEXT DEFAULT 'pendiente',
                fecha_agregado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn_cola.commit()

    def process_item(self, item, spider):
        # 🚨 FILTRO PARA PDFs: Lo guardamos en SQLite y abortamos el envío a Meilisearch
        if item.get('tipo_item') == 'pdf_pendiente':
            try:
                self.cursor_cola.execute(
                    'INSERT OR IGNORE INTO tareas_pdf (url, dominio, estado) VALUES (?, ?, ?)',
                    (item['url'], item['dominio'], 'pendiente')
                )
                self.conn_cola.commit()
                spider.logger.info(f"📝 PDF anotado en la cola: {item['url']}")
            except Exception as e:
                spider.logger.error(f"❌ Error en SQLite: {e}")
            return item # Terminamos aquí para los PDFs

        # --- FLUJO NORMAL PARA HTML ---
        if not self.configurado:
            self.configurar_indice(spider)

        item['categoria'] = self.clasificar(item['url'], item['titulo'], item.get('contenido', ''))
        item['fecha_indexacion'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        self.procesar_y_enviar_chunks(item, spider)
        return item

    # ... (Resto de tus funciones: configurar_indice, clasificar, trocear_por_estructura_html, procesar_y_enviar_chunks se quedan EXACTAMENTE IGUAL) ...

    def clasificar(self, url, titulo, contenido):
        texto_total = f"{url} {titulo} {contenido}".lower()
        if re.search(r'/tramites/|/sede/|cita previa|solicitud|formulario', texto_total):
            return "Tramite/Servicio"
        elif re.search(r'real decreto|ley orgánica|boletín|resolución|disposición', texto_total):
            return "Legislacion/Normativa"
        elif re.search(r'beca|ayuda|subvención|bono', texto_total):
            return "Ayudas/Subvenciones"
        else:
            return "Informativo/General"

    def trocear_por_estructura_html(self, html_bruto, max_chars=1200):
        if not html_bruto:
            return []
            
        soup = BeautifulSoup(html_bruto, 'html.parser')
        chunks = []
        chunk_actual = []
        longitud_actual = 0
        
        etiquetas_validas = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'td']
        
        for elemento in soup.find_all(etiquetas_validas):
            texto = elemento.get_text(separator=" ", strip=True)
            if not texto: continue
                
            es_encabezado = elemento.name.startswith('h')
            if es_encabezado and longitud_actual > 0:
                chunks.append("\n".join(chunk_actual))
                chunk_actual = []
                longitud_actual = 0
            
            chunk_actual.append(texto)
            longitud_actual += len(texto)
            
            if longitud_actual >= max_chars:
                chunks.append("\n".join(chunk_actual))
                chunk_actual = []
                longitud_actual = 0
                
        if chunk_actual:
            chunks.append("\n".join(chunk_actual))
            
        return chunks

    def procesar_y_enviar_chunks(self, item, spider):
        headers = {
            'Authorization': f'Bearer {self.meilisearch_key}',
            'Content-Type': 'application/json'
        }
        
        # 1. EL ESCUDO ANTI-MONOPOLIO (Hash Padre basado en Identidad)
        identidad_base = item.get('url_canonica') or f"{item['dominio']}_{item['titulo']}"
        origen_id = hashlib.md5(identidad_base.encode('utf-8')).hexdigest()
        
        # 2. Troceado exclusivo de HTML
        textos_troceados = self.trocear_por_estructura_html(item.get('html_crudo', ''))
        
        documentos_a_enviar = []
        
        for indice, texto_chunk in enumerate(textos_troceados):
            if not texto_chunk.strip(): continue
            
            # 3. HASH DEL FRAGMENTO (Identidad + Indice)
            firma_chunk = f"{identidad_base}_chunk_{indice}"
            chunk_id = hashlib.md5(firma_chunk.encode('utf-8')).hexdigest()
            
            doc_chunk = {
                'id': chunk_id,
                'origen_id': origen_id, # <--- Para agrupar en el Frontend
                'url': item.get('url_canonica', item['url']),
                'dominio': item['dominio'],
                'categoria': item['categoria'],
                'titulo': item['titulo'], 
                'contenido': texto_chunk,
                'orden_lectura': indice + 1, 
                'fecha_indexacion': item['fecha_indexacion'],
                # ❌ ELIMINADA LA LÍNEA DE _vectors: {"default": None} ❌
                'estado_ia': 'pendiente' 
            }
            documentos_a_enviar.append(doc_chunk)

        if documentos_a_enviar:
            url_api = f"{self.meilisearch_url}/indexes/{self.indice}/documents"
            try:
                lote_size = 100
                for i in range(0, len(documentos_a_enviar), lote_size):
                    lote = documentos_a_enviar[i:i + lote_size]
                    respuesta = requests.post(url_api, headers=headers, json=lote, timeout=10)
                    
                    # 👇 EL CHIVATO DE ERRORES RECUPERADO 👇
                    if respuesta.status_code not in [200, 202]:
                        spider.logger.error(f"❌ Meilisearch rechazó el chunk: {respuesta.text}")
                        
                spider.logger.info(f"✅ Enviados {len(documentos_a_enviar)} chunks HTML de: {item['titulo'][:30]}...")
            except Exception as e:
                spider.logger.error(f"🔌 Error de conexión con Meilisearch: {e}")
