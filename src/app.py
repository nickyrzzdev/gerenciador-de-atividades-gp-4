"""Ponto de entrada: configuração, extensões, blueprint e tratamento de erros."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request
from flask_login import LoginManager, current_user
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.exceptions import HTTPException, MethodNotAllowed, NotFound

from models import Usuario, db
from routes import api
from utils import ErroDeNegocio

BASE_DIR = Path(__file__).resolve().parent
METODOS_ALTERANTES = {"POST", "PUT", "PATCH", "DELETE"}

ERROS_HTTP: dict[int, tuple[str, str]] = {
    400: ("json_invalido", "Requisição inválida"),
    401: ("nao_autenticado", "Faça login para continuar"),
    403: ("sem_permissao", "Você não tem permissão para esta ação"),
    404: ("nao_encontrado", "Recurso não encontrado"),
    405: ("metodo_nao_permitido", "Método não permitido para este recurso"),
    413: ("payload_grande", "Conteúdo enviado é muito grande"),
    415: ("content_type", "Use 'Content-Type: application/json'"),
}

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-labflow-troque-em-producao"),
    SQLALCHEMY_DATABASE_URI=os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'labflow.db'}"
    ),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    DIAS_URGENCIA=int(os.environ.get("DIAS_URGENCIA", "3")),
    DOMINIO_EMAIL_PERMITIDO=os.environ.get("DOMINIO_EMAIL_PERMITIDO", "").strip().lower(),
)

db.init_app(app)

login_manager = LoginManager()
login_manager.session_protection = "basic"
login_manager.init_app(app)


@event.listens_for(Engine, "connect")
def _ativar_chaves_estrangeiras(dbapi_connection, connection_record) -> None:
    """O SQLite ignora FKs por padrão; sem isso o cascade do banco não existe."""
    dbapi_connection.execute("PRAGMA foreign_keys=ON")


@login_manager.unauthorized_handler
def _nao_autenticado():
    return jsonify({"erro": {"codigo": "nao_autenticado", "mensagem": "Faça login para continuar"}}), 401


@login_manager.user_loader
def _carregar_usuario(usuario_id: str) -> Usuario | None:
    """Restaura o usuário da sessão a cada requisição."""
    return db.session.get(Usuario, int(usuario_id))


def _metodo_aceito_pelo_caminho() -> bool:
    """O caminho existe para este método? (se não, quem responde é o 405)"""
    adaptador = app.url_map.bind_to_environ(request.environ)
    try:
        adaptador.match(request.path, request.method)
    except MethodNotAllowed:
        return False
    except NotFound:
        return False
    return True


@app.before_request
def _exigir_json_em_alteracoes():
    """Mitigação de CSRF: rotas que alteram dados só aceitam JSON."""
    if request.method not in METODOS_ALTERANTES or request.is_json:
        return None
    if not _metodo_aceito_pelo_caminho():
        return None
    raise ErroDeNegocio(
        "content_type",
        "Use 'Content-Type: application/json' nesta requisição",
        400,
    )


@app.errorhandler(ErroDeNegocio)
def _erro_de_negocio(erro: ErroDeNegocio):
    db.session.rollback()
    return jsonify({"erro": erro.para_dict()}), erro.status


@app.errorhandler(HTTPException)
def _erro_http(erro: HTTPException):
    db.session.rollback()
    codigo, mensagem = ERROS_HTTP.get(erro.code or 500, ("erro", "Erro na requisição"))
    resposta = jsonify({"erro": {"codigo": codigo, "mensagem": mensagem}})
    resposta.status_code = erro.code or 500

    for cabecalho in erro.get_headers():
        if cabecalho[0].lower() == "allow":
            resposta.headers["Allow"] = cabecalho[1]

    return resposta


@app.errorhandler(Exception)
def _erro_interno(erro: Exception):
    db.session.rollback()
    app.logger.exception("Erro não tratado: %s", erro)
    return jsonify({
        "erro": {
            "codigo": "erro_interno",
            "mensagem": "Erro interno do servidor"
        }
    }), 500


app.register_blueprint(api)


@app.get("/dev/api")
def explorador_da_api():
    """Página de desenvolvimento para exercitar a API pelo navegador."""
    return render_template("explorador.html")


@app.get("/")
def raiz():
    return redirect("/tarefas" if current_user.is_authenticated else "/login")


@app.get("/login")
def pagina_login():
    if current_user.is_authenticated:
        return redirect("/tarefas")
    return render_template("login.html")


@app.get("/cadastro")
def pagina_cadastro():
    if current_user.is_authenticated:
        return redirect("/tarefas")
    return render_template("cadastro.html")


@app.get("/tarefas")
def pagina_tarefas():
    if not current_user.is_authenticated:
        return redirect("/login")
    return render_template("index.html")


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")