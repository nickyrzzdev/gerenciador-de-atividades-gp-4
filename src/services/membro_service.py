"""Membros do projeto: vínculo, desvinculação (RN07) e opções de responsável."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from models import Atividade, AtividadeStatus, Participacao, Usuario, db
from utils import (
    Perfil,
    erro_conflito,
    erro_nao_encontrado,
    erro_validacao,
    montar_paginacao,
)


def listar_membros(projeto, busca: str, pagina: int, por_pagina: int) -> dict:
    consulta = (
        select(Participacao)
        .join(Usuario, Usuario.id == Participacao.usuario_id)
        .where(Participacao.projeto_id == projeto.id)
    )
    if busca:
        consulta = consulta.where(
            or_(Usuario.nome.ilike(f"%{busca}%"), Usuario.email.ilike(f"%{busca}%"))
        )
    consulta = consulta.options(joinedload(Participacao.usuario)).order_by(Usuario.nome)
    paginacao = db.paginate(consulta, page=pagina, per_page=por_pagina, error_out=False)

    atribuidas = _atividades_por_bolsista(projeto.id)
    itens = [
        {
            "usuario": {
                **participacao.usuario.resumo(),
                "email": participacao.usuario.email,
            },
            "vinculado_em": participacao.vinculado_em.isoformat(),
            "atividades_atribuidas": atribuidas.get(participacao.usuario_id, 0),
        }
        for participacao in paginacao.items
    ]

    return {
        **montar_paginacao(paginacao, itens),
        "total_bolsistas": _total_bolsistas(projeto.id),
    }


def opcoes_de_responsaveis(projeto) -> list[dict]:
    """Lista simples (sem paginação) para o select 'Responsável'."""
    linhas = db.session.execute(
        select(Usuario)
        .join(Participacao, Participacao.usuario_id == Usuario.id)
        .where(Participacao.projeto_id == projeto.id)
        .order_by(Usuario.nome)
    ).scalars()
    return [linha.resumo() for linha in linhas]


def vincular(projeto, dados: dict) -> Participacao:
    email = str(dados.get("email") or "").strip().lower()
    if not email:
        raise erro_validacao({"email": "Informe o e-mail do bolsista"})

    usuario = db.session.scalar(select(Usuario).where(Usuario.email == email))
    if usuario is None:
        raise erro_nao_encontrado("Nenhum usuário encontrado com este e-mail")
    if usuario.perfil != Perfil.BOLISTA:
        raise erro_validacao({"email": "Este usuário não é bolsista"})
    if usuario.ativo is False:
        raise erro_validacao({"email": "Este usuário está inativo"})

    if _esta_vinculado(projeto.id, usuario.id):
        raise erro_conflito("Este bolsista já está vinculado ao projeto")

    participacao = Participacao(projeto_id=projeto.id, usuario_id=usuario.id)
    db.session.add(participacao)
    db.session.commit()
    return participacao


def desvincular(projeto, usuario_id: int) -> None:
    """RN07: só desvincula quem não tem atividade não concluída no projeto."""
    if usuario_id == projeto.coordenador_id:
        raise erro_conflito("O coordenador do projeto não pode ser desvinculado")

    participacao = db.session.get(Participacao, {"projeto_id": projeto.id, "usuario_id": usuario_id})
    if participacao is None:
        raise erro_nao_encontrado("Este bolsista não está vinculado ao projeto")

    pendentes = _atividades_nao_concluidas(projeto.id, usuario_id)
    if pendentes:
        raise erro_conflito(
            f"Não é possível desvincular: {pendentes} atividade(s) não concluída(s) deste "
            "bolsista ainda estão no projeto. Reatribua-as antes de desvincular.",
            {"atividades_pendentes": pendentes},
        )

    db.session.delete(participacao)
    db.session.commit()


def _esta_vinculado(projeto_id: int, usuario_id: int) -> bool:
    return (
        db.session.scalar(
            select(Participacao.projeto_id).where(
                Participacao.projeto_id == projeto_id,
                Participacao.usuario_id == usuario_id,
            )
        )
        is not None
    )


def _total_bolsistas(projeto_id: int) -> int:
    return int(
        db.session.scalar(
            select(func.count()).select_from(Participacao).where(Participacao.projeto_id == projeto_id)
        )
        or 0
    )


def _atividades_por_bolsista(projeto_id: int) -> dict[int, int]:
    linhas = db.session.execute(
        select(Atividade.responsavel_id, func.count())
        .where(Atividade.projeto_id == projeto_id)
        .group_by(Atividade.responsavel_id)
    ).all()
    return {responsavel_id: total for responsavel_id, total in linhas}


def _atividades_nao_concluidas(projeto_id: int, usuario_id: int) -> int:
    return int(
        db.session.scalar(
            select(func.count())
            .select_from(Atividade)
            .where(
                Atividade.projeto_id == projeto_id,
                Atividade.responsavel_id == usuario_id,
                Atividade.status != AtividadeStatus.CONCLUIDA,
            )
        )
        or 0
    )