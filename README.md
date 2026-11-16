# SmartPick IA · Arduino Uno

Aplicación local para preparar pedidos por USB. GitHub guarda los archivos;
para controlar el Uno, ejecutá la página en la PC que tiene el Arduino conectado.

1. En Arduino IDE, abrí `Arduino/SmartPick_Uno/SmartPick_Uno.ino`, elegí
   Arduino Uno y su COM, y cargá el sketch. Bibliotecas: Adafruit NeoPixel y
   hd44780 de Bill Perry.
2. Cerrá el Monitor Serie. En Windows, hacé doble clic en
   `ABRIR_SMARTPICK.vbs`. La primera vez instala dependencias en una
   ventana visible (requiere Python 3 e internet); luego abre sin consola.
   Si Windows bloquea el VBS, usá `ABRIR_SMARTPICK.bat`.
3. Si no se abre el navegador, abrí http://127.0.0.1:8501.
   Conectá el Uno por USB: la página busca la placa automáticamente y
   enciende **IA** como una luz verde cuando recibe su respuesta.
   **Desconectar** pausa la búsqueda; **Reanudar búsqueda** la activa de nuevo.
4. Enviá `tuercas 2` y confirmá con el pulsador físico. Probá
   `tuercas 85` (B1 roja y alarma de 4 s) y `martillo 1`
   (barrido rojo por las seis gavetas y alarma de 2 s).
5. Descargá el Excel de la página antes de reiniciar: el stock del prototipo
   vuelve a los valores iniciales al reiniciarse el Uno.

Al retirar la última unidad, el piezo suena 2 s y el aviso visual dura hasta
10 s. El pulsador permite cerrarlo antes.

Para subir el proyecto a GitHub, extraé el ZIP y subí el contenido de la
carpeta, manteniendo el árbol `Arduino/SmartPick_Uno/`.
# Panel visual y exportación

- La LCD virtual y el gabinete muestran el estado del pedido. La gaveta se ilumina en verde cuando el Arduino acepta el pedido y se apaga al confirmar el retiro. El borde rojo distingue stock insuficiente o agotamiento.
- El archivo Excel es una captura del inventario informado por el Arduino. Exportarlo no guarda ni restaura el saldo de la placa.
- Para actualizar una instalación existente, copiá juntos `app.py` y `panel_pedido.py`. El sketch no cambia respecto de la versión de tema claro.

