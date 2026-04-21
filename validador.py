import json
import os
import pandas as pd
from dotenv import load_dotenv
from apify_client import ApifyClient
load_dotenv()

def validar_cuenta(username, client):
    print(f"Validando cuenta: {username}...")
    
    run_input_perfil = {
        "usernames": [username],
        "proxyConfiguration": { "useApifyProxy": True }
    }
    
    try:
        actor_call = client.actor("apify/instagram-profile-scraper").call(run_input=run_input_perfil)
        dataset_items = list(client.dataset(actor_call["defaultDatasetId"]).iterate_items())
        
        if not dataset_items:
            return {"existe": False, "mensaje": f"La cuenta '{username}' no existe."}
        
        perfil = dataset_items[0]
        if perfil.get("isPrivate", False):
            return {"existe": True, "es_privada": True, "mensaje": f"La cuenta '{username}' es privada. No se puede scrappear."}
        
        return {
            "existe": True,
            "es_privada": False,
            "perfil": perfil,
            "mensaje": f"Cuenta '{username}' validada correctamente."
        }
        
    except Exception as e:
        return {"existe": False, "mensaje": f"Error inesperado: {e}"}

def extraer_posts(username, client, limite=10):
    print(f"Extrayendo {limite} posts de {username}...")
    
    run_input_posts = {
        "username": [username],
        "resultsLimit": limite,
        "proxy": { "useApifyProxy": True }
    }
    
    try:
        actor_call = client.actor("muhammad_noman_riaz/instagram-post-super-scraper").call(run_input=run_input_posts)
        dataset_items = list(client.dataset(actor_call["defaultDatasetId"]).iterate_items())
        
        posts_procesados = []
        for post in dataset_items:
            posts_procesados.append({
                "id": post.get("shortcode"),
                "url": f"https://www.instagram.com/p/{post.get('shortcode')}/",
                "fecha": post.get("taken_at"),
                "likes": post.get("likes_count", 0),
                "comentarios": post.get("comments_count", 0),
                "caption": post.get("caption", ""),
                "tipo_media": post.get("media_type"),
                "url_media": post.get("display_url"),
                "hashtags": post.get("hashtags", []),
                "menciones": post.get("mentions", [])
            })
        return {"exito": True, "posts": posts_procesados}
    except Exception as e:
        return {"exito": False, "mensaje": f"Error extrayendo posts: {e}"}

def main():
    API_TOKEN = os.getenv("API_TOKEN") #añadir el valor del token edentro del .env
    if not API_TOKEN:
        raise ValueError("No se encontró API_TOKEN en el archivo .env. Revisa que el archivo exista y contenga la variable.")
    
    client = ApifyClient(API_TOKEN)
    
    username = input("Ingresa el nombre de usuario de Instagram (sin @): ").strip()
    validacion = validar_cuenta(username, client)
    print(validacion["mensaje"])
    
    if not validacion["existe"] or validacion.get("es_privada", False):
        return
    
    opcion = input("¿Qué datos quieres extraer? (1 = primeros 10 posts, 2 = últimos 10 posts): ").strip()
    if opcion not in ["1", "2"]:
        print("Opción no válida. Saliendo...")
        return
    
    limite = 10
    resultado_posts = extraer_posts(username, client, limite)
    
    if not resultado_posts["exito"]:
        print(resultado_posts["mensaje"])
        return
    
    df_posts = pd.DataFrame(resultado_posts["posts"])
    ruta_excel = os.path.join(os.path.expanduser("~"), "Downloads", f"instagram_{username}_posts.xlsx")
    df_posts.to_excel(ruta_excel, index=False, engine='openpyxl')
    
    print(f"\n ¡Éxito! Los datos se han guardado en: {ruta_excel}")

if __name__ == "__main__":
    main()