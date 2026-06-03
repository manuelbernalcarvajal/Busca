from sentence_transformers import SentenceTransformer
import meilisearch
import time
import os

MEILISEARCH_URL = os.getenv('MEILISEARCH_URL', 'http://meilisearch:7700')
MEILISEARCH_KEY = os.getenv('MEILISEARCH_KEY', 'SuperSecreta123')
INDICE = 'documentos_legales'

print("🧠 Cargando modelo de IA...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
client = meilisearch.Client(MEILISEARCH_URL, MEILISEARCH_KEY)
index = client.index(INDICE)

def asegurar_configuracion():
    print("🛠️ Verificando configuración de Meilisearch...")
    
    # 1. Asegurar filterableAttributes (Incluimos _vectors)
    settings = index.get_settings()
    filterable = settings.get('filterableAttributes', [])
    if '_vectors' not in filterable:
        print("🔧 Configurando _vectors como filtrable...")
        index.update_filterable_attributes(filterable + ['_vectors'])
    
    # 2. Asegurar Embedders (La configuración que hacías con curl)
    # Esto es exactamente lo mismo que tu comando PATCH
    index.update_settings({
        "embedders": {
            "default": {
                "source": "userProvided", 
                "dimensions": 384
            }
        }
    })
    print("✅ Configuración de vectores aplicada desde Python.")

asegurar_configuracion()
print("✅ Listo para vectorizar y agrupar.")

def vectorizar_batch():
    try:
        # Buscamos documentos (quitamos el filtro estricto por ahora)
        print("🔍 Buscando documentos...")
        docs = index.search('', {'limit': 20})
        
        # Filtramos en Python los que NO tienen vectores (es más seguro)
        documentos_pendientes = [d for d in docs['hits'] if '_vectors' not in d]
        
        if not documentos_pendientes:
            print("💤 No hay documentos pendientes, durmiendo...")
            return False

        print(f"🔄 Encontrados {len(documentos_pendientes)} documentos para procesar.")
        
        documentos_actualizados = []
        for doc in documentos_pendientes:
            print(f"🔄 Procesando: {doc.get('titulo', '')[:50]}...")
            vector = model.encode(doc['contenido']).tolist()
            
            grupo_id = doc['id'] 
            
            # Busqueda de clones
            busqueda_clones = index.search('', {
                'vector': vector,
                'limit': 1,
                'showRankingScore': True,
                'hybrid': {
                    'semanticRatio': 1.0,
                    'embedder': 'default'
                }
            })
            
            if busqueda_clones.get('hits'):
                mejor_clon = busqueda_clones['hits'][0]
                if mejor_clon.get('_rankingScore', 0) > 0.90:
                    grupo_id = mejor_clon.get('grupo_id', mejor_clon['id'])
                    print(f"   🔗 ¡Grupo encontrado!")

            documentos_actualizados.append({
                'id': doc['id'], 
                '_vectors': {'default': vector},
                'grupo_id': grupo_id
            })
            
        index.update_documents(documentos_actualizados)
        print("✅ Batch actualizado con éxito.")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        time.sleep(10)
        return False

while True:
    if not vectorizar_batch():
        time.sleep(60)
    else:
        time.sleep(2)
