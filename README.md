# SmartPick AI

Prototipo de un sistema Pick to Light asistido por inteligencia artificial para depósitos de repuestos o ferreterías.

## Funciones

- El operario solicita un producto usando lenguaje natural.
- La aplicación identifica producto y cantidad.
- Consulta SKU, stock y ubicación.
- Señala fila, columna y ubicación exacta.
- Genera un comando para Arduino.
- Arduino controla NeoPixel, LCD, piezo y pulsador.
- Registra operaciones y permite exportar el historial.
- Funciona en modo simulación sin Arduino.
- Puede usar una API de IA externa o continuar con interpretación local si no hay internet.

## Ejecutar en la computadora

1. Instalar Python 3.10 o superior.
2. Abrir una terminal dentro de esta carpeta.
3. Instalar las librerías:

```bash
pip install -r requirements.txt
```

4. Ejecutar:

```bash
streamlit run app.py
```

5. Abrir la dirección indicada por Streamlit, normalmente `http://localhost:8501`.

## Conectar Arduino

1. Instalar en Arduino IDE las librerías `Adafruit NeoPixel` y `LiquidCrystal I2C`.
2. Abrir `codigo_arduino/smartpick.ino`.
3. Cargar el programa al Arduino UNO.
4. Cerrar el Monitor Serial del Arduino IDE.
5. Ejecutar Streamlit y seleccionar el puerto correspondiente.
6. Presionar **Conectar Arduino**.

## Activar IA externa

La aplicación funciona sin una clave mediante interpretación local. Para utilizar un modelo externo:

1. Copiar `.streamlit/secrets.example.toml` como `.streamlit/secrets.toml`.
2. Colocar la clave en `OPENAI_API_KEY`.
3. No subir `secrets.toml` a GitHub.

También puede configurarse la variable de entorno `OPENAI_API_KEY` y, opcionalmente, `OPENAI_MODEL`.

## Publicar en Streamlit Community Cloud

Subir la carpeta a un repositorio de GitHub y seleccionar `app.py` como archivo principal. La versión publicada funciona en modo simulación. Para comunicarse con un Arduino por USB, ejecutar la aplicación localmente en la computadora conectada a la placa.

## Protocolo de comunicación

Ejemplo de orden enviada a Arduino:

```text
PICK|B2|202|3
```

Significa: ubicación B2, SKU 202, retirar 3 unidades.

