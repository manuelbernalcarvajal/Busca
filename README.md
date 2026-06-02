# Busca

YALm recomendado:
```
version: '3.8'

services:
  # 1. EL CEREBRO (Totalmente aislado de internet)
  meilisearch:
    image: getmeili/meilisearch:latest
    container_name: buscador-gobierno
    environment:
      # Llama a la clave y al entorno desde el .env
      - MEILI_MASTER_KEY=${MEILI_MASTER_KEY} 
      - MEILI_ENV=${MEILI_ENV}
    volumes:
      # Llama a tu ruta local desde el .env
      - MEILI_DATA_PATH:/meili_data 
    restart: unless-stopped

  # 2. EL TRABAJADOR (Tu Crawler)
  crawler:
    # Usa la versión definida en el .env
    image: ghcr.io/manuelbernalcarvajal/busca-crawler:${APP_VERSION}
    container_name: araña-gobierno
    environment:
      - MEILISEARCH_URL=http://meilisearch:7700
      # Usa la MISMA clave que el cerebro para no equivocarte
      - MEILISEARCH_KEY=${MEILI_MASTER_KEY}
    volumes:
      # Llama a la ruta de tu base de datos SQLite desde el .env
      - CRAWLER_DB_PATH:/app/memoria_crawler.db 
    depends_on:
      - meilisearch
    restart: unless-stopped

  # 3. EL ESCUDO / ESCAPARATE (Tu Servidor Frontend)
  frontend:
    image: ghcr.io/manuelbernalcarvajal/busca-frontend:${APP_VERSION}
    container_name: buscador-web
    environment:
      - MEILISEARCH_URL=http://meilisearch:7700
      - MEILISEARCH_KEY=${MEILI_MASTER_KEY}
    ports:
      # Asigna el puerto exterior desde tu .env y lo conecta al puerto 80 interno
      - "${FRONTEND_PORT}:80" 
    depends_on:
      - meilisearch
    restart: unless-stopped
volumes:
  MEILI_DATA_PATH:
  CRAWLER_DB_PATH:
```
Los .env son:
```
# ==========================================
# CONFIGURACIÓN DEL BUSCADOR GUBERNAMENTAL
# ==========================================

# 🔑 Seguridad
# La contraseña maestra. Debe tener al menos 16 caracteres para producción.
MEILI_MASTER_KEY=SuperSecreta123_CambialaPorFavor

# Entorno de ejecución (development o production). 
# En 'production' se desactiva la interfaz web por defecto de Meilisearch por seguridad.
MEILI_ENV=production

# 🌐 Redes y Puertos
# El puerto por el que accederás a tu web desde el navegador
FRONTEND_PORT=8080

# 📦 Versión de las imágenes
# Por si algún día quieres fijar una versión en vez de usar 'latest' (ej. v1.2)
APP_VERSION=latest
```
