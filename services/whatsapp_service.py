import os, hmac, hashlib, httpx
import requests
from dotenv import load_dotenv
load_dotenv()

WA_BASE_URL = os.getenv("WA_BASE_URL", "http://localhost:21465")
WA_BEARER   = os.getenv("WA_BEARER", "")
WA_SESSION  = os.getenv("WA_SESSION", "ludolovers")
WA_WEBHOOK_SECRET = os.getenv("WA_WEBHOOK_SECRET", "")

def _headers():
    return {"Authorization": f"Bearer {WA_BEARER}"}

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
    data = {"phone": to, "message": text}
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(url, headers=_headers(), json=data)
        r.raise_for_status()
        return r.json()

def send_file(to: str, base64_data: str, filename: str, caption: str = ""):
    """
    Envia arquivo base64 (PDF/Imagem). O WPPConnect aceita base64 em alguns endpoints:
    /send-file-base64  (algumas builds)
    /send-file         (com URL)
    Aqui usamos o mais comum: /send-file-base64
    """
    # -- 1) garantir prefixo data:mime;base64,
    b64 = (base64_data or "").strip()
    fn = (filename or "comprovante").strip()
    mime = None
    # tentar inferir pelo nome primeiro
    fn_l = fn.lower()
    if fn_l.endswith(".pdf"):
        mime = "application/pdf"
    elif fn_l.endswith(".png"):
        mime = "image/png"
    elif fn_l.endswith(".jpg") or fn_l.endswith(".jpeg"):
        mime = "image/jpeg"
    # se não der pelo nome, tentar pela “assinatura” do base64
    if not mime:
        if b64.startswith("JVBERi0"):       # %PDF
            mime = "application/pdf"
            if "." not in fn_l: fn = ".pdf"
        elif b64.startswith("iVBOR"):       # PNG
            mime = "image/png"
            if "." not in fn_l: fn = ".png"
        elif b64.startswith("/9j/"):        # JPEG
            mime = "image/jpeg"
            if "." not in fn_l: fn = ".jpg"
        elif b64.startswith("R0lGOD"):      # GIF
            mime = "image/gif"
            if "." not in fn_l: fn = ".gif"
    # fallback
    if not mime:
        mime = "application/octet-stream"
        if "." not in fn_l:
            fn = ".bin"

    if not b64.startswith("data:"):
        b64 = f"data:{mime};base64,{b64}"

    url = f"{WA_BASE_URL}/api/ludolovers/send-file-base64"
    payload = {
        "phone": to,
        "base64": b64,
        "filename": fn,
        "caption": caption or ""
    }

    r = requests.post(url, headers=_headers(), json=payload, timeout=30)
    r.raise_for_status()
    return r.json()
