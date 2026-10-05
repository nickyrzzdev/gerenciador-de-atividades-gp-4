"""CRUD de atividades, agenda e progresso (RN01, RN05, RN06, RN09, RN11, RN12)."""

from datetime import timedelta

from conftest import apagar, criar_atividade, db_commit, entrar
from models import db
from utils import agora

MARINA = "marina.costa@uea.edu.br"
ANA = "ana.carvalho@uea.edu.br"
JOAO = "joao.silva@uea.edu.br"
LINK = "https://exemplo.uea.edu.br/x"


def _criar(client, projeto_id, usuarios, **extra):
    corpo = {
        "titulo": "Estudar OAuth 2.0",
        "descricao": "Comparar sessão e token",
        "tipo": "estudo",
        # 5 dias: fora da janela de urgência (DIAS_URGENCIA = 3)
        "prazo": (agora() + timedelta(days=5)).strftime("%Y-%m-%d %H:%M"),
        "responsavel_id": usuarios["marina"].id,
    }
    corpo.update(extra)
    return client.post(f"/api/projetos/{projeto_id}/atividades", json=corpo)


# --------------------------------------------------------------------------- #
# RN01 — criação
# --------------------------------------------------------------------------- #


def test_criar_atividade_salva_descricao_e_prazo(client, cenario, usuarios):
    projeto = cenario["projeto"]
    entrar(client, ANA)

    resposta = _criar(client, projeto.id, usuarios)
    assert resposta.status_code == 201, resposta.get_json()

    atividade = resposta.get_json()["atividade"]
    assert atividade["titulo"] == "Estudar OAuth 2.0"
    assert atividade["descricao"] == "Comparar sessão e token"
    assert atividade["status"] == "a_fazer"
    assert atividade["concluida_em"] is None
    assert atividade["responsavel"]["id"] == usuarios["marina"].id
    assert atividade["projeto"]["id"] == projeto.id
    assert atividade["status_exibicao"]["codigo"] == "a_fazer"
    assert "editar" in atividade["acoes_permitidas"]


def test_prazo_apenas_com_data_vira_fim_do_dia(client, cenario, usuarios):
    """'2026-12-31' significa o fim do dia, não a meia-noite."""
    entrar(client, ANA)
    resposta = _criar(client, cenario["projeto"].id, usuarios, prazo="2026-12-31")
    assert resposta.status_code == 201, resposta.get_json()
    assert resposta.get_json()["atividade"]["prazo"].startswith("2026-12-31T23:59")


def test_bolsista_nao_cria_e_coordenador_alheio_nao_acessa(client, cenario, usuarios):
    projeto = cenario["projeto"]

    entrar(client, MARINA)
    assert _criar(client, projeto.id, usuarios).status_code == 403

    entrar(client, JOAO)
    assert _criar(client, projeto.id, usuarios).status_code == 404


def test_link_material_so_em_estudo(client, cenario, usuarios):
    """RN06: link de material é exclusivo do tipo estudo e precisa ser http(s)."""
    projeto = cenario["projeto"]
    entrar(client, ANA)

    assert _criar(client, projeto.id, usuarios, link_material=LINK).status_code == 201
    assert (
        _criar(client, projeto.id, usuarios, tipo="entrega", link_material=LINK).status_code == 422
    )
    assert _criar(client, projeto.id, usuarios, link_material="ftp://exemplo").status_code == 422


def test_campos_invalidos_na_criacao(client, cenario, usuarios):
    projeto = cenario["projeto"]
    entrar(client, ANA)

    sem_titulo = _criar(client, projeto.id, usuarios, titulo="")
    assert sem_titulo.status_code == 422
    assert "titulo" in sem_titulo.get_json()["erro"]["campos"]

    assert _criar(client, projeto.id, usuarios, tipo="pesquisa").status_code == 422
    assert _criar(client, projeto.id, usuarios, prazo="31/02/2026").status_code == 422
    # Coordenador não pode ser responsável (RN05)
    assert _criar(client, projeto.id, usuarios, responsavel_id=usuarios["joao"].id).status_code == 422


def test_criacao_ignora_tentativa_de_definir_status(client, cenario, usuarios):
    """RN11: toda atividade nasce em a_fazer; o status tem um único endpoint."""
    projeto = cenario["projeto"]
    entrar(client, ANA)

    resposta = _criar(client, projeto.id, usuarios, status="concluida")
    assert resposta.status_code == 422
    assert "status" in resposta.get_json()["erro"]["campos"]


# --------------------------------------------------------------------------- #
# Edição e exclusão
# --------------------------------------------------------------------------- #


def test_atualizar_e_excluir_atividade(client, cenario, usuarios):
    projeto = cenario["projeto"]
    entrar(client, ANA)
    atividade_id = _criar(client, projeto.id, usuarios).get_json()["atividade"]["id"]

    atualizada = client.put(
        f"/api/atividades/{atividade_id}",
        json={"titulo": "Estudar OAuth 2.0 (revisto)", "descricao": None},
    )
    assert atualizada.status_code == 200, atualizada.get_json()
    corpo = atualizada.get_json()["atividade"]
    assert corpo["titulo"] == "Estudar OAuth 2.0 (revisto)"
    assert corpo["descricao"] == ""

    assert apagar(client, f"/api/atividades/{atividade_id}").status_code == 200
    assert client.get(f"/api/atividades/{atividade_id}").status_code == 404


def test_put_nao_muda_status(client, cenario, usuarios):
    """RN11: o status muda só pelo PATCH dedicado."""
    entrar(client, ANA)
    atividade_id = _criar(client, cenario["projeto"].id, usuarios).get_json()["atividade"]["id"]

    resposta = client.put(f"/api/atividades/{atividade_id}", json={"status": "concluida"})
    assert resposta.status_code == 422
    assert "status" in resposta.get_json()["erro"]["campos"]


# --------------------------------------------------------------------------- #
# RN09/RN11 — status
# --------------------------------------------------------------------------- #


def test_entrega_nao_aceita_patch_de_status(client, cenario):
    """RN09: a situação da entrega dirige o status da atividade."""
    entrar(client, MARINA)
    resposta = client.patch(
        f"/api/atividades/{cenario['entrega'].id}/status", json={"status": "concluida"}
    )
    assert resposta.status_code == 422
    assert resposta.get_json()["erro"]["codigo"] == "status_controlado"


def test_concluir_direto_e_reabrir(client, cenario, usuarios):
    """RN11: o modal conclui de a_fazer; reabrir limpa concluida_em."""
    projeto = cenario["projeto"]
    entrar(client, ANA)
    alvo_id = _criar(client, projeto.id, usuarios).get_json()["atividade"]["id"]

    entrar(client, MARINA)
    concluida = client.patch(f"/api/atividades/{alvo_id}/status", json={"status": "concluida"})
    assert concluida.status_code == 200
    assert concluida.get_json()["atividade"]["concluida_em"] is not None

    reaberta = client.patch(f"/api/atividades/{alvo_id}/status", json={"status": "a_fazer"})
    assert reaberta.status_code == 200
    assert reaberta.get_json()["atividade"]["concluida_em"] is None


def test_status_desconhecido(client, cenario):
    entrar(client, MARINA)
    resposta = client.patch(
        f"/api/atividades/{cenario['projeto'].id}/atividades",
        json={"status": "cancelada"},
    )
    assert resposta.status_code in (404, 405)


# --------------------------------------------------------------------------- #
# Agenda e listagem
# --------------------------------------------------------------------------- #


def test_minhas_atividades_filtra_por_responsavel_e_ordena(client, cenario, usuarios):
    projeto = cenario["projeto"]
    criar_atividade(projeto, usuarios["marina"], dias=1, titulo="Marina - amanhã")
    criar_atividade(projeto, usuarios["ana"], dias=2, titulo="Ana - depois")
    db_commit()

    entrar(client, MARINA)
    corpo = client.get("/api/atividades/minhas?aba=todas").get_json()
    titulos = [i["titulo"] for i in corpo["itens"]]

    assert "Marina - amanhã" in titulos
    assert "Ana - depois" not in titulos
    assert "Entrega do protótipo" in titulos
    assert set(corpo["contagens"]) >= {"hoje", "semana", "pendentes", "concluidas", "todas"}

    # Ordenação: por prazo, com as concluídas no fim da lista.
    pendentes = [i["prazo"] for i in corpo["itens"] if i["status"] != "concluida"]
    assert pendentes == sorted(pendentes)
    assert corpo["itens"][-1]["status"] == "concluida"


def test_aba_invalida_e_periodo_invalido(client, cenario):
    projeto = cenario["projeto"]

    entrar(client, MARINA)
    assert client.get("/api/atividades/minhas?aba=inexistente").status_code == 400

    entrar(client, ANA)
    assert client.get(f"/api/projetos/{projeto.id}/visao-geral?periodo=45").status_code == 400
    assert client.get(f"/api/projetos/{projeto.id}/visao-geral?periodo=30").status_code == 200


def test_filtros_de_tipo_e_status(client, cenario):
    projeto = cenario["projeto"]
    entrar(client, MARINA)

    apenas_entregas = client.get(f"/api/projetos/{projeto.id}/atividades?tipo=entrega").get_json()
    assert [i["tipo"] for i in apenas_entregas["itens"]] == ["entrega"]

    concluidas = client.get(f"/api/projetos/{projeto.id}/atividades?status=concluida").get_json()
    assert len(concluidas["itens"]) == 1

    assert client.get(f"/api/projetos/{projeto.id}/atividades?tipo=x").status_code == 400
    assert client.get(f"/api/projetos/{projeto.id}/atividades?status=x").status_code == 400
    assert client.get(f"/api/projetos/{projeto.id}/atividades?tipo=").status_code == 200


def test_busca_por_titulo(client, cenario, usuarios):
    projeto = cenario["projeto"]
    entrar(client, ANA)
    criar_atividade(projeto, usuarios["marina"], dias=7, titulo="Diagramas de fluxo")
    db_commit()

    achou = client.get(f"/api/projetos/{projeto.id}/atividades?q=diagr").get_json()
    assert [i["titulo"] for i in achou["itens"]] == ["Diagramas de fluxo"]
    assert client.get(f"/api/projetos/{projeto.id}/atividades?q=zzz").get_json()["itens"] == []


def test_paginacao(client, cenario, usuarios):
    projeto = cenario["projeto"]
    entrar(client, ANA)
    for indice in range(5):
        criar_atividade(projeto, usuarios["marina"], dias=indice + 1, titulo=f"Atividade {indice}")
    db_commit()

    pagina = client.get(
        f"/api/projetos/{projeto.id}/atividades?por_pagina=3&pagina=2"
    ).get_json()
    assert pagina["paginacao"]["total"] == 8
    assert pagina["paginacao"]["pagina"] == 2
    assert pagina["paginacao"]["total_paginas"] == 3
    assert len(pagina["itens"]) == 3

    # Limites de paginação são normalizados, não rejeitados.
    limitada = client.get(f"/api/projetos/{projeto.id}/atividades?por_pagina=999").get_json()
    assert limitada["paginacao"]["por_pagina"] <= 100
    assert client.get(f"/api/projetos/{projeto.id}/atividades?pagina=abc").status_code == 400


# --------------------------------------------------------------------------- #
# Progresso e chips
# --------------------------------------------------------------------------- #


def test_progresso_do_projeto_soma_os_baldes(client, cenario):
    projeto = cenario["projeto"]
    entrar(client, MARINA)

    detalhe = client.get(f"/api/projetos/{projeto.id}").get_json()["projeto"]
    assert detalhe["progresso"] == 33
    assert detalhe["total_atividades"] == 3

    # Os baldes detalhados vêm da visão geral.
    progresso = client.get(f"/api/projetos/{projeto.id}/visao-geral").get_json()["progresso"]
    assert progresso["concluidas"] == 1
    assert progresso["atrasadas"] == 1
    assert progresso["percentual"] == 33
    assert (
        progresso["concluidas"]
        + progresso["atrasadas"]
        + progresso["em_andamento"]
        + progresso["pendentes"]
        == detalhe["total_atividades"]
    )


def test_entrega_sem_envio_continua_pendente(client, cenario):
    """A atividade pode estar em andamento e o chip ser 'Pendente'."""
    entrar(client, MARINA)
    entrega = client.get(f"/api/atividades/{cenario['entrega'].id}").get_json()["atividade"]
    assert entrega["situacao_entrega"] == "pendente"
    assert entrega["status_exibicao"]["rotulo"] == "Pendente"
    assert entrega["status_exibicao"]["atrasada"] is False
    assert entrega["total_envios"] == 0


def test_conta_desativada_nao_entra(client, usuarios):
    from models import Usuario

    conta = db.session.get(Usuario, usuarios["marina"].id)
    conta.ativo = False
    db_commit()

    resposta = client.post("/api/auth/login", json={"email": MARINA, "senha": "Senha123"})
    assert resposta.status_code == 401