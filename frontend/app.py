from flask import Flask, request, jsonify, send_from_directory
import requests
import os
from sentence_transformers import SentenceTransformer # 1. Importamos la IA

app = Flask(__name__)

# 2. CARGA EL MODELO UNA SOLA VEZ AL ARRANCAR (Esto es vital)
# Si lo cargas dentro de la función, el servidor se colapsará cada vez que alguien busque.
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

MEILISEARCH_URL = os.getenv('MEILISEARCH_URL', 'http://meilisearch:7700')
MEILISEARCH_KEY = os.getenv('MEILISEARCH_KEY', 'SuperSecreta123')
INDICE = 'documentos_legales'

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/api/buscar', methods=['POST'])
def buscar():
    datos_usuario = request.json
    user_query = datos_usuario.get('q', '')

    # 3. LÓGICA DE BÚSQUEDA HÍBRIDA
    if user_query:
        # Convertimos la frase del usuario a "números" (vectores)
        query_vector = model.encode(user_query).tolist()
        
        # Le inyectamos los parámetros de vector a la petición para Meilisearch
        datos_usuario['vector'] = query_vector
        datos_usuario['hybrid'] = {
            'semanticRatio': 0.5, # 70% semántica, 30% palabras clave
            'embedder': 'default'
        }

    headers = {
        'Authorization': f'Bearer {MEILISEARCH_KEY}',
        'Content-Type': 'application/json'
    }
    
    try:
        url_interna = f"{MEILISEARCH_URL}/indexes/{INDICE}/search"
        respuesta = requests.post(url_interna, headers=headers, json=datos_usuario, timeout=10) # Aumentamos timeout por seguridad
        return jsonify(respuesta.json())
    except Exception as e:
        return jsonify({"error": "Error interno del servidor"}), 500

# 3. El Chivato de Estadísticas (Para el contador en tiempo real)
@app.route('/api/stats', methods=['GET'])
def stats():
    headers = {'Authorization': f'Bearer {MEILISEARCH_KEY}'}
    try:
        url_interna = f"{MEILISEARCH_URL}/indexes/{INDICE}/stats"
        respuesta = requests.get(url_interna, headers=headers, timeout=5)
        return jsonify(respuesta.json())
    except Exception:
        return jsonify({"numberOfDocuments": 0})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
