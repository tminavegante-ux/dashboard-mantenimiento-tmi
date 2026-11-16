# ============================================================
#  CARGA DE DATOS — GOOGLE SHEETS + MAPEOS DE COLUMNAS
# ============================================================
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

from config.settings import HOJAS, CACHE_TTL, GSHEETS_CONNECTION, GSHEETS_TTL
from core.cleaning import normalizar_columnas


MAPEO_HOROMETRO = {
    "NUMERO SEMANA": "NUMERO SEMANA",
    "TURNO": "TURNO",
    "TIPO DE EQUIPO": "TIPO_EQUIPO",
    "HORAS PROGRAMADAS": "HORAS_PROG",
    "HORÓMETRO INICIAL (DIÉSEL)": "H_INICIAL",
    "HORÓMETRO FINAL (DIÉSEL)": "HFINAL",
    "HORAS DIÉSEL": "HORAS_DIESEL",
    "HORAS EFECTIVAS TRABAJADAS": "HRS_OPERADAS",
    "HR. PARADA MECÁNICA": "PARADA_MEC",
    "HR. PARADA OPERATIVA": "PARADA_OP",
    "HR. INSPECCIÓN": "INSPECCION",
    "TOTAL HR PARADA": "TOTAL_PARADA",
    "TOTAL TIEMPO": "TOTAL_TIEMPO",
    "HR. A AGREGAR O QUITAR POR PARADA OPERATIVA NO REPORTADA": "AJUSTE_PARADA_OP",
    "HR. NO DISPONIBLE": "HR_NO_DISP",
    "HR. DISPONIBLE": "HR_DISP",
    "HR. USADO": "HR_USADO",
    "HR. NO USADO": "HR_NO_USADO",
    "#FALLAS": "N_FALLAS",
    "DISPONIBILIDAD MECANICA": "DISP_MEC",
    "USO EFECTIVO DE DISPONIBILIDAD-1": "USO_EFECTIVO_1",
    "USO EFECTIVO DE DISPONIBILIDAD": "USO_EFECTIVO",
    "USO DE DISPONIBILIDAD": "USO_DISP",
    "UTILIZACIÓN": "UTILIZACION",
    "UTILIZACIÓN EFECTIVA": "UTIL_EFECTIVA",
}

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

MAPEO_GENERAL = {
    "NOMBRE_EQUIPO": "NOMBRE",
    "NOMBR_EQUIPO": "NOMBRE",
    "H_FINAL": "HFINAL",
    "HRS_FINAL": "HFINAL",
    "HORA_FINAL": "HFINAL",
    "H_INICIO": "H_INICIAL",
    "HRS_INICIAL": "H_INICIAL",
    "HORA_INICIAL": "H_INICIAL",
    "HOROMETRO_CAMBIO (PROYECTADO)": "HOROMETRO_CAMBIO(PROYECTADO)",
    "HOROMETRO_CAMBIO_PROYECTADO": "HOROMETRO_CAMBIO(PROYECTADO)",
}


def _aplicar_mapeo(df, mapeo):
    return df.rename(columns={k: v for k, v in mapeo.items() if k in df.columns})


@st.cache_data(ttl=CACHE_TTL, show_spinner="Cargando datos de Google Sheets...")
def cargar_datos():
    try:
        conn = st.connection(GSHEETS_CONNECTION, type=GSheetsConnection)

        df_eq = conn.read(worksheet=HOJAS["equipos"],     ttl=GSHEETS_TTL)
        df_ho = conn.read(worksheet=HOJAS["horometros"],  ttl=GSHEETS_TTL)
        df_co = conn.read(worksheet=HOJAS["componentes"], ttl=GSHEETS_TTL)
        df_ne = conn.read(worksheet=HOJAS["neumaticos"],  ttl=GSHEETS_TTL)
        df_en = conn.read(worksheet=HOJAS["engrase"],     ttl=GSHEETS_TTL)
        df_pa = conn.read(worksheet=HOJAS["paradas"],     ttl=GSHEETS_TTL)

        for df in (df_eq, df_ho, df_co, df_ne, df_en, df_pa):
            normalizar_columnas(df)

        df_ho = _aplicar_mapeo(df_ho, MAPEO_HOROMETRO)
        df_pa = _aplicar_mapeo(df_pa, MAPEO_PARADAS)
        df_co = _aplicar_mapeo(df_co, MAPEO_GENERAL)
        df_ne = _aplicar_mapeo(df_ne, MAPEO_GENERAL)
        df_en = _aplicar_mapeo(df_en, MAPEO_GENERAL)

        if "COLUMNA1" in df_ho.columns:
            df_ho = df_ho.drop(columns=["COLUMNA1"])

        if "ID_EQUIPO" not in df_eq.columns or "NOMBRE" not in df_eq.columns:
            raise ValueError(
                f"Hoja 'EQUIPOS' debe tener ID_EQUIPO y NOMBRE. "
                f"Columnas: {list(df_eq.columns)}"
            )
        falt_ho = [c for c in ["FECHA", "ID_EQUIPO", "H_INICIAL", "HFINAL"]
                   if c not in df_ho.columns]
        if falt_ho:
            raise ValueError(
                f"Hoja 'HOROMETROS' le faltan columnas: {falt_ho}. "
                f"Columnas: {list(df_ho.columns)}"
            )
        falt_pa = [c for c in ["FECHA", "TIPO DE PARADA", "DURACION", "EQUIPO"]
                   if c not in df_pa.columns]
        if falt_pa:
            raise ValueError(
                f"Hoja 'PARADAS-M' le faltan columnas: {falt_pa}. "
                f"Columnas: {list(df_pa.columns)}"
            )
        if "DESCRIPCION DE LA FALLA" not in df_pa.columns:
            df_pa["DESCRIPCION DE LA FALLA"] = ""

        return (df_eq, df_ho, df_co, df_ne, df_en, df_pa, True, "Google Sheets")

    except Exception as e:
        vacio = pd.DataFrame()
        return (vacio, vacio, vacio, vacio, vacio, vacio, False, str(e))
