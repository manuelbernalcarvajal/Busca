#!/bin/bash

echo "🚀 Iniciando contenedor de indexación..."

# 1. Ejecutamos el script que actualiza el dominios.txt
python actualizar_dominios.py

# 2. Llamamos a Scrapy usando el 'name' interno de nuestra araña
echo "🕷️ Soltando a la araña rastreadora..."
scrapy crawl gob_spider
