import re
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from services.whatsapp_service import verify_signature, send_message
from services.supabase_client import get_client
from services.containers_service import get_or_create_open_container, list_container_items
from services.ludocoins_service import convert_item, get_saldo, list_ultimas_transacoes
from services.envios_service import criar_pedido_envio

load_dotenv()
app = FastAPI(title="Ludolovers Webhook")

def normalize_phone(raw: str) -> str:
    return re.sub(r"\D+", "", raw or "")

def format_item_line(idx, it, jogo_nome_publico):
    origem = it.get("origem","?").title()
    status_item = it.get("status_item","?")
    return f"{idx}. {jogo_nome_publico} ({origem}, {status_item})"

@app.post("/webhook")
async def webhook(request: Request, x_signature: str | None = Header(default="")):
    payload = await request.json()

    # --- LOG (você já tem) ---
    print("Incoming webhook headers:", dict(request.headers))
    print("Incoming webhook payload (trim):", str(payload)[:500])

    # 1) Normaliza o tipo de evento
    evt = (payload.get("event") or "").lower()

    # 2) Suporta formatos com e sem "data"
    data = payload.get("data") or {}

    # 3) Extrai telefone (raiz OU data.*)
    raw_from = (
        payload.get("from")
        or payload.get("phone")
        or data.get("from")
        or data.get("chatId")
        or ""
    )

    def normalize_phone(raw: str) -> str:
        import re
        return re.sub(r"\D+", "", raw or "")

    telefone = normalize_phone(raw_from)

    # 4) Extrai texto (agora inclui `payload.get("body")`)
    text = (
        payload.get("text")
        or payload.get("message")
        or payload.get("body")
        or data.get("body")
        or data.get("text")
        or ""
    )
    text = text.strip()

    # 5) Flags comuns (tanto raiz quanto data.*)
    from_me = bool(payload.get("fromMe") or data.get("fromMe"))
    is_group = bool(payload.get("isGroupMsg") or payload.get("isGroup") or data.get("isGroupMsg") or data.get("isGroup"))

    # 6) Ignora eventos que não são mensagem, mensagens minhas e de grupo
    if evt and evt not in ("onmessage", "message", "chat:message"):
        return JSONResponse({"ok": True})
    if from_me or is_group:
        return JSONResponse({"ok": True})

    # 7) Sem telefone ou texto = nada pra fazer
    if not telefone or not text:
        return JSONResponse({"ok": True})

    # --- roteamento por comando (mesmo fluxo de antes) ---
    cmd = text.upper()

    if cmd == "MENU":
        try:
            await send_message(telefone, "Oi! Eu sou o Ludinho 🤖\nDigite: CONTAINER | LUDOCOINS | TROCAR | ENVIAR | AJUDA")
        except Exception as e:
            print("send_message error:", e)
        return {"ok": True}

    if cmd == "AJUDA":
        try:
            await send_message(telefone, "Comandos: CONTAINER, TROCAR, LUDOCOINS, ENVIAR")
        except Exception as e:
            print("send_message error:", e)
        return {"ok": True}

    if cmd.startswith("CONTAINER"):
        container_id = get_or_create_open_container(telefone)
        itens = list_container_items(container_id)
        disponiveis, prevenda = [], []
        idx = 1
        for it in itens:
            jogo = it.get("jogos") or {}
            nome_publico = jogo.get("nome") or "Jogo"
            origem = it.get("origem","?").title()
            status_item = it.get("status_item","?")
            line = f"{idx}. {nome_publico} ({origem}, {status_item})"
            idx += 1
            if status_item == "PRE-VENDA":
                prevenda.append(line)
            else:
                disponiveis.append(line)
        msg = "📦 Container\n\nDISPONÍVEIS\n" + ("\n".join(disponiveis) if disponiveis else "—") + \
              "\n\nPRÉ-VENDA\n" + ("\n".join(prevenda) if prevenda else "—")
        try:
            await send_message(telefone, msg)
        except Exception as e:
            print("send_message error:", e)
        return {"ok": True}

    if cmd.startswith("LUDOCOINS"):
        saldo = get_saldo(telefone)
        ult = list_ultimas_transacoes(telefone, limit=5)
        lines = [f"Saldo: {saldo:.2f} L$"]
        for t in ult:
            lines.append(f"- {t['tipo']}: {t['valor']:.2f} ({t['created_at']})")
        try:
            await send_message(telefone, "\n".join(lines))
        except Exception as e:
            print("send_message error:", e)
        return {"ok": True}

    if cmd.startswith("TROCAR"):
        container_id = get_or_create_open_container(telefone)
        itens = list_container_items(container_id)
        elegiveis = []
        for it in itens:
            if it.get("origem") == "RIFA" and it.get("status_item") in ("DISPONIVEL","PRE-VENDA"):
                jogo = it.get("jogos") or {}
                nome = jogo.get("nome","Jogo")
                valor = round(float(it.get("preco_aplicado_brl",0))*0.85,2)
                elegiveis.append((it["id"], nome, valor))

        if cmd.strip() == "TROCAR":
            if not elegiveis:
                try:
                    await send_message(telefone, "Não há itens elegíveis para troca.")
                except Exception as e:
                    print("send_message error:", e)
                return {"ok": True}
            msg = "Itens elegíveis (responda: TROCAR 1 3 ...):\n"
            for i,(iid,nm,val) in enumerate(elegiveis, start=1):
                msg += f"{i}. {nm} → {val:.2f} L$\n"
            try:
                await send_message(telefone, msg)
            except Exception as e:
                print("send_message error:", e)
            return {"ok": True}
        else:
            parts = cmd.split()
            idxs = [int(p) for p in parts[1:] if p.isdigit()]
            escolhidos = []
            for i in idxs:
                if 1 <= i <= len(elegiveis):
                    escolhidos.append(elegiveis[i-1])
            if not escolhidos:
                try:
                    await send_message(telefone, "Nenhum índice válido. Ex: TROCAR 1 2")
                except Exception as e:
                    print("send_message error:", e)
                return {"ok": True}
            total = 0.0
            for (iid,nm,val) in escolhidos:
                r = convert_item(iid, atendente_email="whatsapp-bot@ludolovers")
                total += float(val)
            novo_saldo = get_saldo(telefone)
            try:
                await send_message(telefone, f"Convertidos {len(escolhidos)} itens. Crédito: {total:.2f} L$. Saldo: {novo_saldo:.2f} L$")
            except Exception as e:
                print("send_message error:", e)
            return {"ok": True}

    if cmd.startswith("ENVIAR"):
        container_id = get_or_create_open_container(telefone)
        itens = list_container_items(container_id)
        snapshot = [{
            "jogo": (it.get("jogos") or {}).get("nome","Jogo"),
            "origem": it.get("origem"),
            "status_item": it.get("status_item"),
            "preco_aplicado_brl": it.get("preco_aplicado_brl")
        } for it in itens]
        supa = get_client()
        cli = supa.table("clientes").select("nome").eq("telefone", telefone).single().execute().data
        nome = cli.get("nome") if cli else f"Cliente {telefone}"
        envio = criar_pedido_envio(container_id, telefone, nome, snapshot)
        try:
            await send_message(telefone, f"Pedido de envio criado: {envio['id']} (status: {envio['status_envio']})")
        except Exception as e:
            print("send_message error:", e)
        return {"ok": True}

    # fallback
    try:
        await send_message(telefone, "Não entendi. Digite MENU para opções.")
    except Exception as e:
        print("send_message error:", e)
    return {"ok": True}
