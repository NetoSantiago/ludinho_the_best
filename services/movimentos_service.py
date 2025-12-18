from typing import List, Dict, Any
import re
from services.supabase_client import get_client
from services.containers_service import get_or_create_open_container


def list_movimentos(limit: int = 100) -> List[Dict[str, Any]]:
    supa = get_client()
    return (
        supa.table("movimentos")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )


def add_item_by_movimento(
    tipo: str,
    telefone: str,
    jogo_id: str,
    preco: float,
    status_item: str,
) -> Dict[str, Any]:
    """
    Cria um item no container ABERTO do cliente e registra o movimento correspondente.
    Mantém os nomes de campos/tabelas conforme o schema atual.
    Retorna o registro de movimento criado (inclui container_id).
    """
    supa = get_client()
    tel = re.sub(r"\D+", "", telefone or "")

    # Garante um container ABERTO
    container_id = get_or_create_open_container(tel)

    # 1) insere o item no container
    it_res = (
        supa.table("container_itens")
        .insert({
            "container_id": container_id,
            "jogo_id": jogo_id,
            "origem": tipo,
            "status_item": status_item,
            "preco_aplicado_brl": preco,
        })
        .execute()
    )
    it_data = (getattr(it_res, "data", None) or [{}])[0]
    item_id = it_data.get("id")

    # 2) registra o movimento já referenciando o item (mantém unicidade em container_item_id)
    mov_res = (
        supa.table("movimentos")
        .insert({
            "tipo": tipo,
            "telefone_cliente": tel,
            "jogo_id": jogo_id,
            "preco_aplicado_brl": preco,
            "container_id": container_id,
            "container_item_id": item_id,
        })
        .execute()
    )
    mov = (getattr(mov_res, "data", None) or [{}])[0]

    # 3) vincula o movimento de volta no item (útil para auditoria)
    try:
        if mov.get("id") and item_id:
            supa.table("container_itens").update({"movimento_id": mov["id"]}).eq("id", item_id).execute()
    except Exception as e:
        print("movimentos_service.add_item_by_movimento: update movimento_id error:", e)

    return mov
