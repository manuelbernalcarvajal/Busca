#!/bin/bash

echo "🚀 Iniciando Minero de PDFs (Modo Fuego Lento)..."

# Aseguramos que existe la carpeta de datos por si acaso
mkdir -p datos

while true; do
    echo "================================================="
    echo "📅 Iniciando ciclo de procesamiento de PDFs: $(date)"
    echo "================================================="

    # 1. Comprobación de vida (¿Está el Poder Judicial online?)
    # Hacemos un ping HTTP rápido usando Python (timeout de 10s)
    PODER_JUDICIAL_VIVO=$(python -c "import requests; print('OK' if requests.get('https://www.poderjudicial.es', timeout=10).status_code == 200 else 'FAIL')")
    
    if [ "$PODER_JUDICIAL_VIVO" = "OK" ]; then
        echo "✅ El servidor del Poder Judicial está vivo. Soltando al Minero..."
        
        # 2. Ejecutamos el spider
        scrapy runspider pdf_spider.py
        
    else
        echo "❌ El servidor del Poder Judicial no responde o está bloqueando. Abortando ciclo."
    fi

    # 3. La pausa larga. 
    # Descargar PDFs consume ancho de banda de las sedes. Descansamos 6 horas (21600 segundos)
    echo "💤 Ciclo terminado. Minero durmiendo 6 horas..."
    sleep 21600 
done
