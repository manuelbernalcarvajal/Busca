import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import time

# Ahora le damos una batería de URLs para que busque en todos los directorios
URLS_DIRECTORIOS = [
    # 1. El directorio de Sedes Electrónicas (Trámites)
    "https://sede.administracion.gob.es/PAG_Sede/SedesElectronicas.html",
    
    # 2. El directorio general de Webs Públicas (Ministerios, Casa Real, etc.)
    "https://administracion.gob.es/pag_Home/atencionCiudadana/SedesElectronicas-y-Webs-Publicas/websPublicas.html",
    
    # 3. La página raíz de atención ciudadana por si se nos escapa algo
    "https://administracion.gob.es/pag_Home/atencionCiudadana/SedesElectronicas-y-Webs-Publicas.html"
]

def actualizar_lista():
    print("🔄 Raspando los directorios oficiales (Sedes y Webs Públicas)...")
    dominios_unicos = set()
    headers = {'User-Agent': 'BuscadorLegalBot/1.0 (+contacto@tudominio.com)'}

    for url_origen in URLS_DIRECTORIOS:
        try:
            print(f"👉 Inspeccionando: {url_origen}")
            respuesta = requests.get(url_origen, headers=headers, timeout=15)
            respuesta.raise_for_status()

            sopa = BeautifulSoup(respuesta.text, 'html.parser')

            # Buscamos todos los enlaces de esta página
            for enlace in sopa.find_all('a', href=True):
                url = enlace['href']
                
                if url.startswith('http'):
                    dominio = urlparse(url).netloc
                    dominio = dominio.replace('www.', '')
                    
                    # Filtramos: solo sitios de España y evitamos redes sociales
                    if dominio.endswith('.es') and 'twitter' not in dominio and 'facebook' not in dominio:
                        dominios_unicos.add(dominio)
                        
            # Pausa ética de 1 segundo entre directorios para no saturar al servidor
            time.sleep(1)

        except Exception as e:
            print(f"❌ Error al raspear {url_origen}: {e}")

    # Añadimos nuestros clásicos intocables
    dominios_unicos.update(['boe.es', 'poderjudicial.es', 'administracion.gob.es', 'mjusticia.gob.es'])
    
    # Guardamos la lista combinada
    if dominios_unicos:
        with open('dominios.txt', 'w', encoding='utf-8') as f:
            for dom in sorted(dominios_unicos):
                f.write(f"{dom}\n")
        print(f"✅ ¡Éxito brutal! Se han extraído y guardado {len(dominios_unicos)} dominios oficiales.")
    else:
        print("⚠️ No se encontró ningún dominio. El crawler usará la lista antigua por seguridad.")

if __name__ == "__main__":
    actualizar_lista()
