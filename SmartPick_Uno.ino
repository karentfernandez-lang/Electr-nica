#include <Wire.h>
#include <hd44780.h>
#include <hd44780ioClass/hd44780_I2Cexp.h>
#include <Adafruit_NeoPixel.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const byte PIN_BOTON = 2, PIN_LED = 6, PIN_BUZZER = 8;
const unsigned long DURACION_ALARMA = 5000UL;
const unsigned long DURACION_CONFIRMACION = 2000UL;
hd44780_I2Cexp lcd;
Adafruit_NeoPixel tira(60, PIN_LED, NEO_GRB + NEO_KHZ800);

struct Gaveta {
  const char* titulo;
  byte arriba, cantidadArriba, abajo, cantidadAbajo, interior;
  int stock;
};
Gaveta gavetas[] = {
  {"A1 Tornillos",    36, 6, 30, 5, 42, 20},
  {"A2 Taco Fischer", 43, 6, 24, 5, 49,  8},
  {"A3 Arandelas",    50, 6, 18, 5, 56, 20},
  {"B1 Tuercas",      30, 5,  0, 6, 35, 20},
  {"B2 Clavos",       24, 5,  6, 6, 29, 20},
  {"B3 Rulemanes",    18, 5, 12, 6, 23, 20}
};

bool lcdListo = false, alarmaActiva = false, confirmacionActiva = false;
int pendiente = -1, cantidadPendiente = 0;
unsigned long inicioAlarma = 0, inicioConfirmacion = 0, cambioBoton = 0;
bool botonAnterior = HIGH, botonEstable = HIGH;
char entrada[64];
byte largo = 0;
bool lineaLarga = false;

// Mensajes y salidas
void mostrar(const char* primera, const char* segunda) {
  if (!lcdListo) return;
  lcd.clear();
  lcd.setCursor(0, 0); lcd.print(primera);
  lcd.setCursor(0, 1); lcd.print(segunda);
}
void mostrarEspera() { mostrar("Esperando pedido", "Ej: clavos 3"); }
void mostrarPedido() {
  if (pendiente < 0) return;
  char mensaje[17];
  snprintf(mensaje, sizeof(mensaje), "Retirar: %d", cantidadPendiente);
  mostrar(gavetas[pendiente].titulo, mensaje);
}
void detenerAlarma() {
  noTone(PIN_BUZZER);
  alarmaActiva = false;
}
void avisarError(const char* primera, const char* segunda) {
  detenerAlarma();
  tone(PIN_BUZZER, 1000, DURACION_ALARMA);
  inicioAlarma = millis();
  alarmaActiva = true;
  mostrar(primera, segunda);
  Serial.print(primera); Serial.print(' '); Serial.println(segunda);
}
void encenderGaveta(int indice) {
  const Gaveta& g = gavetas[indice];
  uint32_t verde = tira.Color(0, 30, 0);
  tira.clear();
  for (byte i = 0; i < g.cantidadArriba; i++)
    tira.setPixelColor(g.arriba + i, verde);
  for (byte i = 0; i < g.cantidadAbajo; i++)
    tira.setPixelColor(g.abajo + i, verde);
  tira.setPixelColor(g.interior, verde);
  tira.show();
}

// Catálogo y validación de pedidos
int buscar(const char* n) {
  if (!strcmp(n,"a1") || !strcmp(n,"tornillo") ||
      !strcmp(n,"tornillos")) return 0;
  if (!strcmp(n,"a2") || !strcmp(n,"taco") || !strcmp(n,"tacos") ||
      !strcmp(n,"taco fischer") || !strcmp(n,"tacos fischer") ||
      !strcmp(n,"taco fisher") || !strcmp(n,"tacos fisher")) return 1;
  if (!strcmp(n,"a3") || !strcmp(n,"arandela") ||
      !strcmp(n,"arandelas")) return 2;
  if (!strcmp(n,"b1") || !strcmp(n,"tuerca") ||
      !strcmp(n,"tuercas")) return 3;
  if (!strcmp(n,"b2") || !strcmp(n,"clavo") ||
      !strcmp(n,"clavos")) return 4;
  if (!strcmp(n,"b3") || !strcmp(n,"ruleman") ||
      !strcmp(n,"rulemanes")) return 5;
  return -1;
}
void publicarStock() {
  Serial.print(F("STOCK"));
  for (byte i = 0; i < sizeof(gavetas) / sizeof(gavetas[0]); i++) {
    Serial.print('|');
    Serial.print(gavetas[i].stock);
  }
  Serial.println();
}
void procesar(char* texto) {
  while (*texto == ' ') texto++;
  if (!*texto) return;
  if (!strcmp(texto, "PING_SMARTPICK")) {
    Serial.println(F("SMARTPICK_OK"));
    return;
  }
  if (!strcmp(texto, "STOCK_SMARTPICK")) {
    publicarStock();
    return;
  }
  char* fin = texto + strlen(texto);
  while (fin > texto && fin[-1] == ' ') *--fin = '\0';
  for (char* p = texto; *p; p++)
    if (*p >= 'A' && *p <= 'Z') *p += 'a' - 'A';
  int cantidad = 0;
  char* espacio = strrchr(texto, ' ');
  if (espacio) {
    const char* numero = espacio + 1;
    size_t digitos = strspn(numero, "0123456789");
    if (digitos > 0 && numero[digitos] == '\0') {
      if (digitos <= 4) cantidad = atoi(numero);
      *espacio = '\0';
      while (espacio > texto && espacio[-1] == ' ') *--espacio = '\0';
    }
  }
  int indice = buscar(texto);
  if (indice < 0) { avisarError("Producto", "no existe"); return; }
  if (cantidad < 1) {
    Serial.println(F("Indica una cantidad de 1 a 9999. Ej: clavos 3"));
    return;
  }
  if (cantidad > gavetas[indice].stock) {
    char mensaje[17];
    snprintf(mensaje, sizeof(mensaje), "Quedan: %d", gavetas[indice].stock);
    avisarError("SIN STOCK", mensaje);
    return;
  }
  if (pendiente >= 0) {
    Serial.println(F("Confirma primero el retiro con el pulsador."));
    return;
  }
  detenerAlarma();
  confirmacionActiva = false;
  pendiente = indice;
  cantidadPendiente = cantidad;
  encenderGaveta(indice);
  mostrarPedido();
  Serial.println(F("Retira las unidades y presiona el pulsador."));
}

// Entradas y confirmación manual
void leerSerie() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (lineaLarga) Serial.println(F("Pedido demasiado largo."));
      else if (largo > 0) {
        entrada[largo] = '\0';
        procesar(entrada);
      }
      largo = 0;
      lineaLarga = false;
    } else if (!lineaLarga) {
      if (largo < sizeof(entrada) - 1) entrada[largo++] = c;
      else lineaLarga = true;
    }
  }
}
void leerBoton() {
  bool lectura = digitalRead(PIN_BOTON);
  if (lectura != botonAnterior) {
    botonAnterior = lectura;
    cambioBoton = millis();
  }
  if (lectura == botonEstable || millis() - cambioBoton < 30) return;
  botonEstable = lectura;
  if (botonEstable != LOW) return;
  if (pendiente < 0) {
    if (confirmacionActiva) {
      confirmacionActiva = false;
      mostrarEspera();
    }
    return;
  }
  gavetas[pendiente].stock -= cantidadPendiente;
  int quedan = gavetas[pendiente].stock;
  pendiente = -1;
  cantidadPendiente = 0;
  detenerAlarma();
  tira.clear(); tira.show();
  char mensaje[17];
  snprintf(mensaje, sizeof(mensaje), "En stock: %d", quedan);
  mostrar("Confirmado", mensaje);
  inicioConfirmacion = millis();
  confirmacionActiva = true;
  Serial.print(F("Producto confirmado. En stock: "));
  Serial.println(quedan);
  publicarStock();
}

void setup() {
  pinMode(PIN_BOTON, INPUT_PULLUP);
  botonAnterior = botonEstable = digitalRead(PIN_BOTON);
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);
  Serial.begin(9600);
  tira.begin(); tira.clear(); tira.show();
  lcdListo = (lcd.begin(16, 2) == 0);
  if (lcdListo) lcd.backlight();
  mostrarEspera();
}
void loop() {
  leerBoton();
  if (confirmacionActiva &&
      millis() - inicioConfirmacion >= DURACION_CONFIRMACION) {
    confirmacionActiva = false;
    mostrarEspera();
    Serial.println(F("Esperando pedido."));
  }
  leerSerie();
  if (alarmaActiva && millis() - inicioAlarma >= DURACION_ALARMA) {
    detenerAlarma();
    if (pendiente >= 0) mostrarPedido();
    else mostrarEspera();
  }
}
