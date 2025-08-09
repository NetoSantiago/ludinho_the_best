from typing import Dict, Any
from services.supabase_client import get_client

def convert_item(item_id: str, atendente_email: str) -> Dict[str, Any]:
    supa = get_client()
    res = supa.rpc("convert_item_to_ludocoins", {"p_item_id": item_id, "p_atendente": atendente_email}).execute()

    return getattr(res, "data", {"ok": False})

def get_saldo(telefone: str) -> float:
    supa = get_client()
    cliente = supa.table("clientes").select("ludocoins_saldo").eq("telefone", telefone).single().execute().data

    return float(cliente["ludocoins_saldo"])

def list_ultimas_transacoes(telefone: str, limit: int = 5):
    supa = get_client()

    return supa.table("ludocoin_transacoes").select("*").eq("telefone_cliente", telefone).order("created_at", desc=True).limit(limit).execute().data or []
