# ============================================================
#  TAB 5: KPIs HORÓMETROS & PARADAS
# ============================================================
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO
import numpy as np
import pandas as pd

from config.settings import COLORES, TEMPLATE_PLOTLY


def render_tab_kpis(ctx: dict, df_horometro: pd.DataFrame, df_paradas: pd.DataFrame):
    st.header("📊 KPIs Horómetros & Paradas")
    st.caption("Los filtros de esta pestaña son **independientes** del sidebar "
               "y solo afectan a los KPIs de Horómetros y Paradas.")

    # ---------- FILTROS ----------
    c1, c2, c3 = st.columns(3)
    with c1:
        eqs = sorted(df_horometro["ID_EQUIPO"].dropna().unique()) \
            if "ID_EQUIPO" in df_horometro.columns else []
        eq_kpi = st.multiselect("Equipo", eqs, default=[],
                                placeholder="Todos los equipos", key="kpi_eq")
    with c2:
        turnos = sorted(df_horometro["TURNO"].dropna().unique()) \
            if "TURNO" in df_horometro.columns else []
        turno_kpi = st.multiselect("Turno", turnos, default=[],
                                   placeholder="Todos los turnos", key="kpi_turno")
    with c3:
        tipos = sorted(df_horometro["TIPO_EQUIPO"].dropna().unique()) \
            if "TIPO_EQUIPO" in df_horometro.columns else []
        tipo_kpi = st.multiselect("Tipo de equipo", tipos, default=[],
                                  placeholder="Todos los tipos", key="kpi_tipo")

    st.markdown("##### 📅 Filtro por período")
    modo = st.radio("Filtrar por:", ["Todo", "Semana", "Mes", "Rango de fechas"],
                    horizontal=True, label_visibility="collapsed", key="kpi_modo")

    semana_kpi, mes_kpi, rango_kpi = [], [], None

    if modo == "Semana":
        semanas = sorted(df_horometro["NUMERO SEMANA"].dropna().astype(int).unique()) \
            if "NUMERO SEMANA" in df_horometro.columns else []
        semana_kpi = st.multiselect("Semana(s)", semanas, default=[],
                                    placeholder="Todas", key="kpi_semana")
    elif modo == "Mes":
        if "PERIODO_MES" not in df_horometro.columns:
            df_horometro["PERIODO_MES"] = df_horometro["FECHA"].dt.strftime("%Y-%m")
        df_m = (df_horometro.dropna(subset=["PERIODO_MES"])
                .drop_duplicates("PERIODO_MES")
                [["PERIODO_MES", "MES_NOMBRE", "ANIO"]]
                .sort_values("PERIODO_MES"))
        opciones = {f"{r.PERIODO_MES} · {r.MES_NOMBRE} {int(r.ANIO)}": r.PERIODO_MES
                    for r in df_m.itertuples()}
        labels = st.multiselect("Mes(es)", list(opciones.keys()), default=[],
                                placeholder="Todos", key="kpi_mes")
        mes_kpi = [opciones[l] for l in labels]
    elif modo == "Rango de fechas":
        if df_horometro["FECHA"].notna().any():
            fmin = df_horometro["FECHA"].min().date()
            fmax = df_horometro["FECHA"].max().date()
            rango_kpi = st.date_input("Rango", value=(fmin, fmax),
                                       min_value=fmin, max_value=fmax,
                                       key="kpi_rango")

    st.markdown("---")

    # ---------- FILTRAR ----------
    hor = df_horometro.copy()
    par = df_paradas.copy() if not df_paradas.empty else pd.DataFrame()

    if eq_kpi:
        hor = hor[hor["ID_EQUIPO"].isin(eq_kpi)]
        if "EQUIPO" in par.columns:
            par = par[par["EQUIPO"].isin(eq_kpi)]
    if turno_kpi and "TURNO" in hor.columns:
        hor = hor[hor["TURNO"].isin(turno_kpi)]
        if "TURNO" in par.columns:
            par = par[par["TURNO"].isin(turno_kpi)]
    if tipo_kpi and "TIPO_EQUIPO" in hor.columns:
        hor = hor[hor["TIPO_EQUIPO"].isin(tipo_kpi)]
    if semana_kpi and "NUMERO SEMANA" in hor.columns:
        hor = hor[hor["NUMERO SEMANA"].isin(semana_kpi)]
        if "FECHA" in par.columns:
            par = par[par["FECHA"].dt.isocalendar().week.astype("Int64").isin(semana_kpi)]
    if mes_kpi and "PERIODO_MES" in hor.columns:
        hor = hor[hor["PERIODO_MES"].isin(mes_kpi)]
        if "PERIODO_MES" in par.columns:
            par = par[par["PERIODO_MES"].isin(mes_kpi)]
    if isinstance(rango_kpi, tuple) and len(rango_kpi) == 2:
        hor = hor[(hor["FECHA"] >= pd.to_datetime(rango_kpi[0])) &
                  (hor["FECHA"] <= pd.to_datetime(rango_kpi[1]))]
        if "FECHA" in par.columns:
            par = par[(par["FECHA"] >= pd.to_datetime(rango_kpi[0])) &
                      (par["FECHA"] <= pd.to_datetime(rango_kpi[1]))]

    if hor.empty and par.empty:
        st.info("No hay registros con los filtros seleccionados.")
        return

    # ---------- MÉTRICAS ----------
    def _sum(df, col):
        return float(df[col].sum()) if col in df.columns else 0.0

    total_efec = _sum(hor, "HRS_OPERADAS")
    total_prog = _sum(hor, "HORAS_PROG")
    p_mec = _sum(hor, "PARADA_MEC")
    p_op = _sum(hor, "PARADA_OP")
    n_fallas = int(hor["N_FALLAS"].sum()) if "N_FALLAS" in hor.columns else 0

    if not par.empty and "DURACION" in par.columns:
        if p_mec == 0 and "TIPO_UP" in par.columns:
            mask = par["TIPO_UP"].str.contains("PM|MEC|MECAN", na=False)
            p_mec = float(par.loc[mask, "DURACION"].sum())
            p_op = float(par.loc[~mask, "DURACION"].sum())
        if n_fallas == 0:
            n_fallas = len(par)
    if total_prog == 0:
        total_prog = total_efec + p_mec + p_op

    disp = ((total_prog - p_mec) / total_prog * 100) if total_prog > 0 else 0
    util = (total_efec / total_prog * 100) if total_prog > 0 else 0
    disp_h = total_prog - p_mec
    util_ef = (total_efec / disp_h * 100) if disp_h > 0 else 0
    mtbf = total_efec / n_fallas if n_fallas else 0
    mttr = p_mec / n_fallas if n_fallas else 0

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Horas Efectivas", f"{total_efec:,.1f} H", f"{len(hor)} registros")
    a2.metric("Parada Mecánica", f"{p_mec:,.1f} H", "Correctivos")
    a3.metric("Parada Operativa", f"{p_op:,.1f} H", "Operativas")
    a4.metric("# Fallas", f"{n_fallas}", f"MTBF {mtbf:.1f} H | MTTR {mttr:.1f} H")

    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Disponibilidad Mecánica", f"{disp:.1f}%",
              f"({disp_h:.1f} H disp / {total_prog:.1f} H prog)")
    b2.metric("Utilización", f"{util:.1f}%",
              f"({total_efec:.1f} H efec / {total_prog:.1f} H prog)")
    b3.metric("Horas Programadas", f"{total_prog:,.1f} H", "Planificado")
    b4.metric("Utilización Efectiva", f"{util_ef:.1f}%",
              f"({total_efec:.1f} H efec / {disp_h:.1f} H disp)")

    st.markdown("---")

    # ---------- GAUGES ----------
    g1, g2, g3 = st.columns(3)

    with g1:
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=disp,
            number={"suffix": "%", "font": {"color": COLORES["info"], "size": 40}},
            title={"text": "Disponibilidad Mecánica", "font": {"size": 14}},
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": COLORES["info"]},
                   "bgcolor": "#1A1F2B",
                   "steps": [{"range": [0, 50], "color": "#3A1F1F"},
                             {"range": [50, 75], "color": "#3A3520"},
                             {"range": [75, 100], "color": "#1F3A2A"}],
                   "threshold": {"line": {"color": COLORES["critico"], "width": 4},
                                 "thickness": 0.75, "value": 85}}))
        fig.update_layout(template=TEMPLATE_PLOTLY, height=250,
                          margin=dict(l=40, r=20, t=50, b=40))
        st.plotly_chart(fig, use_container_width=True)

    with g2:
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=util,
            number={"suffix": "%", "font": {"color": COLORES["ok"], "size": 40}},
            title={"text": "Utilización", "font": {"size": 14}},
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": COLORES["ok"]},
                   "bgcolor": "#1A1F2B",
                   "steps": [{"range": [0, 40], "color": "#3A1F1F"},
                             {"range": [40, 70], "color": "#3A3520"},
                             {"range": [70, 100], "color": "#1F3A2A"}]}))
        fig.update_layout(template=TEMPLATE_PLOTLY, height=250,
                          margin=dict(l=40, r=20, t=50, b=40))
        st.plotly_chart(fig, use_container_width=True)

    with g3:
        if not par.empty and "TIPO DE PARADA" in par.columns:
            tp = par.groupby("TIPO DE PARADA")["DURACION"].sum().reset_index()
            fig = px.pie(tp, values="DURACION", names="TIPO DE PARADA", hole=0.55,
                         color_discrete_sequence=[COLORES["info"], COLORES["ok"],
                                                  COLORES["alerta"], COLORES["purpura"]])
            fig.update_layout(template=TEMPLATE_PLOTLY, height=250,
                              title="Distribución de Paradas por Tipo",
                              margin=dict(l=40, r=20, t=50, b=40))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin datos de paradas para el gráfico.")

    # ---------- BARRAS + PARETO ----------
    r1, r2 = st.columns([7, 5])

    with r1:
        if not hor.empty and "FECHA" in hor.columns:
            agg = hor.groupby("FECHA").agg({
                "HRS_OPERADAS": "sum", "PARADA_MEC": "sum", "PARADA_OP": "sum",
            }).reset_index().sort_values("FECHA")
            fig = go.Figure()
            fig.add_bar(x=agg["FECHA"], y=agg["HRS_OPERADAS"],
                        name="Horas Efectivas", marker_color=COLORES["ok"])
            fig.add_bar(x=agg["FECHA"], y=agg["PARADA_MEC"],
                        name="P. Mecánica", marker_color=COLORES["critico"])
            fig.add_bar(x=agg["FECHA"], y=agg["PARADA_OP"],
                        name="P. Operativa", marker_color=COLORES["alerta"])
            fig.update_layout(template=TEMPLATE_PLOTLY, barmode="group", height=380,
                              title="Horas Efectivas vs Paradas por Fecha",
                              legend=dict(orientation="h", y=-0.2),
                              margin=dict(l=40, r=20, t=50, b=40))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin registros de horómetro.")

    with r2:
        if not par.empty and "TIPO DE PARADA" in par.columns:
            par_p = (par.groupby("TIPO DE PARADA")["DURACION"].sum()
                     .reset_index().sort_values("DURACION", ascending=False))
            par_p["Acum %"] = par_p["DURACION"].cumsum() / par_p["DURACION"].sum() * 100
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_bar(x=par_p["TIPO DE PARADA"], y=par_p["DURACION"],
                        marker_color=COLORES["alerta"], name="Horas")
            fig.add_scatter(x=par_p["TIPO DE PARADA"], y=par_p["Acum %"],
                            mode="lines+markers", name="Acum %",
                            line=dict(color=COLORES["info"], width=3),
                            secondary_y=True)
            fig.update_layout(template=TEMPLATE_PLOTLY, height=380,
                              title="Pareto de Paradas",
                              legend=dict(orientation="h", y=-0.2),
                              margin=dict(l=40, r=20, t=50, b=40))
            fig.update_yaxes(title_text="Horas", secondary_y=False)
            fig.update_yaxes(title_text="% Acum", secondary_y=True, range=[0, 105])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin datos de paradas para el período.")

    # ---------- TENDENCIA + TOP 10 FALLAS ----------
    s1, s2 = st.columns([7, 5])

    with s1:
        if not hor.empty and "FECHA" in hor.columns:
            kd = hor.groupby("FECHA").agg({
                "HRS_OPERADAS": "sum", "PARADA_MEC": "sum",
            }).reset_index().sort_values("FECHA")
            fig = go.Figure()
            fig.add_scatter(x=kd["FECHA"], y=kd["HRS_OPERADAS"], mode="lines+markers",
                            name="Efectivas",
                            line=dict(color=COLORES["ok"], width=3),
                            fill="tozeroy", fillcolor="rgba(0,230,118,0.15)")
            fig.add_scatter(x=kd["FECHA"], y=kd["PARADA_MEC"], mode="lines+markers",
                            name="P. Mecánica",
                            line=dict(color=COLORES["critico"], width=2))
            fig.update_layout(template=TEMPLATE_PLOTLY, height=380,
                              title="Tendencia Diaria",
                              legend=dict(orientation="h", y=-0.2),
                              margin=dict(l=40, r=20, t=50, b=40))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin registros para la tendencia.")

    with s2:
        if not par.empty and "DESCRIPCION DE LA FALLA" in par.columns:
            top = (par.groupby(["EQUIPO", "DESCRIPCION DE LA FALLA"])["DURACION"]
                   .sum().reset_index()
                   .sort_values("DURACION", ascending=False).head(10))
            fig = px.bar(top, x="DURACION", y="DESCRIPCION DE LA FALLA",
                         orientation="h", color="DURACION",
                         color_continuous_scale=[COLORES["alerta"], COLORES["critico"]])
            fig.update_layout(template=TEMPLATE_PLOTLY, height=380,
                              title="Top 10 Fallas", coloraxis_showscale=False,
                              yaxis=dict(autorange="reversed"),
                              margin=dict(l=40, r=20, t=50, b=40))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin paradas registradas.")

    # ---------- HEATMAP ----------
    if (not hor.empty and all(c in hor.columns for c in
                              ["HORAS_PROG", "PARADA_MEC", "HRS_OPERADAS"])):
        hk = hor.groupby("ID_EQUIPO").agg({
            "HORAS_PROG": "sum", "PARADA_MEC": "sum", "HRS_OPERADAS": "sum",
        }).reset_index()
        hk["Disponibilidad %"] = ((hk["HORAS_PROG"] - hk["PARADA_MEC"])
                                  / hk["HORAS_PROG"].replace(0, np.nan) * 100
                                  ).fillna(0).round(1)
        hk["Utilización %"] = (hk["HRS_OPERADAS"]
                               / hk["HORAS_PROG"].replace(0, np.nan) * 100
                               ).fillna(0).round(1)
        mat = hk.set_index("ID_EQUIPO")[["Disponibilidad %", "Utilización %"]]
        fig = px.imshow(mat.T, text_auto=".1f", aspect="auto",
                        color_continuous_scale=[COLORES["critico"], COLORES["alerta"],
                                                COLORES["ok"]],
                        labels=dict(x="Equipo", y="KPI", color="%"))
        fig.update_layout(template=TEMPLATE_PLOTLY, height=260,
                          title="Mapa de Calor KPIs por Equipo",
                          margin=dict(l=40, r=20, t=50, b=40))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ---------- DETALLES ----------
    st.markdown("## 📑 Registros de detalle (KPIs)")
    s_hor, s_par = st.tabs(["📋 Horómetros", "🛠️ Paradas (PARADAS-M)"])

    with s_hor:
        cols = ["FECHA", "TURNO", "ID_EQUIPO", "H_INICIAL", "HFINAL",
                "HRS_OPERADAS", "PARADA_MEC", "PARADA_OP", "INSPECCION",
                "HORAS_PROG", "N_FALLAS"]
        ok = [c for c in cols if c in hor.columns]
        sh = hor[ok].copy()
        if "FECHA" in sh.columns:
            sh["FECHA"] = sh["FECHA"].dt.strftime("%d/%m/%Y")
        if "HORAS_PROG" in sh.columns and "PARADA_MEC" in sh.columns:
            sh["Disp. %"] = ((sh["HORAS_PROG"] - sh["PARADA_MEC"])
                             / sh["HORAS_PROG"].replace(0, np.nan) * 100
                             ).fillna(0).round(1)
        if "HORAS_PROG" in sh.columns and "HRS_OPERADAS" in sh.columns:
            sh["Util. %"] = (sh["HRS_OPERADAS"]
                             / sh["HORAS_PROG"].replace(0, np.nan) * 100
                             ).fillna(0).round(1)
        if "FECHA" in sh.columns:
            keys = ["FECHA", "ID_EQUIPO"] if "ID_EQUIPO" in sh.columns else ["FECHA"]
            asc = [False] + ([True] if "ID_EQUIPO" in sh.columns else [])
            sh = sh.sort_values(keys, ascending=asc)
        st.dataframe(sh, use_container_width=True, height=500, hide_index=True)
        if not sh.empty:
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                sh.to_excel(w, index=False, sheet_name="HOROMETROS_KPI")
            st.download_button("⬇️ Descargar Horómetros KPIs (Excel)",
                               data=buf.getvalue(),
                               file_name="HOROMETROS_kpi.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with s_par:
        if par.empty:
            st.info("⚠️ No hay paradas con los filtros seleccionados.")
        else:
            cols = ["FECHA", "TURNO", "EQUIPO", "TIPO DE PARADA",
                    "DURACION", "DESCRIPCION DE LA FALLA"]
            ok = [c for c in cols if c in par.columns]
            sp = par[ok].copy()
            if "FECHA" in sp.columns:
                sp["FECHA"] = sp["FECHA"].dt.strftime("%d/%m/%Y")
            sk = [c for c in ["FECHA", "EQUIPO"] if c in sp.columns]
            if sk:
                sp = sp.sort_values(sk, ascending=[False] + [True] * (len(sk) - 1))
            st.dataframe(sp, use_container_width=True, height=480, hide_index=True,
                         column_config={"DURACION": st.column_config.NumberColumn(
                             "Duración (H)", format="%.2f H")})
            st.caption(f"📊 {len(sp):,} paradas mostradas")
            if not sp.empty:
                buf = BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as w:
                    sp.to_excel(w, index=False, sheet_name="PARADAS_KPI")
                st.download_button("⬇️ Descargar Paradas KPIs (Excel)",
                                   data=buf.getvalue(),
                                   file_name="PARADAS_kpi.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.markdown("#### 📈 Resumen por tipo de parada")
            if "TIPO DE PARADA" in sp.columns and "DURACION" in sp.columns:
                rt = (sp.groupby("TIPO DE PARADA")
                      .agg(N=("DURACION", "count"), Horas=("DURACION", "sum"),
                           Promedio=("DURACION", "mean"))
                      .reset_index().sort_values("Horas", ascending=False))
                rt["Horas"] = rt["Horas"].round(1)
                rt["Promedio"] = rt["Promedio"].round(2)
                st.dataframe(rt, use_container_width=True, hide_index=True)