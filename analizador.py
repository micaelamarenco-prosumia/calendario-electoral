import re

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "setiembre", "octubre",
    "noviembre", "diciembre",
]

_PATRON_FECHA = re.compile(
    r"\b(\d{1,2})\s+de\s+(" + "|".join(MESES) + r")(?:\s+de\s+(\d{4}))?\b"
)

# Verbos de CONFIRMACION (la noticia asegura algo, no solo lo menciona de paso).
# \w* al final de cada raiz cubre las distintas conjugaciones (confirmo/confirmó/confirma/confirmaron...).
_REGEX_CONFIRMACION = re.compile(
    r"confirm\w*|fij\w*|establec\w*|defini\w*|define\w*|ser[aá]\s+el|"
    r"convoc\w*|decret\w*|oficializ\w*|anunci\w*"
)

# Frases que indican trascendido / todavia sin confirmar.
_REGEX_ESPECULACION = re.compile(
    r"podr[ií]a|se\s+evalu\w*|evalu\w*|analiza\w*|estudia\w*|se\s+especula|"
    r"trascendi\w*\s+que|versiones\s+indican|sonar[ií]a|manejan\s+la\s+fecha|"
    r"no\s+descarta\w*|baraja\w*|circula\w*\s+la\s+versi[oó]n"
)

_REGEX_PASO_ELIMINA = re.compile(
    r"elimin\w*\s+la\w*\s+paso|suprim\w*\s+la\w*\s+paso|sin\s+paso|"
    r"no\s+habr\w*\s+paso|derog\w*\s+la\w*\s+paso|quit\w*\s+la\w*\s+paso"
)

_REGEX_PASO_MANTIENE = re.compile(
    r"mantien\w*\s+la\w*\s+paso|mantendr\w*\s+la\w*\s+paso|"
    r"realizar[aá\w]*\s+la\w*\s+paso|habr\w*\s+paso|conserv\w*\s+la\w*\s+paso|"
    r"ratific\w*\s+la\w*\s+paso|seguir[aá\w]*\s+habiendo\s+paso"
)

# Se chequea primero JUNTO (incluye las formas negadas de "desdoblar") y despues SEPARADA,
# asi "no se desdobla" no queda mal clasificado como desdoblamiento.
_REGEX_DESDOBLAMIENTO_JUNTO = re.compile(
    r"junto\s+(con|a)\s+las\s+nacionales|no\s+se\s+desdobl\w*|no\s+desdoblar\w*|"
    r"unificad\w*\s+con\s+las\s+nacionales|misma\s+fecha\s+que\s+las\s+nacionales|"
    r"concurrente\s+con\s+las\s+nacionales|simultane\w*\s+con\s+las\s+nacionales"
)

_REGEX_DESDOBLAMIENTO_SEPARADA = re.compile(
    r"desdobl\w*|no\s+coincidir[aá\w]*\s+con\s+las\s+nacionales|"
    r"separada\s+de\s+las\s+nacionales|fecha\s+propia|elecci[oó]n\w*\s+propia"
)


def detectar_paso(texto_low):
    if _REGEX_PASO_ELIMINA.search(texto_low):
        return "elimina"
    if _REGEX_PASO_MANTIENE.search(texto_low):
        return "mantiene"
    return None


def detectar_fecha_confirmada(texto_low):
    match = _PATRON_FECHA.search(texto_low)
    if not match:
        return None
    if not _REGEX_CONFIRMACION.search(texto_low):
        return None
    dia, mes, anio = match.group(1), match.group(2), match.group(3)
    mes_cap = mes.capitalize()
    if anio:
        return f"{dia} de {mes_cap} de {anio}"
    return f"{dia} de {mes_cap}"


def detectar_mes_tentativo(texto_low, ya_hay_fecha_confirmada):
    if ya_hay_fecha_confirmada:
        return None
    if not _REGEX_ESPECULACION.search(texto_low):
        return None
    for mes in MESES:
        if re.search(rf"\b{mes}\b", texto_low):
            return mes.capitalize()
    return None


def detectar_desdoblamiento(texto_low):
    if _REGEX_DESDOBLAMIENTO_JUNTO.search(texto_low):
        return "junto"
    if _REGEX_DESDOBLAMIENTO_SEPARADA.search(texto_low):
        return "separada"
    return None


def analizar(texto):
    """Analiza el titulo + resumen de una noticia y devuelve solo los campos
    que pudo detectar con confianza (diccionario parcial)."""
    texto_low = texto.lower()
    resultado = {}

    paso = detectar_paso(texto_low)
    if paso:
        resultado["paso"] = paso

    fecha = detectar_fecha_confirmada(texto_low)
    if fecha:
        resultado["fecha_confirmada"] = fecha

    mes = detectar_mes_tentativo(texto_low, fecha)
    if mes:
        resultado["mes_tentativo"] = mes

    desdoblamiento = detectar_desdoblamiento(texto_low)
    if desdoblamiento:
        resultado["desdoblamiento"] = desdoblamiento

    return resultado
