"""Fixtures compartilhadas. O banco de teste é definido ANTES de importar `app`."""

from __future__ import annotations

import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ["DATABASE_URL"] = "sqlite://"  # em memória, separado do dev
os.environ["SECRET_KEY"] = "testes"

import app as app_module  # noqa: E402
from models import (  # noqa: E402
    Atividade,
    AtividadeStatus,
    AtividadeTipo,
    Participacao,
    Projeto,
    ProjetoStatus,
    Usuario,
    db,
)
from utils import Perfil, agora  # noqa: E402

SENHA = "Senha123"


@pytest.fixture
def app():
    app_module.app.config.update(TESTING=True)
    with app_module.app.app_context():
        db.create_all()
        yield app_module.app
        db.session.rollback()
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def criar_usuario(nome: str, perfil: Perfil, email: str | None = None) -> Usuario:
    usuario = Usuario(
        nome=nome, email=email or _email_de(nome), perfil=perfil, ativo=True
    )
    usuario.definir_senha(SENHA)
    db.session.add(usuario)
    db.session.flush()
    return usuario


def _email_de(nome: str) -> str:
    partes = nome.lower().split()
    return f"{partes[0]}.{partes[-1]}@uea.edu.br"


def criar_projeto(coordenador: Usuario, status=ProjetoStatus.EM_ANDAMENTO) -> Projeto:
    projeto = Projeto(
        nome="Projeto de Teste",
        descricao="Projeto usado nos testes",
        data_inicio=agora().date() - timedelta(days=10),
        data_fim=agora().date() + timedelta(days=20),
        status=status,
        coordenador_id=coordenador.id,
    )
    db.session.add(projeto)
    db.session.flush()
    return projeto


def vincular(projeto: Projeto, usuario: Usuario) -> Participacao:
    participacao = Participacao(projeto_id=projeto.id, usuario_id=usuario.id)
    db.session.add(participacao)
    db.session.flush()
    return participacao


def criar_atividade(
    projeto: Projeto,
    responsavel: Usuario,
    tipo=AtividadeTipo.DESENVOLVIMENTO,
    status=AtividadeStatus.A_FAZER,
    dias=5,
    titulo="Atividade de teste",
) -> Atividade:
    atividade = Atividade(
        projeto_id=projeto.id,
        titulo=titulo,
        descricao="Descrição",
        tipo=tipo,
        status=status,
        prazo=agora() + timedelta(days=dias),
        responsavel_id=responsavel.id,
        criado_por_id=projeto.coordenador_id,
        concluida_em=agora() if status == AtividadeStatus.CONCLUIDA else None,
    )
    db.session.add(atividade)
    db.session.flush()
    return atividade


@pytest.fixture
def usuarios(app):
    """Ana (coordenadora), João (outro coordenador) e Marina (bolsista)."""
    ana = criar_usuario("Ana Carvalho", Perfil.COORDENADOR)
    joao = criar_usuario("João Silva", Perfil.COORDENADOR, "joao.silva@uea.edu.br")
    marina = criar_usuario("Marina Costa", Perfil.BOLISTA)
    db.session.commit()
    return {"ana": ana, "joao": joao, "marina": marina}


@pytest.fixture
def cenario(app, usuarios):
    """Projeto da Ana com a Marina vinculada e três atividades."""
    projeto = criar_projeto(usuarios["ana"])
    vincular(projeto, usuarios["marina"])
    entrega = criar_atividade(
        projeto, usuarios["marina"], AtividadeTipo.ENTREGA, titulo="Entrega do protótipo"
    )
    criar_atividade(projeto, usuarios["marina"], dias=-2)  # atrasada
    criar_atividade(
        projeto,
        usuarios["marina"],
        status=AtividadeStatus.CONCLUIDA,
        dias=-1,
        titulo="Atividade concluída",
    )
    db.session.commit()
    return {"projeto": projeto, "entrega": entrega}


def entrar(client, email: str) -> Any:
    resposta = client.post("/api/auth/login", json={"email": email, "senha": SENHA})
    assert resposta.status_code == 200, resposta.get_json()
    return resposta.get_json()


def db_commit() -> None:
    """Atalho para confirmar as alterações feitas direto no banco do teste."""
    db.session.commit()


def apagar(client, url: str) -> Any:
    """DELETE exige o header JSON por causa da mitigação de CSRF."""
    return client.delete(url, headers={"Content-Type": "application/json"})