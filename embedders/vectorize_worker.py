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
    
    settings = index.get_settings()
    filterable = settings.get('filterableAttributes', [])
    
    # Nos aseguramos de tener estado_ia, origen_id (del pipeline) y cluster_id (temático)
    nuevos_filtros = list(set(filterable + ['_vectors', 'estado_ia', 'origen_id', 'cluster_id']))
    
    if sorted(filterable) != sorted(nuevos_filtros):
        print("🔧 Configurando filtros avanzados y esperando...")
        tarea_filtros = index.update_filterable_attributes(nuevos_filtros)
        client.wait_for_task(tarea_filtros.task_uid)
    
    print("🔧 Aplicando configuración de embedders y esperando...")
    tarea_embedders = index.update_settings({
        "embedders": {
            "default": {
                "source": "userProvided", 
                "dimensions": 384
            }
        }
    })
    client.wait_for_task(tarea_embedders.task_uid)
    print("✅ Configuración de vectores aplicada.")

asegurar_configuracion()
print("✅ Listo para vectorizar.")

# ❌ BORRAMOS LA FUNCIÓN trocear_texto() ❌
# El Pipeline ya nos manda los textos perfectamente troceados por párrafos.

def vectorizar_batch():
    try:
        print("🔍 Buscando chunks pendientes...")
        
        docs = index.search('', {
            'limit': 50, # Como ahora son chunks sueltos, podemos procesar más de golpe
            'filter': "estado_ia = 'pendiente'"
        })
        
        documentos_pendientes = docs['hits']
        
        if not documentos_pendientes:
            print("💤 No hay chunks pendientes, durmiendo...")
            return False

        print(f"🔄 Encontrados {len(documentos_pendientes)} chunks para procesar.")
        
        documentos_actualizados = []
        for doc in documentos_pendientes:
            print(f"🔄 Vectorizando: {doc.get('titulo', '')[:30]} (Chunk)")
            
            # 1. Vectorizamos directamente el contenido entero (porque ya es un trozo pequeño)
            # Retorna una lista plana de floats: [0.12, -0.45, ...]
            vector_unico = model.encode(doc['contenido']).tolist()
            
            # 2. El Cerebro Temático (cluster_id)
            # Buscamos si ya existe algún fragmento en la BD que hable de lo mismo (>90% de similitud)
            cluster_id = doc['id'] 
            
            busqueda_clones = index.search('', {
                'vector': vector_unico, 
                'limit': 1,
                'showRankingScore': True,
                'hybrid': {
                    'semanticRatio': 0.8, # Subimos al 80% semántica para clustering temático
                    'embedder': 'default'
                }
            })
            
            if busqueda_clones.get('hits'):
                mejor_clon = busqueda_clones['hits'][0]
                # Si se parecen muchísimo, los unimos bajo el mismo cluster_id temático
                if mejor_clon.get('_rankingScore', 0) > 0.90:
                    cluster_id = mejor_clon.get('cluster_id', mejor_clon['id'])
                    print(f"   🔗 ¡Coincidencia temática encontrada!")

            # 3. Guardamos el vector único y el cluster_id
            documentos_actualizados.append({
                'id': doc['id'], 
                '_vectors': {'default': vector_unico}, # <--- Un solo vector por documento
                'cluster_id': cluster_id,              # <--- Agrupación por temática
                'estado_ia': 'completado'
            })
            
        index.update_documents(documentos_actualizados)
        print("✅ Batch de chunks actualizado con éxito.")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        time.sleep(10)
        return False

while True:
    if not vectorizar_batch():
        time.sleep(20) # Reducimos la espera si no hay trabajo, porque procesa más rápido
    else:
        time.sleep(2)
