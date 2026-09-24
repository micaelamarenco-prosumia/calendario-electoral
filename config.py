import os


def _limpiar(valor):
    """Saca espacios, comillas y un 'bot' de mas al principio, por si se copiaron sin querer."""
    if not valor:
        return ""
    valor = valor.strip().strip('"').strip("'").strip()
    if valor.lower().startswith("bot") and ":" in valor:
        valor = valor[3:]
    return valor


# Estos dos valores se cargan en Railway, en la pestana Variables.
# No los escribas aca: el repositorio de GitHub puede ser visible.
TELEGRAM_TOKEN = _limpiar(os.environ.get("TELEGRAM_TOKEN"))
TELEGRAM_CHAT_ID = _limpiar(os.environ.get("TELEGRAM_CHAT_ID"))

INTERVALO_MINUTOS = 60

PROVINCIAS = [
    "Buenos Aires",
    "Ciudad de Buenos Aires",
    "Catamarca",
    "Chaco",
    "Chubut",
    "Cordoba",
    "Corrientes",
    "Entre Rios",
    "Formosa",
    "Jujuy",
    "La Pampa",
    "La Rioja",
    "Mendoza",
    "Misiones",
    "Neuquen",
    "Rio Negro",
    "Salta",
    "San Juan",
    "San Luis",
    "Santa Cruz",
    "Santa Fe",
    "Santiago del Estero",
    "Tierra del Fuego",
    "Tucuman",
]

PALABRAS_CLAVE = [
    "PASO",
    "elecciones 2027",
    "eleccion provincial",
    "elecciones provinciales",
    "desdoblamiento",
    "desdoblar",
    "fecha de elecciones",
    "calendario electoral",
    "eleccion desdoblada",
    "junto con las nacionales",
]
