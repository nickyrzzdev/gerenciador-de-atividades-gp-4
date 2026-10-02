# gerenciador-de-atividades-gp-4
# Gerenciador de Atividades

Aplicação web para organizar tarefas do dia a dia, desenvolvida em **Python com Flask**. Permite adicionar, concluir e excluir atividades de forma simples.

Projeto em grupo desenvolvido na disciplina do curso de Sistemas de Informação da Universidade do Estado do Amazonas (UEA).

## Funcionalidades

- Listar todas as atividades cadastradas
- Adicionar uma nova atividade (com validação do título)
- Marcar uma atividade como concluída
- Excluir uma atividade

## Tecnologias utilizadas

- Python 3
- Flask
- HTML e CSS
- Banco de dados
- Figma (diagramas)

## Como executar o projeto

1. Clone o repositório:

```bash
git clone https://github.com/nickyrzzdev/gerenciador-de-atividades-go-4.git
cd gerenciador-de-atividades-gp-4
```

2. Instale o Flask:

```bash
pip install flask
```

3. Execute a aplicação:

```bash
python app.py
```

4. Abra no navegador:

```
http://127.0.0.1:5000
```

## Estrutura do projeto

```
projeto/
├── app.py            # Rotas e lógica da aplicação (Flask)
├── templates/        # Páginas HTML
│   └── index.html
├── static/           # Arquivos CSS
└── README.md
```

## Módulos da aplicação

| Módulo | O que faz |
|--------|-----------|
| Listagem | Exibe todas as atividades na página inicial |
| Cadastro | Recebe o título, valida e salva a nova atividade |
| Conclusão | Marca uma atividade como feita |
| Exclusão | Remove uma atividade da lista |

## Documentação

Os diagramas foram desenhados no Figma:

- Diagrama de atividades: [adicionar link]
- Diagrama de fluxo de telas: [adicionar link]
- Diagrama de casos de uso: [adicionar link]
- Apresentação do projeto: [adicionar link]

## Equipe

| Integrante | Responsabilidades |
|------------|-------------------|
| Nicole | Diagrama de atividades, back-end (Flask) |
| Gabriel | Diagrama de atividades, back-end (Flask) |
| Hanna | Diagrama de fluxo de telas, front-end (HTML e CSS) |
| João Miguel | Diagrama de casos de uso, banco de dados |
| João Vitor | Apresentação (slides), front-end (HTML e CSS) |
