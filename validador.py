import json
from apify_client import ApifyClient

def validar_cuenta(username, client):
    print(f"🔍 Validando cuenta: {username}...")
    
    # Input para el Actor de perfil
    run_input_perfil = {
        "usernames": [username],
        "proxyConfiguration": { "useApifyProxy": True }
    }
    
    try:
        # Ejecutar el Actor y esperar a que termine
        actor_call = client.actor("apify/instagram-profile-scraper").call(run_input=run_input_perfil)
        
        # Obtener los resultados del Dataset generado
        dataset_items = list(client.dataset(actor_call["defaultDatasetId"]).iterate_items())
        
        if not dataset_items:
            return {"existe": False, "mensaje": f"La cuenta '{username}' no existe."}
        
        perfil = dataset_items[0]
        # Verificar si es privada
        if perfil.get("isPrivate", False):
            return {"existe": True, "es_privada": True, "mensaje": f"La cuenta '{username}' es privada. No se puede scrappear."}
        
        # Si todo está bien, devolvemos los datos del perfil
        return {
            "existe": True,
            "es_privada": False,
            "perfil": perfil,
            "mensaje": f"Cuenta '{username}' validada correctamente."
        }
        
    except Exception as e:
        return {"existe": False, "mensaje": f"Error inesperado: {e}"}