"""Rotas de atividade avulsa: minha agenda, detalhe, edição e status."""

from flask import request
from flask_login import current_user

from routes import api
from services import atividade_service
from utils import (
    Perfil,
    corpo_json,
    login_obrigatorio,
    pagina_atual,
    perfil_obrigatorio,
    resposta,
)


@api.get("/atividades/minhas")
@login_obrigatorio
def minhas_atividades():
    pagina, por_pagina = pagina_atual()
    return resposta(
        atividade_service.listar_minhas(
            current_user, pagina, por_pagina, request.args.get("aba")
        )
    )


@api.get("/atividades/<int:atividade_id>")
@login_obrigatorio
def obter_atividade(atividade_id: int):
    atividade, _ = atividade_service.obter_atividade_acessivel(atividade_id, current_user)
    return resposta({"atividade": atividade_service.serializar(atividade, current_user)})


@api.put("/atividades/<int:atividade_id>")
@login_obrigatorio
@perfil_obrigatorio(Perfil.COORDENADOR)
def atualizar_atividade(atividade_id: int):
    atividade = atividade_service.atualizar(atividade_id, current_user, corpo_json())
    return resposta(
        {"atividade": atividade_service.serializar(atividade, current_user)},
        200,
        "Atividade atualizada",
    )


@api.delete("/atividades/<int:atividade_id>")
@login_obrigatorio
@perfil_obrigatorio(Perfil.COORDENADOR)
def excluir_atividade(atividade_id: int):
    atividade_service.excluir(atividade_id, current_user)
    return resposta({}, 200, "Atividade excluída")


@api.patch("/atividades/<int:atividade_id>/status")
@login_obrigatorio
def alterar_status(atividade_id: int):
    atividade = atividade_service.alterar_status(atividade_id, current_user, corpo_json())
    return resposta(
        {"atividade": atividade_service.serializar(atividade, current_user)},
        200,
        "Status atualizado",
    )