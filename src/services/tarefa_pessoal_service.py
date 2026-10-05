"""Regras de negócio para tarefas pessoais."""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select

from models import AtividadeStatus, TarefaPessoal, db
from utils import (
    ErroDeNegocio,
    agora,
    erro_nao_encontrado,
    erro_validacao,
    montar_paginacao,
    validar_status,
    validar_tarefa_pessoal,
)


def listar(
    usuario,
    pagina: int,
    por_pagina: int,
    status: str | None = None,
    busca: str | None = None,
) -> dict[str, Any]:
    consulta = select(TarefaPessoal).where(TarefaPessoal.usuario_id == usuario.id)

    status = (status or "").strip()
    if status:
        if status not in list(AtividadeStatus):
            raise ErroDeNegocio(
                "parametro_invalido",
                "Filtro 'status' inválido: use a_fazer, em_andamento ou concluida",
                400,
            )
        consulta = consulta.where(TarefaPessoal.status == AtividadeStatus(status))

    busca = (busca or "").strip()
    if busca:
        consulta = consulta.where(
            or_(
                TarefaPessoal.titulo.ilike(f"%{busca}%"),
                TarefaPessoal.descricao.ilike(f"%{busca}%"),
            )
        )

    consulta = consulta.order_by(
        TarefaPessoal.prazo.is_(None),
        TarefaPessoal.prazo,
        TarefaPessoal.criado_em.desc(),
    )
    paginacao = db.paginate(consulta, page=pagina, per_page=por_pagina, error_out=False)
    return montar_paginacao(paginacao, [tarefa.to_dict() for tarefa in paginacao.items])


def obter(tarefa_id: int, usuario) -> TarefaPessoal:
    tarefa = db.session.scalar(
        select(TarefaPessoal).where(
            TarefaPessoal.id == tarefa_id,
            TarefaPessoal.usuario_id == usuario.id,
        )
    )
    if tarefa is None:
        raise erro_nao_encontrado("Tarefa não encontrada")
    return tarefa


def criar(usuario, dados: dict) -> TarefaPessoal:
    valores, erros = validar_tarefa_pessoal(dados)
    if "status" in dados:
        erros["status"] = "A tarefa nasce com status a_fazer; altere-o pelo endpoint de status"
    if erros:
        raise erro_validacao(erros)

    tarefa = TarefaPessoal(
        usuario_id=usuario.id,
        status=AtividadeStatus.A_FAZER,
        concluida_em=None,
        **valores,
    )
    db.session.add(tarefa)
    db.session.commit()
    return tarefa


def atualizar(tarefa_id: int, usuario, dados: dict) -> TarefaPessoal:
    tarefa = obter(tarefa_id, usuario)
    valores, erros = validar_tarefa_pessoal(dados, parcial=True)
    if "status" in dados:
        erros["status"] = "O status muda só pelo endpoint /api/tarefas/<id>/status"
    if erros:
        raise erro_validacao(erros)

    for campo, valor in valores.items():
        setattr(tarefa, campo, valor)
    db.session.commit()
    return tarefa


def alterar_status(tarefa_id: int, usuario, dados: dict) -> TarefaPessoal:
    novo_status, erros = validar_status(dados)
    if erros:
        raise erro_validacao(erros)

    tarefa = obter(tarefa_id, usuario)
    tarefa.status = AtividadeStatus(novo_status)
    tarefa.concluida_em = (
        agora() if tarefa.status == AtividadeStatus.CONCLUIDA else None
    )
    db.session.commit()
    return tarefa


def excluir(tarefa_id: int, usuario) -> None:
    tarefa = obter(tarefa_id, usuario)
    db.session.delete(tarefa)
    db.session.commit()
