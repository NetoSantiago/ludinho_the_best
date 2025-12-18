
from __future__ import annotations
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone

from services.supabase_client import get_client

STATE_TTL = timedelta(minutes=15)

class StateNames:
    ONBOARD_ASK_NAME = "ONBOARD_ASK_NAME"
    TROCA_LISTANDO = "TROCA_LISTANDO"
    TROCA_CONFIRM = "TROCA_CONFIRM"
    ENVIAR_CONFIRM = "ENVIAR_CONFIRM"
    COMPROVANTE_WAIT = "COMPROVANTE_WAIT"

def _now_utc():
    return datetime.now(timezone.utc)

def _safe_client():
    try:
        return get_client()
    except Exception as e:
        print("chat_state_service: get_client error:", e)
        return None

def get_state(telefone: str) -> Optional[Dict[str, Any]]:
    supa = _safe_client()
    if not supa:
        return None
    try:
        res = supa.table("chat_states").select("*").eq("telefone", telefone).maybe_single().execute()
        data = getattr(res, "data", None)
        if data is None and isinstance(res, dict):
            data = res.get("data")
        if not data:
            return None
        updated = data.get("updated_at")
        try:
            updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        except Exception:
            updated_dt = _now_utc()
        if _now_utc() - updated_dt > STATE_TTL:
            clear_state(telefone)
            return None
        return {"state": data.get("state"), "data": data.get("data") or {}}
    except Exception as e:
        print("get_state error:", e)
        return None

def set_state(telefone: str, state: str, data: Dict[str, Any] | None = None) -> None:
    supa = _safe_client()
    if not supa:
        return
    try:
        supa.table("chat_states").upsert({
            "telefone": telefone,
            "state": state,
            "data": data or {},
        }).execute()
    except Exception as e:
        print("set_state error:", e)

def clear_state(telefone: str) -> None:
    supa = _safe_client()
    if not supa:
        return
    try:
        supa.table("chat_states").delete().eq("telefone", telefone).execute()
    except Exception as e:
        print("clear_state error:", e)
