# ============================================================
#  FUNCIONES DE LIMPIEZA DE DATOS
# ============================================================
import pandas as pd


def limpiar_horas(serie: pd.Series) -> pd.Series:
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


def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Uppercase y strip de todos los encabezados."""
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df


def normalizar_id_equipo(df: pd.DataFrame, col: str = "ID_EQUIPO") -> pd.DataFrame:
    """Strip y cast a str sobre columna de ID/EQUIPO."""
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    return df


def convertir_fecha(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Convertir columna a datetime (dayfirst)."""
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    return df