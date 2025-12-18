import pandas as pd

TZ = "America/Fortaleza"
FMT = "%d/%m/%Y %H:%M:%S"

def format_ts(df):
    if df is None or df.empty:
        return df
    ts_cols = [c for c in df.columns if c.endswith("_at") or c in ("created_at", "updated_at")]
    for c in ts_cols:
        df[c] = (
            pd.to_datetime(df[c], utc=True, errors="coerce")
              .dt.tz_convert(TZ)
              .dt.strftime(FMT)
        )
    return df
