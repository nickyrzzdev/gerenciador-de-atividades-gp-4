# LabFlow UEA

Gerenciamento de atividades de projetos de P&D da UEA.

Projeto da disciplina **Fundamentos de Sistemas de Informação (FSI)** · Universidade do Estado do Amazonas (UEA) · Outubro de 2026.

O LabFlow UEA é uma aplicação web feita com Flask para organizar o trabalho de equipes de P&D. Coordenadores cadastram projetos, vinculam bolsistas e atribuem atividades de **desenvolvimento**, **estudo** e **entrega**. Bolsistas acompanham suas tarefas, atualizam o andamento e enviam entregas, que recebem feedback do coordenador (aprovação ou pedido de ajustes com comentário).

## Problema e diferenciais

Ferramentas como Trello, Notion, Jira, Todoist e Asana são genéricas: não distinguem estudo, desenvolvimento e entrega, não têm feedback formal por entrega e não dão uma visão clara a quem entra no meio do projeto. O LabFlow resolve isso com:

- **Pensado para P&D acadêmico:** abas por tipo de atividade (Desenvolvimento, Estudo, Entregas).
- **Feedback por entrega:** a entrega só é concluída depois da aprovação do coordenador.
- **Visão geral do projeto:** total de atividades, concluídas, pendentes e progresso, útil para quem ingressa depois.
- **Simplicidade:** sem configuração prévia para começar a usar.

## Funcionalidades

São 24 requisitos funcionais (RF01 a RF24) em 4 módulos:

1. **Autenticação e perfis (RF01–RF05):** cadastro, login, logout, controle de acesso por perfil (coordenador ou bolsista) e edição de perfil.
2. **Projetos (RF06–RF11):** CRUD pelo coordenador, vínculo e desvínculo de bolsistas, listagem dos projetos do usuário e visão geral com progresso.
3. **Atividades com abas (RF12–RF20):** CRUD pelo coordenador com responsável e prazo, atualização de status pelo bolsista (a fazer, em andamento, concluída), filtros por status e responsável, cores de atraso e urgência, visão "Hoje / Esta semana" e link de material nas atividades de estudo.
4. **Entrega com feedback (RF21–RF24):** envio de entrega (descrição + link), avaliação pelo coordenador, reenvio após ajustes e histórico de envios e feedbacks.

## Regras de negócio

- **RN01:** só o coordenador cria projetos e atividades e atribui responsáveis.
- **RN02:** o bolsista só vê projetos em que está vinculado e só altera o status das próprias atividades.
- **RN03:** só o coordenador do projeto avalia as entregas dele.
- **RN04:** fluxo da entrega: Pendente → Enviada → Aprovada; ou Enviada → Ajustes solicitados → Reenviada.
- **RN05:** atividade de entrega só vira concluída quando o coordenador aprova.
- **RN06:** atividade é atrasada quando o prazo passa sem estar concluída.
- **RN07:** cada reenvio gera um novo registro de Entrega, preservando o histórico.

## Tecnologias

| Tecnologia | Uso |
| --- | --- |
| Python + Flask | Framework web: rotas e regras da aplicação |
| SQLite + Flask-SQLAlchemy | Banco de dados e mapeamento das tabelas em classes Python |
| Flask-Login | Login, logout e sessão |
| Jinja2 + Bootstrap 5 (CDN) | Páginas HTML e layout responsivo, sem build de front-end |
| Werkzeug | Hash de senha (já vem com o Flask) |

A stack foi simplificada de propósito: apenas três bibliotecas instaladas (Flask, Flask-SQLAlchemy e Flask-Login).

## Estrutura de pastas

```
labflow/
├── app.py            # inicia o app, configura banco e login
├── models.py         # classes Usuario, Projeto, Atividade e Entrega
├── routes.py         # telas e ações
├── services.py       # regras de negócio: fluxo da entrega, progresso, atraso
├── templates/        # páginas HTML (Jinja2)
├── static/           # CSS próprio, se necessário
└── requirements.txt  # dependências
```

## Como executar

Requisito: Python 3.10 ou superior.

```bash
# 1. Clonar o repositório e entrar na pasta
git clone (https://github.com/nickyrzzdev/gerenciador-de-atividades-gp-4)
cd labflow

# 2. Criar e ativar o ambiente virtual
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# 3. Instalar as dependências
pip install -r requirements.txt

# 4. Rodar a aplicação
python app.py
```

Acesse **http://127.0.0.1:5000** no navegador. O banco SQLite e as tabelas são criados automaticamente na primeira execução.

## Modelo de dados

- **Usuario:** nome, e-mail, senha (hash), perfil (coordenador ou bolsista) e data de cadastro.
- **Projeto:** nome, descrição, datas de início e fim, coordenador responsável.
- **Participacao:** vínculo N:N entre Projeto e Usuario (bolsistas do projeto).
- **Atividade:** projeto, título, descrição, tipo (desenvolvimento, estudo ou entrega), status, prazo, responsável, link de material e data de conclusão.
- **Entrega:** atividade, bolsista, descrição, link, data de envio, resultado (pendente, aprovada ou ajustes), comentário de feedback e data de avaliação.

Duas decisões de modelagem: uma única tabela `Atividade` com a coluna `tipo` (as abas são apenas filtros) e o feedback dentro da própria `Entrega`, sem tabela separada.

## Limitações e evoluções futuras

Limitações conhecidas desta versão:

- Sem proteção CSRF nos formulários (Flask-WTF).
- Sem migrações de banco (tabelas criadas com `db.create_all()`).

Fora do escopo desta versão, previstos como evolução:

- Alertas de prazo por e-mail
- Diário de aprendizado
- Ofensiva e gamificação
- Painel do coordenador
- Relatório mensal exportável (CSV/PDF)
- Proteção CSRF com Flask-WTF e migrações com Flask-Migrate
- Testes automatizados com pytest

## Documentação

A documentação completa (personas, benchmarking, requisitos, diagramas de casos de uso e banco de dados) está em `docs/LabFlow_UEA_Documentacao.docx`.

## Autores

- Nicole Kyrstien (Front-End)
- João Miguel (Back-End)
- Gabriel Augusto (Back-End)
- Hanna Barroncas (Back-End)
- João Vitor (Front-End)

Disciplina: Fundamentos de Sistemas de Informação (FSI) · UEA.
# ajuri
