#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Adafruit_NeoPixel.h>

const int PIN_NEOPIXEL = 6;
const int CANTIDAD_LED = 11;
const int PIN_BOTON = 2;
const int PIN_PIEZO = 9;

LiquidCrystal_I2C lcd(0x27, 16, 2);
Adafruit_NeoPixel tira(CANTIDAD_LED, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

String comando = "";
String ubicacionActiva = "";
String skuActivo = "";
int cantidadActiva = 0;
bool ordenActiva = false;

void setup() {
  Serial.begin(9600);
  pinMode(PIN_BOTON, INPUT_PULLUP);
  pinMode(PIN_PIEZO, OUTPUT);

  tira.begin();
  tira.setBrightness(45);
  apagarLuces();

  lcd.init();
  lcd.backlight();
  mostrarEspera();
  Serial.println("SMARTPICK_READY");
}

void loop() {
  if (Serial.available() > 0) {
    comando = Serial.readStringUntil('\n');
    comando.trim();
    procesarComando(comando);
  }

  if (ordenActiva && digitalRead(PIN_BOTON) == LOW) {
    delay(40);
    if (digitalRead(PIN_BOTON) == LOW) {
      Serial.print("CONFIRMED|");
      Serial.print(ubicacionActiva);
      Serial.print("|");
      Serial.print(skuActivo);
      Serial.print("|");
      Serial.println(cantidadActiva);
      ordenActiva = false;
      apagarLuces();
      mostrarEspera();
      while (digitalRead(PIN_BOTON) == LOW) delay(10);
    }
  }
}

void procesarComando(String texto) {
  if (texto.startsWith("PICK|")) {
    String ubicacion = obtenerCampo(texto, '|', 1);
    String sku = obtenerCampo(texto, '|', 2);
    int cantidad = obtenerCampo(texto, '|', 3).toInt();
    activarUbicacion(ubicacion, sku, cantidad);
  } else if (texto.startsWith("ERROR|")) {
    activarError();
  } else if (texto == "RESET" || texto == "CANCEL" || texto.startsWith("CONFIRM|")) {
    ordenActiva = false;
    apagarLuces();
    noTone(PIN_PIEZO);
    mostrarEspera();
  }
}

void activarUbicacion(String ubicacion, String sku, int cantidad) {
  int ledFila = ubicacion.charAt(0) == 'A' ? 0 : 1;
  int columna = ubicacion.substring(1).toInt();
  int ledColumna = columna + 1;
  int ledProducto = 5;

  if (ubicacion == "A1") ledProducto = 5;
  else if (ubicacion == "A2") ledProducto = 6;
  else if (ubicacion == "A3") ledProducto = 7;
  else if (ubicacion == "B1") ledProducto = 8;
  else if (ubicacion == "B2") ledProducto = 9;
  else if (ubicacion == "B3") ledProducto = 10;
  else {
    activarError();
    return;
  }

  apagarLuces();
  uint32_t verde = tira.Color(0, 220, 95);
  tira.setPixelColor(ledFila, verde);
  tira.setPixelColor(ledColumna, verde);
  tira.setPixelColor(ledProducto, verde);
  tira.show();

  ubicacionActiva = ubicacion;
  skuActivo = sku;
  cantidadActiva = cantidad;
  ordenActiva = true;

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("UBICACION ");
  lcd.print(ubicacion);
  lcd.setCursor(0, 1);
  lcd.print("RETIRAR: ");
  lcd.print(cantidad);
}

void activarError() {
  ordenActiva = false;
  uint32_t rojo = tira.Color(255, 0, 20);
  for (int i = 0; i < CANTIDAD_LED; i++) tira.setPixelColor(i, rojo);
  tira.show();
  tone(PIN_PIEZO, 1000, 900);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("ERROR DE PEDIDO");
  lcd.setCursor(0, 1);
  lcd.print("REVISAR CODIGO");
}

void apagarLuces() {
  tira.clear();
  tira.show();
}

void mostrarEspera() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("SMARTPICK LISTO");
  lcd.setCursor(0, 1);
  lcd.print("ESPERANDO...");
}

String obtenerCampo(String datos, char separador, int indice) {
  int campo = 0;
  int inicio = 0;
  for (int i = 0; i <= datos.length(); i++) {
    if (i == datos.length() || datos.charAt(i) == separador) {
      if (campo == indice) return datos.substring(inicio, i);
      campo++;
      inicio = i + 1;
    }
  }
  return "";
}

