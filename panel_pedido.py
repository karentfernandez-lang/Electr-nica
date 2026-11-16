from dataclasses import dataclass

GAVETAS = {
    "A1": "Tornillos", "A2": "Tacos Fischer", "A3": "Arandelas",
    "B1": "Tuercas", "B2": "Clavos", "B3": "Rulemanes",
}
ALIAS = {
    "A1": ("tornillo", "tornillos"),
    "A2": ("taco", "tacos", "taco fischer", "tacos fischer", "taco fisher", "tacos fisher"),
    "A3": ("arandela", "arandelas"),
    "B1": ("tuerca", "tuercas"),
    "B2": ("clavo", "clavos"),
    "B3": ("ruleman", "rulemanes"),
}

def identificar(comando):
    nombre, _, cantidad = comando.rpartition(" ")
    return (next((g for g, aliases in ALIAS.items() if nombre == g.lower() or nombre in aliases), ""), cantidad)

@dataclass
class Panel:
    modo: str = "espera"
    gaveta: str = ""
    cantidad: str = ""
    detalle: str = ""

def actualizar(panel, mensaje, solicitud):
    gaveta, cantidad = solicitud or ("", "")
    if mensaje == "Esperando pedido.":
        # Puede llegar el fin de un aviso anterior justo antes de aceptar un pedido.
        return (panel, solicitud) if panel.modo == "enviando" else (Panel(), None)
    if mensaje.startswith("Retira las unidades"):
        return Panel("retiro", gaveta, cantidad), None
    if mensaje.startswith("Producto confirmado."):
        detalle = mensaje.partition("En stock: ")[2].strip()
        modo = "agotado" if detalle == "0" else "confirmado"
        return Panel(modo, panel.gaveta, detalle=detalle), None
    if mensaje.startswith("SIN STOCK"):
        return Panel("insuficiente", gaveta, detalle=mensaje.partition(" - ")[2]), None
    if mensaje.startswith(("ERROR", "Producto no existe")):
        return Panel("error", detalle="Producto no existe"), None
    if mensaje.startswith(("Indica una cantidad", "Pedido demasiado largo")):
        return Panel("error", detalle="Revisá producto y cantidad"), None
    if mensaje.startswith("Pulsa el boton"):
        return Panel("bloqueado", detalle="Cerrá el aviso en la maqueta"), None
    if mensaje.startswith("Confirma primero"):
        return Panel("retiro", panel.gaveta, panel.cantidad), None
    return panel, solicitud

def lcd(panel, conectado):
    if not conectado:
        return "SMARTPICK IA", "Conectá el Arduino por USB"
    if panel.modo == "retiro":
        return (GAVETAS.get(panel.gaveta, "Retiro pendiente"),
                f"Retirar: {panel.cantidad} · Confirmá con el pulsador" if panel.cantidad else "Confirmá con el pulsador")
    if panel.modo == "enviando":
        return "ENVIANDO PEDIDO", "Esperando respuesta del Arduino…"
    if panel.modo in ("agotado", "insuficiente"):
        return "SIN STOCK", "Quedan: 0" if panel.modo == "agotado" else panel.detalle
    if panel.modo == "confirmado":
        return "RETIRO VALIDADO", f"En stock: {panel.detalle}"
    if panel.modo in ("error", "bloqueado"):
        return "AVISO", panel.detalle
    return "SMARTPICK IA", "Esperando pedido"
