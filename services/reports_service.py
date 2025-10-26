from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from services.supabase_client import get_client
from services.table_utils import TableData


def _safe_float(value: object) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def inventario_por_status() -> TableData:
    supa = get_client()
    itens = supa.table("container_itens").select("status_item, preco_aplicado_brl").execute().data or []
    acumulado: Dict[str, Dict[str, float]] = defaultdict(lambda: {"quantidade": 0.0, "valor_total": 0.0})

    for item in itens:
        status = item.get("status_item")
        if not status:
            continue
        dados = acumulado[status]
        dados["quantidade"] += 1
        dados["valor_total"] += _safe_float(item.get("preco_aplicado_brl"))

    linhas: List[Dict[str, float]] = [
        {
            "status_item": status,
            "quantidade": int(values["quantidade"]),
            "valor_total": values["valor_total"],
        }
        for status, values in sorted(acumulado.items())
    ]

    return TableData(linhas)


def containers_por_status() -> TableData:
    supa = get_client()
    cts = supa.table("containers").select("status, created_at").execute().data or []
    contagem: Dict[str, int] = defaultdict(int)

    for item in cts:
        status = item.get("status")
        if not status:
            continue
        contagem[status] += 1

    linhas = [
        {"status": status, "quantidade": quantidade}
        for status, quantidade in sorted(contagem.items())
    ]

    return TableData(linhas)


def passivo_ludocoins() -> float:
    supa = get_client()
    v = supa.table("v_passivo_ludocoins").select("*").execute().data or []
    if v:
        return float(v[0]["total_ludocoins"] or 0)

    return 0.0
