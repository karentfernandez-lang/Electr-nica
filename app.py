import time
from datetime import datetime
from io import BytesIO
from html import escape

import serial
import streamlit as st
import xlsxwriter
from serial.tools import list_ports
from panel_pedido import GAVETAS, Panel, actualizar, identificar, lcd

st.set_page_config(page_title="SmartPick IA | Arduino Uno", layout="centered")
st.session_state.setdefault("uno", None)
st.session_state.setdefault("buffer", b"")
st.session_state.setdefault("historial", [])
st.session_state.setdefault("confirmacion", "")
st.session_state.setdefault("stock", None)
st.session_state.setdefault("aviso_usb", "")
st.session_state.setdefault("pausa_usb", False)
st.session_state.setdefault("reintentar_usb", 0.0)
st.session_state.setdefault("panel", Panel())
st.session_state.setdefault("solicitud", None)
st.session_state.setdefault("envio_hora", 0.0)


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
        titulo = libro.add_format({"bold": True, "font_size": 18, "font_color": "#FFFFFF", "bg_color": "#153F36", "valign": "vcenter"})
        fecha = libro.add_format({"font_color": "#47665F", "font_size": 10})
        numero = libro.add_format({"num_format": "0", "align": "right"})
        cero = libro.add_format({"bg_color": "#FDE8E6", "font_color": "#982D28", "bold": True})
        hoja.hide_gridlines(2)
        hoja.merge_range("A1:D1", "  SmartPick IA | Inventario por gaveta", titulo)
        hoja.set_row(0, 33)
        hoja.merge_range("A2:D2", "Exportado: " + datetime.now().strftime("%d/%m/%Y %H:%M"), fecha)
        hoja.add_table(3, 0, 3 + len(GAVETAS), 3, {
            "name": "StockSmartPick", "style": "Table Style Medium 4",
            "columns": [{"header": "Gaveta"}, {"header": "Producto"},
                        {"header": "Stock (unidades)", "format": numero}, {"header": "Estado"}],
            "data": [[g, p, n, "Disponible" if n else "Agotado"]
                     for (g, p), n in zip(GAVETAS.items(), stock)],
        })
        hoja.set_column("A:A", 13)
        hoja.set_column("B:B", 24)
        hoja.set_column("C:C", 21)
        hoja.set_column("D:D", 17)
        hoja.set_default_row(21)
        hoja.conditional_format("C5:C10", {"type": "cell", "criteria": "==", "value": 0, "format": cero})
        hoja.freeze_panes(4, 0)
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
    st.session_state.panel = Panel()
    st.session_state.solicitud = None
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
            st.session_state.panel = Panel()
            st.session_state.solicitud = None
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
.sp-lcd {background:#142425;border:7px solid #253b3b;border-radius:16px;padding:1rem 1.3rem;
  color:#b4ff85;font-family:Consolas,monospace;box-shadow:inset 0 0 19px #081113;margin-bottom:1.3rem;}
.sp-lcd strong {display:block;font-size:1.18rem;letter-spacing:.075em;}
.sp-lcd span {font-size:.9rem;}
.sp-rack {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.7rem;padding:.85rem;
  border-radius:16px;background:#d2dcd6;margin-bottom:1.3rem;}
.sp-drawer {padding:.8rem .85rem;min-height:104px;border:3px solid #b3c4ba;border-radius:9px;
  background:#f6f8f4;color:#17332c;box-shadow:inset 0 -7px 0 #e0e9e0;}
.sp-drawer.active {border-color:#15a963;background:#e3fff0;box-shadow:0 0 10px #28c77899,inset 0 -7px #b7ebca;}
.sp-drawer.alert {border-color:#ce3835;background:#ffefed;box-shadow:0 0 10px #ce38355c,inset 0 -7px #f4ceca;}
.sp-code {display:block;font-weight:850;font-size:.82rem;letter-spacing:.14em;}
.sp-stock {display:block;margin-top:.22rem;font-size:.76rem;color:#47665f;}
@media(max-width:560px){.sp-rack{gap:.35rem;padding:.4rem}.sp-drawer{padding:.45rem;font-size:.8rem}}
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
            if st.session_state.panel.modo in ("enviando", "retiro", "agotado"):
                st.warning("Terminá el retiro o el aviso actual en la maqueta antes de enviar otro pedido.")
            else:
                uno.write(datos)
                st.session_state.solicitud = identificar(comando)
                st.session_state.panel = Panel("enviando")
                st.session_state.envio_hora = time.monotonic()
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
                st.session_state.panel, st.session_state.solicitud = actualizar(
                    st.session_state.panel, mensaje, st.session_state.solicitud)
                if mensaje.startswith("Producto confirmado."):
                    st.session_state.confirmacion = mensaje
        if len(st.session_state.buffer) > 4096:
            st.session_state.buffer = b""
    panel = st.session_state.panel
    if panel.modo == "enviando" and time.monotonic() - st.session_state.envio_hora >= 5:
        panel = st.session_state.panel = Panel("error", detalle="Sin respuesta del Arduino; revisá la maqueta")
        # Se conserva la solicitud para una eventual respuesta demorada.
    a, b = lcd(panel, placa is not None and placa.is_open)
    st.markdown(f'<div class="sp-lcd"><strong>{escape(a)}</strong><span>{escape(b)}</span></div>', unsafe_allow_html=True)
    stock_actual = st.session_state.stock
    cajones = []
    for i, (codigo, producto) in enumerate(GAVETAS.items()):
        clase = ""
        if codigo == panel.gaveta:
            clase = "active" if panel.modo == "retiro" else ("alert" if panel.modo in ("insuficiente", "agotado") else "")
        unidades = "Stock sin leer" if stock_actual is None else f"{stock_actual[i]} unidades"
        estado = (" · Retiro pendiente" if clase == "active" else
                  (" · Agotada" if clase == "alert" and panel.modo == "agotado" else
                   (" · Stock insuficiente" if clase == "alert" else "")))
        cajones.append(f'<div class="sp-drawer {clase}"><span class="sp-code">{codigo}</span>{escape(producto)}<span class="sp-stock">{unidades}{estado}</span></div>')
    st.markdown('<div class="sp-rack">' + "".join(cajones) + '</div>', unsafe_allow_html=True)
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
