"""Rotas da API para tarefas pessoais."""

from flask import request
from flask_login import current_user

from routes import api
from services import tarefa_pessoal_service
from utils import corpo_json, login_obrigatorio, pagina_atual, resposta


@api.get("/tarefas")
@login_obrigatorio
def listar_tarefas():
    pagina, por_pagina = pagina_atual()
    return resposta(
        tarefa_pessoal_service.listar(
            current_user,
            pagina,
            por_pagina,
            request.args.get("status"),
            request.args.get("q"),
        )
    )


@api.post("/tarefas")
@login_obrigatorio
def criar_tarefa():
    tarefa = tarefa_pessoal_service.criar(current_user, corpo_json())
    return resposta({"tarefa": tarefa.to_dict()}, 201, "Tarefa criada")


@api.get("/tarefas/<int:tarefa_id>")
@login_obrigatorio
def obter_tarefa(tarefa_id: int):
    tarefa = tarefa_pessoal_service.obter(tarefa_id, current_user)
    return resposta({"tarefa": tarefa.to_dict()})


@api.put("/tarefas/<int:tarefa_id>")
@login_obrigatorio
def atualizar_tarefa(tarefa_id: int):
    tarefa = tarefa_pessoal_service.atualizar(tarefa_id, current_user, corpo_json())
    return resposta({"tarefa": tarefa.to_dict()}, 200, "Tarefa atualizada")


@api.patch("/tarefas/<int:tarefa_id>/status")
@login_obrigatorio
def alterar_status_tarefa(tarefa_id: int):
    tarefa = tarefa_pessoal_service.alterar_status(tarefa_id, current_user, corpo_json())
    return resposta({"tarefa": tarefa.to_dict()}, 200, "Status atualizado")


@api.delete("/tarefas/<int:tarefa_id>")
@login_obrigatorio
def excluir_tarefa(tarefa_id: int):
    tarefa_pessoal_service.excluir(tarefa_id, current_user)
    return resposta({}, 200, "Tarefa excluída")
