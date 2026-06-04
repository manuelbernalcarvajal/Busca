# settings.py (DEL MINERO DE PDFs)

# 1. Tu etiqueta de identificación (User-Agent)
USER_AGENT = 'BuscadorLegalBot-PDF/2.0 (+minero_pdf@apdespanol.es.eu.org)'

# 2. Respetar las reglas de la casa
ROBOTSTXT_OBEY = True

# 3. Paciencia EXTREMA (Rate Limiting para no enfadar al Poder Judicial)
# Espera 15 segundos entre cada PDF. Son archivos grandes, no hay prisa.
DOWNLOAD_DELAY = 15.0 

# Para que el contenedor no explote por falta de RAM, descargamos de 1 en 1
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1

# 4. Modo Auto-Piloto Ético (AutoThrottle)
# Si el servidor va lento, la araña frenará aún más.
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 15.0
AUTOTHROTTLE_MAX_DELAY = 120.0 # Puede llegar a esperar 2 minutos si el CENDOJ va mal

# Activar el túnel de troceado y envío a Meilisearch específico para PDFs
ITEM_PIPELINES = {
    'pdf_pipeline.PdfPipeline': 300,
}

# Evitar que la araña intente descargar PDFs corruptos o absurdamente gigantes
# Lo subimos a 100MB (104857600 bytes) porque los sumarios judiciales pueden ser enormes
DOWNLOAD_MAXSIZE = 104857600

# Desactivamos reintentos infinitos si un PDF da error 500
RETRY_ENABLED = True
RETRY_TIMES = 2
