import os
from datetime import datetime

import pandas as pd
import streamlit as st

from asistente import interpretar_solicitud
from conexion_arduino import ConexionArduino, listar_puertos


st.set_page_config(
    page_title="SmartPick AI",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

tema = st.sidebar.radio(
    "Apariencia",
    ["Claro", "Oscuro"],
    index=0,
    horizontal=True,
    help="Cambia solamente la apariencia de la aplicación.",
)

st.markdown(
    """
    <style>
    .stApp {background: #08110f; color: #f2f7f5;}
    [data-testid="stSidebar"] {background: #101b18; border-right: 1px solid #253b34;}
    .block-container {max-width: 1450px; padding-top: 1.5rem;}
    h1, h2, h3 {letter-spacing: -0.03em;}
    .hero {padding: 1.1rem 1.3rem; border: 1px solid #25483c; border-radius: 18px;
           background: linear-gradient(120deg, #12251f, #0d1916); margin-bottom: 1rem;}
    .hero h1 {margin: 0; font-size: 2rem;}
    .hero b {color: #59eca0;}
    .hero p {color: #9bb0a9; margin: .25rem 0 0;}
    .status {display:inline-block; padding:.3rem .65rem; border-radius:999px;
             background:#163326; color:#63efa8; font-size:.75rem; font-weight:700;}
    .rack-title {color:#91a79f; font-size:.75rem; text-transform:uppercase; letter-spacing:.12em;}
    .bin {border:1px solid #30463f; border-radius:12px; padding:1rem; min-height:112px;
          background:linear-gradient(145deg,#192721,#101916); margin-bottom:.8rem;}
    .bin.active {border:2px solid #59eca0; box-shadow:0 0 25px rgba(89,236,160,.22);}
    .bin.error {border:2px solid #ff6575; box-shadow:0 0 22px rgba(255,101,117,.2);}
    .led {height:9px; width:9px; border-radius:50%; background:#41544e; float:right;}
    .active .led {background:#59eca0; box-shadow:0 0 14px #59eca0;}
    .error .led {background:#ff6575; box-shadow:0 0 14px #ff6575;}
    .location {font-size:1.05rem; font-weight:800; color:#dceae5;}
    .product {font-size:.87rem; font-weight:700; margin-top:1.3rem;}
    .stock {font-size:.72rem; color:#8ea29b;}
    .lcd {background:#a6d597; color:#17341f; border:6px solid #263b34; border-radius:10px;
          padding:1rem; font:700 1.05rem/1.45 monospace; letter-spacing:.09em;
          box-shadow:inset 0 0 20px rgba(23,52,31,.35); margin:.5rem 0 1rem;}
    .order {padding:1rem; border-radius:12px; border:1px solid #2a443a; background:#111e1a;}
    .command {font-family:monospace; color:#82dcff; background:#07100e; padding:.4rem .6rem;
              border-radius:7px; overflow-wrap:anywhere;}
    div[data-testid="stMetric"] {background:#111e1a; border:1px solid #263d35; padding:.8rem;
                                 border-radius:12px;}
    </style>
    """,
    unsafe_allow_html=True,
)

if tema == "Claro":
    st.markdown(
        """
        <style>
        .stApp {background:#f4f7f5; color:#17231f;}
        [data-testid="stSidebar"] {background:#eaf1ed; border-right:1px solid #c9d8d1;}
        .hero {border-color:#bfd8cc; background:linear-gradient(120deg,#ffffff,#e6f4ed);}
        .hero p, .rack-title, .stock {color:#647970;}
        .hero h1, .product, h1, h2, h3 {color:#16251f;}
        .status {background:#d9f7e8; color:#087442;}
        .bin {border-color:#c7d6d0; background:linear-gradient(145deg,#ffffff,#edf3f0);
              box-shadow:0 6px 16px rgba(28,59,47,.05);}
        .location {color:#203a30;}
        .led {background:#a9b9b2;}
        .order {border-color:#c6d9d0; background:#ffffff;}
        .command {color:#075f82; background:#e6f3f8;}
        div[data-testid="stMetric"] {background:#ffffff; border-color:#c9d9d2;}
        div[data-testid="stChatMessage"] {background:#ffffff; border:1px solid #d7e2dd;
                                           border-radius:12px;}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def cargar_catalogo():
    return pd.read_csv("catalogo.csv", dtype={"sku": str})


def iniciar_estado():
    if "catalogo" not in st.session_state:
        st.session_state.catalogo = cargar_catalogo()
    if "orden" not in st.session_state:
        st.session_state.orden = None
    if "error" not in st.session_state:
        st.session_state.error = None
    if "historial" not in st.session_state:
        st.session_state.historial = []
    if "mensajes" not in st.session_state:
        st.session_state.mensajes = [
            {"role": "assistant", "content": "Hola. Decime qué producto necesitás y cuántas unidades."}
        ]
    if "arduino" not in st.session_state:
        st.session_state.arduino = ConexionArduino()


def registrar(evento, detalle):
    st.session_state.historial.insert(
        0,
        {
            "hora": datetime.now().strftime("%H:%M:%S"),
            "evento": evento,
            "detalle": detalle,
        },
    )


def enviar_arduino(comando):
    if st.session_state.arduino.conectado:
        try:
            st.session_state.arduino.enviar(comando)
            return True
        except Exception as exc:
            registrar("Error de conexión", str(exc))
            st.session_state.arduino.desconectar()
    return False


def activar_error(mensaje):
    st.session_state.orden = None
    st.session_state.error = mensaje
    enviar_arduino("ERROR|BUZZER|RED")
    registrar("Solicitud rechazada", mensaje)


def procesar_pedido(texto):
    st.session_state.error = None
    api_key = ""
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        api_key = ""
    api_key = api_key or os.getenv("OPENAI_API_KEY", "")

    resultado = interpretar_solicitud(
        texto,
        st.session_state.catalogo,
        api_key=api_key,
        modelo=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )

    if not resultado["encontrado"]:
        mensaje = resultado.get("mensaje", "No pude identificar el producto.")
        activar_error(mensaje)
        return mensaje, True

    producto = st.session_state.catalogo[
        st.session_state.catalogo["sku"] == str(resultado["sku"])
    ].iloc[0]
    cantidad = int(resultado["cantidad"])

    if cantidad <= 0:
        mensaje = "La cantidad debe ser mayor que cero."
        activar_error(mensaje)
        return mensaje, True
    if cantidad > int(producto["stock"]):
        mensaje = f"Stock insuficiente. Hay {int(producto['stock'])} unidades de {producto['producto']}."
        activar_error(mensaje)
        return mensaje, True

    comando = f"PICK|{producto['ubicacion']}|{producto['sku']}|{cantidad}"
    st.session_state.orden = {
        "sku": str(producto["sku"]),
        "producto": producto["producto"],
        "ubicacion": producto["ubicacion"],
        "cantidad": cantidad,
        "stock": int(producto["stock"]),
        "comando": comando,
        "metodo": resultado.get("metodo", "local"),
    }
    enviar_arduino(comando)
    registrar("Orden preparada", f"{cantidad} × {producto['producto']} — {producto['ubicacion']}")
    mensaje = (
        f"Encontré {producto['producto']}. Está en {producto['ubicacion']}. "
        f"Retirá {cantidad} unidad{'es' if cantidad != 1 else ''} y confirmá al terminar."
    )
    return mensaje, False


def confirmar_orden():
    orden = st.session_state.orden
    if not orden:
        return
    mascara = st.session_state.catalogo["sku"] == orden["sku"]
    st.session_state.catalogo.loc[mascara, "stock"] -= orden["cantidad"]
    enviar_arduino(f"CONFIRM|{orden['ubicacion']}|{orden['sku']}|{orden['cantidad']}")
    registrar("Picking confirmado", f"{orden['cantidad']} × {orden['producto']}")
    st.session_state.mensajes.append(
        {
            "role": "assistant",
            "content": f"Retiro confirmado. El stock de {orden['producto']} fue actualizado.",
        }
    )
    st.session_state.orden = None
    st.session_state.error = None


iniciar_estado()

st.markdown(
    """
    <div class="hero">
      <span class="status">● SISTEMA OPERATIVO</span>
      <h1>SmartPick <b>AI</b></h1>
      <p>Asistente inteligente para localizar repuestos y reducir errores de picking.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.divider()
    st.header("1. Conectar Arduino")
    st.caption("Conectá la placa por USB y elegí el puerto que aparezca, por ejemplo COM3.")
    puertos = listar_puertos()
    opciones = ["Modo simulación"] + puertos
    puerto = st.selectbox("Puerto de Arduino", opciones)
    velocidad = st.selectbox("Velocidad", [9600, 115200], index=0)

    if not st.session_state.arduino.conectado:
        if puerto == "Modo simulación":
            st.warning("Arduino no detectado: la aplicación está simulando la estantería.")
        if st.button("🔌 Conectar Arduino", type="primary", use_container_width=True, disabled=puerto == "Modo simulación"):
            try:
                st.session_state.arduino.conectar(puerto, velocidad)
                registrar("Arduino conectado", puerto)
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible conectar: {exc}")
    else:
        st.success(f"Conectado en {st.session_state.arduino.puerto}")
        if st.button("Desconectar", use_container_width=True):
            st.session_state.arduino.desconectar()
            registrar("Arduino desconectado", "Modo simulación")
            st.rerun()

    st.divider()
    st.subheader("2. Estado de la IA")
    clave_configurada = bool(os.getenv("OPENAI_API_KEY", ""))
    try:
        clave_configurada = clave_configurada or bool(st.secrets.get("OPENAI_API_KEY", ""))
    except Exception:
        pass
    if clave_configurada:
        st.success("IA externa configurada")
    else:
        st.info("Interpretación local activa")
        st.caption("La aplicación funciona sin internet. Agregá OPENAI_API_KEY para activar el modelo externo.")

    st.divider()
    if st.button("Restaurar demostración", use_container_width=True):
        st.session_state.catalogo = cargar_catalogo()
        st.session_state.orden = None
        st.session_state.error = None
        st.session_state.historial = []
        st.session_state.mensajes = [
            {"role": "assistant", "content": "Demostración restaurada. ¿Qué producto necesitás?"}
        ]
        enviar_arduino("RESET")
        st.rerun()

col_chat, col_mapa, col_estado = st.columns([1.02, 1.35, 0.8], gap="large")

with col_chat:
    st.subheader("Asistente del operario")
    zona_chat = st.container(height=435)
    with zona_chat:
        for mensaje in st.session_state.mensajes:
            with st.chat_message(mensaje["role"]):
                st.write(mensaje["content"])

    texto = st.chat_input("Ej.: Necesito 3 rulemanes 6204")
    if texto:
        st.session_state.mensajes.append({"role": "user", "content": texto})
        respuesta, es_error = procesar_pedido(texto)
        st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
        st.rerun()

    st.caption("Ejemplos rápidos")
    ej1, ej2, ej3 = st.columns(3)
    ejemplos = [
        (ej1, "3 rulemanes", "Necesito 3 rulemanes 6204"),
        (ej2, "4 fusibles", "Buscame cuatro fusibles de 10 amperios"),
        (ej3, "8 tornillos", "Quiero 8 tornillos M8"),
    ]
    for columna, etiqueta, pedido in ejemplos:
        with columna:
            if st.button(etiqueta, use_container_width=True):
                st.session_state.mensajes.append({"role": "user", "content": pedido})
                respuesta, _ = procesar_pedido(pedido)
                st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
                st.rerun()

with col_mapa:
    st.subheader("Estantería R-01")
    st.markdown('<div class="rack-title">Fila × columna × ubicación exacta</div>', unsafe_allow_html=True)
    catalogo = st.session_state.catalogo
    for fila in ["A", "B"]:
        columnas = st.columns(3)
        for indice, columna in enumerate(columnas, start=1):
            ubicacion = f"{fila}{indice}"
            producto = catalogo[catalogo["ubicacion"] == ubicacion].iloc[0]
            estado = ""
            if st.session_state.orden and st.session_state.orden["ubicacion"] == ubicacion:
                estado = "active"
            elif st.session_state.error:
                estado = "error"
            columna.markdown(
                f"""
                <div class="bin {estado}">
                  <span class="led"></span><div class="location">{ubicacion}</div>
                  <div class="product">{producto['producto']}</div>
                  <div class="stock">SKU {producto['sku']} · Stock {int(producto['stock'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if st.session_state.orden:
        orden = st.session_state.orden
        st.markdown(
            f"""
            <div class="order"><b>Orden activa</b><br>
            {orden['producto']} · Ubicación <b>{orden['ubicacion']}</b><br>
            Retirar <b>{orden['cantidad']} unidades</b><br><br>
            <span class="command">{orden['comando']}</span></div>
            """,
            unsafe_allow_html=True,
        )
        confirmar, cancelar = st.columns([1.5, 1])
        with confirmar:
            if st.button("✓ Confirmar retiro", type="primary", use_container_width=True):
                confirmar_orden()
                st.rerun()
        with cancelar:
            if st.button("Cancelar", use_container_width=True):
                enviar_arduino("CANCEL")
                registrar("Orden cancelada", orden["producto"])
                st.session_state.orden = None
                st.rerun()
    elif st.session_state.error:
        st.error(st.session_state.error)
        if st.button("Limpiar alarma", use_container_width=True):
            enviar_arduino("RESET")
            st.session_state.error = None
            st.rerun()
    else:
        st.info("Esperando una solicitud del operario.")

with col_estado:
    st.subheader("Salida Arduino")
    if st.session_state.orden:
        orden = st.session_state.orden
        linea_1 = f"{orden['ubicacion']} {orden['producto']}"[:16].upper().ljust(16)
        linea_2 = f"RETIRAR: {orden['cantidad']}"[:16].upper().ljust(16)
        comando = orden["comando"]
    elif st.session_state.error:
        linea_1 = "ERROR DE PEDIDO ".ljust(16)
        linea_2 = "PIEZO: ACTIVO  ".ljust(16)
        comando = "ERROR|BUZZER|RED"
    else:
        linea_1 = "SMARTPICK LISTO ".ljust(16)
        linea_2 = "ESPERANDO...    ".ljust(16)
        comando = "IDLE"

    st.markdown(f'<div class="lcd">{linea_1}<br>{linea_2}</div>', unsafe_allow_html=True)
    st.caption("Comando preparado")
    st.code(comando, language=None)

    st.subheader("Indicadores")
    total_stock = int(st.session_state.catalogo["stock"].sum())
    st.metric("Stock registrado", f"{total_stock} u.")
    st.metric("Operaciones", len(st.session_state.historial))
    metodo = "Externa" if st.session_state.orden and st.session_state.orden["metodo"] == "ia" else "Local"
    st.metric("Interpretación", metodo)

st.divider()
st.subheader("Trazabilidad de operaciones")
if st.session_state.historial:
    historial_df = pd.DataFrame(st.session_state.historial)
    st.dataframe(historial_df, use_container_width=True, hide_index=True)
    st.download_button(
        "Descargar historial CSV",
        historial_df.to_csv(index=False).encode("utf-8"),
        "historial_smartpick.csv",
        "text/csv",
    )
else:
    st.caption("Todavía no se registraron operaciones.")

with st.expander("Ver catálogo completo"):
    st.dataframe(st.session_state.catalogo, use_container_width=True, hide_index=True)

