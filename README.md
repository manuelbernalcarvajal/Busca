# Busca

YALm recomendado:
```
version: '3.8'

services:
  # 1. EL CEREBRO
  meilisearch:
    image: getmeili/meilisearch:latest
    container_name: buscador-gobierno
    environment:
      - MEILI_MASTER_KEY=${MEILI_MASTER_KEY} 
      - MEILI_ENV=${MEILI_ENV}
    volumes:
      # Conectamos el volumen de Docker a la carpeta interna de Meilisearch
      - meili_data:/meili_data 
    restart: unless-stopped

  # 2. EL TRABAJADOR
  crawler:
    image: ghcr.io/manuelbernalcarvajal/busca-crawler:${APP_VERSION}
    container_name: araña-gobierno
    environment:
      - MEILISEARCH_URL=http://meilisearch:7700
      - MEILISEARCH_KEY=${MEILI_MASTER_KEY}
    volumes:
      # Conectamos el volumen a la carpeta "datos" (donde SQLite guardará el archivo)
      - crawler_data:/app/datos 
    depends_on:
      - meilisearch
    restart: unless-stopped

  # 3. EL ESCUDO
  frontend:
    image: ghcr.io/manuelbernalcarvajal/busca-frontend:${APP_VERSION}
    container_name: buscador-web
    environment:
      - MEILISEARCH_URL=http://meilisearch:7700
      - MEILISEARCH_KEY=${MEILI_MASTER_KEY}
    ports:
      - "${FRONTEND_PORT}:80" 
    depends_on:
      - meilisearch
    restart: unless-stopped

# Aquí declaramos los volúmenes gestionados por Docker
volumes:
  meili_data:
  crawler_data:
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


Para probar si finciona en el icono >_ de portainer puedes lanzar un  a mailiseach este comando, y así te dira cuanto tiene indexado:
```
curl http://localhost:7700/indexes/documentos_legales/stats
```
