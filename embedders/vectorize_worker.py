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
    
    # 1. Asegurar filterableAttributes (AÑADIMOS AMBOS: _vectors y estado_ia)
    settings = index.get_settings()
    filterable = settings.get('filterableAttributes', [])
    
    # Usamos set() para unir la configuración actual con los que necesitamos sin duplicar
    nuevos_filtros = list(set(filterable + ['_vectors', 'estado_ia']))
    
    # Solo actualizamos si Meilisearch no los tiene ya
    if sorted(filterable) != sorted(nuevos_filtros):
        print("🔧 Configurando filtros (_vectors y estado_ia) y esperando...")
        tarea_filtros = index.update_filterable_attributes(nuevos_filtros)
        client.wait_for_task(tarea_filtros.task_uid) # <-- MAGIA ASÍNCRONA
    
    # 2. Asegurar Embedders
    print("🔧 Aplicando configuración de embedders y esperando...")
    tarea_embedders = index.update_settings({
        "embedders": {
            "default": {
                "source": "userProvided", 
                "dimensions": 384
            }
        }
    })
    client.wait_for_task(tarea_embedders.task_uid) # <-- MAGIA ASÍNCRONA
    print("✅ Configuración de vectores aplicada y confirmada desde Python.")

asegurar_configuracion()
print("✅ Listo para vectorizar y agrupar.")

def trocear_texto(texto, max_palabras=150):
    """Corta textos largos en fragmentos más digeribles para la IA"""
    if not texto:
        return [""]
    palabras = texto.split()
    return [' '.join(palabras[i:i + max_palabras]) for i in range(0, len(palabras), max_palabras)]

def vectorizar_batch():
    try:
        print("🔍 Buscando documentos...")
        
        # Filtramos por nuestro ticket, adiós a los problemas de _vectors
        docs = index.search('', {
            'limit': 20,
            'filter': "estado_ia = 'pendiente'"  # <--- BÚSQUEDA INFALIBLE
        })
        
        documentos_pendientes = docs['hits']
        
        if not documentos_pendientes:
            print("💤 No hay documentos pendientes, durmiendo...")
            return False

        print(f"🔄 Encontrados {len(documentos_pendientes)} documentos para procesar.")
        
        documentos_actualizados = []
        for doc in documentos_pendientes:
            print(f"🔄 Procesando: {doc.get('titulo', '')[:50]}...")
            
            # 1. Troceamos el contenido en partes de 150 palabras
            fragmentos = trocear_texto(doc['contenido'])
            
            # 2. Vectorizamos TODOS los fragmentos de golpe (devuelve una lista de vectores)
            vectores = model.encode(fragmentos).tolist()
            
            grupo_id = doc['id'] 
            
            # Busqueda de clones (usamos solo el primer vector para no sobrecargar esta comprobación rápida)
            busqueda_clones = index.search('', {
                'vector': vectores[0], 
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

            # 3. Guardamos la LISTA ENTERA de vectores en Meilisearch
            documentos_actualizados.append({
                'id': doc['id'], 
                '_vectors': {'default': vectores}, # <--- AQUÍ ESTÁ LA MAGIA (Múltiples vectores)
                'grupo_id': grupo_id,
                'estado_ia': 'completado'
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
