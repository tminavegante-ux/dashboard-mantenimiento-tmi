# ============================================================
#  NEW-DASHBOARD.py — Punto de entrada
#  Dashboard KPI Mantenimiento — TMI 2026
# ============================================================
import streamlit as st

from config.settings import TEMPLATE_PLOTLY  # noqa: F401 (se usa en tabs)
from core.loader import cargar_datos
from core.transforms import (
    transformar_equipos, transformar_horometros, transformar_componentes,
    transformar_neumaticos, transformar_engrase, transformar_paradas,
)
from ui.sidebar import render_sidebar
from tabs.tab_horometros import render_tab_horometros
from tabs.tab_neumaticos import render_tab_neumaticos
from tabs.tab_componentes import render_tab_componentes
from tabs.tab_engrase import render_tab_engrase
from tabs.tab_kpis import render_tab_kpis

# ---------- Configuración ----------
st.set_page_config(
    page_title="Dashboard KPI Mantenimiento - Marcio",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("CONTROL NEW MING 2026")
st.markdown("---")

# ---------- Carga ----------
(df_eq, df_ho, df_co, df_ne, df_en, df_pa,
 ok, msg) = cargar_datos()

if not ok or df_eq.empty:
    st.error("❌ No se pudo cargar los datos desde el Excel local")
    st.markdown(f"**Detalle Técnico:** `{msg}`")
    st.info("💡 Verifica la ruta del Excel y que tenga las hojas "
            "**EQUIPOS, HOROMETROS, COMPONENTES, NEUMATICOS, ENGRASE y PARADAS-M**.")
    st.stop()

# ---------- Transformaciones ----------
df_eq = transformar_equipos(df_eq)
df_ho = transformar_horometros(df_ho)
df_co = transformar_componentes(df_co)
df_ne = transformar_neumaticos(df_ne)
df_en = transformar_engrase(df_en)
df_pa = transformar_paradas(df_pa)

# ---------- Sidebar ----------
ctx = render_sidebar(df_eq, df_ho)

# ---------- Pestañas ----------
(t1, t2, t3, t4, t5) = st.tabs([
    "⏱️ Horómetros & Flota",
    "🛞 Control de Neumáticos",
    "⚙️ Gestión de Componentes",
    "🛢️ Control de Engrase",
    "📊 KPIs Horómetros & Paradas",
])

with t1:
    render_tab_horometros(ctx, df_eq)
with t2:
    render_tab_neumaticos(ctx, df_ne)
with t3:
    render_tab_componentes(ctx, df_co)
with t4:
    render_tab_engrase(ctx, df_en)
with t5:
    render_tab_kpis(ctx, df_ho, df_pa)

st.caption("Dashboard generado con Streamlit · Plotly · Pandas")