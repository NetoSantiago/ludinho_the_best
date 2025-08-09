from typing import List, Dict, Any
from services.supabase_client import get_client

def list_movimentos(limit: int = 100) -> List[Dict[str, Any]]:
    supa = get_client()

    return supa.table("movimentos").select("*").order("created_at", desc=True).limit(limit).execute().data or []
