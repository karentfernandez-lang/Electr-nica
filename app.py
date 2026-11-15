import time
from io import BytesIO

import serial
import streamlit as st
import xlsxwriter
from serial.tools import list_ports

GAVETAS = {
    "A1": "Tornillos", "A2": "Tacos Fischer", "A3": "Arandelas",
    "B1": "Tuercas", "B2": "Clavos", "B3": "Rulemanes",
}

st.set_page_config(page_title="SmartPick IA | Arduino Uno", layout="centered")
st.session_state.setdefault("uno", None)
st.session_state.setdefault("buffer", b"")
st.session_state.setdefault("historial", [])
st.session_state.setdefault("confirmacion", "")
st.session_state.setdefault("stock", None)
st.session_state.setdefault("aviso_usb", "")


def conectar(puerto):
    placa = serial.Serial(puerto, 9600, timeout=0.2, write_timeout=1)
    try:
        time.sleep(2.5)
        placa.reset_input_buffer()
        placa.write(b"PING_SMARTPICK\n")
        limite = time.monotonic() + 3
        while time.monotonic() < limite:
            if placa.readline().strip() == b"SMARTPICK_OK":
                placa.timeout = 0
                placa.write(b"STOCK_SMARTPICK\n")
                return placa
        raise serial.SerialException("El puerto abrió, pero el Uno no respondió. Cargá el .ino de este ZIP.")
    except Exception:
        placa.close()
        raise


def leer_stock(mensaje):
    campos = mensaje.split("|")
    if len(campos) == len(GAVETAS) + 1 and campos[0] == "STOCK":
        if all(x.isascii() and x.isdecimal() for x in campos[1:]):
            return tuple(map(int, campos[1:]))
    return None


def excel_stock(stock):
    salida = BytesIO()
    with xlsxwriter.Workbook(salida, {"in_memory": True}) as libro:
        hoja = libro.add_worksheet("Stock")
        cabecera = libro.add_format({"bold": True, "bg_color": "#E1F1EC"})
        hoja.write_row(0, 0, ["Gaveta", "Producto", "Stock restante (unidades)"], cabecera)
        for fila, ((gaveta, producto), unidades) in enumerate(zip(GAVETAS.items(), stock), 1):
            hoja.write_row(fila, 0, [gaveta, producto, unidades])
        hoja.set_column("A:A", 12)
        hoja.set_column("B:B", 22)
        hoja.set_column("C:C", 29)
        hoja.freeze_panes(1, 0)
    return salida.getvalue()


def cerrar_placa(aviso=""):
    placa = st.session_state.uno
    if placa is not None:
        try:
            placa.close()
        except (serial.SerialException, OSError):
            pass
    st.session_state.uno = None
    st.session_state.stock = None
    st.session_state.aviso_usb = aviso


def registrar(mensaje):
    st.session_state.historial = (st.session_state.historial + [mensaje])[-20:]


uno = st.session_state.uno
conectado = uno is not None and uno.is_open
color_ia = "#16a34a" if conectado else "inherit"
st.markdown(f'<h1>SmartPick <span style="color:{color_ia}">IA</span></h1>',
            unsafe_allow_html=True)
st.caption("Preparación de pedidos · Arduino Uno por USB")
puertos = [p.device for p in list_ports.comports()]
with st.sidebar:
    st.header("Arduino Uno")
    if st.session_state.aviso_usb:
        st.warning(st.session_state.aviso_usb)
    if conectado:
        st.success(f"Arduino conectado · {uno.port}")
        if st.button("Desconectar"):
            cerrar_placa()
            st.rerun()
    else:
        if puertos:
            st.warning("Puerto disponible. Elegí el COM del Uno y conectá.")
            puerto = st.selectbox("Puerto USB", puertos)
            if st.button("Conectar"):
                try:
                    st.session_state.uno = conectar(puerto)
                except (serial.SerialException, OSError) as error:
                    st.error(f"No se pudo abrir {puerto}: {error}")
                    st.caption("Cerrá el Monitor Serie del Arduino IDE.")
                else:
                    st.session_state.buffer = b""
                    st.session_state.historial = []
                    st.session_state.confirmacion = ""
                    st.session_state.stock = None
                    st.session_state.aviso_usb = ""
                    st.rerun()
        else:
            st.error("Arduino desconectado. Enchufalo por USB.")
        st.button("Buscar puertos")

st.subheader("Gavetas")
columnas = st.columns(3)
for i, (ubicacion, producto) in enumerate(GAVETAS.items()):
    with columnas[i % 3]:
        with st.container(border=True):
            st.markdown(f"**{ubicacion}**")
            st.write(producto)

with st.form("pedido", clear_on_submit=True):
    pedido = st.text_input("Producto y cantidad", placeholder="Ej.: tacos 5")
    enviar = st.form_submit_button("Enviar pedido", type="primary", disabled=not conectado)

if enviar:
    comando = " ".join(pedido.lower().split())
    datos = (comando + "\n").encode("utf-8")
    if not comando or len(datos) > 64:
        st.warning("Ingresá un pedido corto, por ejemplo: tacos 5.")
    else:
        try:
            uno.write(datos)
            registrar(f"Pedido enviado: {comando}")
        except (serial.SerialException, OSError) as error:
            cerrar_placa(f"No se pudo enviar: {error}")
            st.rerun()


@st.fragment(run_every=1)
def mostrar_estado():
    st.subheader("Estado del pedido")
    placa = st.session_state.uno
    puertos_actuales = [p.device for p in list_ports.comports()]
    if placa is not None and placa.port not in puertos_actuales:
        cerrar_placa("Se perdió la conexión USB.")
        st.rerun()
    if placa is None and sorted(puertos_actuales) != sorted(puertos):
        st.rerun()
    if placa is not None and placa.is_open:
        try:
            st.session_state.buffer += placa.read(placa.in_waiting)
        except (serial.SerialException, OSError):
            cerrar_placa("Se perdió la conexión USB.")
            st.rerun()
        while b"\n" in st.session_state.buffer:
            linea, resto = st.session_state.buffer.split(b"\n", 1)
            st.session_state.buffer = resto
            mensaje = linea.decode("utf-8", errors="replace").strip()
            stock = leer_stock(mensaje)
            if stock is not None:
                st.session_state.stock = stock
                continue
            if mensaje:
                registrar(mensaje)
                if mensaje.startswith("Producto confirmado."):
                    st.session_state.confirmacion = mensaje
        if len(st.session_state.buffer) > 4096:
            st.session_state.buffer = b""
    if st.session_state.historial:
        ultimo = st.session_state.historial[-1]
        if ultimo.startswith(("SIN STOCK", "ERROR", "Producto no existe")):
            st.error(ultimo)
        elif ultimo != st.session_state.confirmacion:
            st.info(ultimo)
    else:
        st.info("Esperando pedido.")
    if st.session_state.confirmacion:
        st.success(f"Último retiro: {st.session_state.confirmacion}")
    if st.session_state.stock is not None:
        stock = st.session_state.stock
        st.subheader("Stock restante")
        st.table([
            {"Gaveta": g, "Producto": p, "Unidades": n}
            for (g, p), n in zip(GAVETAS.items(), stock)
        ])
        st.download_button(
            "Descargar Excel de stock", excel_stock(stock), "Stock_SmartPick.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with st.expander("Historial"):
        for mensaje in reversed(st.session_state.historial):
            st.text(mensaje)


mostrar_estado()
