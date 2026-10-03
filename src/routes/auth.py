"""Rotas de autenticação e do perfil."""

from flask_login import current_user, login_user, logout_user

from routes import api
from services import auth_service
from utils import corpo_json, login_obrigatorio, resposta

INSTITUICAO = "UEA"


@api.post("/auth/cadastro")
def cadastrar():
    usuario = auth_service.cadastrar(corpo_json())
    return resposta({"usuario": usuario.to_dict()}, 201, "Cadastro realizado")


@api.post("/auth/login")
def login():
    dados = corpo_json()
    usuario = auth_service.autenticar(dados)
    login_user(usuario, remember=bool(dados.get("lembrar")))
    return resposta({"usuario": usuario.to_dict()}, 200, "Login realizado")


@api.post("/auth/logout")
@login_obrigatorio
def logout():
    logout_user()
    return resposta({}, 200, "Sessão encerrada")


@api.get("/auth/me")
@login_obrigatorio
def meu_perfil():
    dados = current_user.to_dict()
    dados["instituicao"] = INSTITUICAO
    return resposta({"usuario": dados})


@api.put("/perfil/senha")
@login_obrigatorio
def trocar_senha():
    auth_service.alterar_senha(current_user, corpo_json())
    return resposta({}, 200, "Senha atualizada")