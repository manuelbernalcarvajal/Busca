from sentence_transformers import SentenceTransformer
import meilisearch
import time

# Cargamos el modelo (se descarga una vez y se queda en caché)
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
client = meilisearch.Client('http://meilisearch:7700', 'TU_MASTER_KEY')
index = client.index('documentos_legales')

def vectorizar_batch():
    # Pedimos documentos que no tengan vectores (_vectors es null)
    docs = index.search('', {'filter': '_vectors IS NULL', 'limit': 20})
    
    if not docs['hits']:
        return False # No hay trabajo

    for doc in docs['hits']:
        # Vectorizamos el contenido
        vector = model.encode(doc['contenido']).tolist()
        
        # Guardamos el vector en Meilisearch
        index.update_documents([{'id': doc['id'], '_vectors': vector}])
        
    return True

while True:
    if not vectorizar_batch():
        time.sleep(60) # Si no hay trabajo, descansa 1 minuto
