# settings.py

# 1. Tu etiqueta de identificación (User-Agent)
# Siempre pon un email o una web para que el admin del servidor sepa quién eres.
USER_AGENT = 'Buscadorlegalygobpages/2.0 (+buscadorlegalygobpages@apdespanol.es.eu.org)'

# 2. Respetar las reglas de la casa
ROBOTSTXT_OBEY = True

# 3. Paciencia (Rate Limiting)
# Paciencia extrema: Espera 5 segundos entre cada petición (así no saturas nada)
DOWNLOAD_DELAY = 5.0 

# Si quieres que consuma aún menos CPU, limítale los procesos en paralelo
CONCURRENT_REQUESTS = 100
CONCURRENT_REQUESTS_PER_DOMAIN = 2

# 4. Modo Auto-Piloto Ético (AutoThrottle)
# Si Scrapy detecta que el servidor del BOE va lento, él solo frena y espera más tiempo.
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 5.0
AUTOTHROTTLE_MAX_DELAY = 60.0

# Activar nuestro Middleware personalizado
DOWNLOADER_MIDDLEWARES = {
    'middlewares.MemoriaCrawlerMiddleware': 543, # El número indica la prioridad (orden de ejecución)
}

# Activar el túnel de preclasificación y envío a Meilisearch
ITEM_PIPELINES = {
    'pipelines.ProcesadorGobiernoPipeline': 300,
}
# -----------------------------------------------------------
# CEREBRO GOOGLE: Búsqueda en Amplitud (Breadth-First Search)
# -----------------------------------------------------------
DEPTH_PRIORITY = 1
SCHEDULER_DISK_QUEUE = 'scrapy.squeues.PickleFifoDiskQueue'
SCHEDULER_MEMORY_QUEUE = 'scrapy.squeues.FifoMemoryQueue'
# Evitar que la araña intente descargar PDFs gigantes (Límite 50MB)
DOWNLOAD_MAXSIZE = 52428800
