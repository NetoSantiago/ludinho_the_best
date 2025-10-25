import server

PHONE = "5511999999999"


def make_payload(text: str, phone: str = PHONE):
    return {"from": phone, "text": text, "event": "onMessage"}


def test_onboarding_first_contact(client, message_spy, state_store, monkeypatch):
    monkeypatch.setattr(server, "supa_select_one", lambda *args, **kwargs: None)

    response = client.post("/webhook", json=make_payload("Oi"))
    assert response.status_code == 200
    assert state_store[PHONE]["state"] == server.StateNames.ONBOARD_ASK_NAME
    assert "Como você gostaria de ser chamado" in message_spy[-1]["text"]


def test_onboarding_name_success(client, message_spy, state_store, monkeypatch):
    state_store[PHONE] = {"state": server.StateNames.ONBOARD_ASK_NAME, "data": {}}
    monkeypatch.setattr(server, "supa_select_one", lambda *args, **kwargs: None)
    monkeypatch.setattr(server, "safe_get_client", lambda: None)

    response = client.post("/webhook", json=make_payload("João da Silva"))
    assert response.status_code == 200
    assert PHONE not in state_store
    assert "Perfeito, *João da Silva*!" in message_spy[-1]["text"]


def test_menu_shortcut(client, message_spy, state_store, existing_client):
    response = client.post("/webhook", json=make_payload("menu"))
    assert response.status_code == 200
    assert message_spy[-1]["text"].startswith("Oi, Eu sou o *Ludinho*")


def test_container_flow_success(client, message_spy, state_store, existing_client, monkeypatch):
    monkeypatch.setattr(server, "get_or_create_open_container", lambda phone: "cont-1")
    monkeypatch.setattr(
        server,
        "list_container_items",
        lambda container_id: [
            {"origem": "RIFA", "status_item": "DISPONIVEL", "jogos": {"nome": "Azul"}},
            {"origem": "COMPRA", "status_item": "PRE-VENDA", "jogos": {"nome": "Vermelho"}},
        ],
    )

    response = client.post("/webhook", json=make_payload("1"))
    assert response.status_code == 200
    assert "Seu Container" in message_spy[-1]["text"]


def test_container_flow_without_container(client, message_spy, state_store, existing_client, monkeypatch):
    monkeypatch.setattr(server, "get_or_create_open_container", lambda phone: None)

    response = client.post("/webhook", json=make_payload("CONTAINER"))
    assert response.status_code == 200
    assert "Não achei seu cadastro" in message_spy[-1]["text"]


def test_ludocoins_flow(client, message_spy, state_store, existing_client, monkeypatch):
    monkeypatch.setattr(server, "get_saldo", lambda phone: 123.45)
    monkeypatch.setattr(
        server,
        "list_ultimas_transacoes",
        lambda phone, limit=5: [
            {"tipo": "CRÉDITO", "valor": 50, "created_at": "2024-06-01"},
            {"tipo": "DÉBITO", "valor": -10, "created_at": "2024-06-02"},
        ],
    )

    response = client.post("/webhook", json=make_payload("2"))
    assert response.status_code == 200
    text = message_spy[-1]["text"]
    assert "Saldo: 123.45 L$" in text
    assert "CRÉDITO" in text


def test_troca_listagem(client, message_spy, state_store, existing_client, monkeypatch):
    monkeypatch.setattr(server, "get_or_create_open_container", lambda phone: "cont-1")
    monkeypatch.setattr(
        server,
        "list_container_items",
        lambda container_id: [
            {
                "id": "item-1",
                "origem": "RIFA",
                "status_item": "DISPONIVEL",
                "preco_aplicado_brl": 100,
                "jogos": {"nome": "Jogo 1"},
            }
        ],
    )

    response = client.post("/webhook", json=make_payload("3"))
    assert response.status_code == 200
    assert state_store[PHONE]["state"] == server.StateNames.TROCA_LISTANDO
    assert "Itens elegíveis" in message_spy[-1]["text"]


def test_troca_confirmacao_sim(client, message_spy, state_store, existing_client, monkeypatch):
    chosen = {"id": "item-1", "nome": "Jogo 1", "credito": 42.5}
    state_store[PHONE] = {"state": server.StateNames.TROCA_CONFIRM, "data": {"escolhidos": [chosen]}}
    monkeypatch.setattr(server, "convert_item", lambda item_id, atendente_email: {"ok": True})
    monkeypatch.setattr(server, "get_saldo", lambda phone: 142.5)

    response = client.post("/webhook", json=make_payload("S"))
    assert response.status_code == 200
    assert PHONE not in state_store
    text = message_spy[-1]["text"]
    assert "Converti 1 item" in text
    assert "142.50 L$" in text


def test_troca_cancelamento(client, message_spy, state_store, existing_client):
    state_store[PHONE] = {"state": server.StateNames.TROCA_CONFIRM, "data": {"escolhidos": []}}

    response = client.post("/webhook", json=make_payload("N"))
    assert response.status_code == 200
    assert PHONE not in state_store
    assert "operação cancelada" in message_spy[-1]["text"]


def test_enviar_pedido_inicial(client, message_spy, state_store, existing_client, monkeypatch):
    monkeypatch.setattr(server, "get_or_create_open_container", lambda phone: "cont-9")
    monkeypatch.setattr(
        server,
        "list_container_items",
        lambda container_id: [
            {"origem": "RIFA", "status_item": "DISPONIVEL", "jogos": {"nome": "Jogo 2"}}
        ],
    )

    response = client.post("/webhook", json=make_payload("4"))
    assert response.status_code == 200
    assert state_store[PHONE]["state"] == server.StateNames.ENVIAR_CONFIRM
    assert "Responda *S* ou *N*" in message_spy[-1]["text"]


def test_enviar_confirmacao_sucesso(client, message_spy, state_store, existing_client, monkeypatch):
    state_store[PHONE] = {"state": server.StateNames.ENVIAR_CONFIRM, "data": {}}
    monkeypatch.setattr(server, "safe_get_client", lambda: None)
    monkeypatch.setattr(server, "get_or_create_open_container", lambda phone: "cont-9")
    monkeypatch.setattr(server, "list_container_items", lambda container_id: [])
    monkeypatch.setattr(
        server,
        "criar_pedido_envio",
        lambda container_id, telefone, nome, snapshot: {"id": "env-1", "status_envio": "PENDENTE"},
    )

    response = client.post("/webhook", json=make_payload("Sim"))
    assert response.status_code == 200
    assert PHONE not in state_store
    assert "Pedido criado com sucesso" in message_spy[-1]["text"]


def test_fallback_message(client, message_spy, state_store, existing_client):
    response = client.post("/webhook", json=make_payload("qualquer coisa"))
    assert response.status_code == 200
    assert "Não entendi" in message_spy[-1]["text"]
