# Usamos una imagen oficial de Python ligera
FROM python:3.11-slim

# Creamos una carpeta dentro del contenedor donde vivirá nuestro código
WORKDIR /app

# Copiamos primero los requerimientos (esto optimiza la caché de Docker)
COPY requirements.txt .

# Instalamos Scrapy sin guardar archivos basura
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo tu código (incluyendo el entrypoint.sh y settings.py) a la carpeta /app
COPY . .

# Le damos permisos de ejecución a tu script .sh
RUN chmod +x entrypoint.sh

# Le decimos a Docker qué hacer cuando el contenedor se encienda
CMD ["./entrypoint.sh"]
