# Busca

YALm recomendado:
```
services:
  # 1. EL CEREBRO
  meilisearch:
    image: getmeili/meilisearch:v1.45.2   
    container_name: buscador-gobierno
    environment:
      - MEILI_MASTER_KEY=${MEILI_MASTER_KEY} 
      - MEILI_ENV=${MEILI_ENV}
    volumes:
      # Conectamos el volumen de Docker a la carpeta interna de Meilisearch
      - meili_data:/meili_data 
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "30m"   # Máximo 10 megas por archivo
        max-file: "3"

  # 2. EL TRABAJADOR (Extrae los datos)
  crawler:
    image: ghcr.io/manuelbernalcarvajal/busca-crawler:${APP_VERSION}
    container_name: arana-gobierno
    environment:
      - MEILISEARCH_URL=http://meilisearch:7700
      - MEILISEARCH_KEY=${MEILI_MASTER_KEY}
    volumes:
      # Conectamos el volumen a la carpeta "datos" (donde SQLite guardará el archivo)
      - crawler_data:/app/datos 
    depends_on:
      - meilisearch
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "30m"   
        max-file: "3"

  # 3. EL ESCUDO (Interfaz y traducción a IA del usuario)
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
    logging:
      driver: "json-file"
      options:
        max-size: "10m"   
        max-file: "3"

# 4. EL CEREBRO TRADUCTOR (Proceso de baja prioridad)
  vectorizer:
    image: ghcr.io/manuelbernalcarvajal/busca-vectorizer:latest
    container_name: arana-ia
    environment:
      - PYTHONUNBUFFERED=1  # <--- AÑADE ESTO
      - MEILISEARCH_URL=http://meilisearch:7700
      - MEILISEARCH_KEY=${MEILI_MASTER_KEY}
    depends_on:
      - meilisearch
    restart: unless-stopped
    # LÍMITES DOCKER: Le ponemos una correa corta
    deploy:
      resources:
        limits:
          cpus: '1'        # Nunca podrá usar más de medio núcleo de CPU
          memory: 2024M      # Nunca usará más de 1GB de RAM (si se pasa, espera, no bloquea)
    logging:
      driver: "json-file"
      options:
        max-size: "30m"
        max-file: "3"

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
