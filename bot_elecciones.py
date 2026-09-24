import time
import json
import os
import urllib.parse
import feedparser
import requests

from config import (
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID,
    PROVINCIAS,
    PALABRAS_CLAVE,
    INTERVALO_MINUTOS,
)

ARCHIVO_ENVIADOS = "enviados.json"


def cargar_enviados():
    if os.path.exists(ARCHIVO_ENVIADOS):
        with open(ARCHIVO_ENVIADOS, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def guardar_enviados(enviados):
    with open(ARCHIVO_ENVIADOS, "w", encoding="utf-8") as f:
        json.dump(list(enviados), f)


def armar_query(provincia):
    palabras = " OR ".join(f'"{p}"' for p in PALABRAS_CLAVE)
    return f"{provincia} elecciones 2027 ({palabras})"


def buscar_noticias(provincia):
    query = armar_query(provincia)
    url_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={url_query}&hl=es-419&gl=AR&ceid=AR:es-419"
    feed = feedparser.parse(url)
    return feed.entries


def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    respuesta = requests.post(url, data=payload, timeout=15)
    if not respuesta.ok:
        print("Error enviando a Telegram:", respuesta.text)


def revisar_todas_las_provincias(enviados):
    for provincia in PROVINCIAS:
        try:
            entradas = buscar_noticias(provincia)
        except Exception as error:
            print(f"Error buscando noticias de {provincia}: {error}")
            continue

        for entrada in entradas:
            enlace = entrada.get("link")
            if not enlace or enlace in enviados:
                continue

            titulo = entrada.get("title", "")
            fuente = entrada.get("source", {}).get("title", "")
            texto_completo = f"{titulo} {fuente}".lower()

            if not any(clave.lower() in texto_completo for clave in PALABRAS_CLAVE):
                continue

            mensaje = (
                f"<b>{provincia}</b>\n"
                f"{titulo}\n"
                f"Fuente: {fuente}\n"
                f"{enlace}"
            )
            enviar_telegram(mensaje)
            enviados.add(enlace)
            time.sleep(1)

    guardar_enviados(enviados)


def main():
    enviados = cargar_enviados()
    print("Bot de alertas electorales iniciado.")
    while True:
        print("Revisando novedades...")
        revisar_todas_las_provincias(enviados)
        time.sleep(INTERVALO_MINUTOS * 60)


if __name__ == "__main__":
    main()