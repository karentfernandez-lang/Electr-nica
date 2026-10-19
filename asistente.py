import json
import re
import unicodedata


NUMEROS = {
    "un": 1,
    "uno": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
}


def normalizar(texto):
    texto = str(texto).lower()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(caracter for caracter in texto if unicodedata.category(caracter) != "Mn")


def obtener_cantidad(texto):
    texto_normalizado = normalizar(texto)
    coincidencia = re.search(r"\b(\d+)\b", texto_normalizado)
    if coincidencia:
        return int(coincidencia.group(1))
    for palabra, numero in NUMEROS.items():
        if re.search(rf"\b{palabra}\b", texto_normalizado):
            return numero
    return 1


def interpretar_local(texto, catalogo):
    texto_normalizado = normalizar(texto)
    mejor_producto = None
    mejor_puntaje = 0

    for _, producto in catalogo.iterrows():
        terminos = [
            str(producto["sku"]),
            producto["producto"],
            *str(producto["sinonimos"]).split("|"),
        ]
        puntaje = sum(1 for termino in terminos if normalizar(termino) in texto_normalizado)
        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor_producto = producto

    if mejor_producto is None:
        return {
            "encontrado": False,
            "mensaje": "No pude identificar ese producto en el catálogo. Indicá el nombre, modelo o código.",
            "metodo": "local",
        }

    texto_cantidad = texto_normalizado
    terminos_producto = [
        str(mejor_producto["sku"]),
        mejor_producto["producto"],
        *str(mejor_producto["sinonimos"]).split("|"),
    ]
    # Se retiran modelo, amperaje y nombre del artículo antes de buscar la cantidad.
    # Así, "cuatro fusibles de 10 amperios" se interpreta como 4 y no como 10.
    for termino in sorted(terminos_producto, key=len, reverse=True):
        texto_cantidad = texto_cantidad.replace(normalizar(termino), " ")

    return {
        "encontrado": True,
        "sku": str(mejor_producto["sku"]),
        "cantidad": obtener_cantidad(texto_cantidad),
        "metodo": "local",
    }


def interpretar_con_ia(texto, catalogo, api_key, modelo):
    from openai import OpenAI

    productos = catalogo[["sku", "producto", "sinonimos"]].to_dict(orient="records")
    cliente = OpenAI(api_key=api_key)
    respuesta = cliente.chat.completions.create(
        model=modelo,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Sos el asistente de picking de un depósito. Interpretá la solicitud del operario "
                    "usando exclusivamente el catálogo proporcionado. Respondé solamente un JSON con "
                    "encontrado (boolean), sku (string o null), cantidad (entero positivo) y mensaje. "
                    "No inventes productos. Catálogo: " + json.dumps(productos, ensure_ascii=False)
                ),
            },
            {"role": "user", "content": texto},
        ],
    )
    datos = json.loads(respuesta.choices[0].message.content)
    if datos.get("encontrado") and str(datos.get("sku")) in catalogo["sku"].astype(str).values:
        return {
            "encontrado": True,
            "sku": str(datos["sku"]),
            "cantidad": int(datos.get("cantidad", 1)),
            "mensaje": datos.get("mensaje", "Producto encontrado."),
            "metodo": "ia",
        }
    return {
        "encontrado": False,
        "mensaje": datos.get("mensaje", "La IA no encontró el producto en el catálogo."),
        "metodo": "ia",
    }


def interpretar_solicitud(texto, catalogo, api_key="", modelo="gpt-4o-mini"):
    if api_key:
        try:
            return interpretar_con_ia(texto, catalogo, api_key, modelo)
        except Exception:
            # Si internet o la API fallan, la demostración continúa mediante el intérprete local.
            return interpretar_local(texto, catalogo)
    return interpretar_local(texto, catalogo)

