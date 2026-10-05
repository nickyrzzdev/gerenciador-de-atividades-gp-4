"""Dados de demonstração. Idempotente: `python seed.py` (use --reset para recomeçar).

Os prazos são relativos a `agora()` para que "atrasada" e "vence em 2 dias"
continuem verdadeiros independentemente do dia em que o seed é executado.
"""

from __future__ import annotations

import sys
from datetime import timedelta

from sqlalchemy import func, select

from app import app
from models import (
    Atividade,
    AtividadeStatus,
    AtividadeTipo,
    Entrega,
    EntregaResultado,
    Participacao,
    Projeto,
    ProjetoStatus,
    Usuario,
    db,
)
from utils import Perfil, agora

SENHA_PADRAO = "Senha123"
NOME_PROJETO_SEMINARIO = "P&D — API de Autenticação"


def _usuario(nome: str, email: str, perfil: Perfil) -> Usuario:
    usuario = Usuario(nome=nome, email=email, perfil=perfil, ativo=True)
    usuario.definir_senha(SENHA_PADRAO)
    db.session.add(usuario)
    return usuario


def _projeto(
    nome: str,
    descricao: str,
    inicio: timedelta,
    fim: timedelta,
    status: ProjetoStatus,
    coordenador: Usuario,
) -> Projeto:
    projeto = Projeto(
        nome=nome,
        descricao=descricao,
        data_inicio=agora().date() + inicio,
        data_fim=agora().date() + fim,
        status=status,
        coordenador_id=coordenador.id,
    )
    db.session.add(projeto)
    db.session.flush()  # garante o id para as participações
    return projeto


def _atividade(
    projeto: Projeto,
    titulo: str,
    tipo: AtividadeTipo,
    responsavel: Usuario,
    criado_por: Usuario,
    prazo: timedelta,
    status: AtividadeStatus = AtividadeStatus.A_FAZER,
    descricao: str = "",
    link_material: str | None = None,
    concluida_em: timedelta | None = None,
) -> Atividade:
    atividade = Atividade(
        projeto_id=projeto.id,
        titulo=titulo,
        descricao=descricao or None,
        tipo=tipo,
        status=status,
        prazo=agora() + prazo,
        responsavel_id=responsavel.id,
        criado_por_id=criado_por.id,
        link_material=link_material,
        concluida_em=agora() + concluida_em if concluida_em is not None else None,
        criado_em=agora() + prazo - timedelta(days=10),
    )
    db.session.add(atividade)
    db.session.flush()  # garante o id para as entregas
    return atividade


def _entrega(
    atividade: Atividade,
    autor: Usuario,
    numero: int,
    descricao: str,
    link: str,
    enviado_em: timedelta,
    resultado: EntregaResultado,
    comentario: str | None = None,
    avaliador: Usuario | None = None,
) -> Entrega:
    avaliada = resultado != EntregaResultado.AGUARDANDO_AVALIACAO
    entrega = Entrega(
        atividade_id=atividade.id,
        usuario_id=autor.id,
        numero=numero,
        descricao=descricao,
        link=link,
        enviada_em=agora() + enviado_em,
        resultado=resultado,
        comentario_feedback=comentario,
        avaliador_id=avaliador.id if avaliada and avaliador else None,
        avaliada_em=agora() + enviado_em + timedelta(hours=6) if avaliada else None,
    )
    db.session.add(entrega)
    return entrega


def popular() -> None:
    ana = _usuario("Ana Carvalho", "ana.carvalho@uea.edu.br", Perfil.COORDENADOR)
    joao = _usuario("João Silva", "joao.silva@uea.edu.br", Perfil.COORDENADOR)
    marina = _usuario("Marina Costa", "marina.costa@uea.edu.br", Perfil.BOLISTA)
    lucas = _usuario("Lucas Costa", "lucas.costa@uea.edu.br", Perfil.BOLISTA)
    rafael = _usuario("Rafael Freitas", "rafael.freitas@uea.edu.br", Perfil.BOLISTA)
    vivian = _usuario("Vivian Souza", "vivian.souza@uea.edu.br", Perfil.BOLISTA)
    db.session.flush()

    # --- Projeto 1: o projeto do seminário, cheio de estados variados ------
    p1 = _projeto(
        NOME_PROJETO_SEMINARIO,
        "Desenvolvimento de uma API de autenticação para os sistemas internos da UEA, "
        "com foco em sessão segura, controle de acesso por perfil e documentação.",
        timedelta(days=-20),
        timedelta(days=40),
        ProjetoStatus.EM_ANDAMENTO,
        ana,
    )
    db.session.add_all(
        [
            Participacao(projeto_id=p1.id, usuario_id=u.id)
            for u in (marina, lucas, rafael, vivian)
        ]
    )
    db.session.flush()

    # Desenvolvimento: atrasada, atrasada e concluída
    _atividade(p1, "Modelagem do banco de dados", AtividadeTipo.DESENVOLVIMENTO, marina, ana,
               timedelta(days=-3), AtividadeStatus.EM_ANDAMENTO, "Diagramas e DDL inicial.")
    _atividade(p1, "Endpoint de login com sessão", AtividadeTipo.DESENVOLVIMENTO, lucas, ana,
               timedelta(days=-1), AtividadeStatus.EM_ANDAMENTO, "Cookie HttpOnly + SameSite.")
    _atividade(p1, "Rotas de projetos e atividades", AtividadeTipo.DESENVOLVIMENTO, rafael, ana,
               timedelta(days=5))
    _atividade(p1, "Testes da rota /api/auth/login", AtividadeTipo.DESENVOLVIMENTO, rafael, ana,
               timedelta(days=-6), AtividadeStatus.CONCLUIDA, "pytest cobrindo o fluxo de sessão.",
               concluida_em=timedelta(days=-5))

    # Estudo: vence em 2 dias e vence amanhã
    _atividade(p1, "Leitura: guia de OAuth 2.0", AtividadeTipo.ESTUDO, marina, ana,
               timedelta(days=2), AtividadeStatus.A_FAZER,
               "Comparar OAuth 2.0 com autenticação por sessão.",
               "https://datatracker.ietf.org/doc/html/rfc6749")
    _atividade(p1, "Artigo sobre sessão vs. token", AtividadeTipo.ESTUDO, lucas, ana,
               timedelta(days=1, hours=6), AtividadeStatus.EM_ANDAMENTO,
               link_material="https://exemplo.uea.edu.br/artigos/sessao-vs-token")

    # Entregas em todas as situações
    figma = _atividade(p1, "Protótipo navegável no Figma", AtividadeTipo.ENTREGA, marina, ana,
                       timedelta(days=-2), AtividadeStatus.CONCLUIDA,
                       "Protótipo de todas as telas do fluxo de login.",
                       concluida_em=timedelta(days=-1))
    _entrega(figma, marina, 1, "Primeira versão do protótipo com 5 telas.",
             "https://figma.com/file/abc123", timedelta(days=-4),
             EntregaResultado.AJUSTES_SOLICITADOS,
             "Faltou a tela de erro de senha incorreta e o protótipo está sem os estados vazios.",
             ana)
    _entrega(figma, marina, 2, "Protótipo revisado com tela de erro e estados vazios.",
             "https://figma.com/file/abc123-v2", timedelta(days=-2),
             EntregaResultado.APROVADA, "Ficou ótimo, aprovado!", ana)

    _atividade(p1, "Documentação da API no README", AtividadeTipo.ENTREGA, rafael, ana,
               timedelta(days=3), AtividadeStatus.EM_ANDAMENTO)
    entrega_doc = _atividade(p1, "Diagrama de fluxo do login", AtividadeTipo.ENTREGA, lucas, ana,
                             timedelta(days=1), AtividadeStatus.EM_ANDAMENTO)
    _entrega(entrega_doc, lucas, 1, "Diagrama em Mermaid no Notion.",
             "https://exemplo.uea.edu.br/diagramas/login", timedelta(hours=-6),
             EntregaResultado.AGUARDANDO_AVALIACAO)

    _atividade(p1, "Relatório de testes de carga", AtividadeTipo.ENTREGA, marina, ana,
               timedelta(days=5), AtividadeStatus.A_FAZER)  # PENDENTE

    reenvio = _atividade(p1, "Diagramas de sequência do projeto", AtividadeTipo.ENTREGA, vivian, ana,
                         timedelta(days=-1), AtividadeStatus.EM_ANDAMENTO)
    _entrega(reenvio, vivian, 1, "Diagramas das telas de entrega.",
             "https://exemplo.uea.edu.br/diagramas/sequencia", timedelta(days=-8),
             EntregaResultado.AJUSTES_SOLICITADOS, "Inclua também o fluxo de avaliação.", ana)
    _entrega(reenvio, vivian, 2, "Diagramas atualizados com o fluxo de avaliação.",
             "https://exemplo.uea.edu.br/diagramas/sequencia-v2", timedelta(hours=-10),
             EntregaResultado.AGUARDANDO_AVALIACAO)

    ajustes = _atividade(p1, "Levantamento de requisitos com a coordenação", AtividadeTipo.ENTREGA,
                         rafael, ana, timedelta(days=4), AtividadeStatus.EM_ANDAMENTO)
    _entrega(ajustes, rafael, 1, "Lista de requisitos levantada na reunião.",
             "https://exemplo.uea.edu.br/requisitos", timedelta(days=-1),
             EntregaResultado.AJUSTES_SOLICITADOS,
             "Faltam os requisitos de acessibilidade (leitores de tela).", ana)

    # --- Projetos extras para o dashboard ---------------------------------
    p2 = _projeto(
        "Monitoramento de Energia do Campus",
        "Coleta de consumo dos prédios do campus com sensores IoT e painel de indicadores.",
        timedelta(days=-60), timedelta(days=15), ProjetoStatus.EM_ANDAMENTO, joao,
    )
    db.session.add_all([Participacao(projeto_id=p2.id, usuario_id=u.id) for u in (lucas, vivian)])
    db.session.flush()
    _atividade(p2, "Instalação dos sensores do bloco A", AtividadeTipo.DESENVOLVIMENTO, lucas, joao,
               timedelta(days=-2), AtividadeStatus.EM_ANDAMENTO)
    _atividade(p2, "Leitura: protocolo MQTT", AtividadeTipo.ESTUDO, vivian, joao, timedelta(days=6))
    _atividade(p2, "Dashboard de consumo", AtividadeTipo.ENTREGA, lucas, joao, timedelta(days=9))

    p3 = _projeto(
        "Português: Corpus de Libras",
        "Montagem de um corpus de vídeos de Libras com transcrição para pesquisa de NLP.",
        timedelta(days=10), timedelta(days=120), ProjetoStatus.PLANEJADO, ana,
    )
    db.session.add(Participacao(projeto_id=p3.id, usuario_id=rafael.id))
    db.session.flush()
    _atividade(p3, "Levantar estúdios de gravação", AtividadeTipo.ESTUDO, rafael, ana, timedelta(days=25))

    p4 = _projeto(
        "Estudo de Viabilidade — IoT na UEA",
        "Análise de viabilidade técnica e financeira de soluções IoT para laboratórios.",
        timedelta(days=-90), timedelta(days=-5), ProjetoStatus.REVISAO, joao,
    )
    db.session.add(Participacao(projeto_id=p4.id, usuario_id=marina.id))
    db.session.flush()
    _atividade(p4, "Planilha de custos de hardware", AtividadeTipo.DESENVOLVIMENTO, marina, joao,
               timedelta(days=-10), AtividadeStatus.EM_ANDAMENTO)
    _atividade(p4, "Relatório de viabilidade", AtividadeTipo.ENTREGA, marina, joao,
               timedelta(days=-8), AtividadeStatus.CONCLUIDA, concluida_em=timedelta(days=-6))
    _entrega(
        db.session.scalar(select(Atividade).where(Atividade.titulo == "Relatório de viabilidade")),
        marina, 1, "Relatório completo com análise de 3 cenários.",
        "https://exemplo.uea.edu.br/viabilidade", timedelta(days=-8),
        EntregaResultado.APROVADA, "Aprovado no parecer técnico.", joao,
    )

    p5 = _projeto(
        "Revisão de Acessibilidade do App",
        "Auditoria e correções de acessibilidade nos formulários e na navegação por teclado.",
        timedelta(days=-120), timedelta(days=-30), ProjetoStatus.CONCLUIDO, ana,
    )
    db.session.add_all([Participacao(projeto_id=p5.id, usuario_id=u.id) for u in (marina, vivian)])
    db.session.flush()
    _atividade(p5, "Auditoria de contraste de cores", AtividadeTipo.DESENVOLVIMENTO, vivian, ana,
               timedelta(days=-40), AtividadeStatus.CONCLUIDA, concluida_em=timedelta(days=-38))

    db.session.commit()


def main() -> None:
    reset = "--reset" in sys.argv

    with app.app_context():
        if reset:
            db.drop_all()
            db.create_all()
            print("Banco recriado do zero (--reset).")
        elif db.session.scalar(select(func.count()).select_from(Usuario)):
            print("O banco já está populado. Use 'python seed.py --reset' para recriar.")
            return
        else:
            db.create_all()

        popular()

        print("Dados de demonstração criados.")
        print("  Coordenadores: ana.carvalho@uea.edu.br | joao.silva@uea.edu.br")
        print("  Bolsistas:     marina.costa@ | lucas.costa@ | rafael.freitas@ | vivian.souza@uea.edu.br")
        print(f"  Senha de todos: {SENHA_PADRAO}")


if __name__ == "__main__":
    main()