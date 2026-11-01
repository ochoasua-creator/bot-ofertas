import os
import json
import re
import html
import xml.etree.ElementTree as ET
import requests

# ============ LO QUE TIENES QUE EDITAR ============

# Palabras que te interesan (en minusculas). Si la lista esta vacia, te avisa de TODO.
PALABRAS_CLAVE = ["one plus 15", "tcl c8k", "xiaomi 17", "xiaomi 17 ultra", "smartphones"]

# Palabras que NO quieres ver (opcional)
PALABRAS_EXCLUIDAS = ["funda", "cable"]

# Descuento minimo (en %). Pon 0 para desactivar este filtro.
DESCUENTO_MINIMO = 40

# True  = avisa si coincide una palabra clave O el descuento es suficiente (cualquier categoria).
# False = tienen que cumplirse las dos cosas.
AVISAR_SI_CUMPLE_UNA = True

# Fuentes de ofertas (feeds RSS). Puedes anadir mas lineas.
FEEDS = [
    "https://www.chollometro.com/rss", "https://www.dealabs.com/rss", "https://www.mydealz.de/rss",
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
    PRECIO = r"(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?)\s?€"


def limpiar(texto):
    return html.unescape(re.sub(r"<[^>]+>", " ", texto or ""))


def a_numero(s):
    if "," in s:
        return float(s.replace(".", "").replace(",", "."))
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        return float(s.replace(".", ""))
    return float(s)


def calcular_descuento(titulo, descripcion):
    texto = titulo + " " + descripcion
    candidatos = []

    # Porcentaje escrito: "-45%" o "50% de descuento"
    for m in re.finditer(r"[-−–]\s?(\d{2,3})\s?%", texto):
        candidatos.append(int(m.group(1)))
    for m in re.finditer(r"(\d{2,3})\s?%\s?(?:de\s)?(?:dto|descuento|desc|off|rebaja)", texto, re.I):
        candidatos.append(int(m.group(1)))

    # Precio actual (en el titulo) frente a precio anterior ("antes 59,99€")
    m_actual = re.search(PRECIO, titulo)
    m_antes = re.search(
        r"(?:antes|pvp|precio habitual|precio original|en lugar de|normalmente)\D{0,15}?" + PRECIO,
        texto, re.I)
    if m_actual and m_antes:
        try:
            actual = a_numero(m_actual.group(1))
            antes = a_numero(m_antes.group(1))
            if antes > actual > 0:
                candidatos.append(round((1 - actual / antes) * 100))
        except ValueError:
            pass

    candidatos = [c for c in candidatos if 0 < c <= 100]
    return max(candidatos) if candidatos else None


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
        descripcion = limpiar(item.findtext("description"))
        if titulo and enlace:
            ofertas.append((titulo, enlace, descripcion))
    return ofertas


def main():
    vistos = cargar_vistos()
    primera_vez = vistos is None
    vistos = vistos or []
    set_vistos = set(vistos)
    nuevas = 0

    for feed in FEEDS:
        for titulo, enlace, descripcion in leer_feed(feed):
            if enlace in set_vistos:
                continue
            vistos.append(enlace)
            set_vistos.add(enlace)
            if primera_vez:
                continue

            descuento = calcular_descuento(titulo, descripcion)
            print(f"[descuento: {descuento}] {titulo}")  # para revisar en el registro

            t = titulo.lower()
            if any(x in t for x in PALABRAS_EXCLUIDAS):
                continue

            coincide_palabra = bool(PALABRAS_CLAVE) and any(p in t for p in PALABRAS_CLAVE)
            coincide_descuento = (
                DESCUENTO_MINIMO > 0 and descuento is not None and descuento >= DESCUENTO_MINIMO
            )

            if AVISAR_SI_CUMPLE_UNA:
                avisar = coincide_palabra or coincide_descuento
            else:
                avisar = (not PALABRAS_CLAVE or coincide_palabra) and coincide_descuento

            if avisar:
                etiqueta = f" (-{descuento}%)" if descuento else ""
                enviar(f"🔥 {titulo}{etiqueta}\n{enlace}")
                nuevas += 1

    guardar_vistos(vistos)
    if primera_vez:
        enviar("✅ Bot de ofertas activado. Te avisare cuando aparezca algo interesante.")
    print(f"Avisos enviados: {nuevas}")


if __name__ == "__main__":
    main()
