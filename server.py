
import os
import re
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from services.supabase_client import get_client
from services.ludocoins_service import convert_item, get_saldo, list_ultimas_transacoes
from services.envios_service import criar_pedido_envio
from services.whatsapp_service import send_file
from services.chat_state_service import (
    get_state, set_state, clear_state, StateNames
)

from services.containers_service import (
    get_or_create_open_container,
    list_container_items,
    list_trocaveis,
    list_enviaveis,
)

from services.whatsapp_service import send_message, send_file

load_dotenv()
app = FastAPI(title="Ludolovers Webhook")

# ----------------- Helpers -----------------

GREETINGS = {"OI", "OLA", "OLÁ", "HELLO", "HI", "EAI", "E AÍ", "BOM DIA", "BOA TARDE", "BOA NOITE"}

def normalize_phone(raw: str) -> str:
    return re.sub(r"\D+", "", raw or "")

def extract_phone_and_text(payload: dict):
    data = payload.get("data") or {}
    evt = (payload.get("event") or "").lower()

    raw_from = payload.get("from") or payload.get("phone") or data.get("from") or data.get("chatId") or ""
    telefone = normalize_phone(raw_from)

    msg_obj = data.get("message") or {}

    # caption primeiro (inclui topo), depois campos de texto, por último body (pode ser base64)
    text = (
        payload.get("caption")
        or msg_obj.get("caption")
        or data.get("caption")
        or payload.get("text")
        or payload.get("message")
        or data.get("text")
        or data.get("body")
        or payload.get("body")
        or ""
    )
    text = (text or "").strip()

    from_me = bool(payload.get("fromMe") or data.get("fromMe"))
    is_group = bool(payload.get("isGroupMsg") or payload.get("isGroup") or data.get("isGroupMsg") or data.get("isGroup"))
    return telefone, text, from_me, is_group, evt

def is_only_numbers_or_spaces(s: str) -> bool:
    return bool(re.fullmatch(r"[0-9 ]+", (s or "").strip()))

def render_menu() -> str:
    return (
        "🤖 *Ludinho* — como posso ajudar?\n\n"
        "1) CONTAINER\n"
        "2) LUDOCOINS\n"
        "3) TROCAR (Listinha → L$)\n"
        "4) ENVIAR Container\n"
        "5) AJUDA\n"
        "6) COMPROVANTE (enviar)\n"
        "0) MENU (voltar)\n\n"
        "_Você pode responder pelo número (ex: 3) ou pelo texto (ex: TROCAR)._"
    )


def is_back_to_menu(txt: str) -> bool:
    t = (txt or "").strip().lower()
    return t in ("0", "menu", "início", "inicio", "voltar")

def render_container(itens: list[dict]) -> str:
    disponiveis, prevenda = [], []
    idx = 1
    for it in (itens or []):
        jogo = it.get("jogos") or {}
        nome_publico = jogo.get("nome") or "Jogo"
        origem = it.get("origem", "?").title()
        status_item = it.get("status_item", "?")
        line = f"{idx}. {nome_publico} ({origem}, {status_item})"
        idx += 1
        if status_item == "PRE-VENDA":
            prevenda.append(line)
        else:
            disponiveis.append(line)
    msg = "📦 *Seu Container*\n\n*DISPONÍVEIS*\n" + ("\n".join(disponiveis) if disponiveis else "—")
    msg += "\n\n*PRÉ-VENDA*\n" + ("\n".join(prevenda) if prevenda else "—")
    msg += "\n\nDicas: você pode *3) TROCAR* itens de LISTINHA por L$ ou *4) ENVIAR* seu container."
    return msg

def list_elegiveis(itens: list[dict]):
    out = []
    for it in (itens or []):
        if it.get("origem") == "LISTINHA" and it.get("status_item") in ("DISPONIVEL", "PRE-VENDA"):
            jogo = it.get("jogos") or {}
            nome = jogo.get("nome", "Jogo")
            valor = round(float(it.get("preco_aplicado_brl", 0) or 0) * 0.85, 2)
            out.append({"id": it.get("id"), "nome": nome, "credito": valor})
    return out

def render_elegiveis(elegiveis: list[dict]) -> str:
    if not elegiveis:
        return "Não há itens elegíveis para troca no momento."
    lines = ["Itens elegíveis para *TROCA* (responda com os números, ex: 1 3):"]
    for i, it in enumerate(elegiveis, start=1):
        lines.append(f"{i}. {it['nome']} → {it['credito']:.2f} L$")
    return "\n".join(lines)

def safe_get_client():
    try:
        return get_client()
    except Exception as e:
        print("Supabase client error:", e)
        return None

def supa_select_one(table: str, **filters):
    supa = safe_get_client()
    if not supa:
        return None
    try:
        q = supa.table(table).select("*")
        for k, v in filters.items():
            q = q.eq(k, v)
        # compat both maybe_single/single shapes
        res = getattr(q, "maybe_single", lambda: q)().execute()
        data = getattr(res, "data", None)
        if data is None and isinstance(res, dict):
            data = res.get("data")
        return data
    except Exception as e:
        print(f"supa_select_one error on {table}:", e)
        return None

# ----------------- Endpoint -----------------

@app.post("/webhook")
async def webhook(request: Request, x_signature: str | None = Header(default="")):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    print("Incoming webhook payload (trim):", str(payload)[:500])

    telefone, text, from_me, is_group, evt = extract_phone_and_text(payload)

    if evt and evt not in ("onmessage", "message", "chat:message"):
        return {"ok": True}
    if from_me or is_group:
        return {"ok": True}
    if not telefone:
        return {"ok": True}

    # Onboarding: se cliente não existe, pedir nome — tolerante a falhas
    exists = supa_select_one("clientes", telefone=telefone)
    state = None
    try:
        state = get_state(telefone)
    except Exception as e:
        print("get_state error:", e)

    if not exists and state is None:
        try:
            set_state(telefone, StateNames.ONBOARD_ASK_NAME, {})
        except Exception as e:
            print("set_state error (seguindo sem state persistence):", e)
        await send_message(telefone, "Oi! Eu sou o *Ludinho* 🤖\nParece que é sua primeira vez aqui. Como você gostaria de ser chamado(a)?")
        return {"ok": True}

    if state and state.get("state") == StateNames.ONBOARD_ASK_NAME:
        nome = (text or "").strip()
        if len(nome) < 2:
            await send_message(telefone, "Humm, esse nome ficou muito curtinho. Pode me dizer seu nome completo? 🙂")
            return {"ok": True}
        supa = safe_get_client()
        if supa:
            try:
                supa.table("clientes").upsert({"telefone": telefone, "nome": nome}).execute()
            except Exception as e:
                print("upsert cliente error:", e)
        try:
            clear_state(telefone)
        except Exception as e:
            print("clear_state error:", e)
        await send_message(telefone, f"Perfeito, *{nome}*! 🙌\n{render_menu()}")
        return {"ok": True}
    # PATCH START: menu global (0/menu/inicio) + limpar estado
    upper = (text or "").upper()
    if upper in GREETINGS or is_back_to_menu(text):
        try:
            clear_state(telefone)
        except Exception as e:
            print("clear_state error:", e)
        await send_message(telefone, render_menu())
        return {"ok": True}
    # PATCH END

    if (text or "").strip() in {"1", "2", "3", "4", "5"} and not state:
        upper = {"1": "CONTAINER", "2": "LUDOCOINS", "3": "TROCAR", "4": "ENVIAR", "5": "AJUDA"}[(text or "").strip()]

    # PATCH START: fluxo COMPROVANTE (stateful + atalho com 'COMPROVANTE <ID>')
    m_comp = re.match(r"^\s*COMPROVANTE\s+([A-Za-z0-9\-\._]+)\s*$", text or "", flags=re.IGNORECASE)
    if m_comp:
        txid = m_comp.group(1)
        supa = get_client()
        cfg = supa.table("configuracoes").select("numero_recebimento_comprovantes").eq("id", 1).single().execute().data
        destino = (cfg or {}).get("numero_recebimento_comprovantes")
        if not destino:
            await send_message(telefone, "Ainda não há um número configurado para receber comprovantes. Tente mais tarde.")
            return {"ok": True}

        base64_data, filename = None, None
        try:
            msg = (payload.get("data") or {}).get("message") or {}
            if isinstance(msg.get("file"), dict):
                base64_data = msg["file"].get("data")
                filename = msg["file"].get("filename") or "comprovante"
            elif isinstance(msg.get("mediaData"), dict):
                base64_data = msg["mediaData"].get("data")
                filename = msg["mediaData"].get("filename") or "comprovante"
            else:
                base64_data = msg.get("base64")
                filename = msg.get("filename") or "comprovante"
        except Exception as e:
            print("parse comprovante media error:", e)

        if not base64_data:
            try:
                d0 = payload or {}
                if isinstance(d0.get("file"), dict):
                    base64_data = d0["file"].get("data")
                    filename = d0["file"].get("filename") or filename or "comprovante"
                elif d0.get("base64"):
                    base64_data = d0.get("base64")
                    filename = d0.get("filename") or filename or "comprovante"
                elif isinstance(d0.get("body"), str) and len(d0.get("body") or "") > 100:
                    # body contendo base64 (imagem/pdf)
                    base64_data = d0["body"]
                    filename = d0.get("filename") or filename or "comprovante"
            except Exception as e:
                print("parse comprovante media (top-level) error:", e)

        if not base64_data:
            await send_message(telefone, "Por favor, anexe um PDF ou imagem e envie novamente com: COMPROVANTE <ID_DA_TRANSACAO>.")
            return {"ok": True}

        caption = f"Comprovante de pagamento — ID {txid}\nDe: {telefone}"
        try:
            send_file(destino, base64_data, filename, caption)
            await send_message(telefone, "Comprovante encaminhado. Obrigado! ✅")
        except Exception as e:
            print("send_file comprovante error:", e)
            await send_message(telefone, "Não consegui encaminhar o comprovante agora. Tente novamente mais tarde.")
        return {"ok": True}

    if (text or "").strip() == "6" or (upper.startswith("COMPROVANTE") and not m_comp):
        try:
            set_state(telefone, StateNames.COMPROVANTE_WAIT, {})
        except Exception as e:
            print("set_state error (COMPROVANTE_WAIT):", e)
        await send_message(telefone, "Para enviar seu comprovante, anexe um PDF ou imagem e escreva: COMPROVANTE <ID_DA_TRANSACAO>")
        return {"ok": True}

    d = payload.get("data") or {}
    print("debug: data keys =", list(d.keys()))
    print("debug: message keys =", list((d.get("message") or {}).keys()))

    try:
        current_comp = get_state(telefone)
    except Exception as e:
        current_comp = None
    if current_comp and current_comp.get("state") == StateNames.COMPROVANTE_WAIT:
        m_comp2 = re.match(r"^\s*COMPROVANTE\s+([A-Za-z0-9\-\._]+)\s*$", text or "", flags=re.IGNORECASE)
        if not m_comp2:
            await send_message(telefone, "Envie a mensagem no formato: COMPROVANTE <ID_DA_TRANSACAO>, com o arquivo anexado.")
            return {"ok": True}
        txid = m_comp2.group(1)
        supa = get_client()
        cfg = supa.table("configuracoes").select("numero_recebimento_comprovantes").eq("id", 1).single().execute().data
        destino = (cfg or {}).get("numero_recebimento_comprovantes")
        if not destino:
            await send_message(telefone, "Ainda não há um número configurado para receber comprovantes. Tente mais tarde.")
            return {"ok": True}

        base64_data, filename = None, None
        try:
            msg = (payload.get("data") or {}).get("message") or {}
            if isinstance(msg.get("file"), dict):
                base64_data = msg["file"].get("data")
                filename = msg["file"].get("filename") or "comprovante"
            elif isinstance(msg.get("mediaData"), dict):
                base64_data = msg["mediaData"].get("data")
                filename = msg["mediaData"].get("filename") or "comprovante"
            else:
                base64_data = msg.get("base64")
                filename = msg.get("filename") or "comprovante"
        except Exception as e:
            print("parse comprovante media error:", e)

        if not base64_data:
            try:
                d = payload.get("data") or {}
                if isinstance(d.get("file"), dict):
                    base64_data = d["file"].get("data")
                    filename = d["file"].get("filename") or filename or "comprovante"
                elif d.get("base64"):
                    base64_data = d.get("base64")
                    filename = d.get("filename") or filename or "comprovante"
            except Exception as e:
                print("parse comprovante media (fallback) error:", e)

        if not base64_data:
            await send_message(telefone, "Parece que não veio arquivo. Anexe um PDF/Imagem e envie novamente com: COMPROVANTE <ID_DA_TRANSACAO>.")
            return {"ok": True}

        caption = f"Comprovante de pagamento — ID {txid}\nDe: {telefone}"
        try:
            send_file(destino, base64_data, filename, caption)
            await send_message(telefone, "Comprovante encaminhado. Obrigado! ✅")
            try:
                clear_state(telefone)
            except Exception as e:
                print("clear_state error (COMPROVANTE_WAIT):", e)
            await send_message(telefone, render_menu())
        except Exception as e:
            print("send_file comprovante error:", e)
            await send_message(telefone, "Não consegui encaminhar o comprovante agora. Tente novamente mais tarde.")
        return {"ok": True}
    # PATCH END

# ------- CONTAINER -------
    if upper.startswith("CONTAINER"):
        try:
            container_id = get_or_create_open_container(telefone)
            itens = list_container_items(container_id)
            # PATCH START: ocultar itens RESGATADO na listagem do cliente
            itens = [it for it in (itens or []) if (it.get("status_item") != "RESGATADO")]
            # PATCH END
            await send_message(telefone, render_container(itens))
        except Exception as e:
            print("CONTAINER flow error:", e)
            await send_message(telefone, "Não consegui acessar seu container agora. Tente novamente mais tarde.")
        return {"ok": True}

    # ------- LUDOCOINS -------
    if upper.startswith("LUDOCOINS"):
        try:
            saldo = float(get_saldo(telefone) or 0.0)
            ult = list_ultimas_transacoes(telefone, limit=5) or []
            lines = [f"Saldo: {saldo:.2f} L$"]
            for t in ult:
                tipo = t.get("tipo","?")
                valor = float(t.get("valor") or 0)
                created = t.get("created_at","")
                lines.append(f"- {tipo}: {valor:.2f} ({created})")
            await send_message(telefone, "\n".join(lines))
        except Exception as e:
            print("LUDOCOINS flow error:", e)
            await send_message(telefone, "Não consegui consultar seu saldo agora. Tente novamente mais tarde.")
        return {"ok": True}

    # ------- TROCAR (stateful) -------
    try:
        current = get_state(telefone)
    except Exception as e:
        print("get_state error (troca):", e)
        current = None

    if current and current.get("state") in (StateNames.TROCA_LISTANDO, StateNames.TROCA_CONFIRM):
        if current["state"] == StateNames.TROCA_LISTANDO:
            if not is_only_numbers_or_spaces(text):
                await send_message(telefone, "Por favor, responda só com os números dos itens que deseja trocar. Ex: *1 3*")
                await send_message(telefone, render_elegiveis(current["data"].get("elegiveis", [])))
                return {"ok": True}
            idxs = [int(p) for p in (text or "").split() if p.isdigit()]
            eleg = current["data"].get("elegiveis", [])
            escolhidos = []
            for i in idxs:
                if 1 <= i <= len(eleg):
                    escolhidos.append(eleg[i-1])
            if not escolhidos:
                await send_message(telefone, "Índice inválido. Tente novamente.")
                await send_message(telefone, render_elegiveis(eleg))
                return {"ok": True}
            total = sum(float(x["credito"]) for x in escolhidos)
            try:
                set_state(telefone, StateNames.TROCA_CONFIRM, {"escolhidos": escolhidos})
            except Exception as e:
                print("set_state error (TROCA_CONFIRM):", e)
            nomes = ", ".join(x["nome"] for x in escolhidos)
            msg_confirm = (
                f"Você selecionou: *{nomes}*.\n"
                f"Total de crédito: *{total:.2f} L$*.\n"
                "⚠️ *Atenção*: esta ação é *irreversível*.\n"
                "Confirma a conversão? (Responda *S* ou *N*)"
            )
            await send_message(telefone, msg_confirm)
            return {"ok": True}

        if current["state"] == StateNames.TROCA_CONFIRM:
            if upper in {"S", "SIM", "CONFIRMO"}:
                escolhidos = current["data"].get("escolhidos", [])
                credito_total = 0.0
                for it in escolhidos:
                    try:
                        convert_item(it.get("id"), atendente_email="whatsapp-bot@ludolovers")
                        credito_total += float(it.get("credito") or 0)
                    except Exception as e:
                        print("convert_item error:", e)
                try:
                    clear_state(telefone)
                except Exception as e:
                    print("clear_state error:", e)
                try:
                    novo_saldo = float(get_saldo(telefone) or 0.0)
                except Exception:
                    novo_saldo = 0.0
                await send_message(telefone, f"Prontinho! Converti {len(escolhidos)} item(ns). Crédito: *{credito_total:.2f} L$*.\nSeu saldo agora é *{novo_saldo:.2f} L$*.")
                return {"ok": True}
            elif upper in {"N", "NAO", "NÃO", "CANCELAR"}:
                try:
                    clear_state(telefone)
                except Exception as e:
                    print("clear_state error:", e)
                await send_message(telefone, "Sem problemas — operação cancelada. Se quiser, digite *3* para listar novamente os itens elegíveis.")
                return {"ok": True}
            else:
                await send_message(telefone, "Responda apenas com *S* (sim) ou *N* (não).")
                return {"ok": True}

    if upper.startswith("TROCAR"):
        try:
            container_id = get_or_create_open_container(telefone)
            itens = list_container_items(container_id)
            elegiveis = list_elegiveis(itens)
            if not elegiveis:
                await send_message(telefone, "Não há itens elegíveis para troca no momento.")
                return {"ok": True}
            try:
                set_state(telefone, StateNames.TROCA_LISTANDO, {"elegiveis": elegiveis})
            except Exception as e:
                print("set_state error (TROCA_LISTANDO):", e)
            await send_message(telefone, render_elegiveis(elegiveis))
        except Exception as e:
            print("TROCAR flow error:", e)
            await send_message(telefone, "Não consegui listar itens elegíveis agora. Tente novamente mais tarde.")
        return {"ok": True}

    # ------- ENVIAR (stateful) -------
    try:
        current = get_state(telefone)
    except Exception as e:
        print("get_state error (enviar):", e)
        current = None

    if current and current.get("state") == StateNames.ENVIAR_CONFIRM:
        if upper in {"S", "SIM", "CONFIRMO"}:
            try:
                container_id = get_or_create_open_container(telefone)
                itens = list_container_items(container_id)
                snapshot = [{
                    "jogo": (it.get("jogos") or {}).get("nome", "Jogo"),
                    "origem": it.get("origem"),
                    "status_item": it.get("status_item"),
                    "preco_aplicado_brl": it.get("preco_aplicado_brl"),
                } for it in (itens or [])]
                supa = safe_get_client()
                nome = f"Cliente {telefone}"
                if supa:
                    cli = supa.table("clientes").select("nome").eq("telefone", telefone).maybe_single().execute()
                    cli_data = getattr(cli, "data", None) if not isinstance(cli, dict) else cli.get("data")
                    if cli_data and cli_data.get("nome"):
                        nome = cli_data["nome"]
                envio = criar_pedido_envio(container_id, telefone, nome, snapshot)
                try:
                    clear_state(telefone)
                except Exception as e:
                    print("clear_state error:", e)
                await send_message(telefone, f"Pedido criado com sucesso! 📨\nID: *{envio['id']}* • Status: *{envio['status_envio']}*")
            except Exception as e:
                print("ENVIAR confirm error:", e)
                await send_message(telefone, "Não consegui criar o pedido agora. Tente novamente mais tarde.")
            return {"ok": True}
        elif upper in {"N", "NAO", "NÃO", "CANCELAR"}:
            try:
                clear_state(telefone)
            except Exception as e:
                print("clear_state error:", e)
            await send_message(telefone, "Beleza! Pedido cancelado. Se quiser tentar de novo, mande *4* (ENVIAR).")
            return {"ok": True}
        else:
            await send_message(telefone, "Responda apenas com *S* (sim) ou *N* (não).")
            return {"ok": True}
    if upper.startswith("ENVIAR"):
        try:
            container_id = get_or_create_open_container(telefone)
            itens = list_container_items(container_id) or []
            # PATCH START: filtrar apenas DISPONIVEL
            itens = [it for it in itens if it.get("status_item") == "DISPONIVEL"]
            if not itens:
                await send_message(telefone, "Não consigo criar envio: seu container está vazio ou só tem itens em PRÉ-VENDA.")
                await send_message(telefone, render_menu())
                return {"ok": True}
            # PATCH END
            resumo = "\n".join([
                f"- {(it.get('jogos') or {}).get('nome','(sem nome)')} (origem {it.get('origem')}, {it.get('status_item')})" for it in itens
            ]) or "—"
            supa = get_client()
            cliente = supa.table("clientes").select("endereco, nome").eq("telefone", telefone).single().execute().data
            endereco = (cliente or {}).get("endereco") or "(endereço não cadastrado)"
            try:
                set_state(telefone, StateNames.ENVIAR_CONFIRM, {"snapshot": itens})
            except Exception as e:
                print("set_state error (ENVIAR_CONFIRM):", e)
            confirm_text = (
                "Você está pedindo o *envio* do seu container com os itens:\n"
                + resumo
                + "\n\nEndereço de entrega:\n"
                + endereco
                + "\n\n⚠️ *Atenção*: esta ação é *irreversível*.\n"
                + "Confirma o pedido? (Responda *S* ou *N*)"
            )
            await send_message(telefone, confirm_text)
        except Exception as e:
            print("ENVIAR flow error:", e)
            await send_message(telefone, "Não consegui acessar seu container agora. Tente novamente mais tarde.")
        return {"ok": True}
# Fallback
    await send_message(telefone, "Não entendi 🤔\n" + render_menu())
    return {"ok": True}
