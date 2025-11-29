import requests

TOKEN = "0dec077871e37f77d82b9c01c87ae8a5d2254b8f981e53f08806612d98ef5acd"
BANXICO_URL = "https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF43718/datos/oportuno"

def obtener_tipo_cambio_banxico():
    url = f"{BANXICO_URL}?token={TOKEN}"
    r = requests.get(url)

    if r.status_code != 200:
        return None

    data = r.json()
    
    try:
        dato = data["bmx"]["series"][0]["datos"][0]
        return float(dato["dato"])
    except:
        return None