"""Cadastro, login e troca de senha (RN14)."""

from __future__ import annotations

from flask import current_app
from sqlalchemy import select

from models import Usuario, db
from utils import (
    ErroDeNegocio,
    Perfil,
    email_normalizado,
    erro_validacao,
    validar_cadastro,
    validar_troca_senha,
)

# Mensagem única: não revela se o e-mail existe ou a senha está errada.
ERRO_LOGIN = "E-mail ou senha inválidos"


def cadastrar(dados: dict) -> Usuario:
    """Cria um usuário novo. O perfil é escolhido no cadastro (RN14)."""
    valores, erros = validar_cadastro(dados)

    # aceita "@uea.edu.br" ou "uea.edu.br" na configuração
    dominio = (current_app.config.get("DOMINIO_EMAIL_PERMITIDO") or "").strip().lower().lstrip("@")
    if dominio and not valores["email"].endswith(f"@{dominio}"):
        erros["email"] = f"Só são aceitos e-mails do domínio @{dominio}"

    if erros:
        raise erro_validacao(erros)

    if _buscar_por_email(valores["email"]) is not None:
        raise ErroDeNegocio(
            "email_em_uso", "Este e-mail já está cadastrado", 409, {"email": "Este e-mail já está cadastrado"}
        )

    usuario = Usuario(
        nome=valores["nome"],
        email=valores["email"],
        perfil=Perfil(valores["perfil"]),
        ativo=True,
    )
    usuario.definir_senha(valores["senha"])
    db.session.add(usuario)
    db.session.commit()
    return usuario


def autenticar(dados: dict) -> Usuario:
    """Valida credenciais. Falha sempre devolve 401 com a mesma mensagem."""
    email = email_normalizado(dados.get("email"))
    senha = str(dados.get("senha") or "")
    usuario = _buscar_por_email(email) if email else None

    if usuario is None or not usuario.checar_senha(senha) or not usuario.ativo:
        raise ErroDeNegocio("credenciais_invalidas", ERRO_LOGIN, 401)
    return usuario


def alterar_senha(usuario: Usuario, dados: dict) -> None:
    """Dados pessoais são somente leitura; só a senha é editável."""
    valores, erros = validar_troca_senha(dados)
    if erros:
        raise erro_validacao(erros)

    if not usuario.checar_senha(valores["senha_atual"]):
        raise erro_validacao({"senha_atual": "Senha atual incorreta"})

    usuario.definir_senha(valores["nova_senha"])
    db.session.commit()


def _buscar_por_email(email: str) -> Usuario | None:
    return db.session.scalar(select(Usuario).where(Usuario.email == email))