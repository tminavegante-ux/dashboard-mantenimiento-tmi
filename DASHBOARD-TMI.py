# ============================================================
#  DASHBOARD DE KPIs - HORÓMETROS & PARADAS (STREAMLIT)
#  Versión final — filtros unificados en sidebar
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO
import traceback

# ============================================================
# 1. CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title="Dashboard Horómetros",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# 2. CSS PERSONALIZADO
# ============================================================
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .kpi-card {
        background: #1A1F2B; border-radius: 12px; padding: 18px 20px;
        border: 1px solid #2A2F3B; box-shadow: 0 0 18px rgba(0,212,255,0.10);
        margin-bottom: 10px;
    }
    .kpi-title { color:#8A93A6; font-size:0.78rem; letter-spacing:1.2px; font-weight:600; }
    .kpi-value { font-size:1.9rem; font-weight:800; margin:4px 0 0 0; }
    .kpi-sub   { color:#6A7385; font-size:0.75rem; }
    section[data-testid="stSidebar"] { background:#131824; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 3. FUNCIONES DE LIMPIEZA
# ============================================================
def limpiar_horas(serie):
    return (
        serie.astype(str)
        .str.replace("H", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
        .replace({"": np.nan, "nan": np.nan, "None": np.nan,
                  "NONE": np.nan, "NaN": np.nan, "-": np.nan})
        .astype(float)
    )

def limpiar_pct(serie):
    return (
        serie.astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
        .replace({"": np.nan, "nan": np.nan, "None": np.nan})
        .astype(float)
    )

# ============================================================
# 4. CARGA CON CACHÉ
# ============================================================
@st.cache_data(show_spinner="📥 Leyendo hoja HOROMETROS...")
def cargar_horometros(archivo_bytes):
    df = pd.read_excel(BytesIO(archivo_bytes), sheet_name="HOROMETROS")
    df.columns = df.columns.str.strip()

    cols_horas = [
        "Horas Programadas", "Horómetro Inicial (Diésel)", "Horómetro Final (Diésel)",
        "Horas Diésel", "Horas Efectivas Trabajadas", "Hr. Parada mecánica",
        "Hr. Parada operativa", "Hr. Inspección", "TOTAL HR PARADA", "TOTAL TIEMPO",
        "Hr. No disponible", "Hr. Disponible", "Hr. Usado", "Hr. No Usado",
        "HR. A AGREGAR O QUITAR POR PARADA OPERATIVA NO REPORTADA",
    ]
    for c in cols_horas:
        if c in df.columns:
            try:
                df[c] = limpiar_horas(df[c])
            except Exception:
                pass

    for c in [c for c in df.columns if "%" in str(c)]:
        try:
            df[c] = limpiar_pct(df[c])
        except Exception:
            pass

    df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
    df["NUMERO SEMANA"] = pd.to_numeric(df["NUMERO SEMANA"], errors="coerce")

    df["AÑO"] = df["Fecha"].dt.year
    df["MES"] = df["Fecha"].dt.month
    df["MES_NOMBRE"] = df["Fecha"].dt.strftime("%B").str.capitalize()
    df["PERIODO_MES"] = df["Fecha"].dt.strftime("%Y-%m")

    return df


@st.cache_data(show_spinner="📥 Leyendo hoja PARADAS-M...")
def cargar_paradas(archivo_bytes):
    dfp = pd.read_excel(BytesIO(archivo_bytes), sheet_name="PARADAS-M")
    dfp.columns = dfp.columns.str.strip()
    dfp["Fecha"] = pd.to_datetime(dfp["Fecha"], dayfirst=True, errors="coerce")
    dfp["Duración"] = limpiar_horas(dfp["Duración"])
    dfp["AÑO"] = dfp["Fecha"].dt.year
    dfp["PERIODO_MES"] = dfp["Fecha"].dt.strftime("%Y-%m")
    return dfp

# ============================================================
# 5. SIDEBAR — CARGA DE ARCHIVO
# ============================================================
with st.sidebar:
    st.title("⛏️ Panel de Control")
    st.markdown("### 📂 Cargar archivo Excel")
    st.caption("Hojas requeridas: **HOROMETROS** y **PARADAS-M**.")

    archivo = st.file_uploader(
        "Selecciona el archivo HOROMETROS.xlsx",
        type=["xlsx", "xls", "xlsm"],
    )

if archivo is None:
    st.markdown(
        """
        <div style='text-align:center; margin-top:15vh;'>
            <h1 style='color:#00D4FF;'>⛏️ Dashboard de KPIs Mineros</h1>
            <p style='color:#8A93A6; font-size:1.1rem;'>
                👈 Carga el archivo <b>HOROMETROS.xlsx</b> desde el panel lateral.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

archivo_bytes = archivo.getvalue()

# ============================================================
# 6. CARGA DE DATOS
# ============================================================
try:
    df = cargar_horometros(archivo_bytes)
except Exception as e:
    st.error(f"❌ No se pudo leer la hoja **HOROMETROS**: {e}")
    st.code(traceback.format_exc())
    st.stop()

try:
    dfp = cargar_paradas(archivo_bytes)
except Exception:
    dfp = pd.DataFrame(columns=["Fecha", "Turno", "Tipo de Parada",
                                "Duración", "Equipo", "Descripción de la falla",
                                "AÑO", "PERIODO_MES"])

# ============================================================
# 7. FILTROS EN SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🔎 Filtros")

    equipos = sorted(df["Código-Equipo"].dropna().unique()) if "Código-Equipo" in df.columns else []
    eq_sel = st.multiselect("Equipo", equipos, default=[],
                            placeholder="Todos los equipos")

    turnos = sorted(df["Turno"].dropna().unique()) if "Turno" in df.columns else []
    turno_sel = st.multiselect("Turno", turnos, default=[],
                               placeholder="Todos los turnos")

    tipos = sorted(df["TIPO DE EQUIPO"].dropna().unique()) if "TIPO DE EQUIPO" in df.columns else []
    tipo_sel = st.multiselect("Tipo de equipo", tipos, default=[],
                              placeholder="Todos los tipos")

    st.markdown("##### 📅 Filtro por período")

    modo = st.radio("Filtrar por:", ["Todo", "Semana", "Mes", "Rango de fechas"],
                    horizontal=False, label_visibility="collapsed")

    semana_sel = []
    mes_sel = []
    rango = None

    if modo == "Semana":
        semanas = sorted(df["NUMERO SEMANA"].dropna().astype(int).unique())
        semana_sel = st.multiselect("Semana(s)", semanas, default=[],
                                    placeholder="Todas las semanas")

    elif modo == "Mes":
        df_meses = (df.dropna(subset=["PERIODO_MES"])
                      .drop_duplicates("PERIODO_MES")[["PERIODO_MES", "MES_NOMBRE", "AÑO"]]
                      .sort_values("PERIODO_MES"))
        opciones_mes = {
            f"{r.PERIODO_MES} · {r.MES_NOMBRE} {int(r.AÑO)}": r.PERIODO_MES
            for r in df_meses.itertuples()
        }
        labels_sel = st.multiselect("Mes(es)", list(opciones_mes.keys()), default=[],
                                    placeholder="Todos los meses")
        mes_sel = [opciones_mes[l] for l in labels_sel]

    elif modo == "Rango de fechas":
        if df["Fecha"].notna().any():
            fmin, fmax = df["Fecha"].min().date(), df["Fecha"].max().date()
            rango = st.date_input("Rango", value=(fmin, fmax),
                                  min_value=fmin, max_value=fmax)

# ============================================================
# 8. APLICAR FILTROS
# ============================================================
dff = df.copy()

if eq_sel:
    dff = dff[dff["Código-Equipo"].isin(eq_sel)]
if turno_sel:
    dff = dff[dff["Turno"].isin(turno_sel)]
if tipo_sel:
    dff = dff[dff["TIPO DE EQUIPO"].isin(tipo_sel)]
if semana_sel:
    dff = dff[dff["NUMERO SEMANA"].isin(semana_sel)]
if mes_sel:
    dff = dff[dff["PERIODO_MES"].isin(mes_sel)]
if isinstance(rango, tuple) and len(rango) == 2:
    dff = dff[(dff["Fecha"] >= pd.to_datetime(rango[0])) &
              (dff["Fecha"] <= pd.to_datetime(rango[1]))]

dfp_f = dfp.copy()
if eq_sel and "Equipo" in dfp_f.columns:
    dfp_f = dfp_f[dfp_f["Equipo"].isin(eq_sel)]
if semana_sel and "Fecha" in dfp_f.columns:
    dfp_f = dfp_f[dfp_f["Fecha"].dt.isocalendar().week.astype("Int64").isin(semana_sel)]
if mes_sel and "PERIODO_MES" in dfp_f.columns:
    dfp_f = dfp_f[dfp_f["PERIODO_MES"].isin(mes_sel)]
if isinstance(rango, tuple) and len(rango) == 2:
    dfp_f = dfp_f[(dfp_f["Fecha"] >= pd.to_datetime(rango[0])) &
                  (dfp_f["Fecha"] <= pd.to_datetime(rango[1]))]

if dff.empty:
    st.warning("⚠️ No hay datos con los filtros seleccionados.")
    st.stop()

# ============================================================
# 9. KPIs GLOBALES — CÁLCULO POR AGREGACIÓN DE HORAS
# ============================================================
def safe_sum(col):
    return dff[col].sum() if col in dff.columns else 0

total_prog = float(safe_sum("Horas Programadas"))
total_efec = float(safe_sum("Horas Efectivas Trabajadas"))
parada_mec = float(safe_sum("Hr. Parada mecánica"))
parada_op  = float(safe_sum("Hr. Parada operativa"))
inspeccion = float(safe_sum("Hr. Inspección"))
n_fallas   = int(safe_sum("#Fallas"))

disp = ((total_prog - parada_mec) / total_prog * 100) if total_prog > 0 else 0.0
util = (total_efec / total_prog * 100) if total_prog > 0 else 0.0

horas_disponibles = total_prog - parada_mec
util_efectiva = (total_efec / horas_disponibles * 100) if horas_disponibles > 0 else 0.0

mtbf = total_efec / n_fallas if n_fallas else 0.0
mttr = parada_mec / n_fallas if n_fallas else 0.0

# ============================================================
# 10. HEADER
# ============================================================
sem_min = int(dff["NUMERO SEMANA"].min()) if dff["NUMERO SEMANA"].notna().any() else 0
sem_max = int(dff["NUMERO SEMANA"].max()) if dff["NUMERO SEMANA"].notna().any() else 0

st.markdown(f"""
<h1 style='color:#00D4FF; margin-bottom:0;'>⛏️ Dashboard de KPIs — Flota Minera</h1>
<p style='color:#8A93A6; margin-top:4px;'>
    📄 <b>{archivo.name}</b> &nbsp;|&nbsp;
    📅 Semanas {sem_min}–{sem_max} &nbsp;|&nbsp;
    🧾 {len(dff):,} registros filtrados de {len(df):,}
</p>
""", unsafe_allow_html=True)

# ============================================================
# 11. FUNCIÓN TARJETA KPI (reutilizable)
# ============================================================
def kpi_card(col, titulo, valor, sub, color):
    col.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-title'>{titulo}</div>
        <div class='kpi-value' style='color:{color};'>{valor}</div>
        <div class='kpi-sub'>{sub}</div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# 12. LAYOUT PLOTLY (reutilizable)
# ============================================================
PLOT = dict(paper_bgcolor="#1A1F2B", plot_bgcolor="#1A1F2B",
            font=dict(color="#E0E0E0", family="Segoe UI"),
            margin=dict(l=40, r=20, t=50, b=40))

# ============================================================
# 13. TARJETAS KPI GLOBALES
# ============================================================
c1, c2, c3, c4 = st.columns(4)
kpi_card(c1, "HORAS EFECTIVAS", f"{total_efec:,.1f} H", "Total flota", "#00E676")
kpi_card(c2, "PARADA MECÁNICA", f"{parada_mec:,.1f} H", "Correctivos", "#FF5252")
kpi_card(c3, "PARADA OPERATIVA", f"{parada_op:,.1f} H", "Operativas", "#FFA726")
kpi_card(c4, "# FALLAS", f"{n_fallas}", f"MTBF {mtbf:.1f} H | MTTR {mttr:.1f} H", "#00D4FF")

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

c5, c6, c7, c8 = st.columns(4)
kpi_card(c5, "DISPONIBILIDAD MEC.", f"{disp:.1f}%",
         f"({total_prog - parada_mec:.1f} H disp. / {total_prog:.1f} H prog.)", "#00D4FF")
kpi_card(c6, "UTILIZACIÓN", f"{util:.1f}%",
         f"({total_efec:.1f} H efec. / {total_prog:.1f} H prog.)", "#00E676")
kpi_card(c7, "INSPECCIÓN", f"{inspeccion:,.1f} H", "Preventivo", "#B388FF")
kpi_card(c8, "UTIL. EFECTIVA", f"{util_efectiva:.1f}%",
         f"({total_efec:.1f} H efec. / {horas_disponibles:.1f} H disp.)", "#FFA726")

st.markdown("---")

# ============================================================
# 14. GRÁFICOS GLOBALES
# ============================================================
g1, g2, g3 = st.columns(3)

with g1:
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=disp,
        number={"suffix": "%", "font": {"color": "#00D4FF", "size": 40}},
        title={"text": "Disponibilidad Mecánica", "font": {"size": 14}},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#00D4FF"},
               "bgcolor": "#1A1F2B",
               "steps": [{"range": [0, 50], "color": "#3A1F1F"},
                         {"range": [50, 75], "color": "#3A3520"},
                         {"range": [75, 100], "color": "#1F3A2A"}],
               "threshold": {"line": {"color": "#FF5252", "width": 4},
                             "thickness": 0.75, "value": 85}}))
    fig.update_layout(**PLOT, height=250)
    st.plotly_chart(fig, use_container_width=True)

with g2:
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=util,
        number={"suffix": "%", "font": {"color": "#00E676", "size": 40}},
        title={"text": "Utilización", "font": {"size": 14}},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#00E676"},
               "bgcolor": "#1A1F2B",
               "steps": [{"range": [0, 40], "color": "#3A1F1F"},
                         {"range": [40, 70], "color": "#3A3520"},
                         {"range": [70, 100], "color": "#1F3A2A"}]}))
    fig.update_layout(**PLOT, height=250)
    st.plotly_chart(fig, use_container_width=True)

with g3:
    if "TIPO DE EQUIPO" in dff.columns:
        kpi_tipo = dff.groupby("TIPO DE EQUIPO")["Horas Efectivas Trabajadas"].sum().reset_index()
        fig = px.pie(kpi_tipo, values="Horas Efectivas Trabajadas", names="TIPO DE EQUIPO",
                     hole=0.55, color_discrete_sequence=["#00D4FF", "#00E676", "#FFA726", "#B388FF"])
        fig.update_layout(**PLOT, height=250, title="Horas Efectivas por Tipo")
        st.plotly_chart(fig, use_container_width=True)

kpi_eq = dff.groupby("Código-Equipo").agg({
    "Horas Efectivas Trabajadas": "sum", "Hr. Parada mecánica": "sum",
    "Hr. Parada operativa": "sum", "Horas Programadas": "sum", "#Fallas": "sum",
}).reset_index()

b1, b2 = st.columns([7, 5])

with b1:
    fig = go.Figure()
    fig.add_bar(x=kpi_eq["Código-Equipo"], y=kpi_eq["Horas Efectivas Trabajadas"],
                name="Efectivas", marker_color="#00E676")
    fig.add_bar(x=kpi_eq["Código-Equipo"], y=kpi_eq["Hr. Parada mecánica"],
                name="P. Mecánica", marker_color="#FF5252")
    fig.add_bar(x=kpi_eq["Código-Equipo"], y=kpi_eq["Hr. Parada operativa"],
                name="P. Operativa", marker_color="#FFA726")
    fig.update_layout(**PLOT, barmode="stack", height=380,
                      title="Horas Efectivas vs Paradas por Equipo",
                      legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, use_container_width=True)

with b2:
    if not dfp_f.empty:
        pareto = (dfp_f.groupby("Tipo de Parada")["Duración"].sum()
                     .reset_index().sort_values("Duración", ascending=False))
        pareto["Acum %"] = pareto["Duración"].cumsum() / pareto["Duración"].sum() * 100
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_bar(x=pareto["Tipo de Parada"], y=pareto["Duración"],
                    marker_color="#FFA726", name="Horas")
        fig.add_scatter(x=pareto["Tipo de Parada"], y=pareto["Acum %"],
                        mode="lines+markers", name="Acum %",
                        line=dict(color="#00D4FF", width=3), secondary_y=True)
        fig.update_layout(**PLOT, height=380, title="Pareto de Paradas",
                          legend=dict(orientation="h", y=-0.2))
        fig.update_yaxes(title_text="Horas", secondary_y=False)
        fig.update_yaxes(title_text="% Acum", secondary_y=True, range=[0, 105])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin datos en el rango seleccionado (PARADAS-M)")

kpi_dia = dff.groupby("Fecha").agg({
    "Horas Efectivas Trabajadas": "sum", "Hr. Parada mecánica": "sum"}).reset_index()

t1, t2 = st.columns([7, 5])

with t1:
    fig = go.Figure()
    fig.add_scatter(x=kpi_dia["Fecha"], y=kpi_dia["Horas Efectivas Trabajadas"],
                    mode="lines+markers", name="Efectivas",
                    line=dict(color="#00E676", width=3),
                    fill="tozeroy", fillcolor="rgba(0,230,118,0.15)")
    fig.add_scatter(x=kpi_dia["Fecha"], y=kpi_dia["Hr. Parada mecánica"],
                    mode="lines+markers", name="P. Mecánica",
                    line=dict(color="#FF5252", width=2))
    fig.update_layout(**PLOT, height=380, title="Tendencia Diaria",
                      legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, use_container_width=True)

with t2:
    if not dfp_f.empty:
        top = (dfp_f.groupby(["Equipo", "Descripción de la falla"])["Duración"]
                  .sum().reset_index().sort_values("Duración", ascending=False).head(10))
        fig = px.bar(top, x="Duración", y="Descripción de la falla", orientation="h",
                     color="Duración", color_continuous_scale=["#FFA726", "#FF5252"])
        fig.update_layout(**PLOT, height=380, title="Top 10 Fallas",
                          coloraxis_showscale=False,
                          yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

# Heatmap KPIs por equipo
heat_df = dff.groupby("Código-Equipo").agg({
    "Horas Programadas": "sum",
    "Hr. Parada mecánica": "sum",
    "Horas Efectivas Trabajadas": "sum",
}).reset_index()

heat_df["Disponibilidad %"] = (
    (heat_df["Horas Programadas"] - heat_df["Hr. Parada mecánica"])
    / heat_df["Horas Programadas"].replace(0, np.nan) * 100
).fillna(0).round(1)

heat_df["Utilización %"] = (
    heat_df["Horas Efectivas Trabajadas"]
    / heat_df["Horas Programadas"].replace(0, np.nan) * 100
).fillna(0).round(1)

heat = heat_df.set_index("Código-Equipo")[["Disponibilidad %", "Utilización %"]]

fig = px.imshow(heat.T, text_auto=".1f", aspect="auto",
                color_continuous_scale=["#FF5252", "#FFA726", "#00E676"],
                labels=dict(x="Equipo", y="KPI", color="%"))
fig.update_layout(**PLOT, height=260, title="Mapa de Calor KPIs por Equipo")
st.plotly_chart(fig, use_container_width=True)

# ============================================================
# 15. PESTAÑAS: HORÓMETROS / PARADAS-M / KPIs
# ============================================================
st.markdown("---")
st.markdown("## 📑 Registros de detalle")

tab_hor, tab_par, tab_kpis = st.tabs([
    "📋 Horómetros",
    "🛠️ Paradas (PARADAS-M)",
    "📊 KPIs Horómetros & Paradas",
])

# ------------------------------------------------------------
# TAB 1 — HORÓMETROS
# ------------------------------------------------------------
with tab_hor:
    st.markdown("### 📋 Registro de Horómetros")
    st.caption("Columnas principales del día a día operativo. "
               "Ordenable, filtrable y descargable desde la propia tabla.")

    cols_hor = [
        "Fecha", "NUMERO SEMANA", "Turno", "Código-Equipo", "TIPO DE EQUIPO",
        "Horas Programadas", "Horómetro Inicial (Diésel)", "Horómetro Final (Diésel)",
        "Horas Diésel", "Horas Efectivas Trabajadas",
        "Hr. Parada mecánica", "Hr. Parada operativa", "Hr. Inspección",
        "TOTAL HR PARADA", "TOTAL TIEMPO", "#Fallas",
    ]
    cols_ok_hor = [c for c in cols_hor if c in dff.columns]
    show_hor = dff[cols_ok_hor].copy()

    if "Fecha" in show_hor.columns:
        show_hor["Fecha"] = show_hor["Fecha"].dt.strftime("%d/%m/%Y")

    if "Horas Programadas" in show_hor.columns and "Hr. Parada mecánica" in show_hor.columns:
        show_hor["Disp. %"] = (
            (show_hor["Horas Programadas"] - show_hor["Hr. Parada mecánica"])
            / show_hor["Horas Programadas"].replace(0, np.nan) * 100
        ).fillna(0).round(1)

    if "Horas Programadas" in show_hor.columns and "Horas Efectivas Trabajadas" in show_hor.columns:
        show_hor["Util. %"] = (
            show_hor["Horas Efectivas Trabajadas"]
            / show_hor["Horas Programadas"].replace(0, np.nan) * 100
        ).fillna(0).round(1)

    if "Fecha" in show_hor.columns:
        show_hor = show_hor.sort_values(["Fecha", "Código-Equipo"],
                                        ascending=[False, True])

    st.dataframe(show_hor, use_container_width=True, height=500, hide_index=True)

    st.caption(
        f"📊 {len(show_hor):,} registros · "
        f"{show_hor['Código-Equipo'].nunique() if 'Código-Equipo' in show_hor.columns else 0} equipos · "
        f"{show_hor['Fecha'].nunique() if 'Fecha' in show_hor.columns else 0} fechas únicas"
    )

    if not show_hor.empty:
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            show_hor.to_excel(w, index=False, sheet_name="HOROMETROS_FILT")
        st.download_button(
            "⬇️ Descargar Horómetros filtrados (Excel)",
            data=buf.getvalue(),
            file_name="HOROMETROS_filtrado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ------------------------------------------------------------
# TAB 2 — PARADAS-M
# ------------------------------------------------------------
with tab_par:
    st.markdown("### 🛠️ Registro de Paradas (PARADAS-M)")
    st.caption("Seguimiento detallado de cada parada por equipo y fecha. "
               "Sirve para auditar fallas y cruzar con los horómetros.")

    if dfp_f.empty:
        st.info("⚠️ No hay paradas registradas con los filtros seleccionados.")
    else:
        cols_par = ["Fecha", "Turno", "Equipo", "Tipo de Parada",
                    "Duración", "Descripción de la falla"]
        cols_ok_par = [c for c in cols_par if c in dfp_f.columns]
        show_par = dfp_f[cols_ok_par].copy()

        if "Fecha" in show_par.columns:
            show_par["Fecha"] = show_par["Fecha"].dt.strftime("%d/%m/%Y")

        sort_cols = [c for c in ["Fecha", "Equipo"] if c in show_par.columns]
        if sort_cols:
            show_par = show_par.sort_values(
                sort_cols, ascending=[False] + [True] * (len(sort_cols) - 1)
            )

        total_h = show_par["Duración"].sum() if "Duración" in show_par.columns else 0
        n_paradas = len(show_par)
        n_equipos = show_par["Equipo"].nunique() if "Equipo" in show_par.columns else 0
        prom_h = (total_h / n_paradas) if n_paradas else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total de paradas", f"{n_paradas}")
        m2.metric("Horas totales", f"{total_h:,.1f} H")
        m3.metric("Equipos afectados", f"{n_equipos}")
        m4.metric("Promedio por parada", f"{prom_h:.2f} H")

        st.markdown("---")

        col_f1, col_f2 = st.columns([2, 3])
        with col_f1:
            if "Equipo" in show_par.columns:
                eqs_tab = sorted(show_par["Equipo"].dropna().unique())
                eq_tab = st.multiselect("Filtrar por equipo (tabla)",
                                        eqs_tab, default=[],
                                        placeholder="Todos")
            else:
                eq_tab = []
        with col_f2:
            if "Descripción de la falla" in show_par.columns:
                txt = st.text_input("🔍 Buscar en descripción de falla",
                                    placeholder="Ej: neumático, claxon, motor...")
            else:
                txt = ""

        show_par_v = show_par.copy()
        if eq_tab:
            show_par_v = show_par_v[show_par_v["Equipo"].isin(eq_tab)]
        if txt and "Descripción de la falla" in show_par_v.columns:
            show_par_v = show_par_v[
                show_par_v["Descripción de la falla"]
                .astype(str).str.contains(txt, case=False, na=False)
            ]

        st.dataframe(
            show_par_v,
            use_container_width=True,
            height=480,
            hide_index=True,
            column_config={
                "Duración": st.column_config.NumberColumn(
                    "Duración (H)", format="%.2f H"
                ),
            },
        )

        st.caption(f"📊 {len(show_par_v):,} paradas mostradas "
                   f"de {len(show_par):,} filtradas")

        if not show_par_v.empty:
            buf2 = BytesIO()
            with pd.ExcelWriter(buf2, engine="openpyxl") as w:
                show_par_v.to_excel(w, index=False, sheet_name="PARADAS_FILT")
            st.download_button(
                "⬇️ Descargar Paradas filtradas (Excel)",
                data=buf2.getvalue(),
                file_name="PARADAS_filtrado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        # --- Resumen por equipo ---
        st.markdown("#### 📈 Resumen de paradas por equipo")
        if "Equipo" in show_par_v.columns and "Duración" in show_par_v.columns:
            resumen_eq = (
                show_par_v.groupby("Equipo")
                .agg(
                    N_Paradas=("Duración", "count"),
                    Horas_Totales=("Duración", "sum"),
                    Promedio_H=("Duración", "mean"),
                    Max_Parada=("Duración", "max"),
                )
                .reset_index()
                .sort_values("Horas_Totales", ascending=False)
            )
            resumen_eq["Horas_Totales"] = resumen_eq["Horas_Totales"].round(1)
            resumen_eq["Promedio_H"] = resumen_eq["Promedio_H"].round(2)
            resumen_eq["Max_Parada"] = resumen_eq["Max_Parada"].round(1)

            st.dataframe(
                resumen_eq,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Horas_Totales": st.column_config.NumberColumn(
                        "Horas Totales", format="%.1f H"
                    ),
                    "Promedio_H": st.column_config.NumberColumn(
                        "Promedio / Parada", format="%.2f H"
                    ),
                    "Max_Parada": st.column_config.NumberColumn(
                        "Máx. Parada", format="%.1f H"
                    ),
                },
            )

            fig_eq = px.bar(
                resumen_eq.sort_values("Horas_Totales"),
                x="Horas_Totales", y="Equipo", orientation="h",
                color="Horas_Totales",
                color_continuous_scale=["#FFA726", "#FF5252"],
                title="Horas totales de parada por equipo",
            )
            fig_eq.update_layout(**PLOT, height=320, coloraxis_showscale=False,
                                 yaxis_title="")
            st.plotly_chart(fig_eq, use_container_width=True)

# ------------------------------------------------------------
# TAB 3 — KPIs HORÓMETROS & PARADAS (mismos filtros del sidebar)
# ------------------------------------------------------------
with tab_kpis:
    st.markdown("### 📊 KPIs Horómetros & Paradas")
    st.caption("Esta pestaña usa **exactamente los mismos filtros del sidebar** "
               "(Equipo, Turno, Tipo, Semana/Mes/Rango). Todo se recalcula al instante.")

    hor_mes = dff.copy()
    par_mes = dfp_f.copy()

    if hor_mes.empty and par_mes.empty:
        st.info("No hay registros de horómetro ni de paradas con los filtros seleccionados.")
    else:
        # --- KPIs por agregación ---
        total_efec_k = float(hor_mes["Horas Efectivas Trabajadas"].sum()) if "Horas Efectivas Trabajadas" in hor_mes.columns else 0.0
        total_prog_k = float(hor_mes["Horas Programadas"].sum()) if "Horas Programadas" in hor_mes.columns else 0.0
        parada_mec_k = float(hor_mes["Hr. Parada mecánica"].sum()) if "Hr. Parada mecánica" in hor_mes.columns else 0.0
        parada_op_k  = float(hor_mes["Hr. Parada operativa"].sum()) if "Hr. Parada operativa" in hor_mes.columns else 0.0
        inspeccion_k = float(hor_mes["Hr. Inspección"].sum()) if "Hr. Inspección" in hor_mes.columns else 0.0
        n_fallas_k   = int(hor_mes["#Fallas"].sum()) if "#Fallas" in hor_mes.columns else 0

        if not par_mes.empty and "Duración" in par_mes.columns:
            if parada_mec_k == 0 and "Tipo de Parada" in par_mes.columns:
                mask_mec = par_mes["Tipo de Parada"].astype(str).str.upper().str.contains("PM|MEC|MECAN", na=False)
                parada_mec_k = float(par_mes.loc[mask_mec, "Duración"].sum())
                parada_op_k = float(par_mes.loc[~mask_mec, "Duración"].sum())
            if n_fallas_k == 0:
                n_fallas_k = len(par_mes)

        if total_prog_k == 0:
            total_prog_k = total_efec_k + parada_mec_k + parada_op_k

        disp_k = ((total_prog_k - parada_mec_k) / total_prog_k * 100) if total_prog_k > 0 else 0.0
        util_k = (total_efec_k / total_prog_k * 100) if total_prog_k > 0 else 0.0
        horas_disp_k = total_prog_k - parada_mec_k
        util_efec_k = (total_efec_k / horas_disp_k * 100) if horas_disp_k > 0 else 0.0
        mtbf_k = total_efec_k / n_fallas_k if n_fallas_k else 0.0
        mttr_k = parada_mec_k / n_fallas_k if n_fallas_k else 0.0

        # --- Tarjetas KPI ---
        c1, c2, c3, c4 = st.columns(4)
        kpi_card(c1, "HORAS EFECTIVAS", f"{total_efec_k:,.1f} H",
                 f"{len(hor_mes):,} registros", "#00E676")
        kpi_card(c2, "PARADA MECÁNICA", f"{parada_mec_k:,.1f} H",
                 "Correctivos", "#FF5252")
        kpi_card(c3, "PARADA OPERATIVA", f"{parada_op_k:,.1f} H",
                 "Operativas", "#FFA726")
        kpi_card(c4, "# FALLAS", f"{n_fallas_k}",
                 f"MTBF {mtbf_k:.1f} H | MTTR {mttr_k:.1f} H", "#00D4FF")

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        c5, c6, c7, c8 = st.columns(4)
        kpi_card(c5, "DISPONIBILIDAD MEC.", f"{disp_k:.1f}%",
                 f"({horas_disp_k:.1f} H disp / {total_prog_k:.1f} H prog)", "#00D4FF")
        kpi_card(c6, "UTILIZACIÓN", f"{util_k:.1f}%",
                 f"({total_efec_k:.1f} H efec / {total_prog_k:.1f} H prog)", "#00E676")
        kpi_card(c7, "INSPECCIÓN", f"{inspeccion_k:,.1f} H", "Preventivo", "#B388FF")
        kpi_card(c8, "UTIL. EFECTIVA", f"{util_efec_k:.1f}%",
                 f"({total_efec_k:.1f} H efec / {horas_disp_k:.1f} H disp)", "#FFA726")

        st.markdown("---")

        # --- Gauges ---
        gg1, gg2, gg3 = st.columns(3)

        with gg1:
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=disp_k,
                number={"suffix": "%", "font": {"color": "#00D4FF", "size": 40}},
                title={"text": "Disponibilidad Mecánica", "font": {"size": 14}},
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#00D4FF"},
                       "bgcolor": "#1A1F2B",
                       "steps": [{"range": [0, 50], "color": "#3A1F1F"},
                                 {"range": [50, 75], "color": "#3A3520"},
                                 {"range": [75, 100], "color": "#1F3A2A"}],
                       "threshold": {"line": {"color": "#FF5252", "width": 4},
                                     "thickness": 0.75, "value": 85}}))
            fig.update_layout(**PLOT, height=250)
            st.plotly_chart(fig, use_container_width=True)

        with gg2:
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=util_k,
                number={"suffix": "%", "font": {"color": "#00E676", "size": 40}},
                title={"text": "Utilización", "font": {"size": 14}},
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#00E676"},
                       "bgcolor": "#1A1F2B",
                       "steps": [{"range": [0, 40], "color": "#3A1F1F"},
                                 {"range": [40, 70], "color": "#3A3520"},
                                 {"range": [70, 100], "color": "#1F3A2A"}]}))
            fig.update_layout(**PLOT, height=250)
            st.plotly_chart(fig, use_container_width=True)

        with gg3:
            if not par_mes.empty and "Tipo de Parada" in par_mes.columns:
                kpi_tipo_p = (par_mes.groupby("Tipo de Parada")["Duración"]
                              .sum().reset_index())
                fig = px.pie(kpi_tipo_p, values="Duración", names="Tipo de Parada",
                             hole=0.55,
                             color_discrete_sequence=["#00D4FF", "#00E676",
                                                       "#FFA726", "#B388FF"])
                fig.update_layout(**PLOT, height=250,
                                  title="Distribución de Paradas por Tipo")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sin datos de paradas para el gráfico.")

        # --- Barras + Pareto ---
        kb1, kb2 = st.columns([7, 5])

        with kb1:
            if not hor_mes.empty and "Fecha" in hor_mes.columns:
                hor_agg = hor_mes.groupby("Fecha").agg({
                    "Horas Efectivas Trabajadas": "sum",
                    "Hr. Parada mecánica": "sum",
                    "Hr. Parada operativa": "sum",
                }).reset_index().sort_values("Fecha")
                fig = go.Figure()
                fig.add_bar(x=hor_agg["Fecha"],
                            y=hor_agg["Horas Efectivas Trabajadas"],
                            name="Horas Efectivas", marker_color="#00E676")
                fig.add_bar(x=hor_agg["Fecha"],
                            y=hor_agg["Hr. Parada mecánica"],
                            name="P. Mecánica", marker_color="#FF5252")
                fig.add_bar(x=hor_agg["Fecha"],
                            y=hor_agg["Hr. Parada operativa"],
                            name="P. Operativa", marker_color="#FFA726")
                fig.update_layout(**PLOT, barmode="group", height=380,
                                  title="Horas Efectivas vs Paradas por Fecha",
                                  legend=dict(orientation="h", y=-0.2))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sin registros de horómetro.")

        with kb2:
            if not par_mes.empty and "Tipo de Parada" in par_mes.columns:
                pareto_k = (par_mes.groupby("Tipo de Parada")["Duración"].sum()
                            .reset_index().sort_values("Duración", ascending=False))
                pareto_k["Acum %"] = (pareto_k["Duración"].cumsum()
                                      / pareto_k["Duración"].sum() * 100)
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_bar(x=pareto_k["Tipo de Parada"], y=pareto_k["Duración"],
                            marker_color="#FFA726", name="Horas")
                fig.add_scatter(x=pareto_k["Tipo de Parada"], y=pareto_k["Acum %"],
                                mode="lines+markers", name="Acum %",
                                line=dict(color="#00D4FF", width=3),
                                secondary_y=True)
                fig.update_layout(**PLOT, height=380, title="Pareto de Paradas",
                                  legend=dict(orientation="h", y=-0.2))
                fig.update_yaxes(title_text="Horas", secondary_y=False)
                fig.update_yaxes(title_text="% Acum", secondary_y=True,
                                 range=[0, 105])
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sin datos de paradas para el período.")

        # --- Tendencia + Top 10 Fallas ---
        kt1, kt2 = st.columns([7, 5])

        with kt1:
            if not hor_mes.empty and "Fecha" in hor_mes.columns:
                kpi_d = hor_mes.groupby("Fecha").agg({
                    "Horas Efectivas Trabajadas": "sum",
                    "Hr. Parada mecánica": "sum",
                }).reset_index().sort_values("Fecha")
                fig = go.Figure()
                fig.add_scatter(x=kpi_d["Fecha"],
                                y=kpi_d["Horas Efectivas Trabajadas"],
                                mode="lines+markers", name="Efectivas",
                                line=dict(color="#00E676", width=3),
                                fill="tozeroy", fillcolor="rgba(0,230,118,0.15)")
                fig.add_scatter(x=kpi_d["Fecha"],
                                y=kpi_d["Hr. Parada mecánica"],
                                mode="lines+markers", name="P. Mecánica",
                                line=dict(color="#FF5252", width=2))
                fig.update_layout(**PLOT, height=380, title="Tendencia Diaria",
                                  legend=dict(orientation="h", y=-0.2))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sin registros para la tendencia.")

        with kt2:
            if not par_mes.empty and "Descripción de la falla" in par_mes.columns:
                top_k = (par_mes.groupby(["Equipo", "Descripción de la falla"])["Duración"]
                         .sum().reset_index()
                         .sort_values("Duración", ascending=False).head(10))
                fig = px.bar(top_k, x="Duración", y="Descripción de la falla",
                             orientation="h", color="Duración",
                             color_continuous_scale=["#FFA726", "#FF5252"])
                fig.update_layout(**PLOT, height=380, title="Top 10 Fallas",
                                  coloraxis_showscale=False,
                                  yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sin paradas registradas.")

        # --- Heatmap KPIs por equipo ---
        if not hor_mes.empty and all(c in hor_mes.columns for c in
                                     ["Horas Programadas", "Hr. Parada mecánica",
                                      "Horas Efectivas Trabajadas"]):
            heat_k = hor_mes.groupby("Código-Equipo").agg({
                "Horas Programadas": "sum",
                "Hr. Parada mecánica": "sum",
                "Horas Efectivas Trabajadas": "sum",
            }).reset_index()

            heat_k["Disponibilidad %"] = (
                (heat_k["Horas Programadas"] - heat_k["Hr. Parada mecánica"])
                / heat_k["Horas Programadas"].replace(0, np.nan) * 100
            ).fillna(0).round(1)

            heat_k["Utilización %"] = (
                heat_k["Horas Efectivas Trabajadas"]
                / heat_k["Horas Programadas"].replace(0, np.nan) * 100
            ).fillna(0).round(1)

            heat_matrix_k = heat_k.set_index("Código-Equipo")[
                ["Disponibilidad %", "Utilización %"]
            ]

            fig = px.imshow(heat_matrix_k.T, text_auto=".1f", aspect="auto",
                            color_continuous_scale=["#FF5252", "#FFA726", "#00E676"],
                            labels=dict(x="Equipo", y="KPI", color="%"))
            fig.update_layout(**PLOT, height=260,
                              title="Mapa de Calor KPIs por Equipo")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # --- Sub-tabs de detalle ---
        st.markdown("## 📑 Registros de detalle (KPIs)")
        sub_hor, sub_par = st.tabs(["📋 Horómetros", "🛠️ Paradas (PARADAS-M)"])

        with sub_hor:
            st.markdown("### 📋 Registro de Horómetros (filtros del sidebar)")
            st.caption("Los mismos registros que alimentan los KPIs.")

            cols_hor_k = [
                "Fecha", "NUMERO SEMANA", "Turno", "Código-Equipo",
                "TIPO DE EQUIPO", "Horas Programadas",
                "Horómetro Inicial (Diésel)", "Horómetro Final (Diésel)",
                "Horas Efectivas Trabajadas", "Hr. Parada mecánica",
                "Hr. Parada operativa", "Hr. Inspección", "#Fallas",
            ]
            cols_ok_hor_k = [c for c in cols_hor_k if c in hor_mes.columns]
            show_hor_k = hor_mes[cols_ok_hor_k].copy()

            if "Fecha" in show_hor_k.columns:
                show_hor_k["Fecha"] = show_hor_k["Fecha"].dt.strftime("%d/%m/%Y")

            if ("Horas Programadas" in show_hor_k.columns and
                    "Hr. Parada mecánica" in show_hor_k.columns):
                show_hor_k["Disp. %"] = (
                    (show_hor_k["Horas Programadas"] - show_hor_k["Hr. Parada mecánica"])
                    / show_hor_k["Horas Programadas"].replace(0, np.nan) * 100
                ).fillna(0).round(1)

            if ("Horas Programadas" in show_hor_k.columns and
                    "Horas Efectivas Trabajadas" in show_hor_k.columns):
                show_hor_k["Util. %"] = (
                    show_hor_k["Horas Efectivas Trabajadas"]
                    / show_hor_k["Horas Programadas"].replace(0, np.nan) * 100
                ).fillna(0).round(1)

            if "Fecha" in show_hor_k.columns:
                show_hor_k = show_hor_k.sort_values(
                    ["Fecha", "Código-Equipo"] if "Código-Equipo" in show_hor_k.columns else ["Fecha"],
                    ascending=[False] + ([True] if "Código-Equipo" in show_hor_k.columns else [])
                )

            st.dataframe(show_hor_k, use_container_width=True, height=500, hide_index=True)

            if not show_hor_k.empty:
                buf_k = BytesIO()
                with pd.ExcelWriter(buf_k, engine="openpyxl") as w:
                    show_hor_k.to_excel(w, index=False, sheet_name="HOROMETROS_KPI")
                st.download_button(
                    "⬇️ Descargar Horómetros KPIs (Excel)",
                    data=buf_k.getvalue(),
                    file_name="HOROMETROS_kpi.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

        with sub_par:
            st.markdown("### 🛠️ Registro de Paradas (filtros del sidebar)")
            st.caption("Las mismas paradas que alimentan los KPIs.")

            if par_mes.empty:
                st.info("⚠️ No hay paradas con los filtros seleccionados.")
            else:
                cols_par_k = ["Fecha", "Turno", "Equipo", "Tipo de Parada",
                              "Duración", "Descripción de la falla"]
                cols_ok_par_k = [c for c in cols_par_k if c in par_mes.columns]
                show_par_k = par_mes[cols_ok_par_k].copy()

                if "Fecha" in show_par_k.columns:
                    show_par_k["Fecha"] = show_par_k["Fecha"].dt.strftime("%d/%m/%Y")

                sort_cols_k = [c for c in ["Fecha", "Equipo"] if c in show_par_k.columns]
                if sort_cols_k:
                    show_par_k = show_par_k.sort_values(
                        sort_cols_k, ascending=[False] + [True] * (len(sort_cols_k) - 1)
                    )

                st.dataframe(
                    show_par_k,
                    use_container_width=True,
                    height=480,
                    hide_index=True,
                    column_config={
                        "Duración": st.column_config.NumberColumn(
                            "Duración (H)", format="%.2f H"
                        ),
                    },
                )

                st.caption(f"📊 {len(show_par_k):,} paradas mostradas")

                if not show_par_k.empty:
                    buf_p = BytesIO()
                    with pd.ExcelWriter(buf_p, engine="openpyxl") as w:
                        show_par_k.to_excel(w, index=False, sheet_name="PARADAS_KPI")
                    st.download_button(
                        "⬇️ Descargar Paradas KPIs (Excel)",
                        data=buf_p.getvalue(),
                        file_name="PARADAS_kpi.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

                st.markdown("#### 📈 Resumen por tipo de parada")
                if ("Tipo de Parada" in show_par_k.columns and
                        "Duración" in show_par_k.columns):
                    resumen_tipo = (show_par_k.groupby("Tipo de Parada")
                                    .agg(N=("Duración", "count"),
                                         Horas=("Duración", "sum"),
                                         Promedio=("Duración", "mean"))
                                    .reset_index()
                                    .sort_values("Horas", ascending=False))
                    resumen_tipo["Horas"] = resumen_tipo["Horas"].round(1)
                    resumen_tipo["Promedio"] = resumen_tipo["Promedio"].round(2)
                    st.dataframe(resumen_tipo, use_container_width=True, hide_index=True)

st.caption("Dashboard generado con Streamlit · Plotly · Pandas")
