from typing import List, Dict, Any, Optional

from services.supabase_client import get_client


def _first_record(res: Any) -> Optional[Dict[str, Any]]:
    data = getattr(res, "data", None)
    if data is None and isinstance(res, dict):
        data = res.get("data")
    if isinstance(data, list):
        return data[0] if data else None
    return data


def get_or_create_open_container(cliente_id: str) -> Optional[str]:
    cliente_id = (cliente_id or "").strip()
    if not cliente_id:
        return None

    supa = get_client()
    container = (
        supa.table("containers")
        .select("*")
        .eq("cliente_id", cliente_id)
        .eq("status", "ABERTO")
        .maybe_single()
        .execute()
    )

    existing = _first_record(container)
    if existing and existing.get("id"):
        return existing["id"]

    novo_container = (
        supa.table("containers")
        .insert({"cliente_id": cliente_id, "status": "ABERTO"})
        .execute()
    )
    created = _first_record(novo_container)
    return created.get("id") if created else None

def list_container_items(container_id: str) -> List[Dict[str, Any]]:
    supa = get_client()
    res = supa.table("container_itens").select("*, jogos(*), movimentos(*)").eq("container_id", container_id).execute()

    return res.data or []

def add_item_by_movimento(tipo: str, telefone: str, jogo_id: str, preco: float, status_item: str) -> Dict[str, Any]:
    supa = get_client()
    container_id = get_or_create_open_container(telefone)
    if not container_id:
        raise RuntimeError("Não foi possível criar ou localizar o container do cliente.")

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
