"""Blueprint único da API (prefixo /api)."""

from flask import Blueprint, jsonify

api = Blueprint("api", __name__, url_prefix="/api")


@api.get("/saude")
def saude():
    """Sonda de disponibilidade, sem autenticação."""
    return jsonify({"status": "ok"})


# Importados no fim para que os submódulos usem `api` já definido acima.
from routes import auth, atividades, entregas, membros, projetos  # noqa: E402,F401

__all__ = ["api"]