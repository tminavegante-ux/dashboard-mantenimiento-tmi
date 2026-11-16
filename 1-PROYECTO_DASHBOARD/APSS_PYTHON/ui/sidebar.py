# ============================================================
#  SIDEBAR + FILTROS GLOBALES
# ============================================================
import os
import streamlit as st
import pandas as pd

from config.settings import LOGO_PATH, DICC_MESES


def render_sidebar(df_equipos: pd.DataFrame, df_horometro: pd.DataFrame) -> dict:
    """Dibuja el sidebar y devuelve un dict con el contexto de filtros."""
    if os.path.exists(LOGO_PATH):
        st.sidebar.image(LOGO_PATH, width=160)

    st.sidebar.header("⚙️ Filtros de Control")

    if st.sidebar.button("🔄 Refrescar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    dicc_equipos = dict(zip(df_equipos["NOMBRE"], df_equipos["ID_EQUIPO"]))
    nombre_seleccionado = st.sidebar.selectbox(
        "Seleccione el Equipo:", list(dicc_equipos.keys())
    )
    id_equipo_sel = dicc_equipos[nombre_seleccionado]

    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Filtro Temporal")

    df_h_eq = df_horometro[df_horometro["ID_EQUIPO"] == id_equipo_sel]
    meses_en_datos = sorted(df_h_eq["MES_NUM"].dropna().astype(int).unique())

    mes_sel_num = None
    if meses_en_datos:
        nombres_meses = [DICC_MESES[m] for m in meses_en_datos]
        mes_sel_nombre = st.sidebar.radio("Meses Disponibles:", nombres_meses)
        mes_sel_num = [k for k, v in DICC_MESES.items() if v == mes_sel_nombre][0]
    else:
        st.sidebar.warning("⚠️ No hay registros de horómetro para este equipo.")

    # Derivados: filtros de mes
    if mes_sel_num:
        df_h_filtrado_mes = df_horometro[df_horometro["MES_NUM"] == mes_sel_num]
        df_h_filtrado_equipo = df_h_filtrado_mes[
            df_h_filtrado_mes["ID_EQUIPO"] == id_equipo_sel
        ]
    else:
        df_h_filtrado_mes = pd.DataFrame()
        df_h_filtrado_equipo = pd.DataFrame()

    return {
        "dicc_equipos": dicc_equipos,
        "nombre_seleccionado": nombre_seleccionado,
        "id_equipo_sel": id_equipo_sel,
        "mes_sel_num": mes_sel_num,
        "df_horometro_equipo": df_h_eq,
        "df_h_filtrado_mes": df_h_filtrado_mes,
        "df_h_filtrado_equipo": df_h_filtrado_equipo,
    }