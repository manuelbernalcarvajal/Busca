from sentence_transformers import SentenceTransformer
import meilisearch
import time
import os

# 1. Variables de entorno (¡Seguridad ante todo!)
MEILISEARCH_URL = os.getenv('MEILISEARCH_URL', 'http://meilisearch:7700')
MEILISEARCH_KEY = os.getenv('MEILISEARCH_KEY', 'SuperSecreta123')
INDICE = 'documentos_legales'

print("🧠 Cargando modelo de IA (Esto puede tardar unos segundos)...")
# Cargamos el modelo (se descarga una vez y se queda en caché)
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# Conectamos con Meilisearch
client = meilisearch.Client(MEILISEARCH_URL, MEILISEARCH_KEY)
index = client.index(INDICE)
print("✅ Modelo cargado. Listo para vectorizar documentos.")

def vectorizar_batch():
    try:
        # Pedimos 10 documentos que no tengan vectores (_vectors es null)
        # Lotes pequeños (10) para no saturar la RAM
        docs = index.search('', {'filter': '_vectors IS NULL', 'limit': 10})
        
        if not docs.get('hits'):
            return False # No hay trabajo

        documentos_actualizados = []
        for doc in docs['hits']:
            print(f"🔄 Vectorizando: {doc.get('titulo', 'Documento sin título')[:50]}...")
            
            # Vectorizamos el contenido
            vector = model.encode(doc['contenido']).tolist()
            documentos_actualizados.append({'id': doc['id'], '_vectors': vector})
            
        # Enviamos el lote entero a Meilisearch de una sola vez
        index.update_documents(documentos_actualizados)
        return True

    except Exception as e:
        print(f"❌ Error al comunicar con Meilisearch: {e}")
        time.sleep(10) # Si hay error, esperamos 10 segundos antes de reintentar
        return False

# Bucle infinito del Worker
while True:
    if not vectorizar_batch():
        print("💤 No hay documentos pendientes. Durmiendo 60 segundos...")
        time.sleep(60) # Si no hay trabajo, descansa 1 minuto
    else:
        time.sleep(2) # Pausa táctica de 2 segundos entre lotes para dejar respirar al servidor
