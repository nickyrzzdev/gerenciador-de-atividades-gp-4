# Gerenciador de Tarefas Individual

Sistema web para gerenciamento de tarefas pessoais, desenvolvido como parte do projeto de **Gerência de Projetos (GP)**. A aplicação permite que cada usuário tenha suas próprias tarefas, podendo criá-las, editá-las, consultar seus status e excluí-las.

O projeto possui uma interface web responsiva integrada a um back-end desenvolvido em Flask, com autenticação de usuários e persistência dos dados em banco de dados.

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
* Interface responsiva.

## Tecnologias utilizadas

### Back-end

* Python
* Flask
* Flask-SQLAlchemy
* Flask-Login
* SQLAlchemy

### Front-end

* HTML5
* CSS3
* JavaScript

### Testes

* Pytest

### Controle de versão

* Git
* GitHub

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

# Instalação e execução

## Requisitos

É necessário ter instalado:

* Python 3.10 ou superior
* Git
* Um navegador web

Para verificar se o Python está instalado:

### Windows

```powershell
py --version
```

### Linux

```bash
python3 --version
```

---

# Windows

## 1. Clonar o repositório

```powershell
git clone https://github.com/nickyrzzdev/gerenciador-de-atividades-gp-4.git
```

Entre na pasta do projeto:

```powershell
cd gerenciador-de-atividades-gp-4
```

## 2. Criar um ambiente virtual

Na pasta raiz do projeto:

```powershell
py -m venv venv
```

## 3. Ativar o ambiente virtual

No PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a execução de scripts, execute:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Depois tente novamente:

```powershell
.\venv\Scripts\Activate.ps1
```

Quando estiver ativado, deverá aparecer `(venv)` no início da linha do terminal.

## 4. Instalar as dependências

Entre na pasta `src`:

```powershell
cd src
```

Instale as dependências:

```powershell
py -m pip install -r requirements.txt
```

## 5. Executar a aplicação

Ainda dentro da pasta `src`:

```powershell
py app.py
```

O servidor será iniciado em:

```text
http://127.0.0.1:5000
```

Abra esse endereço no navegador.

## 6. Encerrar a aplicação

Para interromper o servidor:

```text
Ctrl + C
```

Para sair do ambiente virtual:

```powershell
deactivate
```

---

# Linux

## 1. Clonar o repositório

Abra o terminal e execute:

```bash
git clone https://github.com/nickyrzzdev/gerenciador-de-atividades-gp-4.git
```

Entre na pasta do projeto:

```bash
cd gerenciador-de-atividades-gp-4
```

## 2. Verificar o Python

```bash
python3 --version
```

Caso o Python não esteja instalado, em distribuições baseadas em Debian/Ubuntu:

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git
```

## 3. Criar um ambiente virtual

Na pasta raiz do projeto:

```bash
python3 -m venv venv
```

## 4. Ativar o ambiente virtual

```bash
source venv/bin/activate
```

Quando estiver ativado, deverá aparecer `(venv)` no início da linha do terminal.

## 5. Instalar as dependências

Entre na pasta `src`:

```bash
cd src
```

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

## 6. Executar a aplicação

Ainda dentro da pasta `src`:

```bash
python app.py
```

O servidor será iniciado em:

```text
http://127.0.0.1:5000
```

Abra esse endereço no navegador.

## 7. Encerrar a aplicação

Para interromper o servidor:

```text
Ctrl + C
```

Para sair do ambiente virtual:

```bash
deactivate
```

---

# Executando os testes

Os testes automatizados ficam dentro de `src/tests`.

Para executar todos os testes, volte para a pasta raiz do projeto:

```bash
cd ..
```

Depois execute:

### Windows

```powershell
py -m pytest -q
```

### Linux

```bash
python3 -m pytest -q
```

### Resultado esperado

Atualmente, o projeto possui **74 testes automatizados aprovados**:

```text
74 passed
```

Os testes verificam os principais comportamentos do sistema, incluindo funcionalidades relacionadas ao gerenciamento das tarefas pessoais.

---

# Fluxo principal da aplicação

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

# Arquitetura

O sistema é organizado separando suas principais responsabilidades:

* **Models:** representam as entidades e o acesso aos dados.
* **Routes:** definem as rotas e endpoints da aplicação.
* **Services:** concentram regras de negócio relacionadas às tarefas pessoais.
* **Templates:** responsáveis pelas páginas HTML.
* **Static:** contém os arquivos CSS e JavaScript.
* **Tests:** contém os testes automatizados.

Essa organização facilita a manutenção, os testes e a evolução do projeto.

# Banco de dados

A aplicação utiliza **SQLAlchemy** para comunicação com o banco de dados.

Entre as principais entidades estão:

* `Usuario`
* `Projeto`
* `Participacao`
* `Atividade`
* `Entrega`
* `TarefaPessoal`

As tarefas pessoais são associadas ao usuário responsável, garantindo que cada usuário trabalhe com suas próprias tarefas.

# Status das tarefas

As tarefas possuem estados que permitem acompanhar seu andamento dentro do sistema.

O status é utilizado pela interface para organizar, filtrar e apresentar as tarefas ao usuário.

# Controle de versão

O projeto utiliza Git para controle de versão e GitHub para hospedagem do código.

As alterações são desenvolvidas em branches e posteriormente integradas à branch principal por meio de Pull Requests.

A implementação do gerenciador de tarefas individual foi integrada à branch `main` através do Pull Request:

**Implementação do gerenciador de tarefas individual — PR #3**

A integração foi realizada após a resolução dos conflitos entre as branches e a execução dos testes automatizados.

# Objetivo do projeto

O objetivo é disponibilizar uma aplicação simples e organizada para que usuários possam administrar suas tarefas pessoais através de uma interface web, permitindo acompanhar o andamento das atividades e organizar suas demandas de forma centralizada.

# Status do projeto

**Concluído — implementação do gerenciador de tarefas individual integrada à `main`.**

# Integrantes do projeto
* Nicole Kyrstien (Front-End)
* Gabriel Amaral (Back-End)
* Hanna Barroncas (Back-End)
* Joao Miguel (Back-End)
* Joao Vitor (Back-End)
lallalal
