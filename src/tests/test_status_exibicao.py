"""Atraso derivado (RN12) e baldes da visão geral, que devem somar o total."""

from __future__ import annotations

from datetime import datetime, timedelta

from conftest import criar_atividade, criar_projeto, entrar, vincular
from models import AtividadeStatus, db
from utils import status_exibicao_atividade


def criar_projeto_padrao(usuarios):
    return criar_projeto(usuarios["ana"])


def test_status_exibicao_de_atraso_e_urgencia():
    """RN12 + seção 7: atraso e 'vence em N dias' são estados derivados."""
    base = datetime(2026, 10, 2, 10, 0)

    concluida = status_exibicao_atividade(
        tipo="desenvolvimento", status="concluida", prazo=base - timedelta(days=9),
        referencia=base,
    )
    assert concluida["codigo"] == "concluida"
    assert concluida["atrasada"] is False

    atrasada = status_exibicao_atividade(
        tipo="desenvolvimento", status="em_andamento", prazo=base - timedelta(days=1),
        referencia=base,
    )
    assert atrasada["codigo"] == "atrasada"
    assert atrasada["rotulo"] == "Atrasada"
    assert atrasada["atrasada"] is True

    hoje = status_exibicao_atividade(
        tipo="desenvolvimento", status="a_fazer", prazo=base + timedelta(hours=3),
        referencia=base,
    )
    assert hoje["codigo"] == "vence_0"
    assert hoje["rotulo"] == "Vence hoje"

    dois_dias = status_exibicao_atividade(
        tipo="desenvolvimento", status="a_fazer", prazo=base + timedelta(days=2),
        referencia=base,
    )
    assert dois_dias["rotulo"] == "Vence em 2 dias"
    assert dois_dias["tom"] == "alerta"

    longe = status_exibicao_atividade(
        tipo="desenvolvimento", status="a_fazer", prazo=base + timedelta(days=30),
        referencia=base,
    )
    assert longe["codigo"] == "a_fazer"
    assert longe["rotulo"] == "A fazer"


def test_entrega_usa_a_situacao_e_sinaliza_atraso():
    base = datetime(2026, 10, 2, 10, 0)
    chip = status_exibicao_atividade(
        tipo="entrega", status="em_andamento", prazo=base - timedelta(days=3),
        situacao="enviada", referencia=base,
    )
    assert chip["codigo"] == "enviada"
    assert chip["atrasada"] is True


# --------------------------------------------------------------------------- #



def test_buckets_da_visao_geral_somam_o_total(client, usuarios):
    """Os 4 baldes são mutuamente exclusivos: concluída > atrasada > em andamento > a fazer."""
    projeto = criar_projeto_padrao(usuarios)
    marina = usuarios["marina"]
    for u in usuarios.values():
        vincular(projeto, u)

    # 2 concluídas (uma delas com prazo vencido: não pode virar "atrasada")
    criar_atividade(projeto, marina, status=AtividadeStatus.CONCLUIDA, dias=-1, titulo="C1")
    criar_atividade(projeto, marina, status=AtividadeStatus.CONCLUIDA, dias=5, titulo="C2")
    # 1 atrasada em andamento
    criar_atividade(
        projeto, marina, status=AtividadeStatus.EM_ANDAMENTO, dias=-3, titulo="Atrasada"
    )
    # 1 em andamento dentro do prazo
    criar_atividade(
        projeto, marina, status=AtividadeStatus.EM_ANDAMENTO, dias=3, titulo="No prazo"
    )
    # 2 a fazer
    criar_atividade(projeto, marina, status=AtividadeStatus.A_FAZER, dias=8, titulo="P1")
    criar_atividade(projeto, marina, status=AtividadeStatus.A_FAZER, dias=9, titulo="P2")
    db.session.commit()

    entrar(client, "ana.carvalho@uea.edu.br")
    visao = client.get(f"/api/projetos/{projeto.id}/visao-geral").get_json()
    progresso = visao["progresso"]

    assert progresso["concluidas"] == 2
    assert progresso["atrasadas"] == 1
    assert progresso["em_andamento"] == 1
    assert progresso["pendentes"] == 2
    soma = (
        progresso["concluidas"]
        + progresso["atrasadas"]
        + progresso["em_andamento"]
        + progresso["pendentes"]
    )
    assert soma == visao["kpis"]["total"] == 6
    assert progresso["percentual"] == 33  # 2/6, arredondado como nos cartões
    assert sum(item["quantidade"] for item in visao["por_tipo"]) == 6
    assert visao["kpis"]["percentual_concluidas"] == 33  # 2/6 arredondado


def test_ranking_apenas_para_coordenador(client, usuarios):
    projeto = criar_projeto_padrao(usuarios)
    vincular(projeto, usuarios["marina"])
    db.session.commit()

    entrar(client, "marina.costa@uea.edu.br")
    assert "ranking_bolsistas" not in client.get(
        f"/api/projetos/{projeto.id}/visao-geral"
    ).get_json()

    entrar(client, "ana.carvalho@uea.edu.br")
    ranking = client.get(f"/api/projetos/{projeto.id}/visao-geral").get_json()[
        "ranking_bolsistas"
    ]
    assert [linha["usuario"]["nome"] for linha in ranking] == ["Marina Costa"]


# --------------------------------------------------------------------------- #
