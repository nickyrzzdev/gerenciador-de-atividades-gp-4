"""Rotas de projeto, membros e atividades de um projeto."""

from flask import request
from flask_login import current_user

from routes import api
from services import atividade_service, painel_service, projeto_service
from utils import (
    Perfil,
    corpo_json,
    login_obrigatorio,
    pagina_atual,
    perfil_obrigatorio,
    periodo_dias,
    resposta,
)


@api.get("/projetos")
@login_obrigatorio
def listar_projetos():
    pagina, por_pagina = pagina_atual()
    return resposta(
        projeto_service.listar_projetos(
            current_user, request.args.get("aba", "todos"), request.args.get("q", ""), pagina, por_pagina
        )
    )


@api.get("/projetos/resumo")
@login_obrigatorio
def resumo_projetos():
    return resposta(painel_service.resumo(current_user))


def _detalhe(projeto) -> dict:
    """Mesmo formato do GET /api/projetos/{id}, em todas as respostas de projeto."""
    total, concluidas = projeto_service.progresso_do_projeto(projeto.id)
    return projeto_service.serializar_projeto(projeto, total, concluidas)


@api.post("/projetos")
@login_obrigatorio
@perfil_obrigatorio(Perfil.COORDENADOR)
def criar_projeto():
    projeto = projeto_service.criar_projeto(current_user, corpo_json())
    return resposta({"projeto": _detalhe(projeto)}, 201, "Projeto criado")


@api.get("/projetos/<int:projeto_id>")
@login_obrigatorio
def obter_projeto(projeto_id: int):
    projeto = projeto_service.obter_projeto_acessivel(projeto_id, current_user)
    return resposta({"projeto": _detalhe(projeto)})


@api.put("/projetos/<int:projeto_id>")
@login_obrigatorio
@perfil_obrigatorio(Perfil.COORDENADOR)
def atualizar_projeto(projeto_id: int):
    projeto = projeto_service.atualizar_projeto(projeto_id, current_user, corpo_json())
    return resposta({"projeto": _detalhe(projeto)}, 200, "Projeto atualizado")


@api.post("/projetos/<int:projeto_id>/encerrar")
@login_obrigatorio
@perfil_obrigatorio(Perfil.COORDENADOR)
def encerrar_projeto(projeto_id: int):
    projeto = projeto_service.encerrar_projeto(projeto_id, current_user)
    return resposta({"projeto": _detalhe(projeto)}, 200, "Projeto encerrado")


@api.delete("/projetos/<int:projeto_id>")
@login_obrigatorio
@perfil_obrigatorio(Perfil.COORDENADOR)
def excluir_projeto(projeto_id: int):
    projeto_service.excluir_projeto(projeto_id, current_user)
    return resposta({}, 200, "Projeto excluído")


@api.get("/projetos/<int:projeto_id>/visao-geral")
@login_obrigatorio
def visao_geral(projeto_id: int):
    projeto = projeto_service.obter_projeto_acessivel(projeto_id, current_user)
    periodo = periodo_dias(painel_service.PERIODOS_VALIDOS, 30)
    return resposta(painel_service.visao_geral(projeto, current_user, periodo))


# --------------------------------------------------------------------------- #
# Atividades do projeto
# --------------------------------------------------------------------------- #


@api.get("/projetos/<int:projeto_id>/atividades")
@login_obrigatorio
def listar_atividades(projeto_id: int):
    projeto = projeto_service.obter_projeto_acessivel(projeto_id, current_user)
    pagina, por_pagina = pagina_atual()
    return resposta(atividade_service.listar_do_projeto(projeto, current_user, pagina, por_pagina))


@api.post("/projetos/<int:projeto_id>/atividades")
@login_obrigatorio
@perfil_obrigatorio(Perfil.COORDENADOR)
def criar_atividade(projeto_id: int):
    projeto = projeto_service.obter_projeto_acessivel(projeto_id, current_user, exigir_coordenador=True)
    atividade = atividade_service.criar(projeto, current_user, corpo_json())
    return resposta(
        {"atividade": atividade_service.serializar(atividade, current_user)},
        201,
        "Atividade criada",
    )