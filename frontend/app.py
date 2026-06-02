from flask import Flask, request, jsonify, send_from_directory
import requests
import os

app = Flask(__name__)

# El servidor lee las variables ocultas de Docker
MEILISEARCH_URL = os.getenv('MEILISEARCH_URL', 'http://meilisearch:7700')
MEILISEARCH_KEY = os.getenv('MEILISEARCH_KEY', 'SuperSecreta123')
INDICE = 'documentos_legales'

# 1. Cuando el usuario entra a la web, le damos el HTML
@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

# 2. El Escudo de Búsqueda (La API oculta)
@app.route('/api/buscar', methods=['POST'])
def buscar():
    datos_usuario = request.json
    
    # Aquí podríamos añadir filtros de seguridad (ej: limitar a 10 peticiones por minuto)
    # para que nadie nos genere "facturas ajenas"
    
    # Preparamos la petición REAL hacia Meilisearch de forma secreta
    headers = {
        'Authorization': f'Bearer {MEILISEARCH_KEY}',
        'Content-Type': 'application/json'
    }
    
    try:
        url_interna = f"{MEILISEARCH_URL}/indexes/{INDICE}/search"
        respuesta = requests.post(url_interna, headers=headers, json=datos_usuario, timeout=5)
        
        # Devolvemos los datos al usuario sin revelar jamás nuestras contraseñas
        return jsonify(respuesta.json())
        
    except Exception as e:
        return jsonify({"error": "Error interno del servidor"}), 500

if __name__ == '__main__':
    # Arrancamos el servidor en el puerto 80
    app.run(host='0.0.0.0', port=80)
