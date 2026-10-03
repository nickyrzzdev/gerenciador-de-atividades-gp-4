"""Atividades: CRUD, filtros, abas da tela Hoje/Semana e status (RN01, RN02, RN09, RN11)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import current_app, request
from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from models import (
    Atividade,
    AtividadeStatus,
    AtividadeTipo,
    Entrega,
    EntregaResultado,
    Participacao,
    Projeto,
    Usuario,
    db,
)
from services import projeto_service
from utils import (
    ErroDeNegocio,
    Perfil,
    agora,
    eh_coordenador,
    erro_nao_encontrado,
    erro_sem_permissao,
    erro_validacao,
    instante_de_filtro,
    fim_da_semana,
    fim_do_dia,
    montar_paginacao,
    porcentagem,
    situacao_da_entrega,
    status_exibicao_atividade,
    validar_atividade,
    validar_status,
)

ABAS_MINHAS = ("hoje", "semana", "entregues", "todas", "pendentes", "concluidas")
FILTROS_STATUS = (
    "a_fazer",
    "em_andamento",
    "concluida",
    "atrasada",
    "pendente",
    "enviada",
    "ajustes_solicitados",
    "reenviada",
    "aprovada",
)


# --------------------------------------------------------------------------- #
# Carga e acesso
# --------------------------------------------------------------------------- #


def opcoes_de_leitura():
    return (
        joinedload(Atividade.projeto),
        joinedload(Atividade.responsavel),
        joinedload(Atividade.criado_por),
        selectinload(Atividade.entregas).joinedload(Entrega.usuario),
        selectinload(Atividade.entregas).joinedload(Entrega.avaliador),
    )


def carregar(atividade_id: int) -> Atividade | None:
    return db.session.scalar(
        select(Atividade).options(*opcoes_de_leitura()).where(Atividade.id == atividade_id)
    )


def obter_atividade_acessivel(
    atividade_id: int, usuario, exigir_coordenador: bool = False
) -> tuple[Atividade, Projeto]:
    atividade = carregar(atividade_id)
    if atividade is None:
        raise erro_nao_encontrado("Atividade não encontrada")
    projeto = projeto_service.obter_projeto_acessivel(
        atividade.projeto_id, usuario, exigir_coordenador
    )
    return atividade, projeto


# --------------------------------------------------------------------------- #
# Serialização
# --------------------------------------------------------------------------- #


def serializar(atividade: Atividade, usuario) -> dict[str, Any]:
    """Monta o JSON da atividade, incluindo os campos derivados (seção 7)."""
    situacao = situacao_da_entrega(atividade.entregas)
    ultima = max(atividade.entregas, key=lambda e: e.numero, default=None)
    aguardando = bool(ultima and ultima.resultado == EntregaResultado.AGUARDANDO_AVALIACAO)
    coord = eh_coordenador(usuario) and atividade.projeto.coordenador_id == usuario.id
    responsavel = atividade.responsavel_id == usuario.id

    base = atividade.to_dict()
    base.update(
        {
            "projeto": {"id": atividade.projeto.id, "nome": atividade.projeto.nome},
            "responsavel": atividade.responsavel.resumo(),
            "criado_por": atividade.criado_por.resumo(),
            "situacao_entrega": (
                situacao.value if atividade.tipo == AtividadeTipo.ENTREGA else None
            ),
            "total_envios": len(atividade.entregas) if atividade.tipo == AtividadeTipo.ENTREGA else 0,
            "ultimo_envio": ultima.to_dict() if ultima else None,
            "status_exibicao": status_exibicao_atividade(
                tipo=atividade.tipo.value,
                status=atividade.status.value,
                prazo=atividade.prazo,
                situacao=situacao,
                dias_urgencia=current_app.config.get("DIAS_URGENCIA", 3),
            ),
            "acoes_permitidas": acoes_de(atividade, situacao, aguardando, coord, responsavel),
        }
    )
    return base


def acoes_de(
    atividade: Atividade,
    situacao,
    aguardando: bool,
    coord: bool,
    responsavel: bool,
) -> list[str]:
    from utils import acoes_permitidas

    return acoes_permitidas(
        tipo=atividade.tipo.value,
        status=atividade.status.value,
        situacao=situacao,
        total_envios=len(atividade.entregas),
        aguardando_avaliacao=aguardando,
        eh_coordenador=coord,
        eh_responsavel=responsavel,
    )


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #


CAMPOS_EDITAVEIS = {
    "titulo",
    "descricao",
    "tipo",
    "prazo",
    "responsavel_id",
    "link_material",
}


def criar(projeto: Projeto, usuario, dados: dict) -> Atividade:
    valores, erros = validar_atividade(dados)
    if "status" in dados:
        # RN11: toda atividade nasce em a_fazer.
        erros["status"] = (
            "Atividades nascem com status a_fazer; "
            "mude depois por PATCH /api/atividades/<id>/status"
        )
    if not erros:
        erros.update(_checar_responsavel(projeto, valores.get("responsavel_id")))
        erros.update(_checar_link_material(valores.get("tipo"), valores.get("link_material")))
    if erros:
        raise erro_validacao(erros)

    atividade = Atividade(
        projeto_id=projeto.id,
        criado_por_id=usuario.id,
        status=AtividadeStatus.A_FAZER,
        concluida_em=None,
        **valores,
    )
    db.session.add(atividade)
    db.session.commit()
    return atividade


def atualizar(atividade_id: int, usuario, dados: dict) -> Atividade:
    atividade, projeto = obter_atividade_acessivel(atividade_id, usuario, exigir_coordenador=True)
    valores, erros = validar_atividade(dados, parcial=True)
    if "status" in dados:
        # O status tem um único caminho (RN11): PATCH /api/atividades/<id>/status.
        erros["status"] = "O status muda só por PATCH /api/atividades/<id>/status"
    if not erros:
        novo_tipo = valores.get("tipo", atividade.tipo.value)
        link = valores.get("link_material", atividade.link_material)
        if novo_tipo != atividade.tipo.value and atividade.entregas:
            erros["tipo"] = "Não é possível mudar o tipo de uma atividade que já tem entregas"
        erros.update(
            _checar_responsavel(projeto, valores.get("responsavel_id", atividade.responsavel_id))
        )
        erros.update(_checar_link_material(novo_tipo, link))
    if erros:
        raise erro_validacao(erros)

    for campo, valor in valores.items():
        if campo not in CAMPOS_EDITAVEIS:
            continue
        setattr(atividade, campo, AtividadeTipo(valor) if campo == "tipo" else valor)
    db.session.commit()
    return atividade


def excluir(atividade_id: int, usuario) -> None:
    atividade, _ = obter_atividade_acessivel(atividade_id, usuario, exigir_coordenador=True)
    db.session.delete(atividade)
    db.session.commit()


def alterar_status(atividade_id: int, usuario, dados: dict) -> Atividade:
    """Endpoint do modal 'Marcar como concluída' (RN09, RN11)."""
    novo_status, erros = validar_status(dados)
    if erros:
        raise erro_validacao(erros)

    atividade, projeto = obter_atividade_acessivel(atividade_id, usuario)

    if atividade.tipo == AtividadeTipo.ENTREGA:
        raise ErroDeNegocio(
            "status_controlado",
            "Atividades do tipo entrega mudam de status pela avaliação da entrega",
            422,
        )

    if not eh_coordenador(usuario) and atividade.responsavel_id != usuario.id:
        raise erro_sem_permissao("Você só altera o status das suas próprias atividades")
    if eh_coordenador(usuario) and projeto.coordenador_id != usuario.id:
        raise erro_sem_permissao("Você só altera atividades de projetos que coordena")

    atividade.status = AtividadeStatus(novo_status)
    atividade.concluida_em = agora() if novo_status == AtividadeStatus.CONCLUIDA else None
    db.session.commit()
    return atividade


# --------------------------------------------------------------------------- #
# Filtros e ordenações
# --------------------------------------------------------------------------- #


def _existe_envio(*condicoes):
    return exists(select(Entrega.id).where(Entrega.atividade_id == Atividade.id, *condicoes))


def _condicoes_de_status(codigos: list[str], referencia: datetime) -> list:
    partes = []
    nao_entrega = Atividade.tipo != AtividadeTipo.ENTREGA
    for codigo in codigos:
        if codigo == "a_fazer":
            partes.append(and_(nao_entrega, Atividade.status == AtividadeStatus.A_FAZER))
        elif codigo == "em_andamento":
            partes.append(and_(nao_entrega, Atividade.status == AtividadeStatus.EM_ANDAMENTO))
        elif codigo == "concluida":
            partes.append(Atividade.status == AtividadeStatus.CONCLUIDA)
        elif codigo == "atrasada":
            partes.append(
                and_(
                    nao_entrega,
                    Atividade.status != AtividadeStatus.CONCLUIDA,
                    Atividade.prazo.is_not(None),
                    Atividade.prazo < referencia,
                )
            )
        elif codigo == "pendente":
            partes.append(
                and_(Atividade.tipo == AtividadeTipo.ENTREGA, ~_existe_envio())
            )
        elif codigo == "enviada":
            partes.append(
                and_(
                    Atividade.tipo == AtividadeTipo.ENTREGA,
                    _existe_envio(
                        Entrega.numero == 1,
                        Entrega.resultado == EntregaResultado.AGUARDANDO_AVALIACAO,
                    ),
                )
            )
        elif codigo == "reenviada":
            partes.append(
                and_(
                    Atividade.tipo == AtividadeTipo.ENTREGA,
                    _existe_envio(
                        Entrega.numero > 1,
                        Entrega.resultado == EntregaResultado.AGUARDANDO_AVALIACAO,
                    ),
                )
            )
        elif codigo == "ajustes_solicitados":
            partes.append(
                and_(
                    Atividade.tipo == AtividadeTipo.ENTREGA,
                    _existe_envio(Entrega.resultado == EntregaResultado.AJUSTES_SOLICITADOS),
                    ~_existe_envio(Entrega.resultado == EntregaResultado.APROVADA),
                )
            )
        elif codigo == "aprovada":
            partes.append(
                and_(
                    Atividade.tipo == AtividadeTipo.ENTREGA,
                    _existe_envio(Entrega.resultado == EntregaResultado.APROVADA),
                )
            )
    return partes


def _condicoes_de_filtro(projeto_id: int) -> list:
    consulta = [Atividade.projeto_id == projeto_id]
    tipo = (request.args.get("tipo") or "").strip()
    if tipo:
        if tipo not in list(AtividadeTipo):
            raise ErroDeNegocio(
                "parametro_invalido",
                "Filtro 'tipo' inválido: use desenvolvimento, estudo ou entrega",
                400,
            )
        consulta.append(Atividade.tipo == AtividadeTipo(tipo))

    codigos = [c.strip() for c in (request.args.get("status") or "").split(",") if c.strip()]
    invalidos = [c for c in codigos if c not in FILTROS_STATUS]
    if invalidos:
        raise ErroDeNegocio(
            "parametro_invalido",
            f"Filtro 'status' inválido: {', '.join(invalidos)}",
            400,
        )
    if codigos:
        consulta.append(or_(*_condicoes_de_status(codigos, agora())))

    responsavel = (request.args.get("responsavel_id") or "").strip()
    if responsavel:
        try:
            consulta.append(Atividade.responsavel_id == int(responsavel))
        except ValueError:
            raise ErroDeNegocio(
                "parametro_invalido",
                "Filtro 'responsavel_id' deve ser um número",
                400,
            ) from None

    busca = (request.args.get("q") or "").strip()
    if busca:
        consulta.append(
            or_(
                Atividade.titulo.ilike(f"%{busca}%"),
                func.coalesce(Atividade.descricao, "").ilike(f"%{busca}%"),
            )
        )
    return consulta


def _ordenar(consulta, ordenacao: str | None = None):
    ordenacao = ordenacao or (request.args.get("ordenar") or "proximas")
    if ordenacao == "recentes":
        return consulta.order_by(Atividade.criado_em.desc())
    return consulta.order_by(
        case((Atividade.status == AtividadeStatus.CONCLUIDA, 1), else_=0),
        case((Atividade.prazo.is_(None), 1), else_=0),
        Atividade.prazo,
        Atividade.titulo,
    )


def listar_do_projeto(
    projeto: Projeto, usuario, pagina: int, por_pagina: int
) -> dict[str, Any]:
    consulta = _ordenar(select(Atividade).where(*_condicoes_de_filtro(projeto.id)))
    consulta = consulta.options(*opcoes_de_leitura())
    paginacao = db.paginate(consulta, page=pagina, per_page=por_pagina, error_out=False)

    itens = [serializar(atividade, usuario) for atividade in paginacao.items]
    contagem = painel_progresso(projeto.id)
    return {
        **montar_paginacao(paginacao, itens),
        "projeto": {
            "id": projeto.id,
            "nome": projeto.nome,
            "progresso": contagem["percentual"],
        },
        "contagens_por_tipo": contagens_por_tipo(projeto.id),
    }


# --------------------------------------------------------------------------- #
# Tela Hoje / Esta semana
# --------------------------------------------------------------------------- #


def _condicoes_visiveis(usuario) -> list:
    if eh_coordenador(usuario):
        return [
            Atividade.projeto_id.in_(
                select(Projeto.id).where(Projeto.coordenador_id == usuario.id)
            )
        ]
    return [Atividade.responsavel_id == usuario.id]


def _entrega_aprovada() -> Any:
    """'Entregue' é entrega aprovada pelo coordenador, não só atividade concluída."""
    return and_(
        Atividade.tipo == AtividadeTipo.ENTREGA,
        Atividade.status == AtividadeStatus.CONCLUIDA,
        _existe_envio(Entrega.resultado == EntregaResultado.APROVADA),
    )


def _condicoes_de_aba(aba: str, referencia: datetime) -> list:
    nao_concluida = Atividade.status != AtividadeStatus.CONCLUIDA
    if aba == "hoje":
        return [nao_concluida, Atividade.prazo <= fim_do_dia(referencia.date())]
    if aba == "semana":
        return [nao_concluida, Atividade.prazo <= fim_da_semana(referencia.date())]
    if aba == "pendentes":
        return [nao_concluida]
    if aba == "entregues":
        return [_entrega_aprovada()]
    if aba == "concluidas":
        return [Atividade.status == AtividadeStatus.CONCLUIDA]
    return []


def listar_minhas(usuario, pagina: int, por_pagina: int, aba: str | None) -> dict[str, Any]:
    referencia = agora()
    aba = aba or "todas"
    if aba not in ABAS_MINHAS:
        raise ErroDeNegocio(
            "parametro_invalido",
            f"Aba inválida. Use uma destas: {', '.join(ABAS_MINHAS)}",
            400,
        )

    consulta = select(Atividade).where(*_condicoes_visiveis(usuario))
    consulta = consulta.where(*_condicoes_de_aba(aba, referencia))

    for parametro, operador in (("prazo_de", ">="), ("prazo_ate", "<=")):
        bruto = (request.args.get(parametro) or "").strip()
        if not bruto:
            continue
        instante = instante_de_filtro(bruto, parametro)
        consulta = consulta.where(
            Atividade.prazo >= instante if operador == ">=" else Atividade.prazo <= instante
        )

    codigos = [c.strip() for c in (request.args.get("status") or "").split(",") if c.strip()]
    if codigos:
        consulta = consulta.where(or_(*_condicoes_de_status(codigos, referencia)))

    busca = (request.args.get("q") or "").strip()
    if busca:
        consulta = consulta.where(Atividade.titulo.ilike(f"%{busca}%"))

    consulta = consulta.options(*opcoes_de_leitura())
    consulta = _ordenar(consulta)
    paginacao = db.paginate(consulta, page=pagina, per_page=por_pagina, error_out=False)

    itens = [serializar(atividade, usuario) for atividade in paginacao.items]
    return {
        **montar_paginacao(paginacao, itens),
        "aba": aba,
        "contagens": _contagens_de_abas(usuario, referencia),
    }


def _contagens_de_abas(usuario, referencia: datetime) -> dict[str, int]:
    """Todas as abas em uma única query de agregação condicional."""
    base = _condicoes_visiveis(usuario)
    expressoes = [func.count().label("todas")]
    for aba in ("hoje", "semana", "pendentes", "concluidas", "entregues"):
        condicoes = [and_(*base, *_condicoes_de_aba(aba, referencia))]
        expressoes.append(func.sum(case((condicoes[0], 1), else_=0)).label(aba))
    linha = db.session.execute(select(*expressoes).select_from(Atividade).where(*base)).one()
    return {
        "hoje": int(linha.hoje or 0),
        "semana": int(linha.semana or 0),
        "pendentes": int(linha.pendentes or 0),
        "concluidas": int(linha.concluidas or 0),
        "entregues": int(linha.entregues or 0),
        "todas": linha.todas,
    }


# --------------------------------------------------------------------------- #
# Agregações reaproveitadas pelo painel
# --------------------------------------------------------------------------- #


def painel_progresso(projeto_id: int, referencia: datetime | None = None) -> dict[str, Any]:
    """Baldes mutuamente exclusivos: concluída > atrasada > em andamento > a fazer."""
    ref = referencia or agora()
    linha = db.session.execute(
        select(
            func.count().label("total"),
            func.sum(
                case((Atividade.status == AtividadeStatus.CONCLUIDA, 1), else_=0)
            ).label("concluidas"),
            func.sum(
                case(
                    (
                        and_(
                            Atividade.status != AtividadeStatus.CONCLUIDA,
                            Atividade.prazo.is_not(None),
                            Atividade.prazo < ref,
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("atrasadas"),
            func.sum(
                case(
                    (
                        and_(
                            Atividade.status == AtividadeStatus.EM_ANDAMENTO,
                            or_(Atividade.prazo.is_(None), Atividade.prazo >= ref),
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("em_andamento"),
        )
        .select_from(Atividade)
        .where(Atividade.projeto_id == projeto_id)
    ).one()

    total = linha.total
    concluidas = int(linha.concluidas or 0)
    atrasadas = int(linha.atrasadas or 0)
    em_andamento = int(linha.em_andamento or 0)
    pendentes = total - concluidas - atrasadas - em_andamento
    return {
        "percentual": porcentagem(concluidas, total),
        "total": total,
        "concluidas": concluidas,
        "atrasadas": atrasadas,
        "em_andamento": em_andamento,
        "pendentes": max(pendentes, 0),
    }


def contagens_por_tipo(projeto_id: int) -> dict[str, int]:
    linhas = db.session.execute(
        select(Atividade.tipo, func.count())
        .where(Atividade.projeto_id == projeto_id)
        .group_by(Atividade.tipo)
    ).all()
    contagens = {tipo.value: total for tipo, total in linhas}
    return {t.value: contagens.get(t.value, 0) for t in AtividadeTipo}


# --------------------------------------------------------------------------- #
# RN05 e RN13
# --------------------------------------------------------------------------- #


def _checar_responsavel(projeto: Projeto, responsavel_id: int | None) -> dict[str, Any]:
    if not responsavel_id:
        return {"responsavel_id": "Selecione o responsável"}
    usuario = db.session.get(Usuario, responsavel_id)
    if usuario is None:
        return {"responsavel_id": "Responsável não encontrado"}
    if usuario.perfil != Perfil.BOLISTA:
        return {"responsavel_id": "O responsável deve ser bolsista"}
    vinculado = db.session.scalar(
        select(Participacao.projeto_id).where(
            Participacao.projeto_id == projeto.id,
            Participacao.usuario_id == responsavel_id,
        )
    )
    if vinculado is None:
        return {"responsavel_id": "O responsável precisa estar vinculado ao projeto"}
    return {}


def _checar_link_material(tipo: str | None, link: str | None) -> dict[str, Any]:
    if link and tipo != AtividadeTipo.ESTUDO:
        return {"link_material": "Só atividades do tipo estudo aceitam link de material"}
    return {}