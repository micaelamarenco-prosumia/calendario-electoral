import time
import json
import os
import sys
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


def verificar_configuracion():
    """Revisa el token y el chat id antes de empezar, y avisa claro en los logs si algo falla."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        faltante = "TELEGRAM_TOKEN" if not TELEGRAM_TOKEN else "TELEGRAM_CHAT_ID"
        print(f"ERROR: falta la variable {faltante} en Railway (pestana Variables).")
        variables_telegram = sorted(
            k for k in os.environ if "TELEGRAM" in k.upper()
        )
        if variables_telegram:
            print("Variables con 'TELEGRAM' en el nombre que SI encuentra el proceso:",
                  variables_telegram)
        else:
            print("El proceso no encuentra NINGUNA variable con 'TELEGRAM' en el nombre. "
                  "Esto suele pasar cuando las variables estan cargadas en un servicio o "
                  "environment distinto al que esta corriendo este deploy.")
        sys.exit(1)

    try:
        r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe", timeout=15)
    except Exception as error:
        print("ERROR: no se pudo conectar con Telegram:", error)
        sys.exit(1)

    if not r.ok:
        print("ERROR: Telegram no reconoce el token. Volve a copiarlo desde @BotFather "
              "(/mybots > tu bot > API Token) y pegalo en la variable TELEGRAM_TOKEN.")
        print(f"(El token cargado tiene {len(TELEGRAM_TOKEN)} caracteres; "
              f"empieza con {TELEGRAM_TOKEN[:4]}...)")
        sys.exit(1)

    nombre = r.json().get("result", {}).get("username", "")
    print(f"Token OK: conectado como @{nombre}")


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


def escapar_html(texto):
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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
        return False
    return True


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
                f"<b>{escapar_html(provincia)}</b>\n"
                f"{escapar_html(titulo)}\n"
                f"Fuente: {escapar_html(fuente)}\n"
                f"{enlace}"
            )
            if enviar_telegram(mensaje):
                enviados.add(enlace)
            time.sleep(1)

    guardar_enviados(enviados)


def main():
    verificar_configuracion()
    enviar_telegram("Bot de alertas electorales iniciado. Voy a avisarte cuando haya novedades.")
    enviados = cargar_enviados()
    print("Bot de alertas electorales iniciado.")
    while True:
        print("Revisando novedades...")
        revisar_todas_las_provincias(enviados)
        print(f"Listo. Proxima revision en {INTERVALO_MINUTOS} minutos.")
        time.sleep(INTERVALO_MINUTOS * 60)


if __name__ == "__main__":
    main()
