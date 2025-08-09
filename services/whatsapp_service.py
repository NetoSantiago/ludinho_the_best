import os, hmac, hashlib, httpx
from dotenv import load_dotenv
load_dotenv()

WA_BASE_URL = os.getenv("WA_BASE_URL", "http://localhost:21465")
WA_BEARER   = os.getenv("WA_BEARER", "")
WA_SESSION  = os.getenv("WA_SESSION", "ludolovers")
WA_WEBHOOK_SECRET = os.getenv("WA_WEBHOOK_SECRET", "")

def verify_signature(raw_body: bytes, signature: str) -> bool:
    # Se não houver segredo, não valida (útil quando WPPConnect não assina webhooks)
    if not WA_WEBHOOK_SECRET:
        return True
    mac = hmac.new(WA_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, (signature or ""))

async def send_message(to: str, text: str) -> dict:
    if not WA_BEARER:
        raise RuntimeError("WA_BEARER ausente. Gere o token no WPPConnect e defina no .env")

    url = f"{WA_BASE_URL}/api/{WA_SESSION}/send-message"
    headers = {
        "Authorization": f"Bearer {WA_BEARER}",
        "Content-Type": "application/json"
    }
    payload = {"phone": to, "message": text}

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()
