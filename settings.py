# settings.py

# 1. Tu etiqueta de identificación (User-Agent)
# Siempre pon un email o una web para que el admin del servidor sepa quién eres.
USER_AGENT = 'BuscadorLegalBot/1.0 (+contacto@tudominio.com)'

# 2. Respetar las reglas de la casa
ROBOTSTXT_OBEY = True

# 3. Paciencia (Rate Limiting)
# Paciencia extrema: Espera 5 segundos entre cada petición (así no saturas nada)
DOWNLOAD_DELAY = 5.0 

# Si quieres que consuma aún menos CPU, limítale los procesos en paralelo
CONCURRENT_REQUESTS = 10

# 4. Modo Auto-Piloto Ético (AutoThrottle)
# Si Scrapy detecta que el servidor del BOE va lento, él solo frena y espera más tiempo.
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 5.0
AUTOTHROTTLE_MAX_DELAY = 60.0
