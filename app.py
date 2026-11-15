import time
from io import BytesIO
from html import escape

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
st.session_state.setdefault("pausa_usb", False)
st.session_state.setdefault("reintentar_usb", 0.0)


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


def puertos_uno(lista):
    compatibles = {0x2341, 0x2A03, 0x1A86, 0x0403, 0x10C4}
    return [
        p.device for p in lista
        if p.vid in compatibles or "arduino" in (p.description or "").lower()
        or p.device.upper() == "COM9"
    ]


dispositivos = list(list_ports.comports())
puertos = [p.device for p in dispositivos]
candidatos = puertos_uno(dispositivos)
if (
    st.session_state.uno is None and candidatos and not st.session_state.pausa_usb
    and time.monotonic() >= st.session_state.reintentar_usb
):
    for puerto in candidatos:
        try:
            st.session_state.uno = conectar(puerto)
        except (serial.SerialException, OSError) as error:
            st.session_state.aviso_usb = f"{puerto}: {error}"
        else:
            st.session_state.buffer = b""
            st.session_state.historial = []
            st.session_state.confirmacion = ""
            st.session_state.aviso_usb = ""
            break
    st.session_state.reintentar_usb = time.monotonic() + 12

uno = st.session_state.uno
conectado = uno is not None and uno.is_open
estado_led = "on" if conectado else "off"
etiqueta = f"En línea · {uno.port}" if conectado else ("En pausa" if st.session_state.pausa_usb else "Buscando Arduino")
st.markdown("""
<style>
.block-container {max-width:960px;padding-top:2.7rem;}
.sp-hero {padding:1.9rem 2rem;background:linear-gradient(125deg,
  color-mix(in srgb, #38b78c 16%, var(--background-color)),var(--secondary-background-color));
  border:1px solid color-mix(in srgb,var(--text-color) 18%,transparent);
  border-radius:22px;margin-bottom:1.7rem;color:var(--text-color);}
.sp-kicker {opacity:.8;font-size:.72rem;font-weight:700;letter-spacing:.22em;}
.sp-brand {font-size:clamp(2rem,6vw,3.6rem);font-weight:850;letter-spacing:-.055em;}
.sp-ia {display:inline-block;font-size:.56em;letter-spacing:.01em;vertical-align:middle;
  color:#a2b5b8;background:#25353b;border:1px solid #486067;border-radius:.45em;padding:.04em .39em;}
.sp-ia.on {color:#d2ffe6;background:#245b40;border-color:#96ffbb;
  text-shadow:0 0 8px #a5ffc5;box-shadow:0 0 16px #74ffac68,inset 0 0 7px #74ffac42;}
.sp-state {font-size:.83rem;opacity:.8;}
.sp-card {padding:.9rem 1rem;margin-bottom:.65rem;min-height:86px;border-radius:13px;
  border:1px solid color-mix(in srgb,var(--text-color) 15%,transparent);
  background:var(--secondary-background-color);color:var(--text-color);}
.sp-code {font-weight:800;font-size:.78rem;letter-spacing:.12em;opacity:.8;}
</style>
""", unsafe_allow_html=True)
st.markdown(
    f'<div class="sp-hero"><div class="sp-kicker">PICK-TO-LIGHT · MÓDULO 01</div>'
    f'<div class="sp-brand">SmartPick <span class="sp-ia {estado_led}">IA</span></div>'
    f'<div class="sp-state">{escape(etiqueta)}</div></div>', unsafe_allow_html=True
)
with st.sidebar:
    st.header("Arduino Uno")
    st.caption("Tema claro por defecto. Para cambiarlo: ⋮ → Settings → Theme.")
    if st.session_state.aviso_usb:
        st.warning(st.session_state.aviso_usb)
    if conectado:
        st.caption(f"Puerto USB · {uno.port}")
        if st.button("Desconectar"):
            cerrar_placa()
            st.session_state.pausa_usb = True
            st.rerun()
    elif st.session_state.pausa_usb:
        if st.button("Reanudar búsqueda"):
            st.session_state.pausa_usb = False
            st.session_state.reintentar_usb = 0.0
            st.rerun()
    else:
        st.caption("Enchufá el Uno por USB y cerrá el Monitor Serie. La conexión es automática.")

st.subheader("Gavetas")
columnas = st.columns(3)
for i, (ubicacion, producto) in enumerate(GAVETAS.items()):
    with columnas[i % 3]:
        st.markdown(
            f'<div class="sp-card"><div class="sp-code">{ubicacion}</div>{producto}</div>',
            unsafe_allow_html=True,
        )

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
        st.session_state.reintentar_usb = 0.0
        st.rerun()
    if (placa is None and candidatos and not st.session_state.pausa_usb
            and time.monotonic() >= st.session_state.reintentar_usb):
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
