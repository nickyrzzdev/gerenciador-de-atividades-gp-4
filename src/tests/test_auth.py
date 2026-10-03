"""Cadastro, login, sessão e troca de senha (RN02, RN04)."""

from conftest import SENHA, criar_usuario, entrar


def entrar_com(client, email, senha):
    resposta = client.post("/api/auth/login", json={"email": email, "senha": senha})
    assert resposta.status_code == 200, resposta.get_json()
from models import db
from utils import Perfil


def test_cadastro_de_bolsista(client):
    resposta = client.post(
        "/api/auth/cadastro",
        json={
            "nome": "Rafael Nascimento",
            "email": "rafael.nascimento@uea.edu.br",
            "senha": "OutraSenha1",
            "confirmar_senha": "OutraSenha1",
            "perfil": "bolsista",
        },
    )
    assert resposta.status_code == 201, resposta.get_json()

    corpo = resposta.get_json()
    assert corpo["usuario"]["perfil"] == "bolsista"
    assert corpo["usuario"]["nome"] == "Rafael Nascimento"
    assert "email" in corpo["usuario"]  # o próprio usuário vê o e-mail
    assert "senha" not in corpo["usuario"] and "senha_hash" not in corpo["usuario"]

    # cadastro não abre sessão: é preciso entrar
    assert client.get("/api/auth/me").status_code == 401
    entrar_com(client, "rafael.nascimento@uea.edu.br", "OutraSenha1")
    me = client.get("/api/auth/me").get_json()
    assert me["usuario"]["email"] == "rafael.nascimento@uea.edu.br"
    assert set(me["usuario"]) == {
        "id", "nome", "email", "iniciais", "perfil", "ativo", "instituicao",
    }


def test_cadastro_rejeita_duplicado_e_fraco(client):
    criar_usuario("Ana Carvalho", Perfil.COORDENADOR)
    db.session.commit()

    duplicado = client.post(
        "/api/auth/cadastro",
        json={
            "nome": "Outra Ana",
            "email": "ana.carvalho@uea.edu.br",
            "senha": "OutraSenha1",
            "confirmar_senha": "OutraSenha1",
            "perfil": "bolsista",
        },
    )
    assert duplicado.status_code == 409
    assert duplicado.get_json()["erro"]["codigo"] == "email_em_uso"

    curta = client.post(
        "/api/auth/cadastro",
        json={
            "nome": "Curta",
            "email": "curta@uea.edu.br",
            "senha": "123",
            "confirmar_senha": "123",
            "perfil": "bolsista",
        },
    )
    assert curta.status_code == 422
    assert "senha" in curta.get_json()["erro"]["campos"]

    sem_nome = client.post(
        "/api/auth/cadastro",
        json={
            "email": "sem.nome@uea.edu.br",
            "senha": "OutraSenha1",
            "confirmar_senha": "OutraSenha1",
            "perfil": "bolsista",
        },
    )
    assert sem_nome.status_code == 422


def test_dominio_bloqueado_quando_configurado(client, app):
    app.config["DOMINIO_EMAIL_PERMITIDO"] = "@uea.edu.br"
    try:
        fora = client.post(
            "/api/auth/cadastro",
            json={
                "nome": "De Fora",
                "email": "alguem@gmail.com",
                "senha": "OutraSenha1",
                "confirmar_senha": "OutraSenha1",
                "perfil": "bolsista",
            },
        )
        assert fora.status_code == 422
        assert "email" in fora.get_json()["erro"]["campos"]

        dentro = client.post(
            "/api/auth/cadastro",
            json={
                "nome": "De Dentro",
                "email": "dentro@uea.edu.br",
                "senha": "OutraSenha1",
                "confirmar_senha": "OutraSenha1",
                "perfil": "bolsista",
            },
        )
        assert dentro.status_code == 201
    finally:
        app.config["DOMINIO_EMAIL_PERMITIDO"] = ""


def test_login_logout_e_me(client, usuarios):
    anonimo = client.get("/api/auth/me")
    assert anonimo.status_code == 401
    assert anonimo.get_json()["erro"]["codigo"] == "nao_autenticado"

    sessao = entrar(client, "marina.costa@uea.edu.br")
    assert sessao["usuario"]["perfil"] == "bolsista"

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.get_json()["usuario"]["id"] == usuarios["marina"].id
    assert me.get_json()["usuario"]["email"] == "marina.costa@uea.edu.br"

    saida = client.post("/api/auth/logout", json={})
    assert saida.status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_login_invalido_nao_revela_usuario(client, usuarios):
    sem_usuario = client.post(
        "/api/auth/login", json={"email": "ninguem@uea.edu.br", "senha": SENHA}
    )
    senha_errada = client.post(
        "/api/auth/login", json={"email": "marina.costa@uea.edu.br", "senha": "errada"}
    )

    assert sem_usuario.status_code == senha_errada.status_code == 401
    assert sem_usuario.get_json() == senha_errada.get_json()
    assert "erro" in sem_usuario.get_json()
    assert client.get("/api/auth/me").status_code == 401


def test_login_normaliza_email(client, usuarios):
    entrar(client, "  MARINA.COSTA@UEA.EDU.BR  ")
    assert client.get("/api/auth/me").get_json()["usuario"]["email"] == "marina.costa@uea.edu.br"


def test_login_de_usuario_inativo(client, usuarios):
    usuarios["marina"].ativo = False
    db.session.commit()

    resposta = client.post(
        "/api/auth/login", json={"email": "marina.costa@uea.edu.br", "senha": SENHA}
    )
    assert resposta.status_code == 401


def test_troca_de_senha(client, usuarios):
    entrar(client, "marina.costa@uea.edu.br")

    trocada = client.put(
        "/api/perfil/senha",
        json={
            "senha_atual": SENHA,
            "nova_senha": "NovaSenha1",
            "confirmar_nova_senha": "NovaSenha1",
        },
    )
    assert trocada.status_code == 200, trocada.get_json()

    client.post("/api/auth/logout", json={})
    antiga = client.post(
        "/api/auth/login", json={"email": "marina.costa@uea.edu.br", "senha": SENHA}
    )
    assert antiga.status_code == 401

    nova = client.post(
        "/api/auth/login", json={"email": "marina.costa@uea.edu.br", "senha": "NovaSenha1"}
    )
    assert nova.status_code == 200


def test_troca_de_senha_valida_atual_e_nova(client, usuarios):
    """Atual só para deixar explícito: repetir a mesma senha é aceito."""
    entrar(client, "marina.costa@uea.edu.br")

    errada = client.put(
        "/api/perfil/senha",
        json={
            "senha_atual": "nao-e-a-senha",
            "nova_senha": "NovaSenha1",
            "confirmar_nova_senha": "NovaSenha1",
        },
    )
    assert errada.status_code == 422
    assert "senha_atual" in errada.get_json()["erro"]["campos"]

    curta = client.put(
        "/api/perfil/senha",
        json={"senha_atual": SENHA, "nova_senha": "123", "confirmar_nova_senha": "123"},
    )
    assert curta.status_code == 422
    assert "nova_senha" in curta.get_json()["erro"]["campos"]

    confirmar = client.put(
        "/api/perfil/senha",
        json={
            "senha_atual": SENHA,
            "nova_senha": SENHA,
            "confirmar_nova_senha": SENHA,
        },
    )
    assert confirmar.status_code == 200


def test_sessao_exigida_em_todas_as_rotas_protegidas(client):
    protegidas = [
        ("GET", "/api/projetos"),
        ("GET", "/api/projetos/resumo"),
        ("POST", "/api/projetos"),
        ("GET", "/api/atividades/minhas"),
        ("GET", "/api/projetos/1"),
    ]
    for metodo, caminho in protegidas:
        resposta = client.open(caminho, method=metodo, json={})
        assert resposta.status_code in (400, 401), (metodo, caminho, resposta.status_code)
        if resposta.status_code == 401:
            assert resposta.get_json()["erro"]["codigo"] == "nao_autenticado"