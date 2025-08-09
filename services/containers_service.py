from typing import List, Dict, Any
import shortuuid
from services.supabase_client import get_client

def get_or_create_open_container(telefone: str) -> str:
    supa = get_client()
    res = supa.table("containers").select("*").eq("telefone_cliente", telefone).eq("status","ABERTO").order("created_at", desc=True).limit(1).execute()
    rows = res.data or []
    if rows:
        return rows[0]["id"]
    
    container_id = f"{telefone}-{shortuuid.ShortUUID().random(length=7)}"
    supa.table("containers").insert({"id": container_id, "telefone_cliente": telefone, "status": "ABERTO"}).execute()

    return container_id

def list_container_items(container_id: str) -> List[Dict[str, Any]]:
    supa = get_client()
    res = supa.table("container_itens").select("*, jogos(*), movimentos(*)").eq("container_id", container_id).execute()

    return res.data or []

def add_item_by_movimento(tipo: str, telefone: str, jogo_id: str, preco: float, status_item: str) -> Dict[str, Any]:
    supa = get_client()
    container_id = get_or_create_open_container(telefone)

    it = supa.table("container_itens").insert({
        "container_id": container_id,
        "jogo_id": jogo_id,
        "origem": "RIFA" if tipo == "RIFA" else "COMPRA",
        "status_item": status_item,
        "preco_aplicado_brl": preco
    }).execute().data[0]

    mv = supa.table("movimentos").insert({
        "tipo": tipo,
        "telefone_cliente": telefone,
        "jogo_id": jogo_id,
        "preco_aplicado_brl": preco,
        "container_id": container_id,
        "container_item_id": it["id"]
    }).execute().data[0]

    supa.table("container_itens").update({"movimento_id": mv["id"]}).eq("id", it["id"]).execute()

    return {"movimento": mv, "item": it, "container_id": container_id}

def list_container_by_status(status: str):
    supa = get_client()
    
    return (supa.table("containers").select("*").eq("status", status).execute().data or [])
