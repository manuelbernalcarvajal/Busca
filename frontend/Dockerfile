FROM python:3.11-slim
WORKDIR /app

# Instalamos Flask y Requests
RUN pip install flask requests

# Copiamos la app y el html
COPY app.py .
COPY index.html .

EXPOSE 80

# Arrancamos nuestro escudo
CMD ["python", "app.py"]
