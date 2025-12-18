from __future__ import annotations
from typing import List, Dict, Any
import shortuuid

from services.supabase_client import get_client


def _phone_container_id(telefone: str) -> str:
    # id legível + único
    return f"{telefone}-{shortuuid.ShortUUID().random(length=6).upper()}"


def _has_items(supa, container_id: str) -> bool:
    """
    Evita count/head (que podem gerar 204). Apenas tenta pegar 1 item.
    """
    try:
        r = (
            supa.table("container_itens")
            .select("id")
            .eq("container_id", container_id)
            .limit(1)
            .execute()
        )
        data = getattr(r, "data", None) or []
        return len(data) > 0
    except Exception as e:
        # Em caso de erro no PostgREST, assuma vazio (não quebra o fluxo)
        print("containers_service._has_items error:", e)
        return False


def get_or_create_open_container(telefone: str) -> str:
    """
    Estratégia:
      1) Se existir container ABERTO com itens (>0), retorna o MAIS RECENTE entre eles.
      2) Senão, se existir algum ABERTO (mesmo vazio), retorna o mais recente.
      3) Senão, cria um novo container ABERTO.
    Tolerante a erros do PostgREST: nunca levanta exceção para o chamador.
    """
    supa = get_client()

    try:
        # Busca todos os abertos do cliente, mais recente primeiro
        r = (
            supa.table("containers")
            .select("id, created_at, updated_at")
            .eq("telefone_cliente", telefone)
            .eq("status", "ABERTO")
            .order("updated_at", desc=True)
            .order("created_at", desc=True)
            .execute()
        )
        rows = getattr(r, "data", None) or []
    except Exception as e:
        print("containers_service.get_or_create_open_container select error:", e)
        rows = []

    # 1) prioriza o aberto que tenha itens
    for row in rows:
        cid = row["id"]
        if _has_items(supa, cid):
            return cid

    # 2) se nenhum com itens, devolve o mais recente (se existir)
    if rows:
        return rows[0]["id"]

    # 3) criar um novo
    new_id = _phone_container_id(telefone)
    try:
        supa.table("containers").insert({
            "id": new_id,
            "telefone_cliente": telefone,
            "status": "ABERTO",
        }).execute()
    except Exception as e:
        # Mesmo que falhe o insert, retornamos o id gerado para o fluxo do bot/streamlit seguir
        print("containers_service.get_or_create_open_container insert error:", e)
    return new_id


def list_container_items(container_id: str) -> List[Dict[str, Any]]:
    """
    Lista itens (exclui RESGATADO) + join de jogo.
    """
    supa = get_client()
    try:
        res = (
            supa.from_("container_itens")
            .select("*, jogos(*)")
            .eq("container_id", container_id)
            .neq("status_item", "RESGATADO")
            .execute()
        )
        return getattr(res, "data", None) or []
    except Exception as e:
        print("containers_service.list_container_items error:", e)
        return []

def list_enviaveis(container_id: str) -> List[Dict[str, Any]]:
    """
    Itens que podem ir no envio: somente DISPONIVEL (exclui PRE-VENDA/RESGATADO).
    """
    supa = get_client()
    try:
        res = (
            supa.from_("container_itens")
            .select("*, jogos(*)")
            .eq("container_id", container_id)
            .eq("status_item", "DISPONIVEL")
            .execute()
        )
        return getattr(res, "data", None) or []
    except Exception as e:
        print("containers_service.list_enviaveis error:", e)
        return []

def list_trocaveis(container_id: str) -> List[Dict[str, Any]]:
    """
    Itens elegíveis a troca (LISTINHA) mesmo se PRE-VENDA, exclui RESGATADO.
    """
    supa = get_client()
    try:
        res = (
            supa.from_("container_itens")
            .select("*, jogos(*)")
            .eq("container_id", container_id)
            .eq("origem", "LISTINHA")
            .in_("status_item", ["DISPONIVEL", "PRE-VENDA"])
            .execute()
        )
        return getattr(res, "data", None) or []
    except Exception as e:
        print("containers_service.list_trocaveis error:", e)
        return []
