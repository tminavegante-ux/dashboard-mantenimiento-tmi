import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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

st.title("CONTROL NEW MING 2026")
st.markdown("---")

# ==========================================
# 2. CARGA DE DATOS DESDE GOOGLE SHEETS
# ==========================================
@st.cache_data(ttl=300, show_spinner="Cargando datos de Google Sheets...")
def cargar_datos_marcio():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)

        # Leer las 5 hojas
        df_equipos = conn.read(worksheet="EQUIPOS", ttl=0)
        df_horometro = conn.read(worksheet="HOROMETRO", ttl=0)
        df_componentes = conn.read(worksheet="COMPONENTES", ttl=0)
        df_neumaticos = conn.read(worksheet="NEUMATICOS", ttl=0)
        df_engrase = conn.read(worksheet="ENGRASE", ttl=0)

        # --- Normalización de nombres de columnas ---
        def _norm_cols(df):
            df.columns = [str(c).strip().upper() for c in df.columns]
            return df

        df_equipos = _norm_cols(df_equipos)
        df_horometro = _norm_cols(df_horometro)
        df_componentes = _norm_cols(df_componentes)
        df_neumaticos = _norm_cols(df_neumaticos)
        df_engrase = _norm_cols(df_engrase)

        # --- Mapeo de variantes ---
        MAPEO_COLUMNAS = {
            "NOMBRE": "NOMBR",
            "NOMBRE_EQUIPO": "NOMBR",
            "NOMBR_EQUIPO": "NOMBR",
            "EQUIPO": "NOMBR",
            "H_FINAL": "HFINAL",
            "HRS_FINAL": "HFINAL",
            "HORA_FINAL": "HFINAL",
            "H_INICIO": "H_INICIAL",
            "HRS_INICIAL": "H_INICIAL",
            "HORA_INICIAL": "H_INICIAL",
            "HOROMETRO_CAMBIO (PROYECTADO)": "HOROMETRO_CAMBIO(PROYECTADO)",
            "HOROMETRO_CAMBIO_PROYECTADO": "HOROMETRO_CAMBIO(PROYECTADO)",
        }

        def _rename_variants(df):
            return df.rename(columns={k: v for k, v in MAPEO_COLUMNAS.items()
                                     if k in df.columns})

        df_equipos = _rename_variants(df_equipos)
        df_horometro = _rename_variants(df_horometro)
        df_componentes = _rename_variants(df_componentes)
        df_neumaticos = _rename_variants(df_neumaticos)
        df_engrase = _rename_variants(df_engrase)

        # --- Validación de columnas requeridas ---
        requeridas = {
            "EQUIPOS": (df_equipos, ["ID_EQUIPO", "NOMBR"]),
            "HOROMETRO": (df_horometro, ["FECHA", "ID_EQUIPO", "H_INICIAL",
                                          "HFINAL", "STATUS_EQUIPO", "TURNO"]),
            "COMPONENTES": (df_componentes, ["ID_EQUIPO", "TIPO_COMPONENTE",
                                              "HOROMETRO_CAMBIO(PROYECTADO)"]),
            "NEUMATICOS": (df_neumaticos, ["FECHA_MEDICION", "ID_EQUIPO",
                                            "POSICION", "CARA", "COCADA"]),
            "ENGRASE": (df_engrase, ["FECHA", "ID_EQUIPO", "PUNTOS_ENGRASADOS",
                                      "PUNTOS_TOTALES", "CUMPLIDO"]),
        }
        for hoja, (df, cols) in requeridas.items():
            faltantes = [c for c in cols if c not in df.columns]
            if faltantes:
                raise ValueError(
                    f"Hoja '{hoja}' le faltan columnas: {faltantes}. "
                    f"Columnas encontradas: {list(df.columns)}"
                )

        # --- Normalización de ID_EQUIPO ---
        for df in (df_equipos, df_horometro, df_componentes,
                   df_neumaticos, df_engrase):
            if 'ID_EQUIPO' in df.columns:
                df['ID_EQUIPO'] = df['ID_EQUIPO'].astype(str).str.strip()

        if 'NOMBR' in df_equipos.columns:
            df_equipos['NOMBR'] = df_equipos['NOMBR'].astype(str).str.strip()
        if 'POSICION' in df_neumaticos.columns:
            df_neumaticos['POSICION'] = df_neumaticos['POSICION'].astype(str).str.strip()
        if 'CARA' in df_neumaticos.columns:
            df_neumaticos['CARA'] = df_neumaticos['CARA'].astype(str).str.strip().str.upper()

        # --- Fechas ---
        df_horometro['FECHA'] = pd.to_datetime(df_horometro['FECHA'], errors='coerce')
        df_componentes['FECHA_INSTALACION'] = pd.to_datetime(
            df_componentes['FECHA_INSTALACION'], errors='coerce')
        df_neumaticos['FECHA_MEDICION'] = pd.to_datetime(
            df_neumaticos['FECHA_MEDICION'], errors='coerce')
        df_engrase['FECHA'] = pd.to_datetime(df_engrase['FECHA'], errors='coerce')

        # --- Cálculos ---
        df_horometro['HRS_OPERADAS'] = df_horometro['HFINAL'] - df_horometro['H_INICIAL']
        df_horometro.loc[df_horometro['HFINAL'].isna(), 'HRS_OPERADAS'] = pd.NA
        df_horometro.loc[df_horometro['HRS_OPERADAS'] < 0, 'HRS_OPERADAS'] = pd.NA
        df_horometro['MES_NUM'] = df_horometro['FECHA'].dt.month
        df_horometro['ANIO'] = df_horometro['FECHA'].dt.year

        df_engrase['MES_NUM'] = df_engrase['FECHA'].dt.month
        df_engrase['ANIO'] = df_engrase['FECHA'].dt.year
        df_engrase['PCT_CUMPLIMIENTO'] = (
            df_engrase['PUNTOS_ENGRASADOS'] / df_engrase['PUNTOS_TOTALES'] * 100
        ).round(1)

        return (df_equipos, df_horometro, df_componentes, df_neumaticos,
                df_engrase, True, "Google Sheets")

    except Exception as e:
        df_vacio_eq = pd.DataFrame(columns=['ID_EQUIPO', 'NOMBR'])
        df_vacio_ho = pd.DataFrame(columns=['FECHA', 'ID_EQUIPO', 'H_INICIAL', 'HFINAL',
                                            'HRS_OPERADAS', 'MES_NUM', 'ANIO',
                                            'STATUS_EQUIPO', 'TURNO'])
        df_vacio_co = pd.DataFrame(columns=['ID_EQUIPO', 'TIPO_COMPONENTE',
                                            'HOROMETRO_CAMBIO(PROYECTADO)'])
        df_vacio_ne = pd.DataFrame(columns=['FECHA_MEDICION', 'ID_EQUIPO', 'POSICION',
                                            'CARA', 'COCADA'])
        df_vacio_en = pd.DataFrame(columns=['FECHA', 'ID_EQUIPO', 'TURNO', 'TECNICO',
                                            'PUNTOS_ENGRASADOS', 'PUNTOS_TOTALES',
                                            'TIPO_GRASA', 'CANTIDAD_GRASA_KG',
                                            'OBSERVACIONES', 'CUMPLIDO',
                                            'MES_NUM', 'ANIO', 'PCT_CUMPLIMIENTO'])
        return (df_vacio_eq, df_vacio_ho, df_vacio_co, df_vacio_ne,
                df_vacio_en, False, str(e))


(df_equipos, df_horometro, df_componentes, df_neumaticos, df_engrase,
 estado_carga, detalle_error) = cargar_datos_marcio()

if not estado_carga or df_equipos.empty:
    st.error("❌ No se pudo cargar los datos desde Google Sheets")
    st.markdown(f"**Detalle Técnico:** {detalle_error}")
    st.info("💡 Asegúrate de que el Google Sheet tenga las hojas EQUIPOS, HOROMETRO, COMPONENTES, NEUMATICOS y ENGRASE con las columnas correctas, y que esté compartido con el client_email de la cuenta de servicio.")
    st.stop()

# ==========================================
# 3. BARRA LATERAL
# ==========================================
st.sidebar.header("⚙️ Filtros de Control")

if st.sidebar.button("🔄 Refrescar datos", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

dicc_equipos = dict(zip(df_equipos['NOMBR'], df_equipos['ID_EQUIPO']))
nombre_seleccionado = st.sidebar.selectbox("Seleccione el Equipo:", list(dicc_equipos.keys()))
id_equipo_sel = dicc_equipos[nombre_seleccionado]

st.sidebar.markdown("---")
st.sidebar.subheader("📅 Filtro Temporal")

dicc_meses = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

df_horometro_equipo = df_horometro[df_horometro['ID_EQUIPO'] == id_equipo_sel]
meses_en_datos = sorted(df_horometro_equipo['MES_NUM'].dropna().astype(int).unique())

if meses_en_datos:
    nombres_meses_disponibles = [dicc_meses[m] for m in meses_en_datos]
    mes_sel_nombre = st.sidebar.radio("Meses Disponibles:", nombres_meses_disponibles)
    mes_sel_num = [k for k, v in dicc_meses.items() if v == mes_sel_nombre][0]
else:
    st.sidebar.warning("⚠️ No hay registros de horómetro para este equipo.")
    mes_sel_num = None

if mes_sel_num:
    df_h_filtrado_mes = df_horometro[df_horometro['MES_NUM'] == mes_sel_num]
    df_h_filtrado_equipo = df_h_filtrado_mes[df_h_filtrado_mes['ID_EQUIPO'] == id_equipo_sel]
else:
    df_h_filtrado_mes = pd.DataFrame()
    df_h_filtrado_equipo = pd.DataFrame()

# ==========================================
# 4. PESTAÑAS
# ==========================================
tab_horometros, tab_neumaticos, tab_componentes, tab_engrase = st.tabs([
    "⏱️ Horómetros & Flota",
    "🛞 Control de Neumáticos",
    "⚙️ Gestión de Componentes",
    "🛢️ Control de Engrase",
])

# ------------------------------------------
# TAB 1: HORÓMETROS Y FLOTA
# ------------------------------------------
with tab_horometros:
    st.header(f"Análisis de Utilización - {nombre_seleccionado}")

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        total_hrs = df_h_filtrado_equipo['HRS_OPERADAS'].sum() if not df_h_filtrado_equipo.empty else 0
        st.metric("Horas Operadas (Mes Seleccionado)", f"{total_hrs:,.1f} Hrs")
    with kpi2:
        ultimo_horometro = df_horometro_equipo['HFINAL'].max()
        st.metric("Último Horómetro Registrado",
                  f"{ultimo_horometro:,.1f} Hrs" if pd.notna(ultimo_horometro) else "0.0 Hrs")
    with kpi3:
        status_actual = (df_h_filtrado_equipo.sort_values('FECHA').iloc[-1]['STATUS_EQUIPO']
                         if not df_h_filtrado_equipo.empty else "SIN REGISTRO")
        st.metric("Último Estado Operativo", str(status_actual).upper())
    with kpi4:
        if not df_h_filtrado_equipo.empty:
            turnos_operativos = (df_h_filtrado_equipo['STATUS_EQUIPO'] == 'OPERATIVO').sum()
            turnos_inoperativos = (df_h_filtrado_equipo['STATUS_EQUIPO'] != 'OPERATIVO').sum()
            total_turnos = turnos_operativos + turnos_inoperativos
            disponibilidad = (turnos_operativos / total_turnos * 100) if total_turnos > 0 else 0

            st.markdown(
                f"""
                <div style="padding:0;">
                    <div style="font-size:14px;color:#fafafa;margin-bottom:8px;">
                        Turnos Operativos / Inoperativos
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

       st.subheader(f"📊 Rendimiento Mensual - {nombre_seleccionado}")

    df_equipo_todos = df_horometro_equipo.copy()
    df_equipo_todos = df_equipo_todos.dropna(subset=['HRS_OPERADAS'])

    if not df_equipo_todos.empty:
        # Agrupar por año y mes
        df_mensual = (df_equipo_todos
                      .groupby(['ANIO', 'MES_NUM'])['HRS_OPERADAS']
                      .sum()
                      .reset_index())

        # Determinar el año de referencia (el más reciente con datos)
        anio_ref = int(df_mensual['ANIO'].max())

        # Crear una fila para cada uno de los 12 meses del año de referencia
        todos_meses = pd.DataFrame({
            'MES_NUM': list(range(1, 13)),
            'ANIO': [anio_ref] * 12
        })
        todos_meses['MES_NOMBRE'] = todos_meses['MES_NUM'].map(dicc_meses)
        todos_meses['PERIODO'] = todos_meses['MES_NOMBRE'] + " " + todos_meses['ANIO'].astype(str)

        # Unir con los datos reales (los meses sin datos quedan como NaN → 0)
        df_mensual_full = todos_meses.merge(
            df_mensual[['ANIO', 'MES_NUM', 'HRS_OPERADAS']],
            on=['ANIO', 'MES_NUM'],
            how='left'
        )
        df_mensual_full['HRS_OPERADAS'] = df_mensual_full['HRS_OPERADAS'].fillna(0)

        # Marcar el mes actual
        df_mensual_full['ES_MES_ACTUAL'] = (
            (df_mensual_full['MES_NUM'] == mes_sel_num)
        ).map({True: "⭐ Mes Actual", False: "Otros meses"})

        # Marcar meses sin datos (para que se vean distintos)
        df_mensual_full['TIENE_DATOS'] = df_mensual_full['HRS_OPERADAS'] > 0

        fig_mensual = px.bar(
            df_mensual_full,
            x='PERIODO',
            y='HRS_OPERADAS',
            color='ES_MES_ACTUAL',
            color_discrete_map={
                "⭐ Mes Actual": "#F6AD55",
                "Otros meses": "#5A6B7D"
            },
            labels={'HRS_OPERADAS': 'Horas Operadas', 'PERIODO': 'Mes'},
            template="plotly_dark"
        )

        # Etiquetas solo en los meses con datos
        fig_mensual.update_traces(
            width=0.5,
            text=[f"{v:.0f} h" if v > 0 else "" for v in df_mensual_full['HRS_OPERADAS']],
            textposition='outside'
        )

        fig_mensual.update_layout(
            showlegend=False,
            xaxis_title="Mes",
            yaxis_title="Horas Operadas",
            height=280,
            margin=dict(l=40, r=20, t=30, b=60),
            bargap=0.3
        )

        # Rotar etiquetas si son largas
        fig_mensual.update_xaxes(tickangle=-45)

        st.plotly_chart(fig_mensual, use_container_width=True)
    else:
        st.info("Sin registros de horas para este equipo.")

    st.markdown("---")
    
    g1, g2 = st.columns(2)

    with g1:
        st.subheader(f"Desempeño Diario: {nombre_seleccionado}")
        if not df_h_filtrado_equipo.empty:
            fig_linea = px.line(
                df_h_filtrado_equipo.sort_values('FECHA'),
                x='FECHA', y='HRS_OPERADAS', color='TURNO',
                labels={'HRS_OPERADAS': 'Horas Trabajadas', 'FECHA': 'Día'},
                markers=True, template="plotly_dark"
            )
            st.plotly_chart(fig_linea, use_container_width=True)
        else:
            st.info("Sin registros de horas para este equipo en el mes seleccionado.")

    with g2:
        st.subheader("Comparativa de Horas Totales: Toda la Flota")
        if not df_h_filtrado_mes.empty:
            df_resumen_flota = (df_h_filtrado_mes.groupby('ID_EQUIPO')['HRS_OPERADAS']
                                .sum().reset_index())
            df_resumen_flota = df_resumen_flota.merge(df_equipos, on='ID_EQUIPO', how='left')

            df_resumen_flota['ES_SELECCIONADO'] = (
                df_resumen_flota['ID_EQUIPO'] == id_equipo_sel
            ).map({True: "⭐ SELECCIONADO", False: "Resto de flota"})

            df_resumen_flota = df_resumen_flota.sort_values('HRS_OPERADAS', ascending=True)

            fig_barra = px.bar(
                df_resumen_flota,
                x='HRS_OPERADAS', y='NOMBR',
                orientation='h',
                color='ES_SELECCIONADO',
                color_discrete_map={
                    "⭐ SELECCIONADO": "#F6AD55",
                    "Resto de flota": "#4A5568"
                },
                labels={'HRS_OPERADAS': 'Horas Acumuladas', 'NOMBR': 'Equipo'},
                text='HRS_OPERADAS',
                template="plotly_dark"
            )
            fig_barra.update_traces(texttemplate='%{text:.1f} h', textposition='outside')
            fig_barra.update_layout(showlegend=False,
                                     xaxis_title="Horas Acumuladas",
                                     yaxis_title="Equipo")
            st.plotly_chart(fig_barra, use_container_width=True)
        else:
            st.info("No hay datos de flota para este período.")

# ------------------------------------------
# TAB 2: NEUMÁTICOS
# ------------------------------------------
with tab_neumaticos:
    st.header(f"Control de Neumáticos - {nombre_seleccionado}")

    COCADA_CRITICA = 8
    COCADA_MINIMA = 12
    DELTA_ROTACION = 5
    COCADA_NUEVA_MAX = 80.0

    COLOR_ESTADO_HEX = {
        "🟢 OK": ("#48BB78", "#2F855A"),
        "🟡 ATENCIÓN": ("#F6AD55", "#C05621"),
        "🔴 CRÍTICO": ("#F56565", "#C53030"),
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

        ext = fila_opt['EXTERIOR']
        int_ = fila_opt['INTERIOR']
        estado = fila_opt['ESTADO']
        rotacion = fila_opt['ROTACION']
        delta = fila_opt['DELTA']
        color, color_dark = COLOR_ESTADO_HEX.get(estado, ("#888888", "#555555"))

        h_max_px = 55
        h_ext = max(4, min(h_max_px, (ext / COCADA_NUEVA_MAX) * h_max_px))
        h_int = max(4, min(h_max_px, (int_ / COCADA_NUEVA_MAX) * h_max_px))
        base_y = 75
        y_ext = base_y - h_ext
        y_int = base_y - h_int
        dash = 'stroke-dasharray="5,3"' if rotacion == "🔄 ROTAR" else ""
        borde_rot = "#F6E05E" if rotacion == "🔄 ROTAR" else "transparent"
        hor_txt = f"{horometro:,.0f} h" if pd.notna(horometro) else "—"

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
            f'font-size="10" fill="#ffffff" font-weight="bold">{int_:.1f}</text>'
            f'<text x="97" y="{max(12, y_ext - 3):.2f}" text-anchor="middle" '
            f'font-size="10" fill="#ffffff" font-weight="bold">{ext:.1f}</text>'
            '</svg>'
            f'<div style="font-size:11px;color:{color};font-weight:bold;'
            f'margin-top:4px;">{estado} · Δ {delta:+.1f} mm</div>'
            f'<div style="font-size:10px;color:#888888;margin-top:2px;">'
            f'{rotacion} · {hor_txt}</div>'
            '</div>'
        )

    df_n_equipo = (df_neumaticos[df_neumaticos['ID_EQUIPO'] == id_equipo_sel]
                   .dropna(subset=['FECHA_MEDICION'])
                   .sort_values('FECHA_MEDICION'))

    if df_n_equipo.empty:
        st.info("No se registran inspecciones de neumáticos para este equipo.")
    else:
        ultima = (df_n_equipo.sort_values('FECHA_MEDICION')
                  .groupby(['POSICION', 'CARA'], as_index=False)
                  .tail(1))

        horometro_por_pos = (ultima.groupby('POSICION')['HOROMETRO_MAQUINA']
                             .max().to_dict())

        pivot = ultima.pivot(index='POSICION', columns='CARA', values='COCADA')
        pivot = pivot.reindex(columns=['EXTERIOR', 'INTERIOR'])
        pivot['DELTA'] = (pivot['EXTERIOR'] - pivot['INTERIOR']).round(1)
        pivot['COCADA_MIN'] = pivot[['EXTERIOR', 'INTERIOR']].min(axis=1)

        def _estado_cocada(mm):
            if mm < COCADA_CRITICA:
                return "🔴 CRÍTICO"
            elif mm < COCADA_MINIMA:
                return "🟡 ATENCIÓN"
            else:
                return "🟢 OK"

        def _estado_delta(delta):
            if abs(delta) > DELTA_ROTACION:
                return "🔄 ROTAR"
            return "✅ UNIFORME"

        pivot['ESTADO'] = pivot['COCADA_MIN'].apply(_estado_cocada)
        pivot['ROTACION'] = pivot['DELTA'].apply(_estado_delta)
        pivot = pivot.reset_index()

        cocada_min_global = pivot['COCADA_MIN'].min()
        cocada_promedio = pivot[['EXTERIOR', 'INTERIOR']].values.mean()
        delta_max = pivot['DELTA'].abs().max()
        n_alertas = ((pivot['ESTADO'] != "🟢 OK") | (pivot['ROTACION'] == "🔄 ROTAR")).sum()

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Cocada Mínima", f"{cocada_min_global:.1f} mm",
                  delta=f"{cocada_min_global - COCADA_MINIMA:+.1f} vs mín.",
                  delta_color="inverse" if cocada_min_global < COCADA_MINIMA else "normal")
        k2.metric("Cocada Promedio", f"{cocada_promedio:.1f} mm")
        k3.metric("Delta Máx. EXT/INT", f"{delta_max:.1f} mm",
                  delta="Requiere rotación" if delta_max > DELTA_ROTACION else "Uniforme",
                  delta_color="inverse" if delta_max > DELTA_ROTACION else "normal")
        k4.metric("Neumáticos en Alerta", f"{n_alertas} / {len(pivot)}")

        st.markdown("---")
        st.subheader(" Mapa de Neumáticos")

        def _fila_pivote(pos_key):
            fila = pivot[pivot['POSICION'] == pos_key]
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
            " **Leyenda:** Cada llanta muestra dos bandas de cocada — "
            "**INT** (lado hacia el chasis) y **EXT** (lado hacia afuera). "
            f"La altura es proporcional a los mm restantes (máx. {COCADA_NUEVA_MAX:.0f} mm). "
            "🟢 ≥12mm · 🟡 8-12mm · 🔴 <8mm · 🟨 borde amarillo = requiere rotación."
        )

        st.markdown("---")

        rotaciones = pivot[pivot['ROTACION'] == "🔄 ROTAR"]
        if not rotaciones.empty:
            st.subheader("🔄 Recomendaciones de Rotación")
            st.warning(
                f"Se detectaron **{len(rotaciones)}** neumático(s) con desgaste desigual "
                f"(delta > {DELTA_ROTACION} mm entre caras). Se recomienda voltear la rueda "
                f"(intercambiar EXT ↔ INT) para uniformizar el desgaste."
            )
            for _, r in rotaciones.iterrows():
                st.markdown(
                    f"- **{r['POSICION']}** → EXT: {r['EXTERIOR']:.1f} mm | "
                    f"INT: {r['INTERIOR']:.1f} mm | Delta: **{r['DELTA']:+.1f} mm**"
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
                sub = df_trend[(df_trend['POSICION'] == pos) & (df_trend['CARA'] == cara)]
                if sub.empty:
                    continue
                fig_trend.add_trace(go.Scatter(
                    x=sub['FECHA_MEDICION'], y=sub['COCADA'],
                    mode='lines+markers',
                    name=f"{pos} · {cara[:3]}",
                    line=dict(color=colores.get(pos, "#888888"),
                              dash='solid' if cara == "EXTERIOR" else 'dash',
                              width=2),
                    marker=dict(size=5)
                ))

        fig_trend.update_layout(
            template="plotly_dark",
            xaxis_title="Fecha de Medición",
            yaxis_title="Cocada (mm)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
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

    df_c_equipo = df_componentes[df_componentes['ID_EQUIPO'] == id_equipo_sel].copy()

    if 'DEVOLVER_CAMBIO' in df_c_equipo.columns:
        mask_devuelto = df_c_equipo['DEVOLVER_CAMBIO'].astype(str).str.strip().str.upper().isin(
            ['SI', 'SÍ', 'S', 'YES', 'Y', 'TRUE', '1']
        )
        df_c_equipo = df_c_equipo[~mask_devuelto]

    df_c_equipo = df_c_equipo.dropna(subset=['HOROMETRO_CAMBIO(PROYECTADO)'])
    df_c_equipo = df_c_equipo[df_c_equipo['HOROMETRO_CAMBIO(PROYECTADO)'] > 0]

    if not df_c_equipo.empty:
        ultimo_h = df_horometro_equipo['HFINAL'].max()

        if pd.notna(ultimo_h):
            df_c_equipo['HORAS_RESTANTES'] = (
                df_c_equipo['HOROMETRO_CAMBIO(PROYECTADO)'] - ultimo_h
            )

            def _clasificar(h):
                if h <= 0:
                    return 'CRITICO'
                elif h <= 500:
                    return 'ATENCION'
                else:
                    return 'OK'

            df_c_equipo['ESTADO'] = df_c_equipo['HORAS_RESTANTES'].apply(_clasificar)
            orden = {'CRITICO': 0, 'ATENCION': 1, 'OK': 2}
            df_c_equipo = df_c_equipo.sort_values(
                by=['ESTADO', 'HORAS_RESTANTES'],
                key=lambda s: s.map(orden) if s.name == 'ESTADO' else s,
                ascending=[True, True]
            )

            n_crit = (df_c_equipo['ESTADO'] == 'CRITICO').sum()
            n_aten = (df_c_equipo['ESTADO'] == 'ATENCION').sum()
            n_ok = (df_c_equipo['ESTADO'] == 'OK').sum()

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
                h_cambio = row['HOROMETRO_CAMBIO(PROYECTADO)']
                h_inst = row.get('HOROMETRO_INSTALACION', None)
                horas_restantes = row['HORAS_RESTANTES']

                if pd.notna(h_inst) and h_cambio > h_inst:
                    vida_total = h_cambio - h_inst
                    consumida = max(0.0, min(1.0, (ultimo_h - h_inst) / vida_total))
                else:
                    consumida = None

                tipo = row['TIPO_COMPONENTE']
                desc = row['DESCRIPCION']

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

    df_e_equipo = (df_engrase[df_engrase['ID_EQUIPO'] == id_equipo_sel]
                   .dropna(subset=['FECHA'])
                   .sort_values('FECHA'))

    if df_e_equipo.empty:
        st.info("No se registran engrases para este equipo.")
    else:
        df_e_mes = df_e_equipo[df_e_equipo['MES_NUM'] == mes_sel_num] if mes_sel_num else df_e_equipo

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Registros de Engrase (Mes)", f"{len(df_e_mes)}")
        with k2:
            pct_prom = df_e_mes['PCT_CUMPLIMIENTO'].mean() if not df_e_mes.empty else 0
            st.metric("% Cumplimiento Promedio", f"{pct_prom:.1f}%")
        with k3:
            kg_total = df_e_mes['CANTIDAD_GRASA_KG'].sum() if not df_e_mes.empty else 0
            st.metric("Grasa Consumida (Mes)", f"{kg_total:.1f} kg")
        with k4:
            ultimo_engrase = df_e_equipo['FECHA'].max()
            dias_desde = (pd.Timestamp.now().normalize() - ultimo_engrase).days
            st.metric("Último Engrase",
                      f"Hace {dias_desde} día(s)",
                      delta=f"{ultimo_engrase.strftime('%d/%m/%Y')}",
                      delta_color="off")

        st.markdown("---")

        st.subheader("Calendario de Cumplimiento del Mes")

        if mes_sel_num and not df_e_mes.empty:
            anio_ref = df_e_mes['ANIO'].mode().iloc[0] if not df_e_mes.empty else pd.Timestamp.now().year
            cal = calendar.Calendar(firstweekday=0)
            dias_mes = cal.monthdayscalendar(anio_ref, mes_sel_num)

            resumen_dias = {}
            for _, r in df_e_mes.iterrows():
                dia = r['FECHA'].day
                if dia not in resumen_dias:
                    resumen_dias[dia] = {"cumplido": "SI", "pct": r['PCT_CUMPLIMIENTO']}
                else:
                    if r['CUMPLIDO'] == "NO":
                        resumen_dias[dia]["cumplido"] = "NO"
                    resumen_dias[dia]["pct"] = min(resumen_dias[dia]["pct"],
                                                    r['PCT_CUMPLIMIENTO'])

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
                html_cal += '<tr>'
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
                            f'{dia}<br><span style="font-size:10px;">{icon} {info["pct"]:.0f}%</span></td>'
                        )
                    else:
                        html_cal += (
                            f'<td style="padding:6px;background:#1a1a2e;color:#555;'
                            f'border:1px solid #333;border-radius:4px;">'
                            f'{dia}<br><span style="font-size:10px;">—</span></td>'
                        )
                html_cal += '</tr>'
            html_cal += '</table>'
            st.markdown(html_cal, unsafe_allow_html=True)
            st.caption("🟢 Cumplido al 100% · 🟡 Parcial (<100%) · — Sin registro")
        else:
            st.info("Selecciona un mes con datos para ver el calendario.")

        st.markdown("---")

        st.subheader("Tendencia Mensual de Engrase")
        df_mes = df_e_equipo.groupby(['ANIO', 'MES_NUM']).agg(
            registros=('FECHA', 'count'),
            cumplimiento_prom=('PCT_CUMPLIMIENTO', 'mean'),
            grasa_total=('CANTIDAD_GRASA_KG', 'sum')
        ).reset_index()
        df_mes['MES_NOMBRE'] = df_mes['MES_NUM'].map(dicc_meses)
        df_mes['PERIODO'] = df_mes['MES_NOMBRE'] + " " + df_mes['ANIO'].astype(str)

        fig_e = go.Figure()
        fig_e.add_trace(go.Bar(
            x=df_mes['PERIODO'], y=df_mes['registros'],
            name='Registros de engrase',
            marker_color='#4FD1C5',
            yaxis='y1',
            text=df_mes['registros'], textposition='outside'
        ))
        fig_e.add_trace(go.Scatter(
            x=df_mes['PERIODO'], y=df_mes['cumplimiento_prom'],
            name='% Cumplimiento',
            mode='lines+markers',
            line=dict(color='#F6AD55', width=3),
            marker=dict(size=8),
            yaxis='y2'
        ))
        fig_e.update_layout(
            template="plotly_dark",
            xaxis_title="Mes",
            yaxis=dict(title="Registros", side='left'),
            yaxis2=dict(title="% Cumplimiento", overlaying='y', side='right',
                        range=[0, 105]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=400
        )
        st.plotly_chart(fig_e, use_container_width=True)

        st.markdown("---")

        st.subheader("⚠️ Días sin Registro de Engrase (Mes Seleccionado)")

        if mes_sel_num and not df_e_mes.empty:
            dias_con_registro = set(df_e_mes['FECHA'].dt.day.tolist())
            dias_mes_total = calendar.monthrange(anio_ref, mes_sel_num)[1]
            hoy = pd.Timestamp.now().normalize()
            dias_faltantes = []
            for d in range(1, dias_mes_total + 1):
                fecha_d = pd.Timestamp(year=anio_ref, month=mes_sel_num, day=d)
                if fecha_d <= hoy and d not in dias_con_registro:
                    dias_faltantes.append(d)
            if dias_faltantes:
                st.warning(
                    f"Se detectaron **{len(dias_faltantes)}** día(s) sin registro de engrase "
                    f"en el mes: {', '.join(str(d) for d in dias_faltantes)}"
                )
            else:
                st.success("Todos los días hábiles del mes tienen registro de engrase.")
        else:
            st.info("Selecciona un mes con datos para verificar días sin engrase.")
