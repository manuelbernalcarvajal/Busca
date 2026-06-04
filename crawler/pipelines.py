import requests
import re
import os
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup # <--- NUESTRA NUEVA ARMA SECRETA

class ProcesadorGobiernoPipeline:
    
    def __init__(self):
        self.meilisearch_url = os.getenv('MEILISEARCH_URL', 'http://meilisearch:7700')
        self.meilisearch_key = os.getenv('MEILISEARCH_KEY', 'SuperSecreta123')
        self.indice = 'documentos_legales'
        self.configurado = False

    def configurar_indice(self, spider):
        headers = {'Authorization': f'Bearer {self.meilisearch_key}'}
        config = {
            "filterableAttributes": ["categoria", "dominio", "grupo_id", "estado_ia"],
            "sortableAttributes": ["fecha_indexacion"]
        }
        requests.patch(
            f"{self.meilisearch_url}/indexes/{self.indice}/settings", 
            headers=headers, json=config
        )
        self.configurado = True
        spider.logger.info("⚙️ Índice configurado con soporte para RAG semántico.")

    def process_item(self, item, spider):
        if not self.configurado:
            self.configurar_indice(spider)

        # Usamos el contenido de texto para la clasificación
        item['categoria'] = self.clasificar(item['url'], item['titulo'], item.get('contenido', ''))
        item['fecha_indexacion'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        self.procesar_y_enviar_chunks(item, spider)
        return item

    def clasificar(self, url, titulo, contenido):
        texto_total = f"{url} {titulo} {contenido}".lower()
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

    def trocear_por_estructura_html(self, html_bruto, max_chars=1200):
        """
        Corta el texto respetando la estructura lógica.
        - Corta siempre que se encuentra un nuevo título (h1, h2, h3...).
        - Jamás corta a mitad de un párrafo <p> o elemento de lista <li>.
        - Agrupa párrafos hasta llegar al límite de caracteres.
        """
        if not html_bruto:
            return []
            
        soup = BeautifulSoup(html_bruto, 'html.parser')
        chunks = []
        chunk_actual = []
        longitud_actual = 0
        
        # Buscamos en orden de aparición los elementos con texto útil
        etiquetas_validas = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'td']
        
        for elemento in soup.find_all(etiquetas_validas):
            texto = elemento.get_text(separator=" ", strip=True)
            if not texto:
                continue
                
            # REGLA 1: Si es un encabezado (h1-h6) y ya tenemos texto acumulado,
            # cerramos el chunk anterior de inmediato. Así cada sección de la ley empieza limpia.
            es_encabezado = elemento.name.startswith('h')
            if es_encabezado and longitud_actual > 0:
                chunks.append("\n".join(chunk_actual))
                chunk_actual = []
                longitud_actual = 0
            
            # Añadimos el texto completo del párrafo o encabezado
            chunk_actual.append(texto)
            longitud_actual += len(texto)
            
            # REGLA 2: Si el chunk ya es lo bastante grande, lo cerramos.
            # Como añadimos el elemento entero antes de comprobar esto, NUNCA se corta a mitad de <p>.
            if longitud_actual >= max_chars:
                chunks.append("\n".join(chunk_actual))
                chunk_actual = []
                longitud_actual = 0
                
        # Guardar lo que haya sobrado en el último bloque
        if chunk_actual:
            chunks.append("\n".join(chunk_actual))
            
        return chunks

    def procesar_y_enviar_chunks(self, item, spider):
        headers = {
            'Authorization': f'Bearer {self.meilisearch_key}',
            'Content-Type': 'application/json'
        }
        
        # 1. LA IDENTIDAD INQUEBRANTABLE (Anti-Duplicados)
        # Usamos la URL canónica. Si por algún motivo falló, usamos Dominio + Título.
        identidad_base = item.get('url_canonica') or f"{item['dominio']}_{item['titulo']}"
        
        # El Hash Padre (para agrupar en tu frontend)
        grupo_id = hashlib.md5(identidad_base.encode('utf-8')).hexdigest()
        
        # 2. Troceamos (Usando el HTML crudo si existe, como te pasé antes)
        html_crudo = item.get('html_crudo', item.get('contenido', ''))
        if '<' in html_crudo and '>' in html_crudo:
            textos_troceados = self.trocear_por_estructura_html(html_crudo)
        else:
            # Fallback para PDFs
            textos_troceados = [t for t in html_crudo.split('\n\n') if len(t.strip()) > 20]
        
        documentos_a_enviar = []
        
        for indice, texto_chunk in enumerate(textos_troceados):
            if not texto_chunk.strip(): continue
            
            # 3. EL HASH DEL FRAGMENTO (Identidad + Número de trozo)
            # Si el crawler lee 5 URLs distintas del Código Penal, generará 5 veces
            # el mismo hash para el artículo 1. Meilisearch simplemente lo sobrescribirá.
            firma_chunk = f"{identidad_base}_chunk_{indice}"
            chunk_id = hashlib.md5(firma_chunk.encode('utf-8')).hexdigest()
            
            doc_chunk = {
                'id': chunk_id,
                'grupo_id': grupo_id, 
                'url': item.get('url_canonica', item['url']), # Guardamos la buena
                'dominio': item['dominio'],
                'categoria': item['categoria'],
                'titulo': item['titulo'], 
                'contenido': texto_chunk,
                'orden_lectura': indice + 1, 
                'fecha_indexacion': item['fecha_indexacion'],
                '_vectors': {"default": None},
                'estado_ia': 'pendiente' 
            }
            documentos_a_enviar.append(doc_chunk)

        # ... (aquí sigue el código de enviarlo a Meilisearch con requests.post) ...

        if documentos_a_enviar:
            url_api = f"{self.meilisearch_url}/indexes/{self.indice}/documents"
            try:
                # Enviamos en lotes de 100 para no ahogar la petición HTTP si la ley es infinita
                lote_size = 100
                for i in range(0, len(documentos_a_enviar), lote_size):
                    lote = documentos_a_enviar[i:i + lote_size]
                    requests.post(url_api, headers=headers, json=lote, timeout=10)
                spider.logger.info(f"✅ Enviados {len(documentos_a_enviar)} chunks lógicos de: {item['titulo'][:30]}...")
            except Exception as e:
                spider.logger.error(f"🔌 Error de conexión con Meilisearch: {e}")
