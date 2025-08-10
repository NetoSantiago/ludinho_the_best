# Ludolovers – Containers & Ludocoins

Stack: Python 3.11, Streamlit (UI interna), Supabase Postgres (dados, RPC), FastAPI (webhook WhatsApp não-oficial).

## Rodando
1. Crie venv e instale:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
2. No Supabase, execute `sql/001_schema.sql`.
3. Copie `.env.example` para `.env` e preencha.
4. UI: `streamlit run app.py`
5. Webhook: `uvicorn server:app --reload --port 8000`
6. Configure seu provedor WhatsApp para apontar o webhook para `PUBLIC_WEBHOOK_URL/webhook`.
