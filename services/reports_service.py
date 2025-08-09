import pandas as pd
from services.supabase_client import get_client

def inventario_por_status() -> pd.DataFrame:
    supa = get_client()
    itens = supa.table("container_itens").select("status_item, preco_aplicado_brl").execute().data or []
    df = pd.DataFrame(itens)
    if df.empty:
        return pd.DataFrame(columns=["status_item","quantidade","valor_total"])

    g = df.groupby("status_item").agg(quantidade=("status_item","count"), valor_total=("preco_aplicado_brl","sum")).reset_index()

    return g

def containers_por_status() -> pd.DataFrame:
    supa = get_client()
    cts = supa.table("containers").select("status, created_at").execute().data or []
    df = pd.DataFrame(cts)
    if df.empty:
        return pd.DataFrame(columns=["status","quantidade"])
    
    return df.groupby("status").size().reset_index(name="quantidade")

def passivo_ludocoins() -> float:
    supa = get_client()
    v = supa.table("v_passivo_ludocoins").select("*").execute().data or []
    if v:
        return float(v[0]["total_ludocoins"] or 0)

    return 0.0
