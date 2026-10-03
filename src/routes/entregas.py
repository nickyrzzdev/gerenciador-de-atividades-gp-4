"""Rotas de entrega: histórico, envio/reenvio e avaliação."""

from flask_login import current_user

from routes import api
from services import entrega_service
from utils import (
    EntregaResultado,
    Perfil,
    corpo_json,
    login_obrigatorio,
    perfil_obrigatorio,
    resposta,
)


@api.get("/atividades/<int:atividade_id>/entregas")
@login_obrigatorio
def historico(atividade_id: int):
    return resposta(entrega_service.historico(atividade_id, current_user))


@api.post("/atividades/<int:atividade_id>/entregas")
@login_obrigatorio
@perfil_obrigatorio(Perfil.BOLISTA)
def enviar(atividade_id: int):
    entrega = entrega_service.registrar_envio(atividade_id, current_user, corpo_json())
    return resposta({"entrega": entrega.to_dict()}, 201, "Entrega enviada")


@api.post("/entregas/<int:entrega_id>/avaliacao")
@login_obrigatorio
@perfil_obrigatorio(Perfil.COORDENADOR)
def avaliar(entrega_id: int):
    entrega = entrega_service.avaliar(entrega_id, current_user, corpo_json())
    aprovado = entrega.resultado == EntregaResultado.APROVADA
    mensagem = "Entrega aprovada" if aprovado else "Ajustes solicitados"
    return resposta({"entrega": entrega.to_dict()}, 200, mensagem)