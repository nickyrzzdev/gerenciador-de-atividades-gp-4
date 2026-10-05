"""Projetos: acesso centralizado, CRUD, listagem por abas e progresso."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from models import (
    Atividade,
    AtividadeStatus,
    Participacao,
    Projeto,
    ProjetoStatus,
    db,
)
from utils import (
    ROTULO_PROJETO_STATUS,
    ErroDeNegocio,
    agora,
    erro_nao_encontrado,
    erro_sem_permissao,
    erro_validacao,
    eh_coordenador,
    montar_paginacao,
    porcentagem,
    validar_projeto,
)


# --------------------------------------------------------------------------- #
# Acesso (RN01, RN02, RN03) — fonte única de permissão por projeto
# --------------------------------------------------------------------------- #


def obter_projeto_acessivel(
    projeto_id: int, usuario, exigir_coordenador: bool = False
) -> Projeto:
    """Carrega o projeto garantindo acesso; 404 quando inacessível (RN03)."""
    projeto = db.session.get(Projeto, projeto_id)
    if projeto is None:
        raise erro_nao_encontrado("Projeto não encontrado")

    if eh_coordenador(usuario):
        if projeto.coordenador_id != usuario.id:
            raise erro_nao_encontrado("Projeto não encontrado")
    elif not _esta_vinculado(projeto.id, usuario.id):
        raise erro_nao_encontrado("Projeto não encontrado")

    if exigir_coordenador and projeto.coordenador_id != usuario.id:
        raise erro_sem_permissao("Apenas o coordenador do projeto pode fazer isso")

    return projeto


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


def _condicoes_visiveis(usuario) -> list:
    if eh_coordenador(usuario):
        return [Projeto.coordenador_id == usuario.id]
    return [
        Projeto.id.in_(
            select(Participacao.projeto_id).where(Participacao.usuario_id == usuario.id)
        )
    ]


# --------------------------------------------------------------------------- #
# Serialização
# --------------------------------------------------------------------------- #


def serializar_projeto(projeto: Projeto, total_atividades: int, concluidas: int) -> dict[str, Any]:
    rotulo, tom = ROTULO_PROJETO_STATUS[projeto.status.value]
    membros = sorted(projeto.participacoes, key=lambda p: p.usuario.nome)
    return {
        "id": projeto.id,
        "nome": projeto.nome,
        "descricao": projeto.descricao,
        "data_inicio": projeto.data_inicio.isoformat(),
        "data_fim": projeto.data_fim.isoformat(),
        "status": {"codigo": projeto.status.value, "rotulo": rotulo, "tom": tom},
        "coordenador": {
            "id": projeto.coordenador.id,
            "nome": projeto.coordenador.nome,
            "iniciais": projeto.coordenador.resumo()["iniciais"],
        },
        "membros_preview": [p.usuario.resumo() for p in membros[:3]],
        "membros_extra": max(len(membros) - 3, 0),
        "total_bolsistas": len(membros),
        "total_atividades": total_atividades,
        "progresso": porcentagem(concluidas, total_atividades),
    }


def _progresso_por_projeto(projeto_ids: list[int]) -> dict[int, tuple[int, int]]:
    """(total, concluídas) por projeto em uma única query agregada."""
    if not projeto_ids:
        return {}
    linhas = db.session.execute(
        select(
            Atividade.projeto_id,
            func.count().label("total"),
            func.sum(
                case((Atividade.status == AtividadeStatus.CONCLUIDA, 1), else_=0)
            ).label("concluidas"),
        )
        .where(Atividade.projeto_id.in_(projeto_ids))
        .group_by(Atividade.projeto_id)
    ).all()
    return {linha.projeto_id: (linha.total, int(linha.concluidas or 0)) for linha in linhas}


def _opcoes_de_leitura():
    return (
        joinedload(Projeto.coordenador),
        selectinload(Projeto.participacoes).joinedload(Participacao.usuario),
    )


def progresso_do_projeto(projeto_id: int) -> tuple[int, int]:
    """(total de atividades, concluídas) para a serialização de um projeto."""
    return _progresso_por_projeto([projeto_id]).get(projeto_id, (0, 0))


# --------------------------------------------------------------------------- #
# Listagem
# --------------------------------------------------------------------------- #


ABAS_PROJETO = ("em_andamento", "concluidos", "todos")


def listar_projetos(usuario, aba: str, busca: str, pagina: int, por_pagina: int) -> dict[str, Any]:
    if aba not in ABAS_PROJETO:
        raise ErroDeNegocio(
            "parametro_invalido",
            f"Aba inválida. Use uma destas: {', '.join(ABAS_PROJETO)}",
            400,
        )

    consulta = select(Projeto).where(*_condicoes_visiveis(usuario))

    if aba == "em_andamento":
        consulta = consulta.where(Projeto.status != ProjetoStatus.CONCLUIDO)
    elif aba == "concluidos":
        consulta = consulta.where(Projeto.status == ProjetoStatus.CONCLUIDO)
    if busca:
        consulta = consulta.where(
            or_(Projeto.nome.ilike(f"%{busca}%"), Projeto.descricao.ilike(f"%{busca}%"))
        )

    consulta = consulta.options(*_opcoes_de_leitura()).order_by(Projeto.status, Projeto.nome)
    paginacao = db.paginate(consulta, page=pagina, per_page=por_pagina, error_out=False)

    progresso = _progresso_por_projeto([p.id for p in paginacao.items])
    itens = [
        serializar_projeto(projeto, *progresso.get(projeto.id, (0, 0)))
        for projeto in paginacao.items
    ]

    return {**montar_paginacao(paginacao, itens), "contagens": contagens_de_abas(usuario)}


def contagens_de_abas(usuario) -> dict[str, int]:
    linha = db.session.execute(
        select(
            func.count().label("todos"),
            func.sum(case((Projeto.status != ProjetoStatus.CONCLUIDO, 1), else_=0)).label(
                "em_andamento"
            ),
            func.sum(case((Projeto.status == ProjetoStatus.CONCLUIDO, 1), else_=0)).label(
                "concluidos"
            ),
        ).select_from(Projeto).where(*_condicoes_visiveis(usuario))
    ).one()
    return {
        "todos": linha.todos,
        "em_andamento": int(linha.em_andamento or 0),
        "concluidos": int(linha.concluidos or 0),
    }


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #


def criar_projeto(usuario, dados: dict) -> Projeto:
    valores, erros = validar_projeto(dados)
    _checar_periodo(valores.get("data_inicio"), valores.get("data_fim"), erros)
    if erros:
        raise erro_validacao(erros)

    inicio = valores["data_inicio"]
    status = (
        ProjetoStatus.PLANEJADO
        if inicio > agora().date()
        else ProjetoStatus.EM_ANDAMENTO
    )
    projeto = Projeto(
        nome=valores["nome"],
        descricao=valores["descricao"],
        data_inicio=inicio,
        data_fim=valores["data_fim"],
        status=status,
        coordenador_id=usuario.id,
    )
    db.session.add(projeto)
    db.session.commit()
    return projeto


def atualizar_projeto(projeto_id: int, usuario, dados: dict) -> Projeto:
    projeto = obter_projeto_acessivel(projeto_id, usuario, exigir_coordenador=True)
    valores, erros = validar_projeto(dados, parcial=True)
    _checar_periodo(
        valores.get("data_inicio", projeto.data_inicio),
        valores.get("data_fim", projeto.data_fim),
        erros,
    )
    if (
        projeto.status == ProjetoStatus.CONCLUIDO
        and "status" in valores
        and ProjetoStatus(valores["status"]) != ProjetoStatus.CONCLUIDO
    ):
        erros["status"] = "Um projeto concluído não volta para em andamento"
    if erros:
        raise erro_validacao(erros)

    for campo, valor in valores.items():
        setattr(projeto, campo, ProjetoStatus(valor) if campo == "status" else valor)
    db.session.commit()
    return projeto


def encerrar_projeto(projeto_id: int, usuario) -> Projeto:
    projeto = obter_projeto_acessivel(projeto_id, usuario, exigir_coordenador=True)
    projeto.status = ProjetoStatus.CONCLUIDO
    db.session.commit()
    return projeto


def excluir_projeto(projeto_id: int, usuario) -> None:
    projeto = obter_projeto_acessivel(projeto_id, usuario, exigir_coordenador=True)

    pendencias = {
        "membros": int(
            db.session.scalar(
                select(func.count())
                .select_from(Participacao)
                .where(Participacao.projeto_id == projeto.id)
            )
            or 0
        ),
        "atividades_pendentes": int(
            db.session.scalar(
                select(func.count())
                .select_from(Atividade)
                .where(
                    Atividade.projeto_id == projeto.id,
                    Atividade.status != AtividadeStatus.CONCLUIDA,
                )
            )
            or 0
        ),
    }
    if any(pendencias.values()):
        raise ErroDeNegocio(
            "conflito_estado",
            "Não é possível excluir o projeto enquanto houver pendências",
            409,
            campos=pendencias,
        )

    db.session.delete(projeto)
    db.session.commit()


def _checar_periodo(inicio: date | None, fim: date | None, erros: dict) -> None:
    if inicio and fim and fim < inicio:
        erros["data_fim"] = "A data final não pode ser anterior à data inicial"