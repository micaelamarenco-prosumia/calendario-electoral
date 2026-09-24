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
from analizador import analizar

ARCHIVO_VISTOS = "vistos.json"
ARCHIVO_ESTADO = "estado_provincias.json"

ETIQUETAS_CAMPO = {
    "paso": "PASO",
    "fecha_confirmada": "Fecha confirmada",
    "mes_tentativo": "Mes tentativo (sin confirmar)",
    "desdoblamiento": "Desdoblamiento",
}

VALORES_LEGIBLES = {
    ("paso", "elimina"): "Se eliminan",
    ("paso", "mantiene"): "Se mantienen",
    ("desdoblamiento", "separada"): "Elección separada de las nacionales",
    ("desdoblamiento", "junto"): "Junto con las elecciones nacionales",
}


def verificar_configuracion():
    """Revisa el token y el chat id antes de empezar, y avisa claro en los logs si algo falla."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        faltante = "TELEGRAM_TOKEN" if not TELEGRAM_TOKEN else "TELEGRAM_CHAT_ID"
        print(f"ERROR: falta la variable {faltante} en Railway (pestana Variables).")
        variables_telegram = sorted(k for k in os.environ if "TELEGRAM" in k.upper())
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


def cargar_json(ruta, default):
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def guardar_json(ruta, datos):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def plantilla_estado():
    return {
        "paso": None,
        "fecha_confirmada": None,
        "mes_tentativo": None,
        "desdoblamiento": None,
        "fuente": None,
    }


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


def formatear_valor(campo, valor):
    return VALORES_LEGIBLES.get((campo, valor), valor)


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


def revisar_todas_las_provincias(vistos, estado):
    """Busca noticias nuevas, las analiza, actualiza el estado por provincia
    y devuelve la lista de cambios detectados en esta pasada."""
    cambios = []

    for provincia in PROVINCIAS:
        try:
            entradas = buscar_noticias(provincia)
        except Exception as error:
            print(f"Error buscando noticias de {provincia}: {error}")
            continue

        for entrada in entradas:
            enlace = entrada.get("link")
            if not enlace or enlace in vistos:
                continue

            titulo = entrada.get("title", "")
            resumen = entrada.get("summary", "")
            texto_completo = f"{titulo} {resumen}"
            texto_low = texto_completo.lower()

            # Primer filtro grueso: que la nota toque alguno de los temas que nos interesan.
            if not any(clave.lower() in texto_low for clave in PALABRAS_CLAVE):
                vistos.add(enlace)
                continue

            vistos.add(enlace)
            detectado = analizar(texto_completo)
            if not detectado:
                continue

            actual = estado.setdefault(provincia, plantilla_estado())
            cambios_provincia = {}
            for campo, valor_nuevo in detectado.items():
                if actual.get(campo) != valor_nuevo:
                    cambios_provincia[campo] = (actual.get(campo), valor_nuevo)
                    actual[campo] = valor_nuevo

            if not cambios_provincia:
                continue

            # Si ahora hay fecha confirmada, el "mes tentativo" deja de ser relevante.
            if "fecha_confirmada" in cambios_provincia and actual.get("mes_tentativo"):
                actual["mes_tentativo"] = None

            actual["fuente"] = enlace
            cambios.append((provincia, cambios_provincia, enlace))

    guardar_json(ARCHIVO_ESTADO, estado)
    guardar_json(ARCHIVO_VISTOS, list(vistos))
    return cambios


def armar_mensajes(cambios):
    """Arma uno o varios mensajes de Telegram (por si son muchos cambios y
    superan el limite de caracteres) con los cambios detectados."""
    bloques = []
    for provincia, cambios_provincia, enlace in cambios:
        lineas = [f"<b>{escapar_html(provincia)}</b>"]
        for campo, (viejo, nuevo) in cambios_provincia.items():
            etiqueta = ETIQUETAS_CAMPO.get(campo, campo)
            lineas.append(f"{etiqueta}: {formatear_valor(campo, nuevo)}")
        lineas.append(f"Fuente: {enlace}")
        bloques.append("\n".join(lineas))

    mensajes = []
    actual = "📋 <b>Novedades electorales</b>\n\n"
    limite = 3500
    for bloque in bloques:
        candidato = actual + bloque + "\n\n"
        if len(candidato) > limite and actual.strip():
            mensajes.append(actual.strip())
            actual = bloque + "\n\n"
        else:
            actual = candidato
    if actual.strip():
        mensajes.append(actual.strip())
    return mensajes


def main():
    verificar_configuracion()
    vistos = set(cargar_json(ARCHIVO_VISTOS, []))
    estado = cargar_json(ARCHIVO_ESTADO, {})

    enviar_telegram(
        "Bot de alertas electorales iniciado. Te voy a escribir solo cuando "
        "detecte novedades sobre PASO, fecha o desdoblamiento en alguna provincia."
    )
    print("Bot de alertas electorales iniciado.")

    while True:
        print("Revisando novedades...")
        cambios = revisar_todas_las_provincias(vistos, estado)

        if cambios:
            print(f"Se detectaron cambios en {len(cambios)} provincia(s). Enviando resumen...")
            for mensaje in armar_mensajes(cambios):
                enviar_telegram(mensaje)
                time.sleep(1)
        else:
            print("Sin novedades en esta vuelta.")

        print(f"Listo. Proxima revision en {INTERVALO_MINUTOS} minutos.")
        time.sleep(INTERVALO_MINUTOS * 60)


if __name__ == "__main__":
    main()
