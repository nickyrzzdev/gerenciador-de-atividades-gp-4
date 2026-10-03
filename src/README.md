# LabFlow — Gerenciador de Atividades (API)

Backend Flask do projeto de laboratórios da UEA: projetos, membros, atividades,
agenda pessoal e o fluxo de entrega com avaliação do coordenador.

A API é JSON puro e a autenticação é **por sessão (cookie)**, sem JWT.

---

## Como rodar

```bash
cd src
python -m venv .venv && source .venv/bin/activate   # só na primeira vez
pip install -r requirements.txt

python seed.py --reset        # cria o banco de demonstração do zero
python -m flask --app app run --port 5000
```

- API: <http://127.0.0.1:5000/api>
- **Explorador no navegador: <http://127.0.0.1:5000/dev/api>**
- Sonda de saúde: <http://127.0.0.1:5000/api/saude>

### Contas do seed (senha de todas: `Senha123`)

| Perfil | E-mail |
| --- | --- |
| Coordenadora | `ana.carvalho@uea.edu.br` |
| Coordenador | `joao.silva@uea.edu.br` |
| Bolsistas | `marina.costa@`, `lucas.costa@`, `rafael.freitas@`, `vivian.souza@uea.edu.br` (sufixo `@uea.edu.br`) |

### Testes

```bash
python -m pytest tests -q       # 37 testes
```

### Testar sem navegador

- `api.http`: coleções prontas para **VS Code (REST Client)** e **JetBrains/VS HTTP Client**.
- `curl` com cookie jar:

```bash
curl -c /tmp/marina.jar -H 'Content-Type: application/json' \
  -d '{"email":"marina.costa@uea.edu.br","senha":"Senha123"}' \
  http://127.0.0.1:5000/api/auth/login
curl -b /tmp/marina.jar http://127.0.0.1:5000/api/projetos
```

---

## Organização

```
src/
├── app.py                 # configuração, extensões, blueprint, handlers de erro, /dev/api
├── models.py              # tabelas, enums e serialização básica
├── utils.py               # fuso/hora, validações, erros, paginação, chips derivados
├── seed.py                # dados de demonstração (idempotente)
├── services/              # regras de negócio (nenhuma rota importa models)
│   ├── auth_service.py
│   ├── projeto_service.py
│   ├── membro_service.py
│   ├── atividade_service.py
│   ├── entrega_service.py
│   └── painel_service.py
├── routes/                # só HTTP: ler parâmetros, chamar service, responder
│   ├── auth.py  projetos.py  membros.py  atividades.py  entregas.py
└── tests/                 # pytest
```

Fluxo sempre o mesmo: **Route → Service → Model**. Regras de negócio não vivem em
`routes/`, e nenhum módulo de `services/` depende de `request`.

---

## Endpoints

Todos respondem `{...}` em JSON. Erros seguem sempre:

```json
{ "erro": { "codigo": "nao_encontrado", "mensagem": "Recurso não encontrado" } }
```

Erros de validação trazem `campos`:

```json
{ "erro": { "codigo": "validacao", "mensagem": "Dados inválidos",
            "campos": { "titulo": "O título é obrigatório" } } }
```

### Autenticação

| Método | Rota | Quem | Observações |
| --- | --- | --- | --- |
| POST | `/api/auth/cadastro` | público | `nome`, `email`, `senha`, `confirmar_senha`, `perfil` — cria a conta mas **não** abre sessão |
| POST | `/api/auth/login` | público | falha sempre devolve 401 com a mesma mensagem |
| GET | `/api/auth/me` | logado | dados do usuário da sessão + `instituicao` |
| POST | `/api/auth/logout` | logado | encerra a sessão |
| PUT | `/api/perfil/senha` | logado | exige `senha_atual`, `nova_senha` e `confirmar_nova_senha` |

### Projetos

| Método | Rota | Quem |
| --- | --- | --- |
| GET | `/api/projetos?aba=em_andamento\|concluidos\|todos&q=` | logado (aba inválida → 400) |
| GET | `/api/projetos/resumo` | logado (KPIs) |
| POST | `/api/projetos` | coordenador (devolve o projeto já no formato de detalhe) |
| GET | `/api/projetos/{id}` | participante (alheio → 404) |
| PUT | `/api/projetos/{id}` | coordenador do projeto (projeto concluído não volta para em andamento) |
| POST | `/api/projetos/{id}/encerrar` | coordenador do projeto (corpo `{}`; idempotente) |
| DELETE | `/api/projetos/{id}` | coordenador do projeto (409 com membros ou atividades pendentes) |
| GET | `/api/projetos/{id}/visao-geral?periodo=7\|30\|90` | participante |

### Membros

| Método | Rota | Quem |
| --- | --- | --- |
| GET | `/api/projetos/{id}/membros` | participante |
| GET | `/api/projetos/{id}/membros/opcoes` | participante (`id`, `nome`, `iniciais`; sem e-mail) |
| POST | `/api/projetos/{id}/membros` | coordenador (`{"email": ...}`) |
| DELETE | `/api/projetos/{id}/membros/{usuarioId}` | coordenador (409 se houver pendência) |

### Atividades

| Método | Rota | Quem |
| --- | --- | --- |
| GET | `/api/projetos/{id}/atividades?tipo=&status=&q=&aba=` | participante |
| POST | `/api/projetos/{id}/atividades` | coordenador |
| GET | `/api/atividades/{id}` | participante |
| PUT | `/api/atividades/{id}` | coordenador (não muda status) |
| PATCH | `/api/atividades/{id}/status` | responsável (não serve para entrega) |
| DELETE | `/api/atividades/{id}` | coordenador |
| GET | `/api/atividades/minhas?aba=hoje\|semana\|entregues\|pendentes\|concluidas\|todas` | logado (`entregues` = só entrega aprovada) |

### Entregas

| Método | Rota | Quem |
| --- | --- | --- |
| GET | `/api/atividades/{id}/entregas` | participante |
| POST | `/api/atividades/{id}/entregas` | responsável (`descricao` + `link`) |
| POST | `/api/entregas/{id}/avaliacao` | coordenador (`aprovada` ou `ajustes_solicitados`) |

### URLs de exemplo

`{id}` é o numérico. No explorador, a tabela “IDs úteis” mostra os ids das suas atividades.

```
/api/saude
/api/auth/login
/api/projetos/1
/api/projetos/1/atividades?tipo=entrega&status=pendente
/api/atividades/10
/api/atividades/10/entregas
/api/entregas/9/avaliacao
/api/atividades/minhas?aba=hoje
```

---

## Regras de negócio

| RN | Regra |
| --- | --- |
| RN01 | Só o coordenador cria/edita/exclui projeto e atividade |
| RN02 | Bolsista só altera o status das atividades em que é responsável |
| RN03 | Projeto inacessível responde **404** (não vaza existência) |
| RN04 | Só o coordenador do projeto avalia entregas |
| RN05 | Responsável precisa ser bolsista vinculado ao projeto |
| RN06 | `link_material` só no tipo `estudo` |
| RN07 | Desvincular responde **409** se houver atividade não concluída do bolsista |
| RN08 | Atividade do tipo `entrega` é dirigida pela situação da entrega |
| RN09 | `PATCH /status` em entrega → 422 (`status_controlado`) |
| RN10 | Situação da entrega é derivada do histórico: pendente → enviada → ajustes_solicitados → reenviada → aprovada |
| RN11 | Status só muda por `PATCH /status`; atividade nasce em `a_fazer`; concluir preenche `concluida_em` |
| RN12 | `atrasada` é derivado (prazo vencido e não concluída) — nunca é salvo |
| RN13 | Os chips são derivados: `codigo`, `rotulo`, `tom`, `atrasada`, `vence_em_dias` |
| RN14 | Cadastro exige perfil, confirmação de senha e senha forte |

### Campos derivados (nunca persistidos)

- `status_exibicao`: o chip da atividade — `a_fazer`, `em_andamento`, `vence_0..vence_3`,
  `atrasada`, `concluida` e, para entrega, `pendente`/`enviada`/`ajustes_solicitados`/
  `reenviada`/`aprovada`.
- `progresso`: percentual de atividades concluídas.
- `vence_em_dias`: diferença em dias entre o prazo e hoje (datas locais).
- `acoes_permitidas`: o que o usuário corrente pode fazer com aquela atividade.

> Detalhe de produto: atividade de desenvolvimento/estudo **atrasada** mostra “Atrasada”;
> atividade de entrega atrasada continua com o chip da situação e apenas o marca como
> atrasada — o texto “Atrasada” não substitui “Aprovada”/“Pendente”.

---

## Convenções

**Datas.** Todo `datetime` é naive e representa o fuso `America/Manaus`; `utils.agora()` é a
única função que chama `datetime.now()`. Datas do banco são gravadas no formato
`America/Manaus`. No JSON, saem em ISO 8601 (`2026-10-02T23:59:59`).

**Prazo só com data.** `"2026-12-31"` significa o **fim do dia** (23:59:59), não a meia-noite.

**CSRF.** `POST`, `PUT`, `PATCH` e `DELETE` exigem `Content-Type: application/json` — inclusive
quando não há corpo (ex.: `DELETE /api/projetos/1` com header e corpo vazio). Resposta:
400 `content_type`.

**Paginação.** `?pagina=1&por_pagina=20` (máximo 100). A resposta traz
`itens` e `paginacao: {pagina, por_pagina, total, total_paginas}`. Valores fora do intervalo
são normalizados; texto não numérico vira 400.

**Erros.** `400` requisição/JSON inválido · `401` sem sessão · `403` sem permissão ·
`404` inexistente ou inacessível · `409` conflito de estado · `413` payload grande ·
`415` content-type · `422` validação de regra · `500` erro inesperado (sempre JSON).

---

## Configuração

Variáveis de ambiente (todas opcionais):

| Variável | Padrão | Para quê |
| --- | --- | --- |
| `SECRET_KEY` | valor de desenvolvimento | assinar o cookie de sessão — **troque em produção** |
| `DATABASE_URL` | `sqlite:///src/labflow.db` | trocar o banco |
| `DIAS_URGENCIA` | `3` | janela dos chips “Vence em N dias” |
| `DOMINIO_EMAIL_PERMITIDO` | vazio (aceita qualquer domínio) | restringir cadastro a um domínio, ex.: `uea.edu.br` |

### Migrar para Supabase/PostgreSQL (futuro)

Hoje o alvo é SQLite, com `db.Enum(native_enum=False)` (VARCHAR + CHECK) e
`PRAGMA foreign_keys=ON`. Para PostgreSQL serão necessários: driver (`psycopg`),
`db.Enum` sem `native_enum=False`, e o PRAGMA guardado por tipo de driver.

---

## O explorador (`/dev/api`)

Página estática de desenvolvimento, sem framework, para exercitar a API no navegador:
login com as contas do seed, formulário de método/caminho/corpo, tabela com as 28 rotas
(cada uma com exemplo pronto) e a lista de ids das suas atividades e projetos.

No botão **Usar**, o `{id}` do caminho é substituído pelo id mais recente do tipo
correspondente (`/atividades/…` usa atividade, `/entregas/…` usa entrega,
`/projetos/…` usa projeto, `/membros/…` usa usuário). O caminho e o corpo podem ser
editados antes de enviar.

Rotas de desenvolvimento: `GET /` (redireciona para `/dev/api`) e `GET /dev/api`.
Nenhuma delas altera dados; para removê-las, apague o bloco `explorador_da_api`/`raiz`
em `app.py` e o arquivo `templates/explorador.html`.