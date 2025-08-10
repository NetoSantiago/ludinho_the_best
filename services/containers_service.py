from typing import List, Dict, Any
import shortuuid
from services.supabase_client import get_client

def get_or_create_open_container(cliente_id):
    supa = get_client()
    container = supa.table("containers") \
        .select("*") \
        .eq("cliente_id", cliente_id) \
        .eq("status", "ABERTO") \
        .maybe_single() \
        .execute()

    if not container or not container.data:
        # Criar novo container se não existir
        novo_container = supa.table("containers").insert({
            "cliente_id": cliente_id,
            "status": "ABERTO"
        }).execute()
        return novo_container.data[0] if novo_container and novo_container.data else None

    return container.data

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
