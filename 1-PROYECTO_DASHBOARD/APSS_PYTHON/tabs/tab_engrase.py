# ============================================================
#  TAB 4: ENGRASE
# ============================================================
import calendar
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from config.settings import DICC_MESES, COLORES, TEMPLATE_PLOTLY


def render_tab_engrase(ctx: dict, df_engrase: pd.DataFrame):
    nombre = ctx["nombre_seleccionado"]
    id_eq = ctx["id_equipo_sel"]
    mes_sel = ctx["mes_sel_num"]

    st.header(f"Control de Engrase - {nombre}")

    if df_engrase.empty or "ID_EQUIPO" not in df_engrase.columns:
        st.info("No hay datos de engrase disponibles.")
        return

    df_eq = (df_engrase[df_engrase["ID_EQUIPO"] == id_eq]
             .dropna(subset=["FECHA"]).sort_values("FECHA"))
    if df_eq.empty:
        st.info("No se registran engrases para este equipo.")
        return

    df_mes = df_eq[df_eq["MES_NUM"] == mes_sel] if mes_sel else df_eq

    # --- KPIs ---
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Registros de Engrase (Mes)", f"{len(df_mes)}")
    pct = df_mes["PCT_CUMPLIMIENTO"].mean() if not df_mes.empty else 0
    k2.metric("% Cumplimiento Promedio", f"{pct:.1f}%")
    kg = (df_mes["CANTIDAD_GRASA_KG"].sum()
          if "CANTIDAD_GRASA_KG" in df_mes.columns and not df_mes.empty else 0)
    k3.metric("Grasa Consumida (Mes)", f"{kg:.1f} kg")
    ult = df_eq["FECHA"].max()
    dias = (pd.Timestamp.now().normalize() - ult).days
    k4.metric("Último Engrase", f"Hace {dias} día(s)",
              delta=f"{ult.strftime('%d/%m/%Y')}", delta_color="off")

    st.markdown("---")
    st.subheader("Calendario de Cumplimiento del Mes")

    if mes_sel and not df_mes.empty:
        anio = int(df_mes["ANIO"].mode().iloc[0])
        cal = calendar.Calendar(firstweekday=0)
        dias = cal.monthdayscalendar(anio, mes_sel)

        resumen = {}
        for _, r in df_mes.iterrows():
            d = r["FECHA"].day
            if d not in resumen:
                resumen[d] = {"cumplido": "SI", "pct": r["PCT_CUMPLIMIENTO"]}
            else:
                if r.get("CUMPLIDO") == "NO":
                    resumen[d]["cumplido"] = "NO"
                resumen[d]["pct"] = min(resumen[d]["pct"], r["PCT_CUMPLIMIENTO"])

        html = ('<table style="width:100%;border-collapse:collapse;text-align:center;'
                'font-size:13px;"><tr style="background:#2d2d44;color:#ddd;">'
                '<th style="padding:6px;">Lun</th><th style="padding:6px;">Mar</th>'
                '<th style="padding:6px;">Mié</th><th style="padding:6px;">Jue</th>'
                '<th style="padding:6px;">Vie</th><th style="padding:6px;">Sáb</th>'
                '<th style="padding:6px;">Dom</th></tr>')
        for semana in dias:
            html += "<tr>"
            for d in semana:
                if d == 0:
                    html += '<td style="padding:6px;"></td>'
                    continue
                if d in resumen:
                    info = resumen[d]
                    color = "#48BB78" if info["cumplido"] == "SI" else "#F6AD55"
                    icon = "🟢" if info["cumplido"] == "SI" else "🟡"
                    html += (f'<td style="padding:6px;background:{color};color:#fff;'
                             f'border-radius:4px;font-weight:bold;">'
                             f'{d}<br><span style="font-size:10px;">'
                             f'{icon} {info["pct"]:.0f}%</span></td>')
                else:
                    html += (f'<td style="padding:6px;background:#1a1a2e;color:#555;'
                             f'border:1px solid #333;border-radius:4px;">'
                             f'{d}<br><span style="font-size:10px;">—</span></td>')
            html += "</tr>"
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)
        st.caption("🟢 Cumplido al 100% · 🟡 Parcial (<100%) · — Sin registro")
    else:
        st.info("Selecciona un mes con datos para ver el calendario.")

    st.markdown("---")
    st.subheader("Tendencia Mensual de Engrase")

    agg_dict = {
        "registros": ("FECHA", "count"),
        "cumplimiento_prom": ("PCT_CUMPLIMIENTO", "mean"),
        "grasa_total": ("CANTIDAD_GRASA_KG", "sum")
        if "CANTIDAD_GRASA_KG" in df_eq.columns else ("PCT_CUMPLIMIENTO", "count"),
    }
    df_trend = df_eq.groupby(["ANIO", "MES_NUM"]).agg(**agg_dict).reset_index()
    df_trend["MES_NOMBRE"] = df_trend["MES_NUM"].map(DICC_MESES)
    df_trend["PERIODO"] = df_trend["MES_NOMBRE"] + " " + df_trend["ANIO"].astype(str)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_trend["PERIODO"], y=df_trend["registros"],
                         name="Registros", marker_color=COLORES["teal"],
                         text=df_trend["registros"], textposition="outside",
                         yaxis="y1"))
    fig.add_trace(go.Scatter(x=df_trend["PERIODO"], y=df_trend["cumplimiento_prom"],
                             name="% Cumplimiento", mode="lines+markers",
                             line=dict(color=COLORES["primario"], width=3),
                             marker=dict(size=8), yaxis="y2"))
    fig.update_layout(
        template=TEMPLATE_PLOTLY, xaxis_title="Mes",
        yaxis=dict(title="Registros", side="left"),
        yaxis2=dict(title="% Cumplimiento", overlaying="y", side="right",
                    range=[0, 105]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)