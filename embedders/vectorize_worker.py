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
print("✅ Listo para vectorizar y agrupar.")

def vectorizar_batch():
    try:
        # Buscamos documentos vírgenes (sin vector)
        print("🔍 Buscando documentos pendientes...")
        docs = index.search('', {'filter': '_vectors IS NULL', 'limit': 10})
        
        if not docs.get('hits'):
            print("💤 No hay documentos nuevos, durmiendo...")
            return False

        documentos_actualizados = []
        for doc in docs['hits']:
            print(f"🔄 Procesando: {doc.get('titulo', '')[:50]}...")
            vector = model.encode(doc['contenido']).tolist()
            
            # --- EL RADAR DE CLONES SEMÁNTICOS ---
            grupo_id = doc['id'] # Por defecto, creamos un grupo nuevo
            
            # Buscamos en Meilisearch si ya hay algo idéntico (usando el vector)
            busqueda_clones = index.search('', {
                'vector': vector,
                'limit': 1,
                'filter': '_vectors IS NOT NULL', # Solo comparamos con los que ya tienen IA
                'showRankingScore': True
            })
            
            if busqueda_clones.get('hits'):
                mejor_clon = busqueda_clones['hits'][0]
                similitud = mejor_clon.get('_rankingScore', 0)
                print("Clones encontrados")
                
                # 0.90 es una similitud brutal (Ej: Ley Base vs Ley de Reforma)
                if similitud > 0.90:
                    # Heredamos el ID de grupo del documento padre
                    grupo_id = mejor_clon.get('grupo_id', mejor_clon['id'])
                    print(f"   🔗 ¡Grupo encontrado! Similitud: {similitud:.2f}")

            # Preparamos la actualización
            documentos_actualizados.append({
                'id': doc['id'], 
                '_vectors': vector,
                'grupo_id': grupo_id # Etiqueta mágica para el Frontend
            })
            
        index.update_documents(documentos_actualizados)
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        time.sleep(10)
        return False

while True:
    if not vectorizar_batch():
        print("No vectrorizar_bath() sleep 60
        time.sleep(60)
    else:
        time.sleep(2)
