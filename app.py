import time

import serial
import streamlit as st
from serial.tools import list_ports

GAVETAS = {
    "A1": "Tornillos", "A2": "Tacos Fischer", "A3": "Arandelas",
    "B1": "Tuercas", "B2": "Clavos", "B3": "Rulemanes",
}

st.set_page_config(page_title="SmartPick IA | Arduino Uno", layout="centered")
st.title("SmartPick IA")
st.caption("Preparación de pedidos · Arduino Uno por USB")
st.session_state.setdefault("uno", None)
st.session_state.setdefault("buffer", b"")
st.session_state.setdefault("historial", [])
st.session_state.setdefault("confirmacion", "")


def registrar(mensaje):
    st.session_state.historial = (st.session_state.historial + [mensaje])[-20:]


uno = st.session_state.uno
conectado = uno is not None and uno.is_open
with st.sidebar:
    st.header("Arduino Uno")
    if conectado:
        st.success(f"{uno.port} · 9600 baudios")
        if st.button("Desconectar"):
            uno.close()
            st.session_state.uno = None
            st.rerun()
    else:
        puertos = [p.device for p in list_ports.comports()]
        if puertos:
            puerto = st.selectbox("Puerto USB", puertos)
            if st.button("Conectar"):
                try:
                    st.session_state.uno = serial.Serial(
                        puerto, 9600, timeout=0, write_timeout=1
                    )
                except (serial.SerialException, OSError) as error:
                    st.error(f"No se pudo abrir {puerto}: {error}")
                    st.caption("Cerrá el Monitor Serie del Arduino IDE.")
                else:
                    st.session_state.buffer = b""
                    st.session_state.historial = []
                    st.session_state.confirmacion = ""
                    time.sleep(2.5)
                    st.rerun()
        else:
            st.warning("Enchufá el Arduino por USB.")
        st.button("Buscar puertos")

st.subheader("Gavetas")
columnas = st.columns(3)
for i, (ubicacion, producto) in enumerate(GAVETAS.items()):
    with columnas[i % 3]:
        st.markdown(f"**{ubicacion}** · {producto}")

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
            st.error(f"No se pudo enviar: {error}")


@st.fragment(run_every=0.5 if conectado else None)
def mostrar_estado():
    st.subheader("Estado del pedido")
    placa = st.session_state.uno
    if placa is not None and placa.is_open:
        try:
            st.session_state.buffer += placa.read(placa.in_waiting)
        except (serial.SerialException, OSError):
            st.error("Se perdió la conexión USB. Desconectá y volvé a conectar.")
            return
        while b"\n" in st.session_state.buffer:
            linea, resto = st.session_state.buffer.split(b"\n", 1)
            st.session_state.buffer = resto
            mensaje = linea.decode("utf-8", errors="replace").strip()
            if mensaje:
                registrar(mensaje)
                if mensaje.startswith("Producto confirmado."):
                    st.session_state.confirmacion = mensaje
        if len(st.session_state.buffer) > 4096:
            st.session_state.buffer = b""
    if st.session_state.historial:
        ultimo = st.session_state.historial[-1]
        if ultimo.startswith(("SIN STOCK", "Producto no existe")):
            st.error(ultimo)
        elif ultimo != st.session_state.confirmacion:
            st.info(ultimo)
    else:
        st.info("Esperando pedido.")
    if st.session_state.confirmacion:
        st.success(f"Último retiro: {st.session_state.confirmacion}")
    with st.expander("Historial"):
        for mensaje in reversed(st.session_state.historial):
            st.text(mensaje)


mostrar_estado()
