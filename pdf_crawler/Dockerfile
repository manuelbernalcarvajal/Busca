FROM python:3.11-slim

WORKDIR /app

# Instalamos dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el código del minero
COPY . .

# Al arrancar, ejecutamos el script de control (El capataz)
CMD ["bash", "entrypoint.sh"]
