from typing import Dict, Any, List
from services.supabase_client import get_client
import shortuuid

def criar_pedido_envio(container_id: str, telefone: str, nome: str, itens_snapshot: List[dict]) -> Dict[str, Any]:
    supa = get_client()

    existing = (
        supa.table("envios")
        .select("*")
        .eq("container_id", container_id)
        .in_("status_envio", ["PENDENTE", "EM_PREPARACAO"])
        .limit(1)
        .execute()
    ).data or []

    if existing:
        return existing[0]
    
    res = supa.table("envios").insert({
        "container_id": container_id,
        "telefone_cliente": telefone,
        "nome_cliente": nome,
        "status_envio": "PENDENTE",
        "itens_snapshot_json": itens_snapshot
    }).execute()

    try:
    # Fecha o container atual para não aparecer mais ao cliente
        try:
            supa.table("containers").update({"status": "PENDENTE"}).eq("id", container_id).execute()
        except Exception as e:
            print("envios_service: update container to PENDENTE error:", e)

        # Cria um novo container ABERTO
        new_id = f"{telefone}-{shortuuid.ShortUUID().random(length=6).upper()}"
        try:
            supa.table("containers").insert({
                "id": new_id,
                "telefone_cliente": telefone,
                "status": "ABERTO",
            }).execute()
        except Exception as e:
            print("envios_service: create new open container error:", e)

        # Move itens não enviados (PRÉ-VENDA) para o novo container
        try:
            supa.table("container_itens").update({"container_id": new_id}) \
                .eq("container_id", container_id).eq("status_item", "PRE-VENDA").execute()
        except Exception as e:
            print("envios_service: move PRE-VENDA items error:", e)
    except Exception as e:
        print("envios_service: split after envio error:", e)

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
