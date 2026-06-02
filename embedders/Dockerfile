# Usamos una imagen de Python ligera
FROM python:3.11-slim

# Directorio de trabajo
WORKDIR /app

# Instalamos dependencias (primero esto para que Docker cachee bien)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos nuestro script
COPY vectorize_worker.py .

# Comando para ejecutar el worker
CMD ["python", "vectorize_worker.py"]
