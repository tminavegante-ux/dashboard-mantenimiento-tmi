# ============================================================
#  CONFIGURACIÓN GLOBAL DEL DASHBOARD
# ============================================================
import os

# ---------- RUTA DEL EXCEL (solo para modo escritorio) ----------
RUTA_EXCEL = r"C:\Users\USUARIO\Documents\NAVEGANTE_TMI\OneDrive\TMI_NAVEGANTE_PERSONAL\1-PROYECTO_DASHBOARD\APSS_PYTHON\CONTROL_NEW-MINING_2026 (2).xlsx"

# ---------- LOGO ----------
LOGO_PATH = "tmi2026.png"

# ---------- CACHÉ ----------
CACHE_TTL = 300  # segundos

# ---------- MESES ----------
DICC_MESES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

ABREV_MES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Ago",
    9: "Set", 10: "Oct", 11: "Nov", 12: "Dic",
}

# ---------- HOJAS DEL EXCEL ----------
HOJAS = {
    "equipos": "EQUIPOS",
    "horometros": "HOROMETROS",
    "componentes": "COMPONENTES",
    "neumaticos": "NEUMATICOS",
    "engrase": "ENGRASE",
    "paradas": "PARADAS-M",
}

# ---------- GOOGLE SHEETS (para Streamlit Cloud) ----------
GSHEETS_CONNECTION = "gsheets"   # debe coincidir con [connections.gsheets]
GSHEETS_TTL = 0

# ---------- UMBRALES NEUMÁTICOS ----------
NEUMATICOS = {
    "COCADA_CRITICA": 25,
    "COCADA_MINIMA": 50,
    "DELTA_ROTACION": 8,
    "COCADA_NUEVA_MAX": 100.0,
    "COLOR_ESTADO_HEX": {
        "🟢 OK": ("#48BB78", "#2F855A"),
        "🟡 ATENCIÓN": ("#F6AD55", "#C05621"),
        "🔴 CRÍTICO": ("#F56565", "#C53030"),
        "⚪ SIN DATO": ("#888888", "#555555"),
    },
}

# ---------- UMBRALES COMPONENTES ----------
COMPONENTES = {
    "HORAS_CRITICO": 0,      # <= 0 → crítico
    "HORAS_ATENCION": 500,   # <= 500 → atención
}

# ---------- COLORES DE GRÁFICOS ----------
COLORES = {
    "primario": "#F6AD55",
    "secundario": "#5A6B7D",
    "ok": "#00E676",
    "alerta": "#FFA726",
    "critico": "#FF5252",
    "info": "#00D4FF",
    "teal": "#4FD1C5",
    "azul": "#63B3ED",
    "rosa": "#FC8181",
    "purpura": "#B388FF",
}

TEMPLATE_PLOTLY = "plotly_dark"
