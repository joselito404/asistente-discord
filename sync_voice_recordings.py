"""
Script de sincronización y respaldo de grabaciones de llamadas de Discord a OneDrive.
Descarga automáticamente todas las grabaciones de voz y metadatos retenidos (últimas 24 horas)
desde el servicio en la nube (Render) a la carpeta local 'recordings_backup/'.
"""

import os
import sys
import json
import urllib.request
import zipfile
import io
from datetime import datetime

RENDER_BASE_URL = "https://asistente-discord-sj3k.onrender.com"
LOCAL_BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings_backup")

def sync_recordings():
    os.makedirs(LOCAL_BACKUP_DIR, exist_ok=True)
    zip_url = f"{RENDER_BASE_URL}/audios/zip"
    print(f"[*] Conectando a {zip_url} para descargar paquete de grabaciones de 24 horas...")
    
    req = urllib.request.Request(zip_url, headers={"User-Agent": "AntigravitySync/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            if resp.status != 200:
                print(f"[!] Error del servidor: HTTP {resp.status}")
                return
            data = resp.read()
            print(f"[+] Paquete ZIP descargado ({len(data):,} bytes). Extrayendo en {LOCAL_BACKUP_DIR}...")
            
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                zf.extractall(LOCAL_BACKUP_DIR)
                file_list = zf.namelist()
                
            print(f"[✅] ¡Sincronización completada! {len(file_list)} archivos guardados en:")
            print(f"    {LOCAL_BACKUP_DIR}")
            for name in file_list:
                print(f"    - {name}")
    except Exception as ex:
        print(f"[!] Error durante la sincronización: {ex}")

if __name__ == "__main__":
    sync_recordings()
