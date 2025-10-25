
import os
import re
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from services.whatsapp_service import send_message
from services.supabase_client import get_client
from services.containers_service import get_or_create_open_container, list_container_items
from services.ludocoins_service import convert_item, get_saldo, list_ultimas_transacoes
from services.envios_service import criar_pedido_envio
from services.chat_state_service import (
    get_state, set_state, clear_state, StateNames
)

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

    text = (
        payload.get("text")
        or payload.get("message")
        or payload.get("body")
        or data.get("body")
        or data.get("text")
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
        "Oi, Eu sou o *Ludinho* 🤖\n"
        "Posso te ajudar com:\n\n"
        "1) CONTAINER – ver seus jogos (DISPONÍVEIS e PRÉ-VENDA)\n"
        "2) LUDOCOINS – saldo e últimas transações\n"
        "3) TROCAR – converter jogos de *RIFA* em L$ (85%)\n"
        "4) ENVIAR – pedir envio do seu container\n"
        "5) AJUDA – exemplos de uso\n\n"
        "_Você pode responder pelo número (ex: 3) ou pelo texto (ex: TROCAR)._"
    )

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
    msg += "\n\nDicas: você pode *3) TROCAR* itens de RIFA por L$ ou *4) ENVIAR* seu container."
    return msg

def list_elegiveis(itens: list[dict]):
    out = []
    for it in (itens or []):
        if it.get("origem") == "RIFA" and it.get("status_item") in ("DISPONIVEL", "PRE-VENDA"):
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

    upper = (text or "").upper()
    if upper in GREETINGS or upper in {"MENU", "AJUDA"}:
        await send_message(telefone, render_menu())
        return {"ok": True}

    if (text or "").strip() in {"1", "2", "3", "4", "5"}:
        upper = {"1": "CONTAINER", "2": "LUDOCOINS", "3": "TROCAR", "4": "ENVIAR", "5": "AJUDA"}[(text or "").strip()]

    # ------- CONTAINER -------
    if upper.startswith("CONTAINER"):
        try:
            container_id = get_or_create_open_container(telefone)
            if not container_id:
                await send_message(telefone, "Não achei seu cadastro. Confirme o telefone informado e tente novamente.")
                return {"ok": True}
            itens = list_container_items(container_id)
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
            await send_message(telefone, f"Você selecionou: *{nomes}* → total de *{total:.2f} L$*.\nConfirma a conversão? (Responda *S* ou *N*)")
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
            if not container_id:
                await send_message(telefone, "Não encontrei um container ativo para você ainda. Confirme seu telefone ou fale com o suporte.")
                return {"ok": True}
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
                if not container_id:
                    await send_message(telefone, "Não encontrei seu container aberto. Confirme o telefone e tente novamente.")
                    return {"ok": True}
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
            if not container_id:
                await send_message(telefone, "Ainda não temos um container ativo vinculado a este telefone.")
                return {"ok": True}
            itens = list_container_items(container_id) or []
            resumo = "\n".join([f"- {(it.get('jogos') or {}).get('nome','Jogo')} ({it.get('origem')}, {it.get('status_item')})" for it in itens]) or "—"
            try:
                set_state(telefone, StateNames.ENVIAR_CONFIRM, {})
            except Exception as e:
                print("set_state error (ENVIAR_CONFIRM):", e)
            await send_message(telefone, "Você está pedindo o *envio do seu container*. Os itens são:\n" + resumo + "\n\nConfirma o pedido? (Responda *S* ou *N*)")
        except Exception as e:
            print("ENVIAR flow error:", e)
            await send_message(telefone, "Não consegui acessar seu container agora. Tente novamente mais tarde.")
        return {"ok": True}

    # Fallback
    await send_message(telefone, "Não entendi 🤔\n" + render_menu())
    return {"ok": True}
