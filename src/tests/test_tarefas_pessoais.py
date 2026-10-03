"""CRUD de tarefas pessoais e isolamento por usuário."""

from datetime import timedelta

from conftest import SENHA, apagar, entrar
from utils import Perfil, agora


def _criar(client, **dados):
    corpo = {
        "titulo": "Preparar apresentação",
        "descricao": "Organizar os slides",
        "prazo": (agora() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
    }
    corpo.update(dados)
    return client.post("/api/tarefas", json=corpo)


def test_cadastro_de_perfil_individual(client):
    resposta = client.post(
        "/api/auth/cadastro",
        json={
            "nome": "Pessoa Individual",
            "email": "pessoa.individual@uea.edu.br",
            "senha": "OutraSenha1",
            "confirmar_senha": "OutraSenha1",
            "perfil": "individual",
        },
    )
    assert resposta.status_code == 201, resposta.get_json()
    assert resposta.get_json()["usuario"]["perfil"] == "individual"

    login = client.post(
        "/api/auth/login",
        json={"email": "pessoa.individual@uea.edu.br", "senha": "OutraSenha1"},
    )
    assert login.status_code == 200
    assert login.get_json()["usuario"]["perfil"] == "individual"
    tarefa = _criar(client, titulo="Minha primeira tarefa")
    assert tarefa.status_code == 201, tarefa.get_json()
    assert tarefa.get_json()["tarefa"]["titulo"] == "Minha primeira tarefa"


def test_perfis_antigos_continuam_validos(client):
    for perfil, email in (
        (Perfil.COORDENADOR, "novo.coordenador@uea.edu.br"),
        (Perfil.BOLISTA, "novo.bolsista@uea.edu.br"),
    ):
        resposta = client.post(
            "/api/auth/cadastro",
            json={
                "nome": f"Novo {perfil.value}",
                "email": email,
                "senha": "OutraSenha1",
                "confirmar_senha": "OutraSenha1",
                "perfil": perfil.value,
            },
        )
        assert resposta.status_code == 201, resposta.get_json()
        assert resposta.get_json()["usuario"]["perfil"] == perfil.value


def test_criar_listar_filtrar_e_pesquisar_tarefas(client, usuarios):
    entrar(client, "ana.carvalho@uea.edu.br")
    prazo = (agora() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
    criada = _criar(client, prazo=prazo)
    assert criada.status_code == 201, criada.get_json()
    tarefa = criada.get_json()["tarefa"]
    assert tarefa["titulo"] == "Preparar apresentação"
    assert tarefa["descricao"] == "Organizar os slides"
    assert tarefa["status"] == "a_fazer"
    assert tarefa["prazo"] == f"{prazo.replace(' ', 'T')}:00"
    assert tarefa["concluida_em"] is None

    sem_prazo = _criar(client, titulo="Ler documentação", prazo="")
    assert sem_prazo.status_code == 201, sem_prazo.get_json()
    assert sem_prazo.get_json()["tarefa"]["prazo"] is None

    listagem = client.get("/api/tarefas?q=apresentação&status=a_fazer")
    corpo = listagem.get_json()
    assert listagem.status_code == 200
    assert [item["titulo"] for item in corpo["itens"]] == ["Preparar apresentação"]
    assert corpo["paginacao"]["total"] == 1


def test_usuario_so_lista_e_acessa_suas_tarefas(client, usuarios):
    entrar(client, "ana.carvalho@uea.edu.br")
    tarefa_ana = _criar(client).get_json()["tarefa"]
    entrar(client, "joao.silva@uea.edu.br")
    tarefa_joao = _criar(client, titulo="Tarefa do João").get_json()["tarefa"]

    entrar(client, "ana.carvalho@uea.edu.br")
    listagem = client.get("/api/tarefas").get_json()["itens"]
    assert [item["id"] for item in listagem] == [tarefa_ana["id"]]
    assert client.get(f"/api/tarefas/{tarefa_joao['id']}").status_code == 404
    assert client.put(
        f"/api/tarefas/{tarefa_joao['id']}", json={"titulo": "Acesso indevido"}
    ).status_code == 404
    assert client.patch(
        f"/api/tarefas/{tarefa_joao['id']}/status", json={"status": "concluida"}
    ).status_code == 404
    assert apagar(client, f"/api/tarefas/{tarefa_joao['id']}").status_code == 404
    assert client.get(f"/api/tarefas/{tarefa_ana['id']}").status_code == 200


def test_editar_tarefa_e_status_separado(client, usuarios):
    entrar(client, "ana.carvalho@uea.edu.br")
    tarefa = _criar(client).get_json()["tarefa"]
    atualizada = client.put(
        f"/api/tarefas/{tarefa['id']}",
        json={"titulo": "Apresentação revisada", "descricao": None, "prazo": ""},
    )
    assert atualizada.status_code == 200, atualizada.get_json()
    corpo = atualizada.get_json()["tarefa"]
    assert corpo["titulo"] == "Apresentação revisada"
    assert corpo["descricao"] is None
    assert corpo["prazo"] is None
    assert corpo["status"] == "a_fazer"

    tentativa = client.put(
        f"/api/tarefas/{tarefa['id']}", json={"status": "concluida"}
    )
    assert tentativa.status_code == 422
    assert "status" in tentativa.get_json()["erro"]["campos"]


def test_concluir_reabrir_e_excluir_tarefa(client, usuarios):
    entrar(client, "ana.carvalho@uea.edu.br")
    tarefa = _criar(client).get_json()["tarefa"]

    concluida = client.patch(
        f"/api/tarefas/{tarefa['id']}/status", json={"status": "concluida"}
    )
    assert concluida.status_code == 200
    assert concluida.get_json()["tarefa"]["concluida_em"] is not None

    reaberta = client.patch(
        f"/api/tarefas/{tarefa['id']}/status", json={"status": "em_andamento"}
    )
    assert reaberta.status_code == 200
    assert reaberta.get_json()["tarefa"]["status"] == "em_andamento"
    assert reaberta.get_json()["tarefa"]["concluida_em"] is None

    assert apagar(client, f"/api/tarefas/{tarefa['id']}").status_code == 200
    assert client.get(f"/api/tarefas/{tarefa['id']}").status_code == 404


def test_validacao_e_sessao_obrigatoria(client, usuarios):
    entrar(client, "ana.carvalho@uea.edu.br")
    assert _criar(client, titulo="").status_code == 422
    assert _criar(client, prazo="data-invalida").status_code == 422
    assert client.get("/api/tarefas?status=desconhecido").status_code == 400
    client.post("/api/auth/logout", json={})
    assert client.get("/api/tarefas").status_code == 401
    assert client.post(
        "/api/tarefas", json={"titulo": "Sem sessão"}
    ).status_code == 401


def test_migracao_preserva_usuarios_indices_gatilhos_e_chaves():
    from sqlalchemy import create_engine, text

    from migrations.add_individual_profile import upgrade

    engine = create_engine("sqlite://")
    with engine.begin() as conexao:
        conexao.execute(
            text(
                """
                CREATE TABLE usuarios (
                    id INTEGER PRIMARY KEY,
                    nome VARCHAR(120) NOT NULL,
                    email VARCHAR(180) NOT NULL UNIQUE,
                    senha_hash VARCHAR(255) NOT NULL,
                    perfil VARCHAR(40) NOT NULL
                        CHECK (perfil IN ('coordenador', 'bolsista')),
                    ativo BOOLEAN NOT NULL,
                    criado_em DATETIME NOT NULL
                )
                """
            )
        )
        conexao.execute(text("CREATE INDEX ix_usuarios_email ON usuarios (email)"))
        conexao.execute(
            text(
                """
                CREATE TRIGGER usuarios_nome_normalizado
                AFTER UPDATE OF nome ON usuarios
                BEGIN
                    SELECT NEW.nome;
                END
                """
            )
        )
        conexao.execute(
            text(
                """
                CREATE TABLE tarefas_pessoais (
                    id INTEGER PRIMARY KEY,
                    usuario_id INTEGER NOT NULL REFERENCES usuarios(id)
                )
                """
            )
        )
        conexao.execute(
            text(
                """
                INSERT INTO usuarios
                    (id, nome, email, senha_hash, perfil, ativo, criado_em)
                VALUES
                    (17, 'Ana', 'ana@example.org', 'hash', 'coordenador', 1, '2026-01-01'),
                    (28, 'Bia', 'bia@example.org', 'hash', 'bolsista', 1, '2026-01-02')
                """
            )
        )
        conexao.execute(
            text("INSERT INTO tarefas_pessoais (id, usuario_id) VALUES (3, 17)")
        )

    assert upgrade(engine) is True
    assert upgrade(engine) is False
    with engine.connect() as conexao:
        usuarios_salvos = conexao.execute(
            text(
                "SELECT id, nome, email, senha_hash, perfil, ativo, criado_em "
                "FROM usuarios ORDER BY id"
            )
        ).all()
        assert usuarios_salvos == [
            (17, "Ana", "ana@example.org", "hash", "coordenador", 1, "2026-01-01"),
            (28, "Bia", "bia@example.org", "hash", "bolsista", 1, "2026-01-02"),
        ]
        conexao.execute(
            text(
                """
                INSERT INTO usuarios
                    (id, nome, email, senha_hash, perfil, ativo, criado_em)
                VALUES (39, 'Cris', 'cris@example.org', 'hash', 'individual', 1, '2026-01-03')
                """
            )
        )
        assert conexao.execute(
            text("SELECT usuario_id FROM tarefas_pessoais")
        ).scalar_one() == 17
        assert conexao.execute(
            text("PRAGMA foreign_key_check")
        ).all() == []
        assert conexao.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'index' AND name = 'ix_usuarios_email'"
            )
        ).scalar_one() == "ix_usuarios_email"
        assert conexao.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'trigger' AND name = 'usuarios_nome_normalizado'"
            )
        ).scalar_one() == "usuarios_nome_normalizado"
        ddl = conexao.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='usuarios'")
        ).scalar_one()
        assert "'individual'" in ddl

    engine.dispose()
