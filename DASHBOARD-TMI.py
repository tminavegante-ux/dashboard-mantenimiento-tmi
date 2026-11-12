# ============================================================
#  DASHBOARD KPI MANTENIMIENTO — TMI 2026
#  Fuente única: Google Sheets (sin XLS)
#  Hojas: EQUIPOS, HOROMETROS, COMPONENTES, NEUMATICOS,
#         ENGRASE, PARADAS-M
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO
import os
import calendar
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Dashboard KPI Mantenimiento - Marcio",
    layout="wide",
    initial_sidebar_state="expanded"
)

if os.path.exists("tmi2026.png"):
    st.sidebar.image("tmi2026.png", width=160)

st.title("CONTROL NEW MING 2026")
st.markdown("---")


# ==========================================
# 2. FUNCIONES DE LIMPIEZA
# ==========================================
def _limpiar_horas(serie):
    """'7.80 H' -> 7.80 ; tolerante a comas, %, vacíos y 'nan'."""
    return (
        serie.astype(str)
        .str.replace("H", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA,
                  "NONE": pd.NA, "NaN": pd.NA, "-": pd.NA})
        .pipe(pd.to_numeric, errors="coerce")
    )


# ==========================================
# 3. CARGA DE DATOS DESDE GOOGLE SHEETS
# ==========================================
@st.cache_data(ttl=300, show_spinner="Cargando datos de Google Sheets...")
def cargar_datos_marcio():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)

        df_equipos     = conn.read(worksheet="EQUIPOS", ttl=0)
        df_horometro   = conn.read(worksheet="HOROMETROS", ttl=0)
        df_componentes = conn.read(worksheet="COMPONENTES", ttl=0)
        df_neumaticos  = conn.read(worksheet="NEUMATICOS", ttl=0)
        df_engrase     = conn.read(worksheet="ENGRASE", ttl=0)
        df_paradas     = conn.read(worksheet="PARADAS-M", ttl=0)

        def _norm_cols(df):
            df.columns = [str(c).strip().upper() for c in df.columns]
            return df

        df_equipos     = _norm_cols(df_equipos)
        df_horometro   = _norm_cols(df_horometro)
        df_componentes = _norm_cols(df_componentes)
        df_neumaticos  = _norm_cols(df_neumaticos)
        df_engrase     = _norm_cols(df_engrase)
        df_paradas     = _norm_cols(df_paradas)

        # ==================================================
        # EQUIPOS — NOMBRE -> NOMBR
        # ==================================================
        df_equipos = df_equipos.rename(columns={"NOMBRE": "NOMBR"})

        if "ID_EQUIPO" not in df_equipos.columns or "NOMBR" not in df_equipos.columns:
            raise ValueError(
                f"Hoja 'EQUIPOS' debe tener ID_EQUIPO y NOMBR. "
                f"Columnas encontradas: {list(df_equipos.columns)}"
            )

        # ==================================================
        # HOROMETROS — mapeo a nombres internos
        # ==================================================
        MAPEO_HOROMETRO = {
            "CÓDIGO-EQUIPO": "ID_EQUIPO",
            "CÓDIGO EQUIPO": "ID_EQUIPO",
            "HORÓMETRO INICIAL (DIÉSEL)": "H_INICIAL",
            "HORÓMETRO FINAL (DIÉSEL)": "HFINAL",
            "HORAS EFECTIVAS TRABAJADAS": "HRS_OPERADAS",
            "HR. PARADA MECÁNICA": "PARADA_MEC",
            "HR. PARADA OPERATIVA": "PARADA_OP",
            "HR. INSPECCIÓN": "INSPECCION",
            "HORAS PROGRAMADAS": "HORAS_PROG",
            "TOTAL HR PARADA": "TOTAL_PARADA",
            "TOTAL TIEMPO": "TOTAL_TIEMPO",
            "HR. NO DISPONIBLE": "HR_NO_DISP",
            "HR. DISPONIBLE": "HR_DISP",
            "HR. USADO": "HR_USADO",
            "HR. NO USADO": "HR_NO_USADO",
            "#FALLAS": "N_FALLAS",
            "DISPONIBILIDAD MECANICA": "DISP_MEC",
            "UTILIZACIÓN": "UTILIZACION",
            "UTILIZACIÓN EFECTIVA": "UTIL_EFECTIVA",
            "USO EFECTIVO DE DISPONIBILIDAD": "USO_EFECTIVO",
            "USO DE DISPONIBILIDAD": "USO_DISP",
        }
        df_horometro = df_horometro.rename(
            columns={k: v for k, v in MAPEO_HOROMETRO.items()
                     if k in df_horometro.columns}
        )

        req_hor = ["FECHA", "ID_EQUIPO", "H_INICIAL", "HFINAL"]
        falt_hor = [c for c in req_hor if c not in df_horometro.columns]
        if falt_hor:
            raise ValueError(
                f"Hoja 'HOROMETROS' le faltan columnas: {falt_hor}. "
                f"Columnas encontradas: {list(df_horometro.columns)}"
            )

        # ==================================================
        # PARADAS-M — mapeo flexible
        # ==================================================
        MAPEO_PARADAS = {
            "CÓDIGO-EQUIPO": "EQUIPO",
            "CÓDIGO EQUIPO": "EQUIPO",
            "DURACIÓN": "DURACION",
            "DURACION (H)": "DURACION",
            "DURACIÓN (H)": "DURACION",
            "DESCRIPCIÓN DE LA FALLA": "DESCRIPCION DE LA FALLA",
            "DESCRIPCIÓN": "DESCRIPCION DE LA FALLA",
            "DESCRIPCION": "DESCRIPCION DE LA FALLA",
            "TIPO_PARADA": "TIPO DE PARADA",
            "TIPO DE FALLA": "TIPO DE PARADA",
        }
        df_paradas = df_paradas.rename(
            columns={k: v for k, v in MAPEO_PARADAS.items()
                     if k in df_paradas.columns}
        )

        req_par = ["FECHA", "TIPO DE PARADA", "DURACION", "EQUIPO"]
        falt_par = [c for c in req_par if c not in df_paradas.columns]
        if falt_par:
            raise ValueError(
                f"Hoja 'PARADAS-M' le faltan columnas: {falt_par}. "
                f"Columnas encontradas: {list(df_paradas.columns)}"
            )

        if "DESCRIPCION DE LA FALLA" not in df_paradas.columns:
            df_paradas["DESCRIPCION DE LA FALLA"] = ""

        # ==================================================
        # COMPONENTES / NEUMATICOS / ENGRASE — mapeos suaves
        # ==================================================
        MAPEO_GENERAL = {
            "NOMBRE": "NOMBR",
            "NOMBRE_EQUIPO": "NOMBR",
            "NOMBR_EQUIPO": "NOMBR",
            "H_FINAL": "HFINAL",
            "HRS_FINAL": "HFINAL",
            "HORA_FINAL": "HFINAL",
            "H_INICIO": "H_INICIAL",
            "HRS_INICIAL": "H_INICIAL",
            "HORA_INICIAL": "H_INICIAL",
            "HOROMETRO_CAMBIO (PROYECTADO)": "HOROMETRO_CAMBIO(PROYECTADO)",
            "HOROMETRO_CAMBIO_PROYECTADO": "HOROMETRO_CAMBIO(PROYECTADO)",
        }
        df_componentes = df_componentes.rename(
            columns={k: v for k, v in MAPEO_GENERAL.items()
                     if k in df_componentes.columns}
        )
        df_neumaticos = df_neumaticos.rename(
            columns={k: v for k, v in MAPEO_GENERAL.items()
                     if k in df_neumaticos.columns}
        )
        df_engrase = df_engrase.rename(
            columns={k: v for k, v in MAPEO_GENERAL.items()
                     if k in df_engrase.columns}
        )

        # ==================================================
        # Normalizar identificadores
        # ==================================================
        for df in (df_equipos, df_horometro, df_componentes,
                   df_neumaticos, df_engrase, df_paradas):
            if "ID_EQUIPO" in df.columns:
                df["ID_EQUIPO"] = df["ID_EQUIPO"].astype(str).str.strip()
            if "EQUIPO" in df.columns:
                df["EQUIPO"] = df["EQUIPO"].astype(str).str.strip()

        if "NOMBR" in df_equipos.columns:
            df_equipos["NOMBR"] = df_equipos["NOMBR"].astype(str).str.strip()
        if "POSICION" in df_neumaticos.columns:
            df_neumaticos["POSICION"] = df_neumaticos["POSICION"].astype(str).str.strip()
        if "CARA" in df_neumaticos.columns:
            df_neumaticos["CARA"] = (df_neumaticos["CARA"].astype(str)
                                     .str.strip().str.upper())

        # ==================================================
        # Conversión de fechas
        # ==================================================
        df_horometro["FECHA"] = pd.to_datetime(
            df_horometro["FECHA"], errors="coerce", dayfirst=True)
        if "FECHA_INSTALACION" in df_componentes.columns:
            df_componentes["FECHA_INSTALACION"] = pd.to_datetime(
                df_componentes["FECHA_INSTALACION"], errors="coerce", dayfirst=True)
        if "FECHA_MEDICION" in df_neumaticos.columns:
            df_neumaticos["FECHA_MEDICION"] = pd.to_datetime(
                df_neumaticos["FECHA_MEDICION"], errors="coerce", dayfirst=True)
        if "FECHA" in df_engrase.columns:
            df_engrase["FECHA"] = pd.to_datetime(
                df_engrase["FECHA"], errors="coerce", dayfirst=True)
        df_paradas["FECHA"] = pd.to_datetime(
            df_paradas["FECHA"], errors="coerce", dayfirst=True)

        # ==================================================
        # Conversión numérica HOROMETROS
        # ==================================================
        for c in ["H_INICIAL", "HFINAL", "HRS_OPERADAS", "PARADA_MEC",
                  "PARADA_OP", "INSPECCION", "HORAS_PROG", "TOTAL_PARADA",
                  "TOTAL_TIEMPO", "HR_NO_DISP", "HR_DISP", "HR_USADO",
                  "HR_NO_USADO"]:
            if c in df_horometro.columns:
                df_horometro[c] = _limpiar_horas(df_horometro[c])

        for c in ["DISP_MEC", "UTILIZACION", "UTIL_EFECTIVA",
                  "USO_EFECTIVO", "USO_DISP"]:
            if c in df_horometro.columns:
                df_horometro[c] = _limpiar_horas(df_horometro[c])

        if "N_FALLAS" in df_horometro.columns:
            df_horometro["N_FALLAS"] = pd.to_numeric(
                df_horometro["N_FALLAS"], errors="coerce").fillna(0).astype(int)

        # ==================================================
        # Derivadas HOROMETROS
        # ==================================================
        if "HRS_OPERADAS" not in df_horometro.columns:
            df_horometro["HRS_OPERADAS"] = (df_horometro["HFINAL"]
                                            - df_horometro["H_INICIAL"])
        df_horometro.loc[df_horometro["HFINAL"].isna(), "HRS_OPERADAS"] = pd.NA
        df_horometro.loc[df_horometro["HRS_OPERADAS"] < 0, "HRS_OPERADAS"] = pd.NA
        df_horometro["MES_NUM"] = df_horometro["FECHA"].dt.month
        df_horometro["ANIO"]    = df_horometro["FECHA"].dt.year
        df_horometro["PERIODO_MES"] = df_horometro["FECHA"].dt.strftime("%Y-%m")
        df_horometro["MES_NOMBRE"] = df_horometro["FECHA"].dt.strftime("%B").str.capitalize()

        if "STATUS_EQUIPO" not in df_horometro.columns:
            df_horometro["STATUS_EQUIPO"] = np.where(
                df_horometro["HRS_OPERADAS"].fillna(0) > 0,
                "OPERATIVO", "INOPERATIVO"
            )

        # ==================================================
        # Derivadas ENGRASE
        # ==================================================
        if "FECHA" in df_engrase.columns:
            df_engrase["MES_NUM"] = df_engrase["FECHA"].dt.month
            df_engrase["ANIO"]    = df_engrase["FECHA"].dt.year
            if ("PUNTOS_ENGRASADOS" in df_engrase.columns and
                    "PUNTOS_TOTALES" in df_engrase.columns):
                df_engrase["PCT_CUMPLIMIENTO"] = (
                    df_engrase["PUNTOS_ENGRASADOS"]
                    / df_engrase["PUNTOS_TOTALES"] * 100
                ).round(1)
            else:
                df_engrase["PCT_CUMPLIMIENTO"] = 0.0

        # ==================================================
        # Derivadas PARADAS-M
        # ==================================================
        df_paradas["DURACION"] = _limpiar_horas(df_paradas["DURACION"])
        df_paradas["MES_NUM"]  = df_paradas["FECHA"].dt.month
        df_paradas["ANIO"]     = df_paradas["FECHA"].dt.year
        df_paradas["PERIODO_MES"] = df_paradas["FECHA"].dt.strftime("%Y-%m")
        df_paradas["TIPO_UP"]  = (df_paradas["TIPO DE PARADA"]
                                   .astype(str).str.strip().str.upper())

        return (df_equipos, df_horometro, df_componentes, df_neumaticos,
                df_engrase, df_paradas, True, "Google Sheets")

    except Exception as e:
        df_vacio_eq  = pd.DataFrame(columns=["ID_EQUIPO", "NOMBR"])
        df_vacio_ho  = pd.DataFrame(columns=["FECHA", "ID_EQUIPO", "H_INICIAL",
                                              "HFINAL", "HRS_OPERADAS",
                                              "MES_NUM", "ANIO",
                                              "STATUS_EQUIPO", "TURNO"])
        df_vacio_co  = pd.DataFrame(columns=["ID_EQUIPO", "TIPO_COMPONENTE",
                                              "HOROMETRO_CAMBIO(PROYECTADO)"])
        df_vacio_ne  = pd.DataFrame(columns=["FECHA_MEDICION", "ID_EQUIPO",
                                              "POSICION", "CARA", "COCADA"])
        df_vacio_en  = pd.DataFrame(columns=["FECHA", "ID_EQUIPO", "TURNO",
                                              "TECNICO", "PUNTOS_ENGRASADOS",
                                              "PUNTOS_TOTALES", "TIPO_GRASA",
                                              "CANTIDAD_GRASA_KG", "OBSERVACIONES",
                                              "CUMPLIDO", "MES_NUM", "ANIO",
                                              "PCT_CUMPLIMIENTO"])
        df_vacio_par = pd.DataFrame(columns=["FECHA", "TURNO", "TIPO DE PARADA",
                                              "DURACION", "EQUIPO",
                                              "DESCRIPCION DE LA FALLA",
                                              "MES_NUM", "ANIO", "TIPO_UP"])
        return (df_vacio_eq, df_vacio_ho, df_vacio_co, df_vacio_ne,
                df_vacio_en, df_vacio_par, False, str(e))


# ==========================================
# 4. LLAMADA Y VALIDACIÓN
# ==========================================
(df_equipos, df_horometro, df_componentes, df_neumaticos,
 df_engrase, df_paradas, estado_carga, detalle_error) = cargar_datos_marcio()

if not estado_carga or df_equipos.empty:
    st.error("❌ No se pudo cargar los datos desde Google Sheets")
    st.markdown(f"**Detalle Técnico:** `{detalle_error}`")
    st.info(
        "💡 Verifica que el Google Sheet tenga las hojas "
        "**EQUIPOS, HOROMETROS, COMPONENTES, NEUMATICOS, ENGRASE y PARADAS-M** "
        "con las columnas correctas, y que esté compartido con el client_email "
        "de la cuenta de servicio."
    )
    st.stop()


# ==========================================
# 5. BARRA LATERAL (filtros globales 4 primeras pestañas)
# ==========================================
st.sidebar.header("⚙️ Filtros de Control")

if st.sidebar.button("🔄 Refrescar datos", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

dicc_equipos = dict(zip(df_equipos["NOMBR"], df_equipos["ID_EQUIPO"]))
nombre_seleccionado = st.sidebar.selectbox("Seleccione el Equipo:",
                                            list(dicc_equipos.keys()))
id_equipo_sel = dicc_equipos[nombre_seleccionado]

st.sidebar.markdown("---")
st.sidebar.subheader("📅 Filtro Temporal")

dicc_meses = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

df_horometro_equipo = df_horometro[df_horometro["ID_EQUIPO"] == id_equipo_sel]
meses_en_datos = sorted(df_horometro_equipo["MES_NUM"].dropna().astype(int).unique())

if meses_en_datos:
    nombres_meses_disponibles = [dicc_meses[m] for m in meses_en_datos]
    mes_sel_nombre = st.sidebar.radio("Meses Disponibles:", nombres_meses_disponibles)
    mes_sel_num = [k for k, v in dicc_meses.items() if v == mes_sel_nombre][0]
else:
    st.sidebar.warning("⚠️ No hay registros de horómetro para este equipo.")
    mes_sel_num = None

if mes_sel_num:
    df_h_filtrado_mes = df_horometro[df_horometro["MES_NUM"] == mes_sel_num]
    df_h_filtrado_equipo = df_h_filtrado_mes[
        df_h_filtrado_mes["ID_EQUIPO"] == id_equipo_sel
    ]
else:
    df_h_filtrado_mes = pd.DataFrame()
    df_h_filtrado_equipo = pd.DataFrame()


# ==========================================
# 6. PESTAÑAS
# ==========================================
(tab_horometros, tab_neumaticos, tab_componentes, tab_engrase,
 tab_kpis) = st.tabs([
    "⏱️ Horómetros & Flota",
    "🛞 Control de Neumáticos",
    "⚙️ Gestión de Componentes",
    "🛢️ Control de Engrase",
    "📊 KPIs Horómetros & Paradas",
])


# ------------------------------------------
# TAB 1: HORÓMETROS Y FLOTA
# ------------------------------------------
with tab_horometros:
    st.header(f"Análisis de Utilización - {nombre_seleccionado}")

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        total_hrs = (df_h_filtrado_equipo["HRS_OPERADAS"].sum()
                     if not df_h_filtrado_equipo.empty else 0)
        st.metric("Horas Operadas (Mes Seleccionado)", f"{total_hrs:,.1f} Hrs")
    with kpi2:
        ultimo_horometro = df_horometro_equipo["HFINAL"].max()
        st.metric("Último Horómetro Registrado",
                  f"{ultimo_horometro:,.1f} Hrs" if pd.notna(ultimo_horometro) else "0.0 Hrs")
    with kpi3:
        status_actual = (df_h_filtrado_equipo.sort_values("FECHA").iloc[-1]["STATUS_EQUIPO"]
                         if not df_h_filtrado_equipo.empty else "SIN REGISTRO")
        st.metric("Último Estado Operativo", str(status_actual).upper())
    with kpi4:
        if not df_h_filtrado_equipo.empty:
            turnos_operativos = (df_h_filtrado_equipo["STATUS_EQUIPO"] == "OPERATIVO").sum()
            turnos_inoperativos = (df_h_filtrado_equipo["STATUS_EQUIPO"] != "OPERATIVO").sum()
            total_turnos = turnos_operativos + turnos_inoperativos
            disponibilidad = (turnos_operativos / total_turnos * 100) if total_turnos > 0 else 0

            st.markdown(
                f"""
                <div style="padding:0;">
                    <div style="font-size:14px;color:#fafafa;margin-bottom:8px;">
                        TURNOS: Operativos / Inoperativos
                    </div>
                    <div style="display:flex;gap:16px;align-items:baseline;">
                        <div style="text-align:center;min-width:50px;">
                            <div style="font-size:32px;font-weight:600;color:#48BB78;line-height:1;">
                                {turnos_operativos}
                            </div>
                            <div style="font-size:11px;color:#48BB78;margin-top:2px;">
                                OPERATIVOS
                            </div>
                        </div>
                        <div style="font-size:20px;color:#666;">/</div>
                        <div style="text-align:center;min-width:50px;">
                            <div style="font-size:32px;font-weight:600;color:#F56565;line-height:1;">
                                {turnos_inoperativos}
                            </div>
                            <div style="font-size:11px;color:#F56565;margin-top:2px;">
                                INOPERATIVOS
                            </div>
                        </div>
                    </div>
                    <div style="font-size:12px;color:#888;margin-top:8px;">
                        Total: {total_turnos} turnos · Disp: {disponibilidad:.1f}%
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                """
                <div style="padding:0;">
                    <div style="font-size:14px;color:#fafafa;margin-bottom:8px;">
                        Turnos Operativos / Inoperativos
                    </div>
                    <div style="font-size:32px;font-weight:600;color:#666;">0 / 0</div>
                    <div style="font-size:12px;color:#888;margin-top:8px;">Sin datos</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("---")

    g1, g2 = st.columns(2)

    with g1:
        st.subheader(f"Desempeño Diario: {nombre_seleccionado}")
        if not df_h_filtrado_equipo.empty:
            fig_linea = px.line(
                df_h_filtrado_equipo.sort_values("FECHA"),
                x="FECHA", y="HRS_OPERADAS", color="TURNO",
                labels={"HRS_OPERADAS": "Horas Trabajadas", "FECHA": "Día"},
                markers=True, template="plotly_dark"
            )
            st.plotly_chart(fig_linea, use_container_width=True)
        else:
            st.info("Sin registros de horas para este equipo en el mes seleccionado.")

    with g2:
        st.subheader("Comparativa de Horas Totales: Toda la Flota")
        if not df_h_filtrado_mes.empty:
            df_resumen_flota = (df_h_filtrado_mes.groupby("ID_EQUIPO")["HRS_OPERADAS"]
                                .sum().reset_index())
            df_resumen_flota = df_resumen_flota.merge(df_equipos, on="ID_EQUIPO", how="left")

            df_resumen_flota["ES_SELECCIONADO"] = (
                df_resumen_flota["ID_EQUIPO"] == id_equipo_sel
            ).map({True: "⭐ SELECCIONADO", False: "Resto de flota"})

            df_resumen_flota = df_resumen_flota.sort_values("HRS_OPERADAS", ascending=True)

            fig_barra = px.bar(
                df_resumen_flota,
                x="HRS_OPERADAS", y="NOMBR",
                orientation="h",
                color="ES_SELECCIONADO",
                color_discrete_map={
                    "⭐ SELECCIONADO": "#F6AD55",
                    "Resto de flota": "#5A6B7D"
                },
                labels={"HRS_OPERADAS": "Horas Acumuladas", "NOMBR": "Equipo"},
                text="HRS_OPERADAS",
                template="plotly_dark"
            )
            fig_barra.update_traces(texttemplate="%{text:.1f} h", textposition="outside")
            fig_barra.update_layout(showlegend=False,
                                     xaxis_title="Horas Acumuladas",
                                     yaxis_title="Equipo")
            st.plotly_chart(fig_barra, use_container_width=True)
        else:
            st.info("No hay datos de flota para este período.")

    st.markdown("---")

    st.subheader(f"Rendimiento Mensual - {nombre_seleccionado}")
    df_equipo_todos = df_horometro_equipo.dropna(subset=["HRS_OPERADAS"])

    if not df_equipo_todos.empty:
        df_mensual = (df_equipo_todos
                      .groupby(["ANIO", "MES_NUM"])["HRS_OPERADAS"]
                      .sum()
                      .reset_index())

        anio_ref = int(df_mensual["ANIO"].max())
        df_anio = df_mensual[df_mensual["ANIO"] == anio_ref].copy()

        ABREV_MES = {
            1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr",
            5: "May", 6: "Jun", 7: "Jul", 8: "Ago",
            9: "Set", 10: "Oct", 11: "Nov", 12: "Dic"
        }
        meses_eje = list(range(1, 13))
        etiquetas_eje = [ABREV_MES[m] for m in meses_eje]

        horas_por_mes = {m: 0 for m in meses_eje}
        for _, r in df_anio.iterrows():
            horas_por_mes[int(r["MES_NUM"])] = float(r["HRS_OPERADAS"])

        colores = []
        etiquetas_texto = []
        for m in meses_eje:
            if m == mes_sel_num and horas_por_mes[m] > 0:
                colores.append("#F6AD55")
                etiquetas_texto.append(f"{horas_por_mes[m]:.0f} h")
            elif horas_por_mes[m] > 0:
                colores.append("#5A6B7D")
                etiquetas_texto.append(f"{horas_por_mes[m]:.0f} h")
            else:
                colores.append("rgba(0,0,0,0)")
                etiquetas_texto.append("")

        fig_mensual = go.Figure()
        fig_mensual.add_trace(go.Bar(
            x=etiquetas_eje,
            y=[horas_por_mes[m] for m in meses_eje],
            marker_color=colores,
            text=etiquetas_texto,
            textposition="outside",
            width=0.5,
            hovertemplate="<b>%{x}</b><br>Horas: %{y:.0f}<extra></extra>"
        ))
        fig_mensual.update_layout(
            showlegend=False,
            xaxis_title="Mes",
            yaxis_title="Horas Operadas",
            height=280,
            margin=dict(l=40, r=20, t=30, b=40),
            bargap=0.4,
            xaxis=dict(categoryorder="array", categoryarray=etiquetas_eje)
        )
        st.plotly_chart(fig_mensual, use_container_width=True)
    else:
        st.info("Sin registros de horas para este equipo.")


# ------------------------------------------
# TAB 2: NEUMÁTICOS
# ------------------------------------------
with tab_neumaticos:
    st.header(f"Control de Neumáticos - {nombre_seleccionado}")

    COCADA_CRITICA = 25
    COCADA_MINIMA = 50
    DELTA_ROTACION = 8
    COCADA_NUEVA_MAX = 100.0

    COLOR_ESTADO_HEX = {
        "🟢 OK": ("#48BB78", "#2F855A"),
        "🟡 ATENCIÓN": ("#F6AD55", "#C05621"),
        "🔴 CRÍTICO": ("#F56565", "#C53030"),
        "⚪ SIN DATO": ("#888888", "#555555"),
    }

    def _svg_llanta(pos_label, fila_opt, horometro):
        if fila_opt is None:
            return (
                '<div style="display:flex;flex-direction:column;align-items:center;'
                'padding:10px;border:2px dashed #555;border-radius:12px;'
                'background:#1a1a2e;margin:4px;min-height:180px;justify-content:center;">'
                f'<div style="font-size:13px;color:#aaa;font-weight:bold;'
                f'margin-bottom:8px;">{pos_label}</div>'
                '<svg viewBox="0 0 140 90" width="150" height="95">'
                '<rect x="10" y="20" width="120" height="50" rx="8" '
                'fill="#2d2d44" stroke="#444" stroke-width="2"/>'
                '<text x="70" y="50" text-anchor="middle" font-size="11" fill="#777">'
                'SIN DATOS</text></svg></div>'
            )

        ext = fila_opt.get("EXTERIOR", pd.NA)
        int_ = fila_opt.get("INTERIOR", pd.NA)
        estado = fila_opt["ESTADO"]
        rotacion = fila_opt["ROTACION"]
        delta = fila_opt["DELTA"]
        color, color_dark = COLOR_ESTADO_HEX.get(estado, ("#888888", "#555555"))

        h_max_px = 55
        ext_val = 0 if pd.isna(ext) else float(ext)
        int_val = 0 if pd.isna(int_) else float(int_)
        h_ext = max(4, min(h_max_px, (ext_val / COCADA_NUEVA_MAX) * h_max_px)) if ext_val > 0 else 0
        h_int = max(4, min(h_max_px, (int_val / COCADA_NUEVA_MAX) * h_max_px)) if int_val > 0 else 0
        base_y = 75
        y_ext = base_y - h_ext
        y_int = base_y - h_int
        dash = 'stroke-dasharray="5,3"' if rotacion.startswith("🔄") else ""
        borde_rot = "#F6E05E" if rotacion.startswith("🔄") else "transparent"
        hor_txt = f"{horometro:,.0f} h" if pd.notna(horometro) else "—"

        ext_txt = f"{ext:.1f}" if pd.notna(ext) else "—"
        int_txt = f"{int_:.1f}" if pd.notna(int_) else "—"
        delta_txt = f"{delta:+.1f}" if pd.notna(delta) else "—"

        return (
            '<div style="display:flex;flex-direction:column;align-items:center;'
            f'padding:10px;border:3px solid {borde_rot};border-radius:14px;'
            'background:#1a1a2e;margin:4px;min-height:180px;'
            f'box-shadow:0 0 0 1px {color_dark};">'
            f'<div style="font-size:13px;color:#ddd;font-weight:bold;'
            f'margin-bottom:6px;">{pos_label}</div>'
            '<svg viewBox="0 0 140 90" width="160" height="100">'
            f'<rect x="10" y="15" width="120" height="62" rx="10" '
            f'fill="#2d2d44" stroke="{color}" stroke-width="2"/>'
            f'<rect x="20" y="{y_int:.2f}" width="45" height="{h_int:.2f}" rx="4" '
            f'fill="{color}" opacity="0.85" {dash}/>'
            f'<rect x="75" y="{y_ext:.2f}" width="45" height="{h_ext:.2f}" rx="4" '
            f'fill="{color}" opacity="0.85" {dash}/>'
            f'<line x1="14" y1="{base_y}" x2="126" y2="{base_y}" '
            'stroke="#555555" stroke-width="1" stroke-dasharray="2,2"/>'
            '<text x="42" y="86" text-anchor="middle" font-size="9" fill="#aaaaaa">INT</text>'
            '<text x="97" y="86" text-anchor="middle" font-size="9" fill="#aaaaaa">EXT</text>'
            f'<text x="42" y="{max(12, y_int - 3):.2f}" text-anchor="middle" '
            f'font-size="10" fill="#ffffff" font-weight="bold">{int_txt}</text>'
            f'<text x="97" y="{max(12, y_ext - 3):.2f}" text-anchor="middle" '
            f'font-size="10" fill="#ffffff" font-weight="bold">{ext_txt}</text>'
            '</svg>'
            f'<div style="font-size:11px;color:{color};font-weight:bold;'
            f'margin-top:4px;">{estado} · Δ {delta_txt} mm</div>'
            f'<div style="font-size:10px;color:#888888;margin-top:2px;">'
            f'{rotacion} · {hor_txt}</div>'
            '</div>'
        )

    df_n_equipo = (df_neumaticos[df_neumaticos["ID_EQUIPO"] == id_equipo_sel]
                   .dropna(subset=["FECHA_MEDICION"])
                   .sort_values("FECHA_MEDICION")) if "FECHA_MEDICION" in df_neumaticos.columns else pd.DataFrame()

    if df_n_equipo.empty:
        st.info("No se registran inspecciones de neumáticos para este equipo.")
    else:
        df_n_equipo = df_n_equipo.copy()
        df_n_equipo["COCADA"] = pd.to_numeric(df_n_equipo["COCADA"], errors="coerce")

        ultima = (df_n_equipo.sort_values("FECHA_MEDICION")
                  .groupby(["POSICION", "CARA"], as_index=False)
                  .tail(1))

        horometro_por_pos = (ultima.groupby("POSICION")["HOROMETRO_MAQUINA"]
                             .max().to_dict()) if "HOROMETRO_MAQUINA" in ultima.columns else {}

        pivot = ultima.pivot_table(index="POSICION", columns="CARA",
                                    values="COCADA", aggfunc="last")
        for c in ["EXTERIOR", "INTERIOR"]:
            if c not in pivot.columns:
                pivot[c] = pd.NA
        pivot = pivot[["EXTERIOR", "INTERIOR"]]

        pivot["DELTA"] = (pivot["EXTERIOR"] - pivot["INTERIOR"]).round(1)
        pivot["COCADA_MIN"] = pivot[["EXTERIOR", "INTERIOR"]].min(axis=1, skipna=True)
        pivot["COCADA_MAX"] = pivot[["EXTERIOR", "INTERIOR"]].max(axis=1, skipna=True)

        def _estado_cocada(mm):
            if pd.isna(mm):
                return "⚪ SIN DATO"
            if mm < COCADA_CRITICA:
                return "🔴 CRÍTICO"
            elif mm < COCADA_MINIMA:
                return "🟡 ATENCIÓN"
            else:
                return "🟢 OK"

        def _estado_rotacion(delta, cocada_min, cocada_max):
            motivos = []
            if pd.notna(delta) and abs(delta) > DELTA_ROTACION:
                motivos.append("desgaste desigual")
            if pd.notna(cocada_max) and cocada_max <= COCADA_MINIMA:
                motivos.append("cocada baja")
            if motivos:
                return "🔄 ROTAR · " + " + ".join(motivos)
            return "✅ UNIFORME"

        pivot["ESTADO"] = pivot["COCADA_MIN"].apply(_estado_cocada)
        pivot["ROTACION"] = pivot.apply(
            lambda r: _estado_rotacion(r["DELTA"], r["COCADA_MIN"], r["COCADA_MAX"]),
            axis=1
        )
        pivot = pivot.reset_index()

        valores_validos = pivot[["EXTERIOR", "INTERIOR"]].values.flatten()
        valores_validos = valores_validos[~pd.isna(valores_validos)]
        cocada_min_global = valores_validos.min() if len(valores_validos) else 0
        cocada_promedio = valores_validos.mean() if len(valores_validos) else 0
        deltas_validos = pivot["DELTA"].dropna()
        delta_max = deltas_validos.abs().max() if len(deltas_validos) else 0
        n_alertas = ((pivot["ESTADO"].isin(["🔴 CRÍTICO", "🟡 ATENCIÓN"])) |
                     (pivot["ROTACION"].str.startswith("🔄"))).sum()

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Cocada Mínima", f"{cocada_min_global:.1f} mm",
                  delta=f"{cocada_min_global - COCADA_MINIMA:+.1f} vs mín.",
                  delta_color="inverse" if cocada_min_global < COCADA_MINIMA else "normal")
        k2.metric("Cocada Promedio", f"{cocada_promedio:.1f} mm")
        if delta_max > 0:
            k3.metric("Delta Máx. EXT/INT", f"{delta_max:.1f} mm",
                      delta="Requiere rotación" if delta_max > DELTA_ROTACION else "Uniforme",
                      delta_color="inverse" if delta_max > DELTA_ROTACION else "normal")
        else:
            k3.metric("Delta Máx. EXT/INT", "—",
                      delta="Sin ambas caras", delta_color="off")
        k4.metric("Neumáticos en Alerta", f"{n_alertas} / {len(pivot)}")

        st.markdown("---")
        st.subheader("Mapa de Neumáticos")

        def _fila_pivote(pos_key):
            fila = pivot[pivot["POSICION"] == pos_key]
            return None if fila.empty else fila.iloc[0]

        st.markdown("##### 🔹 Eje Delantero")
        d1, d2 = st.columns(2)
        with d1:
            st.markdown(_svg_llanta("Delantero Izquierdo",
                                     _fila_pivote("DEL_IZQ"),
                                     horometro_por_pos.get("DEL_IZQ")),
                        unsafe_allow_html=True)
        with d2:
            st.markdown(_svg_llanta("Delantero Derecho",
                                     _fila_pivote("DEL_DER"),
                                     horometro_por_pos.get("DEL_DER")),
                        unsafe_allow_html=True)

        st.markdown(
            "<div style='text-align:center;color:#666666;font-size:12px;"
            "margin:10px 0;'>──────────── 🚜 EQUIPO ────────────</div>",
            unsafe_allow_html=True
        )

        st.markdown("##### 🔹 Eje Trasero")
        t1, t2 = st.columns(2)
        with t1:
            st.markdown(_svg_llanta("Posterior Izquierdo",
                                     _fila_pivote("POST_IZQ"),
                                     horometro_por_pos.get("POST_IZQ")),
                        unsafe_allow_html=True)
        with t2:
            st.markdown(_svg_llanta("Posterior Derecho",
                                     _fila_pivote("POST_DER"),
                                     horometro_por_pos.get("POST_DER")),
                        unsafe_allow_html=True)

        st.caption(
            f"🎨 **Leyenda:** "
            f"🟢 ≥{COCADA_MINIMA} · 🟡 {COCADA_CRITICA}-{COCADA_MINIMA} · "
            f"🔴 <{COCADA_CRITICA} · 🟨 borde amarillo = requiere rotación."
        )

        st.markdown("---")

        rotaciones = pivot[pivot["ROTACION"].str.startswith("🔄")]
        if not rotaciones.empty:
            st.subheader("🔄 Recomendaciones de Rotación")
            st.warning(
                f"Se detectaron **{len(rotaciones)}** neumático(s) que requieren atención "
                f"(delta > {DELTA_ROTACION} mm entre caras o cocada baja)."
            )
            for _, r in rotaciones.iterrows():
                ext_v = f"{r['EXTERIOR']:.1f}" if pd.notna(r["EXTERIOR"]) else "—"
                int_v = f"{r['INTERIOR']:.1f}" if pd.notna(r["INTERIOR"]) else "—"
                delta_v = f"{r['DELTA']:+.1f}" if pd.notna(r["DELTA"]) else "—"
                st.markdown(
                    f"- **{r['POSICION']}** → EXT: {ext_v} mm | "
                    f"INT: {int_v} mm | Delta: **{delta_v} mm** · {r['ROTACION']}"
                )

        st.markdown("---")
        st.subheader("Tendencia Histórica de Desgaste (mm)")
        df_trend = df_n_equipo.copy()
        fig_trend = go.Figure()
        colores = {
            "DEL_IZQ": "#F6AD55", "DEL_DER": "#4FD1C5",
            "POST_IZQ": "#63B3ED", "POST_DER": "#FC8181"
        }
        for pos in ["DEL_IZQ", "DEL_DER", "POST_IZQ", "POST_DER"]:
            for cara in ["EXTERIOR", "INTERIOR"]:
                sub = df_trend[(df_trend["POSICION"] == pos) &
                               (df_trend["CARA"] == cara)].dropna(subset=["COCADA"])
                if sub.empty:
                    continue
                fig_trend.add_trace(go.Scatter(
                    x=sub["FECHA_MEDICION"], y=sub["COCADA"],
                    mode="lines+markers",
                    name=f"{pos} · {cara[:3]}",
                    line=dict(color=colores.get(pos, "#888888"),
                              dash="solid" if cara == "EXTERIOR" else "dash",
                              width=2),
                    marker=dict(size=5),
                    connectgaps=False
                ))

        fig_trend.update_layout(
            template="plotly_dark",
            xaxis_title="Fecha de Medición",
            yaxis_title="Cocada (mm)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1),
            height=450
        )
        fig_trend.add_hline(y=COCADA_MINIMA, line_dash="dot", line_color="orange",
                            annotation_text=f"Mínima operativa ({COCADA_MINIMA} mm)")
        fig_trend.add_hline(y=COCADA_CRITICA, line_dash="dot", line_color="red",
                            annotation_text=f"Crítica ({COCADA_CRITICA} mm)")
        st.plotly_chart(fig_trend, use_container_width=True)
        st.caption("Líneas sólidas = Cara EXTERIOR · Líneas punteadas = Cara INTERIOR. "
                   "Si las líneas se cruzan, indica que el neumático fue rotado/volteado.")


# ------------------------------------------
# TAB 3: COMPONENTES
# ------------------------------------------
with tab_componentes:
    st.header(f"Evolución de Componentes Mayores - {nombre_seleccionado}")

    if df_componentes.empty or "ID_EQUIPO" not in df_componentes.columns:
        st.info("No hay datos de componentes disponibles.")
    else:
        df_c_equipo = df_componentes[df_componentes["ID_EQUIPO"] == id_equipo_sel].copy()

        if "DEVOLVER_CAMBIO" in df_c_equipo.columns:
            mask_devuelto = (df_c_equipo["DEVOLVER_CAMBIO"]
                             .astype(str).str.strip().str.upper()
                             .isin(["SI", "SÍ", "S", "YES", "Y", "TRUE", "1"]))
            df_c_equipo = df_c_equipo[~mask_devuelto]

        if "HOROMETRO_CAMBIO(PROYECTADO)" in df_c_equipo.columns:
            df_c_equipo = df_c_equipo.dropna(subset=["HOROMETRO_CAMBIO(PROYECTADO)"])
            df_c_equipo = df_c_equipo[df_c_equipo["HOROMETRO_CAMBIO(PROYECTADO)"] > 0]

        if not df_c_equipo.empty:
            ultimo_h = df_horometro_equipo["HFINAL"].max()

            if pd.notna(ultimo_h):
                df_c_equipo["HORAS_RESTANTES"] = (
                    df_c_equipo["HOROMETRO_CAMBIO(PROYECTADO)"] - ultimo_h
                )

                def _clasificar(h):
                    if h <= 0:
                        return "CRITICO"
                    elif h <= 500:
                        return "ATENCION"
                    else:
                        return "OK"

                df_c_equipo["ESTADO"] = df_c_equipo["HORAS_RESTANTES"].apply(_clasificar)
                orden = {"CRITICO": 0, "ATENCION": 1, "OK": 2}
                df_c_equipo = df_c_equipo.sort_values(
                    by=["ESTADO", "HORAS_RESTANTES"],
                    key=lambda s: s.map(orden) if s.name == "ESTADO" else s,
                    ascending=[True, True]
                )

                n_crit = (df_c_equipo["ESTADO"] == "CRITICO").sum()
                n_aten = (df_c_equipo["ESTADO"] == "ATENCION").sum()
                n_ok = (df_c_equipo["ESTADO"] == "OK").sum()

                st.markdown(
                    f"### 🚨 Alertas Preventivas de Ciclo de Vida "
                    f"(Horómetro Máquina: **{ultimo_h:,.1f} Hrs**)"
                )
                m1, m2, m3 = st.columns(3)
                m1.metric("🔴 Críticos", n_crit)
                m2.metric("🟡 Próximos", n_aten)
                m3.metric("🟢 OK", n_ok)

                st.markdown("---")

                for _, row in df_c_equipo.iterrows():
                    h_cambio = row["HOROMETRO_CAMBIO(PROYECTADO)"]
                    h_inst = row.get("HOROMETRO_INSTALACION", None)
                    horas_restantes = row["HORAS_RESTANTES"]

                    if pd.notna(h_inst) and h_cambio > h_inst:
                        vida_total = h_cambio - h_inst
                        consumida = max(0.0, min(1.0, (ultimo_h - h_inst) / vida_total))
                    else:
                        consumida = None

                    tipo = row.get("TIPO_COMPONENTE", "—")
                    desc = row.get("DESCRIPCION", "—")

                    with st.container(border=True):
                        cc1, cc2 = st.columns([3, 1])
                        with cc1:
                            st.markdown(f"**{tipo}** — {desc}")
                        with cc2:
                            if consumida is not None:
                                st.caption(f"Vida usada: {consumida*100:.1f}%")

                        if consumida is not None:
                            st.progress(consumida)

                        if horas_restantes <= 0:
                            st.error(
                                f"🔴 CRÍTICO: El componente **{tipo}** ({desc}) superó su "
                                f"límite de cambio proyectado por **{abs(horas_restantes):,.1f} horas**. "
                                f"¡Agendar parada técnica inmediata!"
                            )
                        elif horas_restantes <= 500:
                            st.warning(
                                f"🟡 ATENCIÓN: El componente **{tipo}** está próximo al desgaste "
                                f"programado. Quedan **{horas_restantes:,.1f} horas**."
                            )
                        else:
                            st.success(
                                f"🟢 O.K: Componente **{tipo}** operativo. Cuenta con "
                                f"**{horas_restantes:,.1f} horas** de trabajo seguro disponible."
                            )
            else:
                st.info("No se registran lecturas de horómetro recientes para calcular las alertas.")
        else:
            st.info("No se registran componentes mayores activos asociados a este equipo.")


# ------------------------------------------
# TAB 4: ENGRASE
# ------------------------------------------
with tab_engrase:
    st.header(f"Control de Engrase - {nombre_seleccionado}")

    if df_engrase.empty or "ID_EQUIPO" not in df_engrase.columns:
        st.info("No hay datos de engrase disponibles.")
    else:
        df_e_equipo = (df_engrase[df_engrase["ID_EQUIPO"] == id_equipo_sel]
                       .dropna(subset=["FECHA"])
                       .sort_values("FECHA"))

        if df_e_equipo.empty:
            st.info("No se registran engrases para este equipo.")
        else:
            df_e_mes = (df_e_equipo[df_e_equipo["MES_NUM"] == mes_sel_num]
                        if mes_sel_num else df_e_equipo)

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.metric("Registros de Engrase (Mes)", f"{len(df_e_mes)}")
            with k2:
                pct_prom = (df_e_mes["PCT_CUMPLIMIENTO"].mean()
                            if not df_e_mes.empty else 0)
                st.metric("% Cumplimiento Promedio", f"{pct_prom:.1f}%")
            with k3:
                kg_total = (df_e_mes["CANTIDAD_GRASA_KG"].sum()
                            if "CANTIDAD_GRASA_KG" in df_e_mes.columns and not df_e_mes.empty
                            else 0)
                st.metric("Grasa Consumida (Mes)", f"{kg_total:.1f} kg")
            with k4:
                ultimo_engrase = df_e_equipo["FECHA"].max()
                dias_desde = (pd.Timestamp.now().normalize() - ultimo_engrase).days
                st.metric("Último Engrase",
                          f"Hace {dias_desde} día(s)",
                          delta=f"{ultimo_engrase.strftime('%d/%m/%Y')}",
                          delta_color="off")

            st.markdown("---")
            st.subheader("Calendario de Cumplimiento del Mes")

            if mes_sel_num and not df_e_mes.empty:
                anio_ref = (df_e_mes["ANIO"].mode().iloc[0]
                            if not df_e_mes.empty else pd.Timestamp.now().year)
                cal = calendar.Calendar(firstweekday=0)
                dias_mes = cal.monthdayscalendar(anio_ref, mes_sel_num)

                resumen_dias = {}
                for _, r in df_e_mes.iterrows():
                    dia = r["FECHA"].day
                    if dia not in resumen_dias:
                        resumen_dias[dia] = {"cumplido": "SI",
                                              "pct": r["PCT_CUMPLIMIENTO"]}
                    else:
                        if r.get("CUMPLIDO") == "NO":
                            resumen_dias[dia]["cumplido"] = "NO"
                        resumen_dias[dia]["pct"] = min(resumen_dias[dia]["pct"],
                                                        r["PCT_CUMPLIMIENTO"])

                html_cal = (
                    '<table style="width:100%;border-collapse:collapse;text-align:center;'
                    'font-size:13px;">'
                    '<tr style="background:#2d2d44;color:#ddd;">'
                    '<th style="padding:6px;">Lun</th><th style="padding:6px;">Mar</th>'
                    '<th style="padding:6px;">Mié</th><th style="padding:6px;">Jue</th>'
                    '<th style="padding:6px;">Vie</th><th style="padding:6px;">Sáb</th>'
                    '<th style="padding:6px;">Dom</th></tr>'
                )
                for semana in dias_mes:
                    html_cal += "<tr>"
                    for dia in semana:
                        if dia == 0:
                            html_cal += '<td style="padding:6px;"></td>'
                            continue
                        if dia in resumen_dias:
                            info = resumen_dias[dia]
                            if info["cumplido"] == "SI":
                                color = "#48BB78"
                                icon = "🟢"
                            else:
                                color = "#F6AD55"
                                icon = "🟡"
                            html_cal += (
                                f'<td style="padding:6px;background:{color};color:#fff;'
                                f'border-radius:4px;font-weight:bold;">'
                                f'{dia}<br><span style="font-size:10px;">'
                                f'{icon} {info["pct"]:.0f}%</span></td>'
                            )
                        else:
                            html_cal += (
                                f'<td style="padding:6px;background:#1a1a2e;color:#555;'
                                f'border:1px solid #333;border-radius:4px;">'
                                f'{dia}<br><span style="font-size:10px;">—</span></td>'
                            )
                    html_cal += "</tr>"
                html_cal += "</table>"
                st.markdown(html_cal, unsafe_allow_html=True)
                st.caption("🟢 Cumplido al 100% · 🟡 Parcial (<100%) · — Sin registro")
            else:
                st.info("Selecciona un mes con datos para ver el calendario.")

            st.markdown("---")
            st.subheader("Tendencia Mensual de Engrase")

            df_mes = df_e_equipo.groupby(["ANIO", "MES_NUM"]).agg(
                registros=("FECHA", "count"),
                cumplimiento_prom=("PCT_CUMPLIMIENTO", "mean"),
                grasa_total=("CANTIDAD_GRASA_KG", "sum")
                if "CANTIDAD_GRASA_KG" in df_e_equipo.columns
                else ("PCT_CUMPLIMIENTO", "count")
            ).reset_index()
            df_mes["MES_NOMBRE"] = df_mes["MES_NUM"].map(dicc_meses)
            df_mes["PERIODO"] = (df_mes["MES_NOMBRE"] + " "
                                 + df_mes["ANIO"].astype(str))

            fig_e = go.Figure()
            fig_e.add_trace(go.Bar(
                x=df_mes["PERIODO"], y=df_mes["registros"],
                name="Registros de engrase",
                marker_color="#4FD1C5",
                yaxis="y1",
                text=df_mes["registros"], textposition="outside"
            ))
            fig_e.add_trace(go.Scatter(
                x=df_mes["PERIODO"], y=df_mes["cumplimiento_prom"],
                name="% Cumplimiento",
                mode="lines+markers",
                line=dict(color="#F6AD55", width=3),
                marker=dict(size=8),
                yaxis="y2"
            ))
            fig_e.update_layout(
                template="plotly_dark",
                xaxis_title="Mes",
                yaxis=dict(title="Registros", side="left"),
                yaxis2=dict(title="% Cumplimiento", overlaying="y", side="right",
                            range=[0, 105]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02,
                            xanchor="right", x=1),
                height=400
            )
            st.plotly_chart(fig_e, use_container_width=True)


# ------------------------------------------
# TAB 5: KPIs HORÓMETROS & PARADAS
# (filtros PROPIOS dentro de la pestaña)
# ------------------------------------------
with tab_kpis:
    st.header("📊 KPIs Horómetros & Paradas")
    st.caption("Los filtros de esta pestaña son **independientes** del sidebar "
               "y solo afectan a los KPIs de Horómetros y Paradas.")

    # ==================================================
    # FILTROS DENTRO DE LA PESTAÑA
    # ==================================================
    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        equipos_kpi = sorted(df_horometro["ID_EQUIPO"].dropna().unique()) \
            if "ID_EQUIPO" in df_horometro.columns else []
        eq_kpi = st.multiselect("Equipo", equipos_kpi, default=[],
                                placeholder="Todos los equipos",
                                key="kpi_eq")

    with col_f2:
        turnos_kpi = sorted(df_horometro["TURNO"].dropna().unique()) \
            if "TURNO" in df_horometro.columns else []
        turno_kpi = st.multiselect("Turno", turnos_kpi, default=[],
                                    placeholder="Todos los turnos",
                                    key="kpi_turno")

    with col_f3:
        # Tipo de equipo: derivado del ID (prefijo SC-/DU-/DP-)
        if "ID_EQUIPO" in df_horometro.columns:
            df_horometro["TIPO_EQUIPO"] = df_horometro["ID_EQUIPO"].astype(str).str.split("-").str[0].map({
                "SC": "SCOOP", "DU": "DUMPER", "DP": "DUMPER"
            }).fillna("OTRO")
            tipos_kpi = sorted(df_horometro["TIPO_EQUIPO"].dropna().unique())
        else:
            tipos_kpi = []
        tipo_kpi = st.multiselect("Tipo de equipo", tipos_kpi, default=[],
                                   placeholder="Todos los tipos",
                                   key="kpi_tipo")

    # --- Filtro por período ---
    st.markdown("##### 📅 Filtro por período")
    modo_kpi = st.radio("Filtrar por:", ["Todo", "Semana", "Mes", "Rango de fechas"],
                        horizontal=True, label_visibility="collapsed",
                        key="kpi_modo")

    semana_kpi = []
    mes_kpi = []
    rango_kpi = None

    if modo_kpi == "Semana":
        if "NUMERO SEMANA" in df_horometro.columns:
            semanas_kpi = sorted(df_horometro["NUMERO SEMANA"]
                                 .dropna().astype(int).unique())
        else:
            semanas_kpi = []
        semana_kpi = st.multiselect("Semana(s)", semanas_kpi, default=[],
                                     placeholder="Todas las semanas",
                                     key="kpi_semana")

    elif modo_kpi == "Mes":
        if "PERIODO_MES" not in df_horometro.columns:
            df_horometro["PERIODO_MES"] = df_horometro["FECHA"].dt.strftime("%Y-%m")
            df_horometro["MES_NOMBRE"] = df_horometro["FECHA"].dt.strftime("%B").str.capitalize()
            df_horometro["ANIO"] = df_horometro["FECHA"].dt.year
        df_meses_kpi = (df_horometro.dropna(subset=["PERIODO_MES"])
                        .drop_duplicates("PERIODO_MES")
                        [["PERIODO_MES", "MES_NOMBRE", "ANIO"]]
                        .sort_values("PERIODO_MES"))
        opciones_mes_kpi = {
            f"{r.PERIODO_MES} · {r.MES_NOMBRE} {int(r.ANIO)}": r.PERIODO_MES
            for r in df_meses_kpi.itertuples()
        }
        labels_mes_kpi = st.multiselect("Mes(es)", list(opciones_mes_kpi.keys()),
                                         default=[],
                                         placeholder="Todos los meses",
                                         key="kpi_mes")
        mes_kpi = [opciones_mes_kpi[l] for l in labels_mes_kpi]

    elif modo_kpi == "Rango de fechas":
        if df_horometro["FECHA"].notna().any():
            fmin = df_horometro["FECHA"].min().date()
            fmax = df_horometro["FECHA"].max().date()
            rango_kpi = st.date_input("Rango",
                                       value=(fmin, fmax),
                                       min_value=fmin,
                                       max_value=fmax,
                                       key="kpi_rango")

    st.markdown("---")

    # ==================================================
    # APLICAR FILTROS A HORÓMETROS Y PARADAS
    # ==================================================
    hor_mes = df_horometro.copy()
    par_mes = df_paradas.copy() if not df_paradas.empty else pd.DataFrame()

    if eq_kpi:
        hor_mes = hor_mes[hor_mes["ID_EQUIPO"].isin(eq_kpi)]
        if "EQUIPO" in par_mes.columns:
            par_mes = par_mes[par_mes["EQUIPO"].isin(eq_kpi)]

    if turno_kpi and "TURNO" in hor_mes.columns:
        hor_mes = hor_mes[hor_mes["TURNO"].isin(turno_kpi)]
        if "TURNO" in par_mes.columns:
            par_mes = par_mes[par_mes["TURNO"].isin(turno_kpi)]

    if tipo_kpi and "TIPO_EQUIPO" in hor_mes.columns:
        hor_mes = hor_mes[hor_mes["TIPO_EQUIPO"].isin(tipo_kpi)]

    if semana_kpi and "NUMERO SEMANA" in hor_mes.columns:
        hor_mes = hor_mes[hor_mes["NUMERO SEMANA"].isin(semana_kpi)]
        if "FECHA" in par_mes.columns:
            par_mes = par_mes[par_mes["FECHA"].dt.isocalendar().week
                              .astype("Int64").isin(semana_kpi)]

    if mes_kpi and "PERIODO_MES" in hor_mes.columns:
        hor_mes = hor_mes[hor_mes["PERIODO_MES"].isin(mes_kpi)]
        if "PERIODO_MES" in par_mes.columns:
            par_mes = par_mes[par_mes["PERIODO_MES"].isin(mes_kpi)]

    if isinstance(rango_kpi, tuple) and len(rango_kpi) == 2:
        hor_mes = hor_mes[(hor_mes["FECHA"] >= pd.to_datetime(rango_kpi[0])) &
                          (hor_mes["FECHA"] <= pd.to_datetime(rango_kpi[1]))]
        if "FECHA" in par_mes.columns:
            par_mes = par_mes[(par_mes["FECHA"] >= pd.to_datetime(rango_kpi[0])) &
                              (par_mes["FECHA"] <= pd.to_datetime(rango_kpi[1]))]

    if hor_mes.empty and par_mes.empty:
        st.info("No hay registros de horómetro ni de paradas con los filtros seleccionados.")
    else:
        # --------------------------------------------------
        # KPIs POR AGREGACIÓN
        # --------------------------------------------------
        total_efec = float(hor_mes["HRS_OPERADAS"].sum()) if "HRS_OPERADAS" in hor_mes.columns else 0.0
        total_prog = float(hor_mes["HORAS_PROG"].sum()) if "HORAS_PROG" in hor_mes.columns else 0.0
        parada_mec = float(hor_mes["PARADA_MEC"].sum()) if "PARADA_MEC" in hor_mes.columns else 0.0
        parada_op  = float(hor_mes["PARADA_OP"].sum()) if "PARADA_OP" in hor_mes.columns else 0.0
        inspeccion = float(hor_mes["INSPECCION"].sum()) if "INSPECCION" in hor_mes.columns else 0.0
        n_fallas   = int(hor_mes["N_FALLAS"].sum()) if "N_FALLAS" in hor_mes.columns else 0

        if not par_mes.empty and "DURACION" in par_mes.columns:
            if parada_mec == 0 and "TIPO_UP" in par_mes.columns:
                mask_mec = par_mes["TIPO_UP"].str.contains("PM|MEC|MECAN", na=False)
                parada_mec = float(par_mes.loc[mask_mec, "DURACION"].sum())
                parada_op = float(par_mes.loc[~mask_mec, "DURACION"].sum())
            if n_fallas == 0:
                n_fallas = len(par_mes)

        if total_prog == 0:
            total_prog = total_efec + parada_mec + parada_op

        disp = ((total_prog - parada_mec) / total_prog * 100) if total_prog > 0 else 0.0
        util = (total_efec / total_prog * 100) if total_prog > 0 else 0.0
        horas_disponibles = total_prog - parada_mec
        util_efec = (total_efec / horas_disponibles * 100) if horas_disponibles > 0 else 0.0
        mtbf = total_efec / n_fallas if n_fallas else 0.0
        mttr = parada_mec / n_fallas if n_fallas else 0.0

        # --------------------------------------------------
        # TARJETAS KPI
        # --------------------------------------------------
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Horas Efectivas", f"{total_efec:,.1f} H",
                  f"{len(hor_mes)} registros")
        c2.metric("Parada Mecánica", f"{parada_mec:,.1f} H", "Correctivos")
        c3.metric("Parada Operativa", f"{parada_op:,.1f} H", "Operativas")
        c4.metric("# Fallas", f"{n_fallas}",
                  f"MTBF {mtbf:.1f} H | MTTR {mttr:.1f} H")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Disponibilidad Mecánica", f"{disp:.1f}%",
                  f"({horas_disponibles:.1f} H disp / {total_prog:.1f} H prog)")
        c6.metric("Utilización", f"{util:.1f}%",
                  f"({total_efec:.1f} H efec / {total_prog:.1f} H prog)")
        c7.metric("Horas Programadas", f"{total_prog:,.1f} H", "Planificado")
        c8.metric("Utilización Efectiva", f"{util_efec:.1f}%",
                  f"({total_efec:.1f} H efec / {horas_disponibles:.1f} H disp)")

        st.markdown("---")

        # --------------------------------------------------
        # GAUGES
        # --------------------------------------------------
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
            fig.update_layout(template="plotly_dark", height=250,
                              margin=dict(l=40, r=20, t=50, b=40))
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
            fig.update_layout(template="plotly_dark", height=250,
                              margin=dict(l=40, r=20, t=50, b=40))
            st.plotly_chart(fig, use_container_width=True)

        with g3:
            if not par_mes.empty and "TIPO DE PARADA" in par_mes.columns:
                kpi_tipo_par = (par_mes.groupby("TIPO DE PARADA")["DURACION"]
                                .sum().reset_index())
                fig = px.pie(kpi_tipo_par, values="DURACION",
                             names="TIPO DE PARADA", hole=0.55,
                             color_discrete_sequence=["#00D4FF", "#00E676",
                                                       "#FFA726", "#B388FF"])
                fig.update_layout(template="plotly_dark", height=250,
                                  title="Distribución de Paradas por Tipo",
                                  margin=dict(l=40, r=20, t=50, b=40))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sin datos de paradas para el gráfico.")

        # --------------------------------------------------
        # BARRAS + PARETO
        # --------------------------------------------------
        b1, b2 = st.columns([7, 5])

        with b1:
            if not hor_mes.empty and "FECHA" in hor_mes.columns:
                hor_agg = hor_mes.groupby("FECHA").agg({
                    "HRS_OPERADAS": "sum",
                    "PARADA_MEC": "sum",
                    "PARADA_OP": "sum",
                }).reset_index().sort_values("FECHA")
                fig = go.Figure()
                fig.add_bar(x=hor_agg["FECHA"], y=hor_agg["HRS_OPERADAS"],
                            name="Horas Efectivas", marker_color="#00E676")
                fig.add_bar(x=hor_agg["FECHA"], y=hor_agg["PARADA_MEC"],
                            name="P. Mecánica", marker_color="#FF5252")
                fig.add_bar(x=hor_agg["FECHA"], y=hor_agg["PARADA_OP"],
                            name="P. Operativa", marker_color="#FFA726")
                fig.update_layout(template="plotly_dark", barmode="group",
                                  height=380,
                                  title="Horas Efectivas vs Paradas por Fecha",
                                  legend=dict(orientation="h", y=-0.2),
                                  margin=dict(l=40, r=20, t=50, b=40))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sin registros de horómetro.")

        with b2:
            if not par_mes.empty and "TIPO DE PARADA" in par_mes.columns:
                pareto = (par_mes.groupby("TIPO DE PARADA")["DURACION"]
                          .sum().reset_index().sort_values("DURACION", ascending=False))
                pareto["Acum %"] = pareto["DURACION"].cumsum() / pareto["DURACION"].sum() * 100
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_bar(x=pareto["TIPO DE PARADA"], y=pareto["DURACION"],
                            marker_color="#FFA726", name="Horas")
                fig.add_scatter(x=pareto["TIPO DE PARADA"], y=pareto["Acum %"],
                                mode="lines+markers", name="Acum %",
                                line=dict(color="#00D4FF", width=3),
                                secondary_y=True)
                fig.update_layout(template="plotly_dark", height=380,
                                  title="Pareto de Paradas",
                                  legend=dict(orientation="h", y=-0.2),
                                  margin=dict(l=40, r=20, t=50, b=40))
                fig.update_yaxes(title_text="Horas", secondary_y=False)
                fig.update_yaxes(title_text="% Acum", secondary_y=True, range=[0, 105])
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sin datos de paradas para el período.")

        # --------------------------------------------------
        # TENDENCIA + TOP 10 FALLAS
        # --------------------------------------------------
        t1, t2 = st.columns([7, 5])

        with t1:
            if not hor_mes.empty and "FECHA" in hor_mes.columns:
                kpi_dia = hor_mes.groupby("FECHA").agg({
                    "HRS_OPERADAS": "sum",
                    "PARADA_MEC": "sum",
                }).reset_index().sort_values("FECHA")
                fig = go.Figure()
                fig.add_scatter(x=kpi_dia["FECHA"], y=kpi_dia["HRS_OPERADAS"],
                                mode="lines+markers", name="Efectivas",
                                line=dict(color="#00E676", width=3),
                                fill="tozeroy", fillcolor="rgba(0,230,118,0.15)")
                fig.add_scatter(x=kpi_dia["FECHA"], y=kpi_dia["PARADA_MEC"],
                                mode="lines+markers", name="P. Mecánica",
                                line=dict(color="#FF5252", width=2))
                fig.update_layout(template="plotly_dark", height=380,
                                  title="Tendencia Diaria",
                                  legend=dict(orientation="h", y=-0.2),
                                  margin=dict(l=40, r=20, t=50, b=40))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sin registros para la tendencia.")

        with t2:
            if not par_mes.empty and "DESCRIPCION DE LA FALLA" in par_mes.columns:
                top = (par_mes.groupby(["EQUIPO", "DESCRIPCION DE LA FALLA"])["DURACION"]
                       .sum().reset_index()
                       .sort_values("DURACION", ascending=False).head(10))
                fig = px.bar(top, x="DURACION", y="DESCRIPCION DE LA FALLA",
                             orientation="h", color="DURACION",
                             color_continuous_scale=["#FFA726", "#FF5252"])
                fig.update_layout(template="plotly_dark", height=380,
                                  title="Top 10 Fallas",
                                  coloraxis_showscale=False,
                                  yaxis=dict(autorange="reversed"),
                                  margin=dict(l=40, r=20, t=50, b=40))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sin paradas registradas.")

        # --------------------------------------------------
        # HEATMAP KPIs POR EQUIPO
        # --------------------------------------------------
        if not hor_mes.empty and all(c in hor_mes.columns for c in
                                     ["HORAS_PROG", "PARADA_MEC", "HRS_OPERADAS"]):
            heat_kpi = hor_mes.groupby("ID_EQUIPO").agg({
                "HORAS_PROG": "sum",
                "PARADA_MEC": "sum",
                "HRS_OPERADAS": "sum",
            }).reset_index()

            heat_kpi["Disponibilidad %"] = (
                (heat_kpi["HORAS_PROG"] - heat_kpi["PARADA_MEC"])
                / heat_kpi["HORAS_PROG"].replace(0, np.nan) * 100
            ).fillna(0).round(1)

            heat_kpi["Utilización %"] = (
                heat_kpi["HRS_OPERADAS"]
                / heat_kpi["HORAS_PROG"].replace(0, np.nan) * 100
            ).fillna(0).round(1)

            heat_matrix = heat_kpi.set_index("ID_EQUIPO")[
                ["Disponibilidad %", "Utilización %"]
            ]

            fig = px.imshow(heat_matrix.T, text_auto=".1f", aspect="auto",
                            color_continuous_scale=["#FF5252", "#FFA726", "#00E676"],
                            labels=dict(x="Equipo", y="KPI", color="%"))
            fig.update_layout(template="plotly_dark", height=260,
                              title="Mapa de Calor KPIs por Equipo",
                              margin=dict(l=40, r=20, t=50, b=40))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # --------------------------------------------------
        # SUB-TABS DE DETALLE
        # --------------------------------------------------
        st.markdown("## 📑 Registros de detalle (KPIs)")
        sub_hor, sub_par = st.tabs(["📋 Horómetros", "🛠️ Paradas (PARADAS-M)"])

        with sub_hor:
            st.markdown("### 📋 Registro de Horómetros (filtros de la pestaña)")
            st.caption("Registros que alimentan los KPIs.")

            cols_hor = ["FECHA", "TURNO", "ID_EQUIPO", "H_INICIAL", "HFINAL",
                        "HRS_OPERADAS", "PARADA_MEC", "PARADA_OP", "INSPECCION",
                        "HORAS_PROG", "N_FALLAS"]
            cols_ok_hor = [c for c in cols_hor if c in hor_mes.columns]
            show_hor = hor_mes[cols_ok_hor].copy()

            if "FECHA" in show_hor.columns:
                show_hor["FECHA"] = show_hor["FECHA"].dt.strftime("%d/%m/%Y")

            if ("HORAS_PROG" in show_hor.columns and
                    "PARADA_MEC" in show_hor.columns):
                show_hor["Disp. %"] = (
                    (show_hor["HORAS_PROG"] - show_hor["PARADA_MEC"])
                    / show_hor["HORAS_PROG"].replace(0, np.nan) * 100
                ).fillna(0).round(1)

            if ("HORAS_PROG" in show_hor.columns and
                    "HRS_OPERADAS" in show_hor.columns):
                show_hor["Util. %"] = (
                    show_hor["HRS_OPERADAS"]
                    / show_hor["HORAS_PROG"].replace(0, np.nan) * 100
                ).fillna(0).round(1)

            if "FECHA" in show_hor.columns:
                show_hor = show_hor.sort_values(
                    ["FECHA", "ID_EQUIPO"] if "ID_EQUIPO" in show_hor.columns else ["FECHA"],
                    ascending=[False] + ([True] if "ID_EQUIPO" in show_hor.columns else [])
                )

            st.dataframe(show_hor, use_container_width=True, height=500, hide_index=True)

            if not show_hor.empty:
                buf = BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as w:
                    show_hor.to_excel(w, index=False, sheet_name="HOROMETROS_KPI")
                st.download_button(
                    "⬇️ Descargar Horómetros KPIs (Excel)",
                    data=buf.getvalue(),
                    file_name="HOROMETROS_kpi.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

        with sub_par:
            st.markdown("### 🛠️ Registro de Paradas (filtros de la pestaña)")
            st.caption("Paradas que alimentan los KPIs.")

            if par_mes.empty:
                st.info("⚠️ No hay paradas con los filtros seleccionados.")
            else:
                cols_par = ["FECHA", "TURNO", "EQUIPO", "TIPO DE PARADA",
                            "DURACION", "DESCRIPCION DE LA FALLA"]
                cols_ok_par = [c for c in cols_par if c in par_mes.columns]
                show_par = par_mes[cols_ok_par].copy()

                if "FECHA" in show_par.columns:
                    show_par["FECHA"] = show_par["FECHA"].dt.strftime("%d/%m/%Y")

                sort_cols = [c for c in ["FECHA", "EQUIPO"] if c in show_par.columns]
                if sort_cols:
                    show_par = show_par.sort_values(
                        sort_cols, ascending=[False] + [True] * (len(sort_cols) - 1)
                    )

                st.dataframe(
                    show_par,
                    use_container_width=True,
                    height=480,
                    hide_index=True,
                    column_config={
                        "DURACION": st.column_config.NumberColumn(
                            "Duración (H)", format="%.2f H"
                        ),
                    },
                )

                st.caption(f"📊 {len(show_par):,} paradas mostradas")

                if not show_par.empty:
                    buf2 = BytesIO()
                    with pd.ExcelWriter(buf2, engine="openpyxl") as w:
                        show_par.to_excel(w, index=False, sheet_name="PARADAS_KPI")
                    st.download_button(
                        "⬇️ Descargar Paradas KPIs (Excel)",
                        data=buf2.getvalue(),
                        file_name="PARADAS_kpi.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

                st.markdown("#### 📈 Resumen por tipo de parada")
                if ("TIPO DE PARADA" in show_par.columns and
                        "DURACION" in show_par.columns):
                    resumen_tipo = (show_par.groupby("TIPO DE PARADA")
                                    .agg(N=("DURACION", "count"),
                                         Horas=("DURACION", "sum"),
                                         Promedio=("DURACION", "mean"))
                                    .reset_index()
                                    .sort_values("Horas", ascending=False))
                    resumen_tipo["Horas"] = resumen_tipo["Horas"].round(1)
                    resumen_tipo["Promedio"] = resumen_tipo["Promedio"].round(2)
                    st.dataframe(resumen_tipo, use_container_width=True, hide_index=True)

st.caption("Dashboard generado con Streamlit · Plotly · Pandas")
