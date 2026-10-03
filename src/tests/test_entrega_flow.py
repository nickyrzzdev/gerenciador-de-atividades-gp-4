"""Fluxo completo da entrega: pendente -> enviada -> ajustes -> reenviada -> aprovada."""

from __future__ import annotations

from conftest import criar_atividade, entrar
from models import AtividadeStatus, AtividadeTipo


def _enviar(client, atividade_id, descricao="Envio 1"):
    return client.post(
        f"/api/atividades/{atividade_id}/entregas",
        json={"descricao": descricao, "link": "https://exemplo.uea.edu.br/entrega"},
    )


def _avaliar(client, entrega_id, resultado, comentario=None):
    return client.post(
        f"/api/entregas/{entrega_id}/avaliacao",
        json={"resultado": resultado, "comentario": comentario},
    )


def test_fluxo_completo_da_entrega(client, cenario, usuarios):
    entrar(client, "ana.carvalho@uea.edu.br")
    assert _avaliar(client, 999, "aprovada").status_code == 404  # entrega inexistente

    entrega = cenario["entrega"]

    # 1. Sem envios: situação pendente (só a responsável pode reenviar)
    historico = client.get(f"/api/atividades/{entrega.id}/entregas").get_json()
    assert historico["situacao"] == "pendente"
    assert historico["total_envios"] == 0
    assert historico["pode_reenviar"] is False  # Ana é coordenadora, não responsável

    # 2. A bolsista envia -> enviada, atividade vai para em_andamento
    entrar(client, "marina.costa@uea.edu.br")
    assert client.get(f"/api/atividades/{entrega.id}/entregas").get_json()["pode_reenviar"] is True
    resposta = _enviar(client, entrega.id)
    assert resposta.status_code == 201
    assert resposta.get_json()["mensagem"] == "Entrega enviada"
    primeira = resposta.get_json()["entrega"]["id"]

    atividade = client.get(f"/api/atividades/{entrega.id}").get_json()["atividade"]
    assert atividade["status"] == AtividadeStatus.EM_ANDAMENTO.value
    assert atividade["situacao_entrega"] == "enviada"
    assert atividade["total_envios"] == 1

    # Não pode enviar de novo enquanto aguarda avaliação
    assert _enviar(client, entrega.id, " Envio indevido").status_code == 409

    # 3. Coordenador pede ajustes (comentário obrigatório)
    entrar(client, "ana.carvalho@uea.edu.br")
    sem_comentario = _avaliar(client, primeira, "ajustes_solicitados")
    assert sem_comentario.status_code == 422
    assert "comentario" in sem_comentario.get_json()["erro"]["campos"]

    ajustes = _avaliar(client, primeira, "ajustes_solicitados", "Ajuste a fonte do título.")
    assert ajustes.status_code == 200

    # 4. Reenvio -> reenviada
    entrar(client, "marina.costa@uea.edu.br")
    segunda = _enviar(client, entrega.id, "Envio 2 revisado").get_json()["entrega"]["id"]
    atividade = client.get(f"/api/atividades/{entrega.id}").get_json()["atividade"]
    assert atividade["situacao_entrega"] == "reenviada"
    assert atividade["total_envios"] == 2
    assert atividade["status"] == AtividadeStatus.EM_ANDAMENTO.value

    # 5. Aprovação -> atividade concluída
    entrar(client, "ana.carvalho@uea.edu.br")
    aprovacao = _avaliar(client, segunda, "aprovada", "Muito bom!")
    assert aprovacao.status_code == 200
    assert aprovacao.get_json()["mensagem"] == "Entrega aprovada"

    atividade = client.get(f"/api/atividades/{entrega.id}").get_json()["atividade"]
    assert atividade["status"] == AtividadeStatus.CONCLUIDA.value
    assert atividade["concluida_em"] is not None
    assert atividade["situacao_entrega"] == "aprovada"
    assert atividade["status_exibicao"]["codigo"] == "aprovada"
    assert "enviar_entrega" not in atividade["acoes_permitidas"]

    # Histórico preserva os dois envios (RN10)
    historico = client.get(f"/api/atividades/{entrega.id}/entregas").get_json()
    assert historico["total_envios"] == 2
    assert [e["numero"] for e in historico["envios"]] == [1, 2]
    assert historico["envios"][0]["feedback"]["comentario"] == "Ajuste a fonte do título."
    assert historico["envios"][1]["resultado"] == "aprovada"
    assert historico["atividade"]["aprovada_em"] is not None

    # Não reavalia a mesma entrega
    assert _avaliar(client, segunda, "aprovada").status_code == 409


def test_entrega_nao_aceita_status_manual(client, cenario, usuarios):
    """RN09: atividade do tipo entrega não aceita PATCH de status."""
    entrega = cenario["entrega"]
    entrar(client, "marina.costa@uea.edu.br")
    resposta = client.patch(
        f"/api/atividades/{entrega.id}/status", json={"status": "concluida"}
    )
    assert resposta.status_code == 422
    assert resposta.get_json()["erro"]["codigo"] == "status_controlado"


def test_dev_estudo_transitam_livremente(client, cenario, usuarios):
    """RN11: a_fazer -> em_andamento -> concluida -> reaberta."""
    projeto, marina = cenario["projeto"], usuarios["marina"]
    atividade = criar_atividade(projeto, marina, AtividadeTipo.ESTUDO)
    entrar(client, "marina.costa@uea.edu.br")

    def marcar(status):
        return client.patch(
            f"/api/atividades/{atividade.id}/status", json={"status": status}
        ).get_json()["atividade"]

    assert marcar("em_andamento")["status"] == "em_andamento"
    concluida = marcar("concluida")
    assert concluida["concluida_em"] is not None
    assert concluida["status_exibicao"]["rotulo"] == "Concluída"

    reaberta = marcar("a_fazer")
    assert reaberta["status"] == "a_fazer"
    assert reaberta["concluida_em"] is None


def test_progresso_sobe_apos_aprovacao(client, cenario, usuarios):
    projeto, entrega = cenario["projeto"], cenario["entrega"]
    entrar(client, "ana.carvalho@uea.edu.br")

    antes = client.get(f"/api/projetos/{projeto.id}").get_json()["projeto"]["progresso"]
    entrar(client, "marina.costa@uea.edu.br")
    id_entrega = _enviar(client, entrega.id).get_json()["entrega"]["id"]
    entrar(client, "ana.carvalho@uea.edu.br")
    _avaliar(client, id_entrega, "aprovada")

    depois = client.get(f"/api/projetos/{projeto.id}").get_json()["projeto"]["progresso"]
    assert depois > antes