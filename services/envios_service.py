from typing import Dict, Any, List
from services.supabase_client import get_client

def criar_pedido_envio(container_id: str, telefone: str, nome: str, itens_snapshot: List[dict]) -> Dict[str, Any]:
    supa = get_client()
    res = supa.table("envios").insert({
        "container_id": container_id,
        "telefone_cliente": telefone,
        "nome_cliente": nome,
        "status_envio": "PENDENTE",
        "itens_snapshot_json": itens_snapshot
    }).execute()

    return res.data[0]

def listar_envios(status: str = None):
    supa = get_client()
    q = supa.table("envios").select("*").order("created_at", desc=True)
    if status:
        q = q.eq("status_envio", status)

    return q.execute().data or []

def atualizar_status_envio(envio_id: str, status: str):
    supa = get_client()

    return supa.table("envios").update({"status_envio": status}).eq("id", envio_id).execute().data[0]
