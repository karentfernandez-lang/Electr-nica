import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None


def listar_puertos():
    if list_ports is None:
        return []
    return [puerto.device for puerto in list_ports.comports()]


class ConexionArduino:
    def __init__(self):
        self._serial = None
        self.puerto = None

    @property
    def conectado(self):
        return self._serial is not None and self._serial.is_open

    def conectar(self, puerto, velocidad=9600):
        if serial is None:
            raise RuntimeError("La librería pyserial no está instalada.")
        self.desconectar()
        self._serial = serial.Serial(puerto, velocidad, timeout=0.2)
        self.puerto = puerto
        time.sleep(2)
        self.enviar("RESET")

    def enviar(self, comando):
        if not self.conectado:
            raise RuntimeError("Arduino no está conectado.")
        self._serial.write((comando.strip() + "\n").encode("utf-8"))
        self._serial.flush()

    def leer(self):
        if not self.conectado or self._serial.in_waiting == 0:
            return ""
        return self._serial.readline().decode("utf-8", errors="ignore").strip()

    def desconectar(self):
        if self._serial is not None:
            try:
                self._serial.close()
            finally:
                self._serial = None
                self.puerto = None

