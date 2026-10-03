"""Projetos, membros, painel e tratamento de erro (RN01, RN03, RN07, RN13)."""

from conftest import (
    apagar,
    criar_atividade,
    criar_projeto,
    criar_usuario,
    db_commit,
    entrar,
    vincular,
)
from models import db
from utils import Perfil

ANA = "ana.carvalho@uea.edu.br"
JOAO = "joao.silva@uea.edu.br"
MARINA = "marina.costa@uea.edu.br"

NOVO_PROJETO = {
    "nome": "Sensores do bloco B",
    "descricao": "Coleta de temperatura",
    "data_inicio": "2026-10-01",
    "data_fim": "2027-06-30",
}


# --------------------------------------------------------------------------- #
# RN01/RN03 — criação e acesso
# --------------------------------------------------------------------------- #


def test_criar_projeto_e_ver_progresso(client, usuarios):
    entrar(client, ANA)

    resposta = client.post("/api/projetos", json=NOVO_PROJETO)
    assert resposta.status_code == 201, resposta.get_json()

    projeto = resposta.get_json()["projeto"]
    assert projeto["nome"] == "Sensores do bloco B"
    assert projeto["progresso"] == 0
    assert projeto["total_atividades"] == 0
    assert projeto["status"]["codigo"] == "em_andamento"
    assert projeto["coordenador"]["id"] == usuarios["ana"].id

    detalhe = client.get(f"/api/projetos/{projeto['id']}").get_json()["projeto"]
    assert detalhe["membros_extra"] == 0
    assert detalhe["total_bolsistas"] == 0


def test_projeto_alheio_responde_404(client, usuarios):
    projeto = criar_projeto(usuarios["joao"])
    db_commit()
    entrar(client, ANA)

    assert client.get(f"/api/projetos/{projeto.id}").status_code == 404
    assert client.get(f"/api/projetos/{projeto.id}/atividades").status_code == 404
    assert client.get(f"/api/projetos/{projeto.id}/membros").status_code == 404
    assert client.get(f"/api/projetos/{projeto.id}/visao-geral").status_code == 404


def test_data_final_anterior_a_inicial(client, usuarios):
    entrar(client, ANA)
    corpo = dict(NOVO_PROJETO, data_fim="2026-09-30")

    resposta = client.post("/api/projetos", json=corpo)
    assert resposta.status_code == 422
    assert "data_fim" in resposta.get_json()["erro"]["campos"]


def test_projeto_exige_nome_e_datas(client, usuarios):
    entrar(client, ANA)
    resposta = client.post("/api/projetos", json={"descricao": "sem nome"})
    campos = resposta.get_json()["erro"]["campos"]
    assert resposta.status_code == 422
    assert {"nome", "data_inicio", "data_fim"} <= set(campos)


def test_encerrar_e_nao_voltar_para_em_andamento(client, usuarios):
    projeto = criar_projeto(usuarios["ana"])
    db_commit()
    entrar(client, ANA)

    encerrado = client.post(f"/api/projetos/{projeto.id}/encerrar", json={})
    assert encerrado.status_code == 200
    assert encerrado.get_json()["projeto"]["status"]["codigo"] == "concluido"

    # a resposta traz o mesmo formato do GET de detalhe
    assert encerrado.get_json()["projeto"]["coordenador"]["id"] == usuarios["ana"].id

    # encerrar de novo é idempotente
    assert client.post(f"/api/projetos/{projeto.id}/encerrar", json={}).status_code == 200

    voltar = client.put(f"/api/projetos/{projeto.id}", json={"status": "em_andamento"})
    assert voltar.status_code == 422
    assert "não volta" in voltar.get_json()["erro"]["campos"]["status"]

    # continuar como concluído é aceito
    assert client.put(f"/api/projetos/{projeto.id}", json={"status": "concluido"}).status_code == 200


def test_excluir_projeto_com_pendencias_responde_409(client, cenario, usuarios):
    """RN07/RN03: projeto com atividades não concluídas não sai de graça."""
    projeto = cenario["projeto"]
    entrar(client, ANA)

    conflito = apagar(client, f"/api/projetos/{projeto.id}")
    assert conflito.status_code == 409
    campos = conflito.get_json()["erro"]["campos"]
    assert campos["membros"] == 1 and campos["atividades_pendentes"] == 2

    # Conclui tudo e desvincula a bolsista: aí a exclusão passa
    for atividade in client.get(f"/api/projetos/{projeto.id}/atividades").get_json()["itens"]:
        if atividade["tipo"] == "entrega":
            # a bolsista envia e só a coordenadora avalia
            entrar(client, MARINA)
            envio = client.post(
                f"/api/atividades/{atividade['id']}/entregas",
                json={"descricao": "v1", "link": "https://github.com/uea-lab/prototipo"},
            ).get_json()
            assert "entrega" in envio, envio
            entrar(client, ANA)
            avaliacao = client.post(
                f"/api/entregas/{envio['entrega']['id']}/avaliacao",
                json={"resultado": "aprovada", "comentario": "Top"},
            )
            assert avaliacao.status_code == 200, avaliacao.get_json()
        else:
            client.patch(
                f"/api/atividades/{atividade['id']}/status", json={"status": "concluida"}
            )

    assert apagar(client, f"/api/projetos/{projeto.id}/membros/{usuarios['marina'].id}").status_code == 200
    assert apagar(client, f"/api/projetos/{projeto.id}").status_code == 200
    assert client.get(f"/api/projetos/{projeto.id}").status_code == 404


# --------------------------------------------------------------------------- #
# RN07 — membros
# --------------------------------------------------------------------------- #


def test_vincular_e_desvincular_membro(client, cenario, usuarios):
    projeto = cenario["projeto"]
    vivian = criar_usuario("Vivian Souza", Perfil.BOLISTA)
    db_commit()
    entrar(client, ANA)

    entrada = client.post(
        f"/api/projetos/{projeto.id}/membros", json={"email": "vivian.souza@uea.edu.br"}
    )
    assert entrada.status_code == 201, entrada.get_json()
    assert entrada.get_json()["mensagem"] == "Bolsista vinculado ao projeto"

    # Já vinculado -> 409
    assert (
        client.post(
            f"/api/projetos/{projeto.id}/membros", json={"email": "vivian.souza@uea.edu.br"}
        ).status_code
        == 409
    )
    # E-mail que não existe / não é bolsista
    assert client.post(f"/api/projetos/{projeto.id}/membros", json={"email": "ninguem@uea.edu.br"}).status_code == 404
    assert client.post(f"/api/projetos/{projeto.id}/membros", json={"email": JOAO}).status_code == 422

    # Membro sem atividade pendente sai
    assert apagar(client, f"/api/projetos/{projeto.id}/membros/{vivian.id}").status_code == 200


def test_membros_lista_e_opcoes(client, cenario, usuarios):
    projeto = cenario["projeto"]
    vivian = criar_usuario("Vivian Souza", Perfil.BOLISTA)
    vincular(projeto, vivian)
    criar_atividade(projeto, vivian, titulo="Atividade da Vivian")
    db_commit()
    entrar(client, ANA)

    lista = client.get(f"/api/projetos/{projeto.id}/membros").get_json()
    nomes = [m["usuario"]["nome"] for m in lista["itens"]]
    assert "Marina Costa" in nomes and "Vivian Souza" in nomes
    assert lista["total_bolsistas"] == 2

    atribuidas = {m["usuario"]["nome"]: m["atividades_atribuidas"] for m in lista["itens"]}
    assert atribuidas["Marina Costa"] == 3
    assert atribuidas["Vivian Souza"] == 1

    # select de responsáveis: id + nome + iniciais, sem expor e-mail
    opcoes = client.get(f"/api/projetos/{projeto.id}/membros/opcoes").get_json()["itens"]
    assert {o["nome"] for o in opcoes} == {"Marina Costa", "Vivian Souza"}
    assert {o["id"] for o in opcoes} == {usuarios["marina"].id, vivian.id}
    assert all(set(o) == {"id", "nome", "iniciais"} for o in opcoes)


def test_bolsista_nao_gerencia_membros(client, cenario):
    projeto = cenario["projeto"]
    entrar(client, MARINA)

    assert client.post(f"/api/projetos/{projeto.id}/membros", json={"email": ANA}).status_code == 403
    assert apagar(client, f"/api/projetos/{projeto.id}/membros/3").status_code == 403


# --------------------------------------------------------------------------- #
# Listagem, abas e resumo
# --------------------------------------------------------------------------- #


def test_abas_de_projetos(client, cenario):
    entrar(client, ANA)
    corpo = client.get("/api/projetos").get_json()

    assert corpo["itens"][0]["nome"] == cenario["projeto"].nome
    assert set(corpo["contagens"]) == {"em_andamento", "concluidos", "todos"}
    assert corpo["contagens"]["todos"] == 1

    assert client.get("/api/projetos?aba=em_andamento").get_json()["itens"]
    assert client.get("/api/projetos?aba=concluidos").get_json()["itens"] == []

    # aba desconhecida é erro, não fallback silencioso
    invalida = client.get("/api/projetos?aba=x")
    assert invalida.status_code == 400
    assert invalida.get_json()["erro"]["codigo"] == "parametro_invalido"

    busca = client.get("/api/projetos?q=inexistente").get_json()
    assert busca["itens"] == []


def test_resumo_de_projetos(client, cenario):
    entrar(client, ANA)

    resumo = client.get("/api/projetos/resumo").get_json()
    assert resumo["total"] == 1
    assert resumo["em_andamento"] == 1
    assert resumo["concluidos"] == 0
    assert resumo["atrasados"] == 1


def test_paginacao_de_projetos(client, usuarios):
    for indice in range(3):
        projeto = criar_projeto(usuarios["ana"])
        projeto.nome = f"Projeto {indice}"
    db_commit()
    entrar(client, ANA)

    pagina = client.get("/api/projetos?por_pagina=2").get_json()
    assert pagina["paginacao"]["total"] == 3
    assert pagina["paginacao"]["total_paginas"] == 2
    assert len(pagina["itens"]) == 2


# --------------------------------------------------------------------------- #
# RN13 — painel
# --------------------------------------------------------------------------- #


def test_visao_geral_completa(client, cenario):
    projeto = cenario["projeto"]
    entrar(client, ANA)

    visao = client.get(f"/api/projetos/{projeto.id}/visao-geral").get_json()
    assert visao["kpis"]["total"] == 3
    assert visao["kpis"]["concluidas"] == 1
    assert visao["kpis"]["atrasadas"] == 1
    assert visao["por_tipo"]
    assert visao["resumo"]["nome"] == projeto.nome
    assert len(visao["proximas_entregas"]) <= 3
    assert visao["ranking_bolsistas"][0]["usuario"]["nome"] == "Marina Costa"
    assert "variacao_mes" in visao  # None quando o período anterior não tinha atividades


def test_bolsista_nao_ve_ranking(client, cenario):
    projeto = cenario["projeto"]
    entrar(client, MARINA)

    visao = client.get(f"/api/projetos/{projeto.id}/visao-geral").get_json()
    assert "ranking_bolsistas" not in visao
    assert visao["kpis"]["total"] == 3


def test_periodos_aceitos(client, cenario):
    projeto = cenario["projeto"]
    entrar(client, ANA)

    for periodo in (7, 30, 90):
        resposta = client.get(f"/api/projetos/{projeto.id}/visao-geral?periodo={periodo}")
        assert resposta.status_code == 200
        assert resposta.get_json()["periodo"] == periodo


# --------------------------------------------------------------------------- #
# Infraestrutura
# --------------------------------------------------------------------------- #


def test_exige_json_em_metodos_alterantes(client, usuarios):
    """Mitigação de CSRF: sem Content-Type JSON, 400 antes de qualquer regra."""
    entrar(client, ANA)
    resposta = client.post(
        "/api/projetos", data="nome=x", content_type="text/plain"
    )
    assert resposta.status_code == 400
    assert resposta.get_json()["erro"]["codigo"] == "content_type"


def test_json_malformado_e_404_tem_formato_de_erro(client, usuarios):
    entrar(client, ANA)

    malformado = client.post(
        "/api/projetos", data="{quebrado", content_type="application/json"
    )
    assert malformado.status_code == 400
    assert malformado.get_json()["erro"]["codigo"] == "json_invalido"

    inexistente = client.get("/api/rotas/que/nao/existe")
    assert inexistente.status_code == 404
    assert inexistente.is_json
    assert inexistente.get_json()["erro"]["codigo"] == "nao_encontrado"

    metodo_errado = client.delete("/api/auth/login", headers={"Content-Type": "application/json"})
    assert metodo_errado.status_code == 405
    assert metodo_errado.get_json()["erro"]["codigo"] == "metodo_nao_permitido"
    assert "POST" in metodo_errado.headers["Allow"]  # método aceito pela rota

    # 405 tem precedência sobre o 400 de content-type
    sem_json = client.put("/api/auth/login", data="x", content_type="text/plain")
    assert sem_json.status_code == 405


def test_saude_e_explorador(client):
    assert client.get("/api/saude").get_json()["status"] == "ok"
    assert client.get("/dev/api").status_code == 200
    assert client.get("/").status_code == 302


def test_transacao_desfeita_quando_o_request_falha(client, usuarios):
    """O handler de erro faz rollback: a alteração inválida não fica no banco."""
    from models import Projeto

    projeto = criar_projeto(usuarios["ana"])
    db_commit()
    entrar(client, ANA)

    original = db.session.get(Projeto, projeto.id).data_fim
    resposta = client.put(f"/api/projetos/{projeto.id}", json={"data_fim": "2020-01-01"})
    assert resposta.status_code == 422

    db.session.expire_all()
    assert db.session.get(Projeto, projeto.id).data_fim == original