"""Rotas de membros do projeto (vinculação e desvinculação)."""

from flask import request
from flask_login import current_user

from routes import api
from services import membro_service, projeto_service
from utils import (
    Perfil,
    corpo_json,
    login_obrigatorio,
    pagina_atual,
    perfil_obrigatorio,
    resposta,
)


@api.get("/projetos/<int:projeto_id>/membros")
@login_obrigatorio
def listar_membros(projeto_id: int):
    projeto = projeto_service.obter_projeto_acessivel(projeto_id, current_user)
    pagina, por_pagina = pagina_atual()
    return resposta(
        membro_service.listar_membros(projeto, request.args.get("q", ""), pagina, por_pagina)
    )


@api.get("/projetos/<int:projeto_id>/membros/opcoes")
@login_obrigatorio
def opcoes_responsaveis(projeto_id: int):
    projeto = projeto_service.obter_projeto_acessivel(projeto_id, current_user)
    return resposta({"itens": membro_service.opcoes_de_responsaveis(projeto)})


@api.post("/projetos/<int:projeto_id>/membros")
@login_obrigatorio
@perfil_obrigatorio(Perfil.COORDENADOR)
def vincular_membro(projeto_id: int):
    projeto = projeto_service.obter_projeto_acessivel(projeto_id, current_user, exigir_coordenador=True)
    participacao = membro_service.vincular(projeto, corpo_json())
    return resposta({"usuario_id": participacao.usuario_id}, 201, "Bolsista vinculado ao projeto")


@api.delete("/projetos/<int:projeto_id>/membros/<int:usuario_id>")
@login_obrigatorio
@perfil_obrigatorio(Perfil.COORDENADOR)
def desvincular_membro(projeto_id: int, usuario_id: int):
    projeto = projeto_service.obter_projeto_acessivel(projeto_id, current_user, exigir_coordenador=True)
    membro_service.desvincular(projeto, usuario_id)
    return resposta({}, 200, "Bolsista desvinculado do projeto")