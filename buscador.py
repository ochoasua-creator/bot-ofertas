import os
import json
import xml.etree.ElementTree as ET
import requests

# ============ LO QUE TIENES QUE EDITAR ============

# Palabras que te interesan (en minusculas). Si la lista esta vacia, te avisa de TODO.
PALABRAS_CLAVE = ["sony", "iphone", "samsung", "nintendo", "ssd"]

# Palabras que NO quieres ver (opcional)
PALABRAS_EXCLUIDAS = ["funda", "cable"]

# Fuentes de ofertas (feeds RSS). Puedes anadir mas lineas.
FEEDS = [
    "https://www.chollometro.com/rss",
    # "https://www.dealabs.com/rss",
]

# ==================================================

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
ARCHIVO_VISTOS = "seen.json"
CABECERAS = {"User-Agent": "Mozilla/5.0 (compatible; BotOfertas/1.0)"}


def cargar_vistos():
    if os.path.exists(ARCHIVO_VISTOS):
        with open(ARCHIVO_VISTOS, "r", encoding="utf-8") as f:
            return json.load(f)
    return None  # None = primera ejecucion


def guardar_vistos(vistos):
    with open(ARCHIVO_VISTOS, "w", encoding="utf-8") as f:
        json.dump(vistos[-3000:], f)


def enviar(texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    r = requests.post(url, data={"chat_id": CHAT_ID, "text": texto}, timeout=20)
    if not r.ok:
        print("Error enviando a Telegram:", r.text)


def leer_feed(url):
    try:
        r = requests.get(url, headers=CABECERAS, timeout=20)
        r.raise_for_status()
        raiz = ET.fromstring(r.content)
    except Exception as e:
        print(f"No se pudo leer {url}: {e}")
        return []
    ofertas = []
    for item in raiz.iter("item"):
        titulo = (item.findtext("title") or "").strip()
        enlace = (item.findtext("link") or "").strip()
        if titulo and enlace:
            ofertas.append((titulo, enlace))
    return ofertas


def interesa(titulo):
    t = titulo.lower()
    if any(x in t for x in PALABRAS_EXCLUIDAS):
        return False
    if not PALABRAS_CLAVE:
        return True
    return any(p in t for p in PALABRAS_CLAVE)


def main():
    vistos = cargar_vistos()
    primera_vez = vistos is None
    vistos = vistos or []
    set_vistos = set(vistos)
    nuevas = 0

    for feed in FEEDS:
        for titulo, enlace in leer_feed(feed):
            if enlace in set_vistos:
                continue
            vistos.append(enlace)
            set_vistos.add(enlace)
            # En la primera ejecucion solo memorizamos, para no recibir un aluvion
            if primera_vez:
                continue
            if interesa(titulo):
                enviar(f"🔥 {titulo}\n{enlace}")
                nuevas += 1

    guardar_vistos(vistos)
    if primera_vez:
        enviar("✅ Bot de ofertas activado. Te avisare cuando aparezca algo interesante.")
    print(f"Avisos enviados: {nuevas}")


if __name__ == "__main__":
    main()
