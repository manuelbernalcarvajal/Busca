import scrapy
import sqlite3
import fitz # PyMuPDF
import re

class PdfSpider(scrapy.Spider):
    name = 'pdf_spider'
    
    # 🚨 CONFIGURACIÓN DE ÉTICA Y SEGURIDAD 🚨
    custom_settings = {
        'DOWNLOAD_DELAY': 10.0, # 10 segundos entre cada PDF (No queremos cabrear al Estado)
        'CONCURRENT_REQUESTS': 1, # Solo un PDF a la vez (Ahorro brutal de RAM)
        'DOWNLOAD_MAXSIZE': 104857600, # Límite de 100MB por PDF
        'ITEM_PIPELINES': {'pdf_pipeline.PdfPipeline': 300},
        'USER_AGENT': 'BuscadorLegalBot/2.0 (+minero_pdf@apdespanol.es.eu.org)'
    }
    
    def start_requests(self):
        # 1. Miramos el buzón (cola_pdfs.db)
        try:
            conn = sqlite3.connect('datos/cola_pdfs.db')
            cursor = conn.cursor()
            # Cogemos 50 PDFs pendientes
            cursor.execute("SELECT url, dominio FROM tareas_pdf WHERE estado = 'pendiente' LIMIT 50")
            pendientes = cursor.fetchall()
            
            if not pendientes:
                self.logger.info("💤 No hay PDFs pendientes en la base de datos.")
                return

            self.logger.info(f"📥 Encontrados {len(pendientes)} PDFs para minar.")

            # 2. Hacemos las peticiones
            for url, dominio in pendientes:
                # Marcamos como 'en_proceso' para que si se corta, no se quede en bucle infinito
                cursor.execute("UPDATE tareas_pdf SET estado = 'en_proceso' WHERE url = ?", (url,))
                conn.commit()
                
                # Le pasamos el dominio a la Request para usarlo luego
                yield scrapy.Request(url, callback=self.parse_pdf, cb_kwargs={'dominio': dominio})
                
        except sqlite3.Error as e:
            self.logger.error(f"❌ Error leyendo SQLite: {e}")
        finally:
            conn.close()

    def parse_pdf(self, response, dominio):
        url = response.url
        
        try:
            # 3. Trabajo pesado: Extraer texto con PyMuPDF
            doc = fitz.open(stream=response.body, filetype="pdf")
            paginas_texto = []
            
            for pagina in doc:
                # sort=True: La magia que arregla las leyes a 2 columnas
                texto_pagina = pagina.get_text("text", sort=True) 
                if texto_pagina:
                    paginas_texto.append(texto_pagina)
                    
            texto_completo = "\n\n".join(paginas_texto)
            texto_completo = re.sub(r'\s+', ' ', texto_completo).strip()
            
            # Limpiamos el título a partir de la URL
            titulo = url.split('/')[-1]
            if not titulo.endswith('.pdf'):
                titulo += ".pdf"
            
            # 4. Mandamos al Pipeline
            if len(texto_completo) > 500:
                yield {
                    'url': url,
                    'dominio': dominio,
                    'titulo': titulo,
                    'contenido': texto_completo
                }
                nuevo_estado = 'completado'
            else:
                self.logger.warning(f"⚠️ PDF demasiado corto o vacío: {url}")
                nuevo_estado = 'error_vacio'

        except Exception as e:
            self.logger.error(f"❌ Error catastrófico procesando PDF ({url}): {e}")
            nuevo_estado = 'error_lectura'

        # 5. Actualizamos el estado final en SQLite
        try:
            conn = sqlite3.connect('datos/cola_pdfs.db')
            conn.execute("UPDATE tareas_pdf SET estado = ? WHERE url = ?", (nuevo_estado, url))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"❌ Error actualizando estado en SQLite: {e}")
