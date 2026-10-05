"""Permissões: bolsista não cria, não vê projeto alheio e não avalia (RN01-RN04)."""

from __future__ import annotations

from conftest import apagar, criar_atividade, criar_projeto, db_commit, entrar, vincular


def test_nao_autenticado_recebe_401_json(client, cenario):
    for rota in ("/api/projetos", "/api/atividades/minhas", "/api/auth/me"):
        resposta = client.get(rota)
        assert resposta.status_code == 401
        assert resposta.is_json
        assert resposta.get_json()["erro"]["codigo"] == "nao_autenticado"


def test_bolsista_nao_cria_projeto(client, cenario, usuarios):
    entrar(client, "marina.costa@uea.edu.br")
    resposta = client.post(
        "/api/projetos",
        json={
            "nome": "Tentativa",
            "descricao": "x",
            "data_inicio": "2026-01-01",
            "data_fim": "2026-02-01",
        },
    )
    assert resposta.status_code == 403


def test_bolsista_nao_cria_atividade(client, cenario, usuarios):
    projeto = cenario["projeto"].id
    marina = usuarios["marina"].id
    entrar(client, "marina.costa@uea.edu.br")
    resposta = client.post(
        f"/api/projetos/{projeto}/atividades",
        json={
            "titulo": "Não deveria",
            "tipo": "desenvolvimento",
            "prazo": "2026-10-20",
            "responsavel_id": marina,
        },
    )
    assert resposta.status_code == 403
    assert resposta.get_json()["erro"]["codigo"] == "sem_permissao"


def test_bolsista_nao_ve_projeto_alheio(client, usuarios):
    """RN03: projeto inacessível responde 404, sem vazar existência."""
    projeto_do_joao = criar_projeto(usuarios["joao"])
    db_commit()
    entrar(client, "marina.costa@uea.edu.br")

    assert client.get(f"/api/projetos/{projeto_do_joao.id}").status_code == 404
    assert client.get(f"/api/projetos/{projeto_do_joao.id}/atividades").status_code == 404
    assert client.get(f"/api/projetos/{projeto_do_joao.id}/visao-geral").status_code == 404
    assert client.get(f"/api/projetos/{projeto_do_joao.id}/membros").status_code == 404

    # O projeto também não aparece na lista dela
    lista = client.get("/api/projetos").get_json()
    assert lista["itens"] == []


def test_coordenador_nao_altera_projeto_de_outro(client, usuarios):
    projeto_do_joao = criar_projeto(usuarios["joao"])
    db_commit()
    entrar(client, "ana.carvalho@uea.edu.br")
    assert client.put(f"/api/projetos/{projeto_do_joao.id}", json={"nome": "X"}).status_code == 404
    assert apagar(client, f"/api/projetos/{projeto_do_joao.id}").status_code == 404


def test_bolsista_nao_avalia_entrega(client, cenario):
    entrega = cenario["entrega"]
    entrar(client, "marina.costa@uea.edu.br")
    id_entrega = client.post(
        f"/api/atividades/{entrega.id}/entregas",
        json={"descricao": "Envio", "link": "https://exemplo.uea.edu.br/x"},
    ).get_json()["entrega"]["id"]

    # Perfil errado -> 403
    assert client.post(
        f"/api/entregas/{id_entrega}/avaliacao", json={"resultado": "aprovada"}
    ).status_code == 403


def test_coordenador_alheio_nao_avalia(client, cenario):
    entrega = cenario["entrega"]
    entrar(client, "marina.costa@uea.edu.br")
    id_entrega = client.post(
        f"/api/atividades/{entrega.id}/entregas",
        json={"descricao": "Envio", "link": "https://exemplo.uea.edu.br/x"},
    ).get_json()["entrega"]["id"]

    # Coordinator of another project -> 404 (não vaza o projeto)
    entrar(client, "joao.silva@uea.edu.br")
    assert client.post(
        f"/api/entregas/{id_entrega}/avaliacao", json={"resultado": "aprovada"}
    ).status_code == 404


def test_bolsista_so_altera_status_das_proprias_atividades(client, cenario, usuarios):
    """RN02: só o responsável mexe no status das atividades de dev/estudo."""
    projeto = cenario["projeto"]
    outro = criar_projeto(usuarios["ana"])
    vincular(outro, usuarios["marina"])
    # Atividade de outro projeto que NÃO é da Marina
    alheia = criar_atividade(outro, usuarios["ana"], titulo="Atividade da Ana")
    db_commit()

    entrar(client, "marina.costa@uea.edu.br")
    atividade = client.get(f"/api/projetos/{projeto.id}/atividades").get_json()["itens"][0]

    assert (
        client.patch(
            f"/api/atividades/{atividade['id']}/status", json={"status": "concluida"}
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/atividades/{alheia.id}/status", json={"status": "em_andamento"}
        ).status_code
        == 403
    )


def test_responsavel_precisa_ser_bolsista_vinculado(client, cenario, usuarios):
    """RN05."""
    projeto = cenario["projeto"]
    entrar(client, "ana.carvalho@uea.edu.br")
    resposta = client.post(
        f"/api/projetos/{projeto.id}/atividades",
        json={
            "titulo": "Atividade",
            "tipo": "desenvolvimento",
            "prazo": "2026-10-20",
            "responsavel_id": usuarios["joao"].id,  # coordenador, não bolsista
        },
    )
    assert resposta.status_code == 422
    assert "responsavel_id" in resposta.get_json()["erro"]["campos"]


def test_desvincular_com_atividade_pendente_retorna_409(client, cenario, usuarios):
    """RN07."""
    projeto, marina = cenario["projeto"], usuarios["marina"]
    entrar(client, "ana.carvalho@uea.edu.br")
    resposta = apagar(client, f"/api/projetos/{projeto.id}/membros/{marina.id}")
    assert resposta.status_code == 409
    assert resposta.get_json()["erro"]["campos"]["atividades_pendentes"] > 0

