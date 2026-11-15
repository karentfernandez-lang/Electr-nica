# SmartPick IA · Arduino Uno

Aplicación local para preparar pedidos por USB. GitHub guarda los archivos;
para controlar el Uno, ejecutá la página en la PC que tiene el Arduino conectado.

1. En Arduino IDE, abrí `Arduino/SmartPick_Uno/SmartPick_Uno.ino`, elegí
   Arduino Uno y su COM, y cargá el sketch. Bibliotecas: Adafruit NeoPixel y
   hd44780 de Bill Perry.
2. Cerrá el Monitor Serie. En Windows, ejecutá `ABRIR_SMARTPICK.bat`
   con Python 3 instalado. El primer arranque puede necesitar internet.
3. Abrí la dirección local que indica el lanzador, elegí el COM del Uno y hacé
   clic en **Conectar**. Solo las letras **IA** del título pasan a verde
   después de que la placa responde.
4. Enviá `tuercas 2` y confirmá con el pulsador físico. Probá
   `tuercas 85` (B1 roja y alarma de 4 s) y `martillo 1`
   (barrido rojo por las seis gavetas y alarma de 2 s).
5. Descargá el Excel de la página antes de reiniciar: el stock del prototipo
   vuelve a los valores iniciales al reiniciarse el Uno.

Para subir el proyecto a GitHub, extraé el ZIP y subí el contenido de la
carpeta, manteniendo el árbol `Arduino/SmartPick_Uno/`.
