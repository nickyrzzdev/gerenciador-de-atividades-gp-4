"""Utilitários transversais: fuso/hora, enums, erros, HTTP, validação e exibição.

Vive aqui tudo que não depende de SQLAlchemy para que `models.py` possa
importar este módulo sem ciclo de import.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from enum import StrEnum
from functools import wraps
from typing import Any, Callable, Iterable, Sequence
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from flask import jsonify, request
from flask_login import current_user

FUSO = ZoneInfo("America/Manaus")

POR_PAGINA_PADRAO = 6
MAX_POR_PAGINA = 50

LIMITE_NOME = 120
LIMITE_TITULO = 150
LIMITE_DESCRICAO = 4000
LIMITE_LINK = 500
LIMITE_COMENTARIO = 2000
LIMITE_CAMPO_CURTO = 200

FIM_DO_DIA = time(23, 59, 59)


# --------------------------------------------------------------------------- #
# Enums de dominio
# --------------------------------------------------------------------------- #


class Perfil(StrEnum):
    COORDENADOR = "coordenador"
    BOLISTA = "bolsista"
    INDIVIDUAL = "individual"


class ProjetoStatus(StrEnum):
    PLANEJADO = "planejado"
    EM_ANDAMENTO = "em_andamento"
    REVISAO = "revisao"
    CONCLUIDO = "concluido"


class AtividadeTipo(StrEnum):
    DESENVOLVIMENTO = "desenvolvimento"
    ESTUDO = "estudo"
    ENTREGA = "entrega"


class AtividadeStatus(StrEnum):
    A_FAZER = "a_fazer"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"


class EntregaResultado(StrEnum):
    AGUARDANDO_AVALIACAO = "aguardando_avaliacao"
    APROVADA = "aprovada"
    AJUSTES_SOLICITADOS = "ajustes_solicitados"


class SituacaoEntrega(StrEnum):
    PENDENTE = "pendente"
    ENVIADA = "enviada"
    AJUSTES_SOLICITADOS = "ajustes_solicitados"
    REENVIADA = "reenviada"
    APROVADA = "aprovada"


class Acao(StrEnum):
    CONCLUIR = "concluir"
    REABRIR = "reabrir"
    ENVIAR_ENTREGA = "enviar_entrega"
    VER_HISTORICO = "ver_historico"
    AVALIAR = "avaliar"
    EDITAR = "editar"
    EXCLUIR = "excluir"


ROTULO_PROJETO_STATUS: dict[str, tuple[str, str]] = {
    ProjetoStatus.PLANEJADO: ("Planejado", "neutro"),
    ProjetoStatus.EM_ANDAMENTO: ("Em andamento", "info"),
    ProjetoStatus.REVISAO: ("Em revisão", "alerta"),
    ProjetoStatus.CONCLUIDO: ("Concluído", "sucesso"),
}

ROTULO_ATIVIDADE_STATUS: dict[str, tuple[str, str]] = {
    AtividadeStatus.A_FAZER: ("A fazer", "alerta"),
    AtividadeStatus.EM_ANDAMENTO: ("Em andamento", "info"),
    AtividadeStatus.CONCLUIDA: ("Concluída", "sucesso"),
}

ROTULO_SITUACAO: dict[str, tuple[str, str]] = {
    SituacaoEntrega.PENDENTE: ("Pendente", "neutro"),
    SituacaoEntrega.ENVIADA: ("Enviada", "info"),
    SituacaoEntrega.AJUSTES_SOLICITADOS: ("Ajustes solicitados", "alerta"),
    SituacaoEntrega.REENVIADA: ("Reenviada", "destaque"),
    SituacaoEntrega.APROVADA: ("Aprovada", "sucesso"),
}


# --------------------------------------------------------------------------- #
# Tempo
# --------------------------------------------------------------------------- #


def agora() -> datetime:
    """Instante atual em America/Manaus, como datetime naive."""
    return datetime.now(FUSO).replace(tzinfo=None)


def fim_do_dia(dia: date) -> datetime:
    return datetime.combine(dia, FIM_DO_DIA)


def fim_da_semana(referencia: date | None = None) -> datetime:
    """Domingo da semana corrente (segunda a domingo) às 23:59:59."""
    base = referencia or agora().date()
    return fim_do_dia(base + timedelta(days=6 - base.weekday()))


# --------------------------------------------------------------------------- #
# Erros e respostas
# --------------------------------------------------------------------------- #


class ErroDeNegocio(Exception):
    """Erro de regra de negócio, serializado pelo handler global."""

    def __init__(
        self,
        codigo: str,
        mensagem: str,
        status: int = 422,
        campos: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.status = status
        self.campos: dict[str, Any] = campos or {}

    def para_dict(self) -> dict[str, Any]:
        erro: dict[str, Any] = {"codigo": self.codigo, "mensagem": self.mensagem}
        if self.campos:
            erro["campos"] = self.campos
        return erro

    def para_resposta(self):
        return jsonify({"erro": self.para_dict()}), self.status


def erro_validacao(campos: dict[str, Any], mensagem: str = "Dados inválidos") -> ErroDeNegocio:
    return ErroDeNegocio("validacao", mensagem, 422, campos)


def erro_nao_encontrado(mensagem: str = "Recurso não encontrado") -> ErroDeNegocio:
    return ErroDeNegocio("nao_encontrado", mensagem, 404)


def erro_sem_permissao(mensagem: str = "Você não tem permissão para esta ação") -> ErroDeNegocio:
    return ErroDeNegocio("sem_permissao", mensagem, 403)


def erro_conflito(mensagem: str, campos: dict[str, Any] | None = None) -> ErroDeNegocio:
    return ErroDeNegocio("conflito_estado", mensagem, 409, campos)


def resposta(payload: dict[str, Any], status: int = 200, mensagem: str | None = None):
    corpo = dict(payload)
    if mensagem:
        corpo["mensagem"] = mensagem
    return jsonify(corpo), status


def iso(valor: date | datetime | None) -> str | None:
    return valor.isoformat() if valor is not None else None


# --------------------------------------------------------------------------- #
# Leitura da requisição
# --------------------------------------------------------------------------- #


def corpo_json() -> dict[str, Any]:
    """Corpo da requisição como dict; 400 se não for um JSON de objeto."""
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        raise ErroDeNegocio(
            "json_invalido",
            "Envie um corpo no formato JSON válido",
            400,
        )
    return dados


def pagina_atual() -> tuple[int, int]:
    return _inteiro("pagina", 1, minimo=1), _inteiro(
        "por_pagina", POR_PAGINA_PADRAO, minimo=1, maximo=MAX_POR_PAGINA
    )


def _inteiro(nome: str, padrao: int, minimo: int = 1, maximo: int | None = None) -> int:
    bruto = request.args.get(nome)
    if bruto is None or bruto == "":
        return padrao
    try:
        valor = int(bruto)
    except (TypeError, ValueError):
        raise ErroDeNegocio(
            "parametro_invalido", f"O parâmetro '{nome}' deve ser um número", 400
        ) from None
    if valor < minimo:
        valor = minimo
    if maximo is not None and valor > maximo:
        valor = maximo
    return valor


def montar_paginacao(paginacao, itens: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "itens": itens,
        "paginacao": {
            "pagina": paginacao.page,
            "por_pagina": paginacao.per_page,
            "total": paginacao.total,
            "total_paginas": paginacao.pages,
        },
    }


def periodo_dias(validos: Sequence[int], padrao: int) -> int:
    bruto = request.args.get("periodo")
    if not bruto:
        return padrao
    try:
        valor = int(bruto)
    except ValueError:
        raise ErroDeNegocio(
            "parametro_invalido",
            f"'periodo' deve ser um destes valores: {', '.join(str(v) for v in validos)}",
            400,
        ) from None
    if valor not in validos:
        raise ErroDeNegocio(
            "parametro_invalido",
            f"'periodo' deve ser um destes valores: {', '.join(str(v) for v in validos)}",
            400,
        )
    return valor


# --------------------------------------------------------------------------- #
# Autenticação e perfil
# --------------------------------------------------------------------------- #


def login_obrigatorio(view: Callable) -> Callable:
    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any):
        if not current_user.is_authenticated:
            raise ErroDeNegocio(
                "nao_autenticado", "Faça login para continuar", 401
            )
        return view(*args, **kwargs)

    return wrapper


def perfil_obrigatorio(*perfis: Perfil) -> Callable:
    """Exige um dos perfis informados (403 caso contrário)."""

    def decorador(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any):
            if current_user.perfil not in perfis:
                raise erro_sem_permissao(
                    "Esta ação é exclusiva de "
                    + " e ".join(p.value for p in perfis)
                )
            return view(*args, **kwargs)

        return wrapper

    return decorador


def eh_coordenador(usuario) -> bool:
    return usuario.perfil == Perfil.COORDENADOR


# --------------------------------------------------------------------------- #
# Formatação
# --------------------------------------------------------------------------- #


def iniciais(nome: str) -> str:
    partes = [p for p in nome.replace("\n", " ").split() if p]
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[-1][0]).upper()


def porcentagem(parte: int, total: int) -> int:
    if not total:
        return 0
    return int(round(parte * 100 / total))


def _texto(valor: Any) -> str:
    return "" if valor is None else str(valor).strip()


def email_normalizado(valor: Any) -> str:
    return _texto(valor).lower()


def eh_url_http(valor: str) -> bool:
    try:
        partes = urlparse(valor)
    except ValueError:
        return False
    return partes.scheme in {"http", "https"} and bool(partes.netloc)


# --------------------------------------------------------------------------- #
# Validadores puros (retornam dict {campo: mensagem})
# --------------------------------------------------------------------------- #


def problema_senha(senha: str) -> str | None:
    if not senha or len(senha) < 8:
        return "A senha deve ter no mínimo 8 caracteres"
    if not any(c.isupper() for c in senha):
        return "A senha deve conter pelo menos 1 letra maiúscula"
    if not any(c.isdigit() for c in senha):
        return "A senha deve conter pelo menos 1 número"
    return None


def validar_texto(
    valor: Any,
    campo: str,
    erros: dict[str, Any],
    *,
    obrigatorio: bool = False,
    mensagem_obrigatorio: str = "",
    maximo: int | None = None,
    mensagem_maximo: str = "",
) -> str:
    limpo = _texto(valor)
    if not limpo:
        if obrigatorio:
            erros[campo] = mensagem_obrigatorio
        return ""
    if maximo is not None and len(limpo) > maximo:
        erros[campo] = mensagem_maximo
        return limpo[:maximo]
    return limpo


def _data(valor: Any, campo: str, erros: dict[str, Any], *, obrigatorio: bool) -> date | None:
    bruto = _texto(valor)
    if not bruto:
        if obrigatorio:
            erros[campo] = "Informe a data"
        return None
    try:
        return date.fromisoformat(bruto[:10])
    except ValueError:
        erros[campo] = "Informe uma data válida"
        return None


def _prazo(valor: Any, campo: str, erros: dict[str, Any], *, obrigatorio: bool) -> datetime | None:
    """Aceita 'YYYY-MM-DD' (-> 23:59), 'YYYY-MM-DDTHH:MM' ou 'DD/MM/AAAA'."""
    bruto = _texto(valor)
    if not bruto:
        if obrigatorio:
            erros[campo] = "Informe o prazo"
        return None
    formatos = ("%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M")
    for formato in formatos:
        try:
            return datetime.strptime(bruto, formato)
        except ValueError:
            continue
    try:
        instante = datetime.fromisoformat(bruto.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        erros[campo] = "Informe um prazo válido"
        return None
    # Data pura ("2026-10-02") significa o fim do dia, não a meia-noite.
    if len(bruto) == 10:
        return instante.replace(hour=23, minute=59, second=59, microsecond=0)
    return instante


def instante_de_filtro(valor: str, campo: str) -> datetime:
    """Converte um filtro de data da query string; 400 se não for data válida."""
    erros: dict[str, Any] = {}
    instante = _prazo(valor, campo, erros, obrigatorio=True)
    if erros or instante is None:
        raise ErroDeNegocio(
            "parametro_invalido", erros.get(campo, f"Informe um prazo válido para '{campo}'"), 400
        )
    return instante


def validar_cadastro(dados: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    erros: dict[str, Any] = {}
    nome = validar_texto(
        dados.get("nome"),
        "nome",
        erros,
        obrigatorio=True,
        mensagem_obrigatorio="O nome é obrigatório",
        maximo=LIMITE_NOME,
        mensagem_maximo=f"O nome deve ter no máximo {LIMITE_NOME} caracteres",
    )
    email = email_normalizado(dados.get("email"))
    if not email:
        erros["email"] = "O e-mail é obrigatório"
    elif "@" not in email or email.startswith("@") or email.endswith("@"):
        erros["email"] = "Informe um e-mail válido"

    senha = str(dados.get("senha") or "")
    problema = problema_senha(senha)
    if problema:
        erros["senha"] = problema
    if str(dados.get("confirmar_senha") or "") != senha:
        erros["confirmar_senha"] = "As senhas não conferem"

    perfil = _texto(dados.get("perfil"))
    if perfil not in list(Perfil):
        erros["perfil"] = "Escolha um perfil: coordenador, bolsista ou individual"

    return {"nome": nome, "email": email, "senha": senha, "perfil": perfil}, erros


def validar_troca_senha(dados: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    erros: dict[str, Any] = {}
    senha_atual = str(dados.get("senha_atual") or "")
    if not senha_atual:
        erros["senha_atual"] = "Informe a senha atual"
    nova = str(dados.get("nova_senha") or "")
    problema = problema_senha(nova)
    if problema:
        erros["nova_senha"] = problema
    if nova and str(dados.get("confirmar_nova_senha") or "") != nova:
        erros["confirmar_nova_senha"] = "As senhas não conferem"
    return {"senha_atual": senha_atual, "nova_senha": nova}, erros


def validar_projeto(
    dados: dict[str, Any], parcial: bool = False
) -> tuple[dict[str, Any], dict[str, Any]]:
    erros: dict[str, Any] = {}
    obrigatorio = not parcial
    validos: dict[str, Any] = {}
    if "nome" in dados or obrigatorio:
        validos["nome"] = validar_texto(
            dados.get("nome"),
            "nome",
            erros,
            obrigatorio=obrigatorio,
            mensagem_obrigatorio="O nome é obrigatório",
            maximo=LIMITE_TITULO,
            mensagem_maximo=f"O nome deve ter no máximo {LIMITE_TITULO} caracteres",
        )
    if "descricao" in dados or obrigatorio:
        validos["descricao"] = validar_texto(
            dados.get("descricao"),
            "descricao",
            erros,
            obrigatorio=obrigatorio,
            mensagem_obrigatorio="A descrição é obrigatória",
            maximo=LIMITE_DESCRICAO,
            mensagem_maximo=f"A descrição deve ter no máximo {LIMITE_DESCRICAO} caracteres",
        )
    if "data_inicio" in dados or obrigatorio:
        validos["data_inicio"] = _data(dados.get("data_inicio"), "data_inicio", erros, obrigatorio=obrigatorio)
    if "data_fim" in dados or obrigatorio:
        validos["data_fim"] = _data(dados.get("data_fim"), "data_fim", erros, obrigatorio=obrigatorio)
    if "status" in dados:
        status = _texto(dados.get("status"))
        if status not in list(ProjetoStatus):
            erros["status"] = "Status inválido"
        else:
            validos["status"] = status
    return validos, erros


def validar_atividade(
    dados: dict[str, Any], parcial: bool = False
) -> tuple[dict[str, Any], dict[str, Any]]:
    erros: dict[str, Any] = {}
    obrigatorio = not parcial
    validos: dict[str, Any] = {}

    if "titulo" in dados or obrigatorio:
        validos["titulo"] = validar_texto(
            dados.get("titulo"),
            "titulo",
            erros,
            obrigatorio=True,
            mensagem_obrigatorio="O título é obrigatório",
            maximo=LIMITE_TITULO,
            mensagem_maximo=f"O título deve ter no máximo {LIMITE_TITULO} caracteres",
        )
    if "descricao" in dados:
        validos["descricao"] = validar_texto(
            dados.get("descricao"),
            "descricao",
            erros,
            maximo=LIMITE_DESCRICAO,
            mensagem_maximo=f"A descrição deve ter no máximo {LIMITE_DESCRICAO} caracteres",
        )
    if "tipo" in dados or obrigatorio:
        tipo = _texto(dados.get("tipo"))
        if tipo not in list(AtividadeTipo):
            erros["tipo"] = "Escolha o tipo: desenvolvimento, estudo ou entrega"
        else:
            validos["tipo"] = tipo
    if "prazo" in dados or obrigatorio:
        validos["prazo"] = _prazo(dados.get("prazo"), "prazo", erros, obrigatorio=obrigatorio)
    if "responsavel_id" in dados or obrigatorio:
        try:
            validos["responsavel_id"] = int(dados.get("responsavel_id"))
        except (TypeError, ValueError):
            erros["responsavel_id"] = "Selecione o responsável"
    if "link_material" in dados:
        link = _texto(dados.get("link_material"))
        if link and not eh_url_http(link):
            erros["link_material"] = "Informe uma URL válida começando em http:// ou https://"
        validos["link_material"] = link or None
    return validos, erros


def validar_tarefa_pessoal(
    dados: dict[str, Any], parcial: bool = False
) -> tuple[dict[str, Any], dict[str, Any]]:
    erros: dict[str, Any] = {}
    obrigatorio = not parcial
    validos: dict[str, Any] = {}

    if "titulo" in dados or obrigatorio:
        validos["titulo"] = validar_texto(
            dados.get("titulo"),
            "titulo",
            erros,
            obrigatorio=True,
            mensagem_obrigatorio="O título é obrigatório",
            maximo=LIMITE_TITULO,
            mensagem_maximo=f"O título deve ter no máximo {LIMITE_TITULO} caracteres",
        )
    if "descricao" in dados:
        validos["descricao"] = validar_texto(
            dados.get("descricao"),
            "descricao",
            erros,
            maximo=LIMITE_DESCRICAO,
            mensagem_maximo=f"A descrição deve ter no máximo {LIMITE_DESCRICAO} caracteres",
        ) or None
    if "prazo" in dados or obrigatorio:
        validos["prazo"] = _prazo(
            dados.get("prazo"), "prazo", erros, obrigatorio=False
        )
    return validos, erros


def validar_entrega(dados: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    erros: dict[str, Any] = {}
    descricao = validar_texto(
        dados.get("descricao"),
        "descricao",
        erros,
        obrigatorio=True,
        mensagem_obrigatorio="Descreva o que você entregou",
        maximo=LIMITE_DESCRICAO,
        mensagem_maximo=f"A descrição deve ter no máximo {LIMITE_DESCRICAO} caracteres",
    )
    link = _texto(dados.get("link"))
    if not link:
        erros["link"] = "Informe o link da entrega"
    elif not eh_url_http(link):
        erros["link"] = "Informe uma URL válida começando em http:// ou https://"
    return {"descricao": descricao, "link": link}, erros


def validar_avaliacao(dados: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    erros: dict[str, Any] = {}
    resultado = _texto(dados.get("resultado"))
    if resultado not in {EntregaResultado.APROVADA, EntregaResultado.AJUSTES_SOLICITADOS}:
        erros["resultado"] = "Informe 'aprovada' ou 'ajustes_solicitados'"
    comentario = validar_texto(
        dados.get("comentario"),
        "comentario",
        erros,
        maximo=LIMITE_COMENTARIO,
        mensagem_maximo=f"O comentario deve ter no máximo {LIMITE_COMENTARIO} caracteres",
    )
    if resultado == EntregaResultado.AJUSTES_SOLICITADOS and not comentario:
        erros["comentario"] = "Explique os ajustes necessários para o bolsista"
    return {"resultado": resultado, "comentario": comentario or None}, erros


def validar_status(dados: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    erros: dict[str, Any] = {}
    status = _texto(dados.get("status"))
    if status not in list(AtividadeStatus):
        erros["status"] = "Status inválido"
    return status, erros


# --------------------------------------------------------------------------- #
# Estados derivados (RN10, RN12 e seção 7) — funções puras
# --------------------------------------------------------------------------- #


def calcular_atrasada(prazo: datetime | None, concluida: bool, referencia: datetime | None = None) -> bool:
    if prazo is None or concluida:
        return False
    return prazo < (referencia or agora())


def dias_para_prazo(prazo: datetime | None, referencia: datetime | None = None) -> int | None:
    if prazo is None:
        return None
    return (prazo.date() - (referencia or agora()).date()).days


def situacao_da_entrega(entregas: Iterable[Any]) -> SituacaoEntrega:
    """RN10: situação da atividade a partir do histórico de envios."""
    ordered = sorted(entregas, key=lambda e: e.numero)
    if not ordered:
        return SituacaoEntrega.PENDENTE
    ultima = ordered[-1]
    if ultima.resultado == EntregaResultado.APROVADA:
        return SituacaoEntrega.APROVADA
    if ultima.resultado == EntregaResultado.AJUSTES_SOLICITADOS:
        return SituacaoEntrega.AJUSTES_SOLICITADOS
    return SituacaoEntrega.ENVIADA if ultima.numero == 1 else SituacaoEntrega.REENVIADA


def situacao_exibicao(situacao: SituacaoEntrega | str) -> dict[str, str]:
    codigo = SituacaoEntrega(situacao).value
    rotulo, tom = ROTULO_SITUACAO[codigo]
    return {"codigo": codigo, "rotulo": rotulo, "tom": tom}


def status_exibicao_atividade(
    *,
    tipo: str,
    status: str,
    prazo: datetime | None,
    situacao: SituacaoEntrega | None = None,
    dias_urgencia: int = 3,
    referencia: datetime | None = None,
) -> dict[str, Any]:
    """Fonte única dos chips (seção 7). Nunca grava estado."""
    ref = referencia or agora()
    atrasada = calcular_atrasada(prazo, status == AtividadeStatus.CONCLUIDA, ref)
    restante = dias_para_prazo(prazo, ref)

    if tipo == AtividadeTipo.ENTREGA:
        chip = situacao_exibicao(situacao or SituacaoEntrega.PENDENTE)
        chip["atrasada"] = atrasada
        chip["vence_em_dias"] = restante
        return chip

    if status == AtividadeStatus.CONCLUIDA:
        codigo, rotulo, tom = "concluida", "Concluída", "sucesso"
    elif atrasada:
        codigo, rotulo, tom = "atrasada", "Atrasada", "perigo"
    elif restante is not None and 0 <= restante <= dias_urgencia:
        codigo = f"vence_{restante}"
        rotulo = "Vence hoje" if restante == 0 else f"Vence em {restante} dia{'s' if restante > 1 else ''}"
        tom = "alerta"
    else:
        rotulo, tom = ROTULO_ATIVIDADE_STATUS[status]
        codigo = status

    return {
        "codigo": codigo,
        "rotulo": rotulo,
        "tom": tom,
        "atrasada": atrasada,
        "vence_em_dias": restante,
    }


def acoes_permitidas(
    *,
    tipo: str,
    status: str,
    situacao: SituacaoEntrega,
    total_envios: int,
    aguardando_avaliacao: bool,
    eh_coordenador: bool,
    eh_responsavel: bool,
) -> list[str]:
    """Botões que o usuário corrente pode usar nesta atividade."""
    acoes: list[str] = []
    if eh_coordenador:
        acoes.append(Acao.EDITAR.value)
        acoes.append(Acao.EXCLUIR.value)
    if total_envios > 0:
        acoes.append(Acao.VER_HISTORICO.value)
    if eh_coordenador and tipo == AtividadeTipo.ENTREGA and aguardando_avaliacao:
        acoes.append(Acao.AVALIAR.value)
    if eh_responsavel:
        if tipo != AtividadeTipo.ENTREGA:
            acoes.append(
                Acao.REABRIR.value
                if status == AtividadeStatus.CONCLUIDA
                else Acao.CONCLUIR.value
            )
        elif situacao in {SituacaoEntrega.PENDENTE, SituacaoEntrega.AJUSTES_SOLICITADOS}:
            acoes.append(Acao.ENVIAR_ENTREGA.value)
    return acoes