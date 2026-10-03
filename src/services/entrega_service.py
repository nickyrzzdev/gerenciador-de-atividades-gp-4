"""Fluxo da entrega: envio, reenvio, histórico e avaliação do coordenador (RN04, RN10)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from models import AtividadeStatus, AtividadeTipo, Entrega, EntregaResultado, db
from services import atividade_service, projeto_service
from utils import (
    ErroDeNegocio,
    SituacaoEntrega,
    agora,
    erro_conflito,
    erro_nao_encontrado,
    erro_sem_permissao,
    erro_validacao,
    situacao_da_entrega,
    validar_avaliacao,
    validar_entrega,
)


def registrar_envio(atividade_id: int, usuario, dados: dict) -> Entrega:
    """Cobre o 1º envio e o reenvio; cobre o mesmo endpoint (RN10)."""
    atividade, _ = atividade_service.obter_atividade_acessivel(atividade_id, usuario)
    valores, erros = validar_entrega(dados)

    if atividade.tipo != AtividadeTipo.ENTREGA:
        raise ErroDeNegocio(
            "tipo_invalido", "Esta atividade não é do tipo entrega", 422
        )
    if atividade.responsavel_id != usuario.id:
        raise erro_sem_permissao("Apenas o responsável envia a entrega")

    situacao = situacao_da_entrega(atividade.entregas)
    if situacao not in {SituacaoEntrega.PENDENTE, SituacaoEntrega.AJUSTES_SOLICITADOS}:
        raise erro_conflito(
            "Esta entrega já foi enviada e está aguardando avaliação do coordenador"
        )
    if erros:
        raise erro_validacao(erros)

    entrega = Entrega(
        atividade_id=atividade.id,
        usuario_id=usuario.id,
        numero=_proximo_numero(atividade.id),
        descricao=valores["descricao"],
        link=valores["link"],
        enviada_em=agora(),
        resultado=EntregaResultado.AGUARDANDO_AVALIACAO,
    )
    db.session.add(entrega)
    atividade.status = AtividadeStatus.EM_ANDAMENTO
    db.session.commit()
    return entrega


def avaliar(entrega_id: int, usuario, dados: dict) -> Entrega:
    """Só o coordenador do projeto avalia (RN04)."""
    entrega = db.session.get(Entrega, entrega_id)
    if entrega is None:
        raise erro_nao_encontrado("Entrega não encontrada")

    atividade = atividade_service.carregar(entrega.atividade_id)
    entrega.atividade = atividade
    projeto_service.obter_projeto_acessivel(
        atividade.projeto_id, usuario, exigir_coordenador=True
    )
    if entrega.resultado != EntregaResultado.AGUARDANDO_AVALIACAO:
        raise erro_conflito("Esta entrega já foi avaliada")

    valores, erros = validar_avaliacao(dados)
    if erros:
        raise erro_validacao(erros)

    entrega.resultado = EntregaResultado(valores["resultado"])
    entrega.comentario_feedback = valores["comentario"]
    entrega.avaliador_id = usuario.id
    entrega.avaliada_em = agora()

    if entrega.resultado == EntregaResultado.APROVADA:
        entrega.atividade.status = AtividadeStatus.CONCLUIDA
        entrega.atividade.concluida_em = agora()

    db.session.commit()
    return entrega


def historico(atividade_id: int, usuario) -> dict[str, Any]:
    """Tela 'Histórico da entrega' (drawer e página)."""
    atividade, _ = atividade_service.obter_atividade_acessivel(atividade_id, usuario)
    envios = sorted(atividade.entregas, key=lambda e: e.numero)
    situacao = situacao_da_entrega(envios)
    aprovada = next(
        (e for e in reversed(envios) if e.resultado == EntregaResultado.APROVADA), None
    )
    return {
        "atividade": {
            **atividade_service.serializar(atividade, usuario),
            "aprovada_em": aprovada.avaliada_em.isoformat() if aprovada else None,
        },
        "envios": [entrega.to_dict() for entrega in envios],
        "total_envios": len(envios),
        "situacao": situacao.value,
        "pode_reenviar": (
            atividade.tipo == AtividadeTipo.ENTREGA
            and atividade.responsavel_id == usuario.id
            and situacao in {SituacaoEntrega.PENDENTE, SituacaoEntrega.AJUSTES_SOLICITADOS}
        ),
    }


def _proximo_numero(atividade_id: int) -> int:
    maior = db.session.scalar(
        select(func.coalesce(func.max(Entrega.numero), 0)).where(Entrega.atividade_id == atividade_id)
    )
    return int(maior) + 1