# ============================================================
#  TAB 3: COMPONENTES
# ============================================================
import streamlit as st
import pandas as pd

from config.settings import COMPONENTES


def render_tab_componentes(ctx: dict, df_componentes: pd.DataFrame):
    nombre = ctx["nombre_seleccionado"]
    id_eq = ctx["id_equipo_sel"]
    df_eq_hor = ctx["df_horometro_equipo"]

    st.header(f"Evolución de Componentes Mayores - {nombre}")

    if df_componentes.empty or "ID_EQUIPO" not in df_componentes.columns:
        st.info("No hay datos de componentes disponibles.")
        return

    df_c = df_componentes[df_componentes["ID_EQUIPO"] == id_eq].copy()

    # Filtrar devueltos
    if "DEVOLVER_CAMBIO" in df_c.columns:
        mask_dev = (df_c["DEVOLVER_CAMBIO"].astype(str).str.strip().str.upper()
                    .isin(["SI", "SÍ", "S", "YES", "Y", "TRUE", "1"]))
        df_c = df_c[~mask_dev]

    if "HOROMETRO_CAMBIO(PROYECTADO)" in df_c.columns:
        df_c = df_c.dropna(subset=["HOROMETRO_CAMBIO(PROYECTADO)"])
        df_c = df_c[df_c["HOROMETRO_CAMBIO(PROYECTADO)"] > 0]

    if df_c.empty:
        st.info("No se registran componentes mayores activos asociados a este equipo.")
        return

    ultimo_h = df_eq_hor["HFINAL"].max()
    if pd.isna(ultimo_h):
        st.info("No se registran lecturas de horómetro recientes para calcular las alertas.")
        return

    df_c["HORAS_RESTANTES"] = df_c["HOROMETRO_CAMBIO(PROYECTADO)"] - ultimo_h

    def _clasif(h):
        if h <= COMPONENTES["HORAS_CRITICO"]:
            return "CRITICO"
        if h <= COMPONENTES["HORAS_ATENCION"]:
            return "ATENCION"
        return "OK"

    df_c["ESTADO"] = df_c["HORAS_RESTANTES"].apply(_clasif)
    orden = {"CRITICO": 0, "ATENCION": 1, "OK": 2}
    df_c = df_c.sort_values(
        by=["ESTADO", "HORAS_RESTANTES"],
        key=lambda s: s.map(orden) if s.name == "ESTADO" else s,
        ascending=[True, True],
    )

    n_crit = (df_c["ESTADO"] == "CRITICO").sum()
    n_aten = (df_c["ESTADO"] == "ATENCION").sum()
    n_ok = (df_c["ESTADO"] == "OK").sum()

    st.markdown(f"### 🚨 Alertas Preventivas de Ciclo de Vida "
                f"(Horómetro Máquina: **{ultimo_h:,.1f} Hrs**)")
    m1, m2, m3 = st.columns(3)
    m1.metric("🔴 Críticos", n_crit)
    m2.metric("🟡 Próximos", n_aten)
    m3.metric("🟢 OK", n_ok)

    st.markdown("---")

    for _, row in df_c.iterrows():
        h_cambio = row["HOROMETRO_CAMBIO(PROYECTADO)"]
        h_inst = row.get("HOROMETRO_INSTALACION", None)
        h_rest = row["HORAS_RESTANTES"]

        if pd.notna(h_inst) and h_cambio > h_inst:
            vida = h_cambio - h_inst
            consumida = max(0.0, min(1.0, (ultimo_h - h_inst) / vida))
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

            if h_rest <= 0:
                st.error(
                    f"🔴 CRÍTICO: El componente **{tipo}** ({desc}) superó su "
                    f"límite por **{abs(h_rest):,.1f} horas**. ¡Agendar parada inmediata!"
                )
            elif h_rest <= COMPONENTES["HORAS_ATENCION"]:
                st.warning(
                    f"🟡 ATENCIÓN: El componente **{tipo}** está próximo al desgaste "
                    f"programado. Quedan **{h_rest:,.1f} horas**."
                )
            else:
                st.success(
                    f"🟢 O.K: Componente **{tipo}** operativo. "
                    f"**{h_rest:,.1f} horas** de trabajo seguro disponible."
                )