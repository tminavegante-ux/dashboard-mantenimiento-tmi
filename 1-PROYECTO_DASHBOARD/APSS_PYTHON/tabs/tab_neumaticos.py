# ============================================================
#  TAB 2: NEUMÁTICOS
# ============================================================
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from config.settings import NEUMATICOS, TEMPLATE_PLOTLY
from ui.components import svg_llanta


def _estado_cocada(mm: float) -> str:
    if pd.isna(mm):
        return "⚪ SIN DATO"
    if mm < NEUMATICOS["COCADA_CRITICA"]:
        return "🔴 CRÍTICO"
    if mm < NEUMATICOS["COCADA_MINIMA"]:
        return "🟡 ATENCIÓN"
    return "🟢 OK"


def _estado_rotacion(delta, cmin, cmax) -> str:
    motivos = []
    if pd.notna(delta) and abs(delta) > NEUMATICOS["DELTA_ROTACION"]:
        motivos.append("desgaste desigual")
    if pd.notna(cmax) and cmax <= NEUMATICOS["COCADA_MINIMA"]:
        motivos.append("cocada baja")
    return "🔄 ROTAR · " + " + ".join(motivos) if motivos else "✅ UNIFORME"


def render_tab_neumaticos(ctx: dict, df_neumaticos: pd.DataFrame):
    nombre = ctx["nombre_seleccionado"]
    id_eq = ctx["id_equipo_sel"]

    st.header(f"Control de Neumáticos - {nombre}")

    if df_neumaticos.empty or "FECHA_MEDICION" not in df_neumaticos.columns:
        st.info("No se registran inspecciones de neumáticos para este equipo.")
        return

    df_eq = (df_neumaticos[df_neumaticos["ID_EQUIPO"] == id_eq]
             .dropna(subset=["FECHA_MEDICION"])
             .sort_values("FECHA_MEDICION").copy())
    if df_eq.empty:
        st.info("No se registran inspecciones de neumáticos para este equipo.")
        return

    df_eq["COCADA"] = pd.to_numeric(df_eq["COCADA"], errors="coerce")
    ultima = (df_eq.sort_values("FECHA_MEDICION")
              .groupby(["POSICION", "CARA"], as_index=False).tail(1))

    hor_pos = (ultima.groupby("POSICION")["HOROMETRO_MAQUINA"].max().to_dict()
               if "HOROMETRO_MAQUINA" in ultima.columns else {})

    pivot = ultima.pivot_table(index="POSICION", columns="CARA",
                               values="COCADA", aggfunc="last")
    for c in ["EXTERIOR", "INTERIOR"]:
        if c not in pivot.columns:
            pivot[c] = pd.NA
    pivot = pivot[["EXTERIOR", "INTERIOR"]]
    pivot["DELTA"] = (pivot["EXTERIOR"] - pivot["INTERIOR"]).round(1)
    pivot["COCADA_MIN"] = pivot[["EXTERIOR", "INTERIOR"]].min(axis=1, skipna=True)
    pivot["COCADA_MAX"] = pivot[["EXTERIOR", "INTERIOR"]].max(axis=1, skipna=True)
    pivot["ESTADO"] = pivot["COCADA_MIN"].apply(_estado_cocada)
    pivot["ROTACION"] = pivot.apply(
        lambda r: _estado_rotacion(r["DELTA"], r["COCADA_MIN"], r["COCADA_MAX"]),
        axis=1,
    )
    pivot = pivot.reset_index()

    # --- KPIs ---
    validos = pivot[["EXTERIOR", "INTERIOR"]].values.flatten()
    validos = validos[~pd.isna(validos)]
    cmin_glob = validos.min() if len(validos) else 0
    cprom = validos.mean() if len(validos) else 0
    dmax = pivot["DELTA"].dropna().abs().max() if not pivot["DELTA"].dropna().empty else 0
    n_alert = ((pivot["ESTADO"].isin(["🔴 CRÍTICO", "🟡 ATENCIÓN"])) |
               (pivot["ROTACION"].str.startswith("🔄"))).sum()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Cocada Mínima", f"{cmin_glob:.1f} mm",
              delta=f"{cmin_glob - NEUMATICOS['COCADA_MINIMA']:+.1f} vs mín.",
              delta_color="inverse" if cmin_glob < NEUMATICOS["COCADA_MINIMA"] else "normal")
    k2.metric("Cocada Promedio", f"{cprom:.1f} mm")
    if dmax > 0:
        k3.metric("Delta Máx. EXT/INT", f"{dmax:.1f} mm",
                  delta="Requiere rotación" if dmax > NEUMATICOS["DELTA_ROTACION"] else "Uniforme",
                  delta_color="inverse" if dmax > NEUMATICOS["DELTA_ROTACION"] else "normal")
    else:
        k3.metric("Delta Máx. EXT/INT", "—", delta="Sin ambas caras", delta_color="off")
    k4.metric("Neumáticos en Alerta", f"{n_alert} / {len(pivot)}")

    st.markdown("---")
    st.subheader("Mapa de Neumáticos")

    def _fila(pos_key):
        f = pivot[pivot["POSICION"] == pos_key]
        return None if f.empty else f.iloc[0]

    st.markdown("##### 🔹 Eje Delantero")
    d1, d2 = st.columns(2)
    with d1:
        st.markdown(svg_llanta("Delantero Izquierdo", _fila("DEL_IZQ"),
                               hor_pos.get("DEL_IZQ"),
                               NEUMATICOS["COCADA_NUEVA_MAX"],
                               NEUMATICOS["COLOR_ESTADO_HEX"]),
                    unsafe_allow_html=True)
    with d2:
        st.markdown(svg_llanta("Delantero Derecho", _fila("DEL_DER"),
                               hor_pos.get("DEL_DER"),
                               NEUMATICOS["COCADA_NUEVA_MAX"],
                               NEUMATICOS["COLOR_ESTADO_HEX"]),
                    unsafe_allow_html=True)

    st.markdown("<div style='text-align:center;color:#666;font-size:12px;"
                "margin:10px 0;'>──────────── 🚜 EQUIPO ────────────</div>",
                unsafe_allow_html=True)

    st.markdown("##### 🔹 Eje Trasero")
    t1, t2 = st.columns(2)
    with t1:
        st.markdown(svg_llanta("Posterior Izquierdo", _fila("POST_IZQ"),
                               hor_pos.get("POST_IZQ"),
                               NEUMATICOS["COCADA_NUEVA_MAX"],
                               NEUMATICOS["COLOR_ESTADO_HEX"]),
                    unsafe_allow_html=True)
    with t2:
        st.markdown(svg_llanta("Posterior Derecho", _fila("POST_DER"),
                               hor_pos.get("POST_DER"),
                               NEUMATICOS["COCADA_NUEVA_MAX"],
                               NEUMATICOS["COLOR_ESTADO_HEX"]),
                    unsafe_allow_html=True)

    st.caption(
        f"🎨 **Leyenda:** 🟢 ≥{NEUMATICOS['COCADA_MINIMA']} · "
        f"🟡 {NEUMATICOS['COCADA_CRITICA']}-{NEUMATICOS['COCADA_MINIMA']} · "
        f"🔴 <{NEUMATICOS['COCADA_CRITICA']} · 🟨 borde amarillo = requiere rotación."
    )

    st.markdown("---")

    rot = pivot[pivot["ROTACION"].str.startswith("🔄")]
    if not rot.empty:
        st.subheader("🔄 Recomendaciones de Rotación")
        st.warning(
            f"Se detectaron **{len(rot)}** neumático(s) que requieren atención "
            f"(delta > {NEUMATICOS['DELTA_ROTACION']} mm o cocada baja)."
        )
        for _, r in rot.iterrows():
            ext = f"{r['EXTERIOR']:.1f}" if pd.notna(r["EXTERIOR"]) else "—"
            inn = f"{r['INTERIOR']:.1f}" if pd.notna(r["INTERIOR"]) else "—"
            dl = f"{r['DELTA']:+.1f}" if pd.notna(r["DELTA"]) else "—"
            st.markdown(f"- **{r['POSICION']}** → EXT: {ext} mm | INT: {inn} mm | "
                        f"Delta: **{dl} mm** · {r['ROTACION']}")

    st.markdown("---")
    st.subheader("Tendencia Histórica de Desgaste (mm)")

    colores = {"DEL_IZQ": "#F6AD55", "DEL_DER": "#4FD1C5",
               "POST_IZQ": "#63B3ED", "POST_DER": "#FC8181"}
    fig = go.Figure()
    for pos in ["DEL_IZQ", "DEL_DER", "POST_IZQ", "POST_DER"]:
        for cara in ["EXTERIOR", "INTERIOR"]:
            sub = df_eq[(df_eq["POSICION"] == pos) & (df_eq["CARA"] == cara)].dropna(subset=["COCADA"])
            if sub.empty:
                continue
            fig.add_trace(go.Scatter(
                x=sub["FECHA_MEDICION"], y=sub["COCADA"],
                mode="lines+markers",
                name=f"{pos} · {cara[:3]}",
                line=dict(color=colores.get(pos, "#888888"),
                          dash="solid" if cara == "EXTERIOR" else "dash", width=2),
                marker=dict(size=5), connectgaps=False,
            ))
    fig.update_layout(template=TEMPLATE_PLOTLY, height=450,
                      xaxis_title="Fecha de Medición", yaxis_title="Cocada (mm)",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                  xanchor="right", x=1))
    fig.add_hline(y=NEUMATICOS["COCADA_MINIMA"], line_dash="dot",
                  line_color="orange",
                  annotation_text=f"Mínima operativa ({NEUMATICOS['COCADA_MINIMA']} mm)")
    fig.add_hline(y=NEUMATICOS["COCADA_CRITICA"], line_dash="dot",
                  line_color="red",
                  annotation_text=f"Crítica ({NEUMATICOS['COCADA_CRITICA']} mm)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Líneas sólidas = EXTERIOR · Líneas punteadas = INTERIOR. "
               "Si se cruzan, el neumático fue rotado/volteado.")