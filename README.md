# Gerenciador de Tarefas Individual

Sistema web para gerenciamento de tarefas pessoais, desenvolvido como parte do projeto de **Gerência de Projetos (GP)**. A aplicação permite que cada usuário tenha suas próprias tarefas, podendo criá-las, editá-las, consultar seus status e excluí-las.

O projeto possui uma interface web responsiva integrada a uma API desenvolvida em Flask, com autenticação de usuários e persistência dos dados em banco de dados.

## Funcionalidades

### Usuários

* Cadastro de novos usuários.
* Login e logout.
* Autenticação e controle de sessão.
* Proteção das tarefas por usuário.

### Tarefas pessoais

* Criar tarefas.
* Visualizar tarefas cadastradas.
* Editar tarefas.
* Excluir tarefas.
* Alterar o status das tarefas.
* Definir título, descrição e prazo.
* Registrar a data de criação.
* Registrar a conclusão da tarefa.

### Organização

* Busca por tarefas.
* Filtros por status.
* Paginação.
* Indicadores e estatísticas das tarefas.
* Interface responsiva para diferentes tamanhos de tela.

## Tecnologias utilizadas

### Back-end

* **Python**
* **Flask**
* **Flask-SQLAlchemy**
* **Flask-Login**
* **SQLAlchemy**

### Front-end

* **HTML5**
* **CSS3**
* **JavaScript**

### Testes

* **Pytest**

### Controle de versão

* **Git**
* **GitHub**

## Estrutura do projeto

```text
gerenciador-de-atividades-gp-4/
│
├── src/
│   ├── app.py
│   ├── models.py
│   ├── utils.py
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   └── tarefas.py
│   │
│   ├── services/
│   │   └── tarefa_pessoal_service.py
│   │
│   ├── templates/
│   │   ├── base_auth.html
│   │   ├── cadastro.html
│   │   ├── index.html
│   │   └── login.html
│   │
│   ├── static/
│   │   ├── css/
│   │   │   └── app.css
│   │   └── js/
│   │       ├── api.js
│   │       ├── auth.js
│   │       └── tarefas.js
│   │
│   ├── migrations/
│   │   ├── __init__.py
│   │   └── add_individual_profile.py
│   │
│   ├── tests/
│   │   └── test_tarefas_pessoais.py
│   │
│   └── requirements.txt
│
├── README.md
└── .gitignore
```

## Como executar o projeto

### Requisitos

É necessário ter instalado:

* Python 3
* Git

### 1. Clonar o repositório

```bash
git clone https://github.com/nickyrzzdev/gerenciador-de-atividades-gp-4.git
```

Entre na pasta do projeto:

```bash
cd gerenciador-de-atividades-gp-4
```

### 2. Instalar as dependências

Entre na pasta `src`:

```bash
cd src
```

Instale as dependências:

```bash
py -m pip install -r requirements.txt
```

### 3. Executar a aplicação

Ainda dentro da pasta `src`, execute:

```bash
py app.py
```

O Flask iniciará o servidor local.

A aplicação ficará disponível em:

```text
http://127.0.0.1:5000
```

Abra esse endereço em um navegador para acessar o sistema.

### 4. Encerrar a aplicação

Para interromper o servidor, pressione:

```text
Ctrl + C
```

## Executando os testes

Os testes automatizados podem ser executados a partir da pasta raiz do projeto com:

```bash
py -m pytest -q
```

### Resultado atual

O projeto possui **74 testes automatizados**, atualmente aprovados:

```text
74 passed
```

Os testes abrangem os principais comportamentos do sistema, incluindo funcionalidades relacionadas ao gerenciamento das tarefas pessoais.

## Fluxo principal da aplicação

```text
Cadastro
   ↓
Login
   ↓
Tela principal
   ↓
Gerenciamento de tarefas
   ├── Criar tarefa
   ├── Visualizar tarefa
   ├── Editar tarefa
   ├── Alterar status
   └── Excluir tarefa
```

## Arquitetura

O sistema é organizado separando as principais responsabilidades da aplicação:

* **Models:** representam as entidades e o acesso aos dados.
* **Routes:** definem as rotas e endpoints da aplicação.
* **Services:** concentram regras de negócio relacionadas às tarefas pessoais.
* **Templates:** responsáveis pelas páginas HTML.
* **Static:** contém arquivos CSS e JavaScript.
* **Tests:** contém os testes automatizados.

Essa organização facilita a manutenção e a evolução do projeto.

## Banco de dados

A aplicação utiliza **SQLAlchemy** para comunicação com o banco de dados.

Entre as principais entidades estão:

* `Usuario`
* `Projeto`
* `Participacao`
* `Atividade`
* `Entrega`
* `TarefaPessoal`

As tarefas pessoais são associadas ao usuário responsável, garantindo que cada usuário trabalhe com suas próprias tarefas.

## Status das tarefas

As tarefas podem possuir diferentes estados, permitindo acompanhar seu andamento dentro do sistema.

O status é utilizado pela interface para organizar, filtrar e apresentar as tarefas ao usuário.

## Controle de versão

O projeto utiliza Git para controle de versão e GitHub para hospedagem do repositório.

As alterações são desenvolvidas em branches e posteriormente integradas à branch principal por meio de Pull Requests.

A implementação do gerenciador de tarefas individual foi integrada à branch `main` através do Pull Request:

**Implementação do gerenciador de tarefas individual — PR #3**

A integração foi realizada após a resolução dos conflitos entre as branches e a execução dos testes automatizados.

## Objetivo do projeto

O objetivo é disponibilizar uma aplicação simples e organizada para que usuários possam administrar suas tarefas pessoais através de uma interface web, permitindo acompanhar o andamento das atividades e organizar suas demandas de forma centralizada.

## Status do projeto

**Concluído — implementação do gerenciador de tarefas individual integrada à `main`.**
