import json
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from apify_client import ApifyClient
from tkinter import Tk, filedialog

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
    print(f"Extrayendo hasta {limite} posts de {username}...")
    
    run_input_posts = {
        "username": username,
        "maxPosts": limite,
        "requestDelay": 5,
        "useProxy": True
    }
    
    try:
        actor_call = client.actor("iron-crawler/instagram-posts").call(run_input=run_input_posts)
        dataset_items = list(client.dataset(actor_call["defaultDatasetId"]).iterate_items())
        
        if not dataset_items:
            return {"exito": False, "mensaje": f"No se encontraron posts para '{username}'. La cuenta podria ser privada o no tener publicaciones."}
        
        posts_procesados = []
        for post in dataset_items:
            post_id = post.get("shortcode") or post.get("code") or post.get("post_id")
            if not post_id:
                continue
            
            timestamp = post.get("taken_at")
            if timestamp and isinstance(timestamp, (int, float)):
                fecha_legible = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            else:
                fecha_legible = None
            
            caption_data = post.get("caption")
            texto_caption = ""
            hashtags_list = []
            menciones_list = []
            
            if isinstance(caption_data, dict):
                texto_caption = caption_data.get("text", "")
                hashtags_list = caption_data.get("hashtags", [])
                menciones_list = caption_data.get("mentions", [])
            elif isinstance(caption_data, str):
                texto_caption = caption_data
            elif isinstance(caption_data, list):
                texto_caption = " ".join(str(item) for item in caption_data)
            
            if not hashtags_list:
                hashtags_list = post.get("hashtags", [])
            if not menciones_list:
                menciones_list = post.get("mentions", [])
            
            posts_procesados.append({
                "id": post_id,
                "url": f"https://www.instagram.com/p/{post_id}/",
                "fecha": fecha_legible,
                "likes": post.get("like_count", 0),
                "comentarios": post.get("comment_count", 0),
                "caption": texto_caption,
                "tipo_media": post.get("media_type"),
                "url_media": post.get("media_url") or post.get("display_url"),
                "hashtags": ", ".join(hashtags_list) if hashtags_list else "",
                "menciones": ", ".join(menciones_list) if menciones_list else ""
            })
        
        if not posts_procesados:
            return {"exito": False, "mensaje": f"No se pudo extraer ningun post valido para '{username}'. La cuenta podria ser privada."}
        
        return {"exito": True, "posts": posts_procesados}
    except Exception as e:
        return {"exito": False, "mensaje": f"Error extrayendo posts: {e}"}

def seleccionar_ruta_guardado(nombre_sugerido):
    root = Tk()
    root.withdraw()
    ruta = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Archivos Excel", "*.xlsx"), ("Todos los archivos", "*.*")],
        initialfile=nombre_sugerido,
        title="Guardar archivo Excel"
    )
    root.destroy()
    return ruta

def main():
    API_TOKEN = os.getenv("API_TOKEN")
    if not API_TOKEN:
        raise ValueError("No se encontro API_TOKEN en el archivo .env.")
    
    client = ApifyClient(API_TOKEN)
    
    username = input("Ingresa el nombre de usuario de Instagram (sin @): ").strip()
    validacion = validar_cuenta(username, client)
    print(validacion["mensaje"])
    
    if not validacion["existe"] or validacion.get("es_privada", False):
        return
    
    # Mostrar opciones ampliadas
    print("\nOpciones de extraccion:")
    print("1 - Los 10 primeros posts")
    print("2 - Los 10 ultimos posts")
    print("3 - Todos los posts (puede tomar varios minutos)")
    opcion = input("Elige una opcion: ").strip()
    
    if opcion == "1":
        limite_temporal = 1000  #limite del cual se hará el conteo para los 10 primeros ó ultimos
        resultado_temporal = extraer_posts(username, client, limite_temporal)
        if not resultado_temporal["exito"]:
            print(resultado_temporal["mensaje"])
            return
        
        posts_ordenados = sorted(resultado_temporal["posts"], key=lambda x: x["fecha"] if x["fecha"] else "")
        posts_final = posts_ordenados[:10]
        
        resultado_posts = {"exito": True, "posts": posts_final}
    elif opcion == "2":
        limite = 10
        resultado_posts = extraer_posts(username, client, limite)
    elif opcion == "3":
        
        limite = 1000
        print(f"ADVERTENCIA: Se intentaran extraer hasta {limite} posts. Esto puede tomar varios minutos dependiendo de la cantidad de publicaciones.")
        resultado_posts = extraer_posts(username, client, limite)
    else:
        print("Opcion no valida. Saliendo...")
        return
    
    if not resultado_posts["exito"]:
        print(resultado_posts["mensaje"])
        return
    
    df_posts = pd.DataFrame(resultado_posts["posts"])
    
    nombre_sugerido = f"instagram_{username}_posts.xlsx"
    ruta_excel = seleccionar_ruta_guardado(nombre_sugerido)
    
    if not ruta_excel: 
        print("Guardado cancelado por el usuario.")
        return
    
    df_posts.to_excel(ruta_excel, index=False, engine='openpyxl')
    print(f"\nExito! Los datos se han guardado en: {ruta_excel}")

if __name__ == "__main__":
    main()