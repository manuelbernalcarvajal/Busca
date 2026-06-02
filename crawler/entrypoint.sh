#!/bin/bash

echo "🚀 Iniciando contenedor de indexación en modo 24/7 (Fuego Lento)..."

# Creamos un bucle infinito
while true; do
    echo "================================================="
    echo "📅 Iniciando nuevo ciclo de rastreo: $(date)"
    echo "================================================="

    # 1. Actualizamos la lista de dominios por si hay novedades
    python actualizar_dominios.py

    # 2. Soltamos a la araña
    echo "🕷️ Rastreando..."
    scrapy runspider gob_spider.py

    # 3. La pausa de descanso
    # Cuando la araña termine (o si se corta), el contenedor dormirá.
    # 86400 segundos = 24 horas. Puedes ajustarlo a 43200 (12 horas) o lo que prefieras.
    echo "💤 Ciclo terminado. Liberando memoria y durmiendo hasta mañana..."
    sleep 86400 
done
