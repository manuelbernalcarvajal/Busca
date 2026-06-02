# Busca

YALm recomendado:
```
version: '3.8'

services:
  # 1. EL CEREBRO (Meilisearch)
  meilisearch:
    image: getmeili/meilisearch:latest
    container_name: buscador-gobierno
    environment:
      # ¡Cambia esta contraseña por una tuya!
      - MEILI_MASTER_KEY=SuperSecreta123 
      - MEILI_ENV=production
    ports:
      - "7700:7700" # Exponemos el puerto para poder consultarlo desde fuera
    volumes:
      # Guardamos los datos de Meilisearch en tu servidor para no perderlos
      - /ruta/en/tu/servidor/meili_data:/meili_data 
    restart: unless-stopped

  # 2. EL TRABAJADOR (Tu Crawler)
  crawler:
    image: ghcr.io/tu-usuario/busca:latest # Aquí pones la imagen que te genera GitHub
    container_name: araña-gobierno
    environment:
      # Así es como hablan: usando el nombre del contenedor de arriba
      - MEILISEARCH_URL=http://meilisearch:7700
      - MEILISEARCH_KEY=SuperSecreta123
    volumes:
      # Guardamos la memoria SQLite de las 24h
      - /ruta/en/tu/servidor/memoria_crawler.db:/app/memoria_crawler.db 
    depends_on:
      - meilisearch # El crawler espera a que el cerebro despierte primero
    restart: unless-stopped
```
