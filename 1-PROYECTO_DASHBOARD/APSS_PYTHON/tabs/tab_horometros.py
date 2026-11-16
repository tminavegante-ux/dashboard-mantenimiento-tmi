# ============================================================
#  TAB 1: HORÓMETROS & FLOTA
# ============================================================
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from config.settings import COLORES, TEMPLATE_PLOTLY, ABREV_MES
from ui.components import tarjeta_turnos_html


def render_tab_horometros(ctx: dict, df_equipos: pd.DataFrame):
    nombre = ctx["nombre_seleccionado"]
    id_eq = ctx["id_equipo_sel"]
    mes_sel = ctx["mes_sel_num"]
    df_eq = ctx["df_horometro_equipo"]
    df_mes = ctx["df_h_filtrado_mes"]
    df_filt = ctx["df_h_filtrado_equipo"]

    st.header(f"Análisis de Utilización - {nombre}")

    # --- KPIs ---
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        total = df_filt["HRS_OPERADAS"].sum() if not df_filt.empty else 0
        st.metric("Horas Operadas (Mes Seleccionado)", f"{total:,.1f} Hrs")
    with k2:
        ult_h = df_eq["HFINAL"].max()
        st.metric("Último Horómetro Registrado",
                  f"{ult_h:,.1f} Hrs" if pd.notna(ult_h) else "0.0 Hrs")
    with k3:
        st_ = (df_filt.sort_values("FECHA").iloc[-1]["STATUS_EQUIPO"]
               if not df_filt.empty else "SIN REGISTRO")
        st.metric("Último Estado Operativo", str(st_).upper())
    with k4:
        if not df_filt.empty:
            op = (df_filt["STATUS_EQUIPO"] == "OPERATIVO").sum()
            inop = (df_filt["STATUS_EQUIPO"] != "OPERATIVO").sum()
            disp = op / (op + inop) * 100 if (op + inop) else 0
            st.markdown(tarjeta_turnos_html(op, inop, disp), unsafe_allow_html=True)
        else:
            st.markdown(tarjeta_turnos_html(0, 0, 0), unsafe_allow_html=True)

    st.markdown("---")

    # --- Gráficos ---
    g1, g2 = st.columns(2)

    with g1:
        st.subheader(f"Desempeño Diario: {nombre}")
        if not df_filt.empty:
            fig = px.line(
                df_filt.sort_values("FECHA"),
                x="FECHA", y="HRS_OPERADAS", color="TURNO",
                markers=True, template=TEMPLATE_PLOTLY,
                labels={"HRS_OPERADAS": "Horas Trabajadas", "FECHA": "Día"},
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin registros de horas para este equipo en el mes seleccionado.")

    with g2:
        st.subheader("Comparativa de Horas Totales: Toda la Flota")
        if not df_mes.empty:
            resumen = (df_mes.groupby("ID_EQUIPO")["HRS_OPERADAS"]
                       .sum().reset_index()
                       .merge(df_equipos[["ID_EQUIPO", "NOMBRE"]],
                              on="ID_EQUIPO", how="left"))
            resumen["ES_SELECCIONADO"] = (
                resumen["ID_EQUIPO"] == id_eq
            ).map({True: "⭐ SELECCIONADO", False: "Resto de flota"})
            resumen = resumen.sort_values("HRS_OPERADAS", ascending=True)

            fig = px.bar(
                resumen, x="HRS_OPERADAS", y="NOMBRE", orientation="h",
                color="ES_SELECCIONADO",
                color_discrete_map={"⭐ SELECCIONADO": COLORES["primario"],
                                    "Resto de flota": COLORES["secundario"]},
                text="HRS_OPERADAS", template=TEMPLATE_PLOTLY,
                labels={"HRS_OPERADAS": "Horas Acumuladas", "NOMBRE": "Equipo"},
            )
            fig.update_traces(texttemplate="%{text:.1f} h", textposition="outside")
            fig.update_layout(showlegend=False, xaxis_title="Horas Acumuladas",
                              yaxis_title="Equipo")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos de flota para este período.")

    st.markdown("---")
    st.subheader(f"Rendimiento Mensual - {nombre}")

    df_todos = df_eq.dropna(subset=["HRS_OPERADAS"])
    if df_todos.empty:
        st.info("Sin registros de horas para este equipo.")
        return

    df_mens = (df_todos.groupby(["ANIO", "MES_NUM"])["HRS_OPERADAS"]
               .sum().reset_index())
    anio_ref = int(df_mens["ANIO"].max())
    df_anio = df_mens[df_mens["ANIO"] == anio_ref]

    meses_eje = list(range(1, 13))
    etiquetas = [ABREV_MES[m] for m in meses_eje]
    valores = {m: 0 for m in meses_eje}
    for _, r in df_anio.iterrows():
        valores[int(r["MES_NUM"])] = float(r["HRS_OPERADAS"])

    colores, textos = [], []
    for m in meses_eje:
        if m == mes_sel and valores[m] > 0:
            colores.append(COLORES["primario"])
            textos.append(f"{valores[m]:.0f} h")
        elif valores[m] > 0:
            colores.append(COLORES["secundario"])
            textos.append(f"{valores[m]:.0f} h")
        else:
            colores.append("rgba(0,0,0,0)")
            textos.append("")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=etiquetas, y=[valores[m] for m in meses_eje],
        marker_color=colores, text=textos, textposition="outside", width=0.5,
        hovertemplate="<b>%{x}</b><br>Horas: %{y:.0f}<extra></extra>",
    ))
    fig.update_layout(
        showlegend=False, xaxis_title="Mes", yaxis_title="Horas Operadas",
        height=280, margin=dict(l=40, r=20, t=30, b=40), bargap=0.4,
        xaxis=dict(categoryorder="array", categoryarray=etiquetas),
    )
    st.plotly_chart(fig, use_container_width=True)