import sqlite3
import time
from scrapy.exceptions import IgnoreRequest

class MemoriaCrawlerMiddleware:
    def __init__(self):
        # Conecta (o crea) la base de datos en un archivo local llamado memoria.db
        self.conn = sqlite3.connect('memoria_crawler.db')
        self.cursor = self.conn.cursor()
        
        # Crea la tabla si es la primera vez que se ejecuta
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS historial (
                url TEXT PRIMARY KEY,
                ultimo_acceso REAL
            )
        ''')
        self.conn.commit()

    def process_request(self, request, spider):
        url = request.url
        ahora = time.time()
        
        # Buscamos si ya hemos visitado esta URL antes
        self.cursor.execute('SELECT ultimo_acceso FROM historial WHERE url = ?', (url,))
        resultado = self.cursor.fetchone()
        
        if resultado:
            ultimo_acceso = resultado[0]
            # 86400 segundos = 24 horas. Si han pasado menos, la ignoramos.
            if (ahora - ultimo_acceso) < 86400:
                spider.logger.info(f"🧠 Memoria: Saltando {url} (Leída hace menos de 24h)")
                raise IgnoreRequest("URL leída recientemente")
        
        # Si no estaba o pasaron más de 24h, actualizamos la base de datos y la dejamos pasar
        self.cursor.execute('REPLACE INTO historial (url, ultimo_acceso) VALUES (?, ?)', (url, ahora))
        self.conn.commit()
        
        return None # Devuelve None para decirle a Scrapy: "Todo en orden, continúa descargando"
