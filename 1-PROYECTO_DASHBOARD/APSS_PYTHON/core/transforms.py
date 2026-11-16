# ============================================================
#  TRANSFORMACIONES / DERIVADAS
# ============================================================
import numpy as np
import pandas as pd

from core.cleaning import limpiar_horas, convertir_fecha, normalizar_id_equipo


def transformar_horometros(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    # Numéricas
    cols_horas = ["H_INICIAL", "HFINAL", "HORAS_DIESEL", "HRS_OPERADAS",
                  "PARADA_MEC", "PARADA_OP", "INSPECCION", "HORAS_PROG",
                  "TOTAL_PARADA", "TOTAL_TIEMPO", "AJUSTE_PARADA_OP",
                  "HR_NO_DISP", "HR_DISP", "HR_USADO", "HR_NO_USADO"]
    for c in cols_horas:
        if c in df.columns:
            df[c] = limpiar_horas(df[c])

    cols_pct = ["DISP_MEC", "USO_EFECTIVO_1", "USO_EFECTIVO",
                "USO_DISP", "UTILIZACION", "UTIL_EFECTIVA"]
    for c in cols_pct:
        if c in df.columns:
            df[c] = limpiar_horas(df[c])

    if "N_FALLAS" in df.columns:
        df["N_FALLAS"] = pd.to_numeric(df["N_FALLAS"], errors="coerce").fillna(0).astype(int)

    # Fechas
    convertir_fecha(df, "FECHA")

    # Derivadas
    if "HRS_OPERADAS" not in df.columns:
        df["HRS_OPERADAS"] = df["HFINAL"] - df["H_INICIAL"]
    df.loc[df["HFINAL"].isna(), "HRS_OPERADAS"] = pd.NA
    df.loc[df["HRS_OPERADAS"] < 0, "HRS_OPERADAS"] = pd.NA

    df["MES_NUM"] = df["FECHA"].dt.month
    df["ANIO"] = df["FECHA"].dt.year
    df["PERIODO_MES"] = df["FECHA"].dt.strftime("%Y-%m")
    df["MES_NOMBRE"] = df["FECHA"].dt.strftime("%B").str.capitalize()

    if "STATUS_EQUIPO" not in df.columns:
        df["STATUS_EQUIPO"] = np.where(
            df["HRS_OPERADAS"].fillna(0) > 0, "OPERATIVO", "INOPERATIVO"
        )

    normalizar_id_equipo(df)
    return df


def transformar_paradas(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    convertir_fecha(df, "FECHA")
    df["DURACION"] = limpiar_horas(df["DURACION"])
    df["MES_NUM"] = df["FECHA"].dt.month
    df["ANIO"] = df["FECHA"].dt.year
    df["PERIODO_MES"] = df["FECHA"].dt.strftime("%Y-%m")
    df["TIPO_UP"] = df["TIPO DE PARADA"].astype(str).str.strip().str.upper()
    normalizar_id_equipo(df, "EQUIPO")
    return df


def transformar_componentes(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    normalizar_id_equipo(df)
    if "FECHA_INSTALACION" in df.columns:
        convertir_fecha(df, "FECHA_INSTALACION")
    return df


def transformar_neumaticos(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    normalizar_id_equipo(df)
    if "FECHA_MEDICION" in df.columns:
        convertir_fecha(df, "FECHA_MEDICION")
    if "POSICION" in df.columns:
        df["POSICION"] = df["POSICION"].astype(str).str.strip()
    if "CARA" in df.columns:
        df["CARA"] = df["CARA"].astype(str).str.strip().str.upper()
    return df


def transformar_engrase(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    normalizar_id_equipo(df)
    if "FECHA" in df.columns:
        convertir_fecha(df, "FECHA")
        df["MES_NUM"] = df["FECHA"].dt.month
        df["ANIO"] = df["FECHA"].dt.year
    if ("PUNTOS_ENGRASADOS" in df.columns and
            "PUNTOS_TOTALES" in df.columns):
        df["PCT_CUMPLIMIENTO"] = (
            df["PUNTOS_ENGRASADOS"] / df["PUNTOS_TOTALES"] * 100
        ).round(1)
    else:
        df["PCT_CUMPLIMIENTO"] = 0.0
    return df


def transformar_equipos(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    normalizar_id_equipo(df)
    if "NOMBRE" in df.columns:
        df["NOMBRE"] = df["NOMBRE"].astype(str).str.strip()
    return df