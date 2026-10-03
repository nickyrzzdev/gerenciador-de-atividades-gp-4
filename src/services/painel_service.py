"""Agregações do dashboard: resumo de projetos e visão geral do projeto."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from models import (
    Atividade,
    AtividadeStatus,
    AtividadeTipo,
    Participacao,
    Projeto,
    Usuario,
    db,
)
from services import atividade_service, projeto_service
from utils import (
    ROTULO_PROJETO_STATUS,
    agora,
    eh_coordenador,
    iniciais,
    porcentagem,
)

PERIODOS_VALIDOS = (7, 30, 90)


def _ids_visiveis(usuario) -> list[int]:
    return list(
        db.session.scalars(
            select(Projeto.id).where(*projeto_service._condicoes_visiveis(usuario))
        )
    )


def resumo(usuario) -> dict[str, Any]:
    """GET /api/projetos/resumo — KPIs da tela Meus Projetos."""
    ids = _ids_visiveis(usuario)
    contagens = projeto_service.contagens_de_abas(usuario)

    atrasados = 0
    if ids:
        atrasados = int(
            db.session.scalar(
                select(func.count(func.distinct(Atividade.projeto_id))).where(
                    Atividade.projeto_id.in_(ids),
                    Atividade.status != AtividadeStatus.CONCLUIDA,
                    Atividade.prazo.is_not(None),
                    Atividade.prazo < agora(),
                )
            )
            or 0
        )

    return {
        "total": contagens["todos"],
        "em_andamento": contagens["em_andamento"],
        "concluidos": contagens["concluidos"],
        "atrasados": atrasados,
    }


def visao_geral(projeto: Projeto, usuario, periodo: int = 30) -> dict[str, Any]:
    """GET /api/projetos/<id>/visao-geral — visão de quem entra no meio do projeto."""
    baldes = atividade_service.painel_progresso(projeto.id)
    total = baldes["total"]
    rotulo, tom = ROTULO_PROJETO_STATUS[projeto.status.value]

    resultado: dict[str, Any] = {
        "periodo": periodo,
        "resumo": {
            "id": projeto.id,
            "nome": projeto.nome,
            "descricao": projeto.descricao,
            "status": {"codigo": projeto.status.value, "rotulo": rotulo, "tom": tom},
            "data_inicio": projeto.data_inicio.isoformat(),
            "data_fim": projeto.data_fim.isoformat(),
            "coordenador": projeto.coordenador.resumo(),
            "total_bolsistas": _total_bolsistas(projeto.id),
            "total_atividades": total,
        },
        "kpis": {
            "total": total,
            "concluidas": baldes["concluidas"],
            "pendentes": baldes["pendentes"],
            "atrasadas": baldes["atrasadas"],
            "em_andamento": baldes["em_andamento"],
            "percentual_concluidas": porcentagem(baldes["concluidas"], total),
            "percentual_pendentes": porcentagem(baldes["pendentes"], total),
            "percentual_atrasadas": porcentagem(baldes["atrasadas"], total),
            "percentual_em_andamento": porcentagem(baldes["em_andamento"], total),
        },
        "progresso": {
            "percentual": baldes["percentual"],
            "concluidas": baldes["concluidas"],
            "atrasadas": baldes["atrasadas"],
            "em_andamento": baldes["em_andamento"],
            "pendentes": baldes["pendentes"],
        },
        "por_tipo": _por_tipo(projeto.id, total),
        "proximas_entregas": _proximas_entregas(projeto, usuario),
        "atividades_criadas_no_periodo": _criadas_no_periodo(projeto.id, periodo),
        "variacao_mes": variacao_mensal(projeto.id),
    }
    if eh_coordenador(usuario):
        resultado["ranking_bolsistas"] = _ranking_bolsistas(projeto.id)
    return resultado


# --------------------------------------------------------------------------- #
# Blocos
# --------------------------------------------------------------------------- #


def _total_bolsistas(projeto_id: int) -> int:
    return int(
        db.session.scalar(
            select(func.count()).select_from(Participacao).where(Participacao.projeto_id == projeto_id)
        )
        or 0
    )


def _por_tipo(projeto_id: int, total: int) -> list[dict[str, Any]]:
    linhas = db.session.execute(
        select(Atividade.tipo, func.count())
        .where(Atividade.projeto_id == projeto_id)
        .group_by(Atividade.tipo)
    ).all()
    contagens = {tipo.value: quantidade for tipo, quantidade in linhas}
    return [
        {
            "tipo": tipo.value,
            "quantidade": contagens.get(tipo.value, 0),
            "percentual": porcentagem(contagens.get(tipo.value, 0), total),
        }
        for tipo in AtividadeTipo
    ]


def _proximas_entregas(projeto: Projeto, usuario, limite: int = 3) -> list[dict[str, Any]]:
    consulta = (
        select(Atividade)
        .options(*atividade_service.opcoes_de_leitura())
        .where(
            Atividade.projeto_id == projeto.id,
            Atividade.tipo == AtividadeTipo.ENTREGA,
            Atividade.status != AtividadeStatus.CONCLUIDA,
        )
        .order_by(Atividade.prazo.is_(None), Atividade.prazo)
        .limit(limite)
    )
    return [atividade_service.serializar(linha, usuario) for linha in db.session.scalars(consulta)]


def _criadas_no_periodo(projeto_id: int, periodo: int) -> int:
    limite = agora() - timedelta(days=periodo)
    return int(
        db.session.scalar(
            select(func.count())
            .select_from(Atividade)
            .where(Atividade.projeto_id == projeto_id, Atividade.criado_em >= limite)
        )
        or 0
    )


def variacao_mensal(projeto_id: int) -> int | None:
    """% de atividades criadas nos últimos 30 dias vs. os 30 anteriores."""
    ref = agora()
    inicio_atual = ref - timedelta(days=30)
    inicio_anterior = ref - timedelta(days=60)

    def contar(desde: datetime, ate: datetime) -> int:
        return int(
            db.session.scalar(
                select(func.count())
                .select_from(Atividade)
                .where(
                    Atividade.projeto_id == projeto_id,
                    Atividade.criado_em >= desde,
                    Atividade.criado_em < ate,
                )
            )
            or 0
        )

    atual = contar(inicio_atual, ref)
    anterior = contar(inicio_anterior, inicio_atual)
    if anterior == 0:
        return None
    return int(round((atual - anterior) * 100 / anterior))


def _ranking_bolsistas(projeto_id: int) -> list[dict[str, Any]]:
    """Só o coordenador enxerga isto (seção 12, item 9)."""
    linhas = db.session.execute(
        select(
            Usuario.id,
            Usuario.nome,
            func.count(Atividade.id).label("total"),
            func.sum(
                func.cast(
                    Atividade.status == AtividadeStatus.CONCLUIDA,
                    db.Integer,
                )
            ).label("concluidas"),
        )
        .join(Participacao, Participacao.usuario_id == Usuario.id)
        .outerjoin(
            Atividade,
            (Atividade.responsavel_id == Usuario.id)
            & (Atividade.projeto_id == projeto_id),
        )
        .where(Participacao.projeto_id == projeto_id)
        .group_by(Usuario.id, Usuario.nome)
        .order_by(func.count(Atividade.id).desc(), Usuario.nome)
    ).all()

    return [
        {
            "usuario": {"id": linha.id, "nome": linha.nome, "iniciais": iniciais(linha.nome)},
            "atividades_atribuidas": int(linha.total or 0),
            "entregas_concluidas": int(linha.concluidas or 0),
            "percentual_concluidas": porcentagem(int(linha.concluidas or 0), int(linha.total or 0)),
        }
        for linha in linhas
    ]