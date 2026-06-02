FROM python:3.11-slim
WORKDIR /app

# 1. Copiamos el archivo de dependencias primero
COPY requirements.txt .

# 2. Instalamos TODO (Flask, Requests, Torch, Sentence-Transformers)
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copiamos la app y el html
COPY app.py .
COPY index.html .

EXPOSE 80

# Arrancamos nuestro escudo
CMD ["python", "app.py"]
