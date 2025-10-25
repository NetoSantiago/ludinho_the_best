Stack: Python 3.11, Streamlit (UI interna), Supabase Postgres (dados, RPC), FastAPI (webhook WhatsApp não-oficial).

## Rodando com uv
1. Instale o [uv](https://docs.astral.sh/uv/getting-started/installation/):
   ```bash
   pip install uv
   ```
2. Sincronize as dependências e gere o `.venv` gerenciado pelo uv:
   ```bash
   uv sync
   ```
3. No Supabase, execute `sql/001_schema.sql` para criar objetos necessários.
4. Copie `.env.example` para `.env` (ou crie um novo) preenchendo `SUPABASE_URL`, `SUPABASE_KEY`, `WA_BEARER` e demais segredos.
5. Suba o painel interno:
   ```bash
   uv run streamlit run app.py
   ```
6. Suba o webhook WhatsApp (porta configurável):
   ```bash
   uv run uvicorn server:app --reload --port 8000
   ```
7. Ajuste seu provedor WhatsApp para enviar webhooks para `PUBLIC_WEBHOOK_URL/webhook`.
8. Execute a suíte de testes:
   ```bash
   uv run pytest
   ```

## Alternativa com pip tradicional
Se preferir um fluxo clássico:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Em seguida repita os passos 3 a 8 acima usando `python -m streamlit ...`, `uvicorn ...` e `pytest` dentro do ambiente virtual.
