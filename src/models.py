"""Tabelas do domínio LabFlow e suas serializações básicas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from flask_login import UserMixin
from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from utils import (
    AtividadeStatus,
    AtividadeTipo,
    EntregaResultado,
    Perfil,
    ProjetoStatus,
    agora,
    iniciais,
    iso,
)

# `db` mora aqui para que utils.py nunca precise importar models.py (sem ciclo).
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def enum_col(enum_cls, **kwargs):
    """VARCHAR + CHECK constraint no SQLite (native_enum=False)."""
    return db.Enum(
        enum_cls,
        native_enum=False,
        values_callable=lambda cls: [membro.value for membro in cls],
        validate_strings=True,
        length=40,
        **kwargs,
    )


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(120), nullable=False)
    email: Mapped[str] = mapped_column(db.String(180), unique=True, index=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(db.String(255), nullable=False)
    perfil: Mapped[Perfil] = mapped_column(enum_col(Perfil), nullable=False)
    ativo: Mapped[bool] = mapped_column(default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(default=agora, nullable=False)

    projetos_coordenados: Mapped[list["Projeto"]] = relationship(
        "Projeto",
        back_populates="coordenador",
        foreign_keys="Projeto.coordenador_id",
    )
    participacoes: Mapped[list["Participacao"]] = relationship(
        "Participacao", back_populates="usuario", cascade="all, delete-orphan"
    )
    tarefas_pessoais: Mapped[list["TarefaPessoal"]] = relationship(
        "TarefaPessoal", back_populates="usuario", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:  # noqa: D401 - substitui o UserMixin
        """O Flask-Login usa esta flag para bloquear contas desativadas."""
        return bool(self.ativo)

    def definir_senha(self, senha: str) -> None:
        self.senha_hash = generate_password_hash(senha)

    def checar_senha(self, senha: str) -> bool:
        return bool(senha) and check_password_hash(self.senha_hash, senha)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "iniciais": iniciais(self.nome),
            "perfil": self.perfil.value,
            "ativo": self.ativo,
        }

    def resumo(self) -> dict[str, Any]:
        return {"id": self.id, "nome": self.nome, "iniciais": iniciais(self.nome)}


class Projeto(db.Model):
    __tablename__ = "projetos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(150), nullable=False)
    descricao: Mapped[str] = mapped_column(db.Text, nullable=False)
    data_inicio: Mapped[date] = mapped_column(nullable=False)
    data_fim: Mapped[date] = mapped_column(nullable=False)
    status: Mapped[ProjetoStatus] = mapped_column(
        enum_col(ProjetoStatus), default=ProjetoStatus.PLANEJADO, nullable=False
    )
    coordenador_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    criado_em: Mapped[datetime] = mapped_column(default=agora, nullable=False)

    coordenador: Mapped[Usuario] = relationship(
        "Usuario", back_populates="projetos_coordenados", foreign_keys=[coordenador_id]
    )
    participacoes: Mapped[list["Participacao"]] = relationship(
        "Participacao",
        back_populates="projeto",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    atividades: Mapped[list["Atividade"]] = relationship(
        "Atividade",
        back_populates="projeto",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "nome": self.nome,
            "descricao": self.descricao,
            "data_inicio": iso(self.data_inicio),
            "data_fim": iso(self.data_fim),
            "status": self.status.value,
            "coordenador_id": self.coordenador_id,
        }


class Participacao(db.Model):
    __tablename__ = "participacoes"

    projeto_id: Mapped[int] = mapped_column(
        ForeignKey("projetos.id", ondelete="CASCADE"), primary_key=True
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    vinculado_em: Mapped[datetime] = mapped_column(default=agora, nullable=False)

    projeto: Mapped[Projeto] = relationship("Projeto", back_populates="participacoes")
    usuario: Mapped[Usuario] = relationship("Usuario", back_populates="participacoes")


class Atividade(db.Model):
    __tablename__ = "atividades"
    __table_args__ = (
        Index("ix_atividades_projeto_tipo", "projeto_id", "tipo"),
        Index("ix_atividades_responsavel_prazo", "responsavel_id", "prazo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    projeto_id: Mapped[int] = mapped_column(
        ForeignKey("projetos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    titulo: Mapped[str] = mapped_column(db.String(150), nullable=False)
    descricao: Mapped[str | None] = mapped_column(db.Text)
    tipo: Mapped[AtividadeTipo] = mapped_column(enum_col(AtividadeTipo), nullable=False)
    status: Mapped[AtividadeStatus] = mapped_column(
        enum_col(AtividadeStatus), default=AtividadeStatus.A_FAZER, nullable=False
    )
    prazo: Mapped[datetime] = mapped_column(nullable=False)
    responsavel_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    criado_por_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    link_material: Mapped[str | None] = mapped_column(db.String(500))
    concluida_em: Mapped[datetime | None] = mapped_column()
    criado_em: Mapped[datetime] = mapped_column(default=agora, nullable=False)

    projeto: Mapped[Projeto] = relationship("Projeto", back_populates="atividades")
    responsavel: Mapped[Usuario] = relationship("Usuario", foreign_keys=[responsavel_id])
    criado_por: Mapped[Usuario] = relationship("Usuario", foreign_keys=[criado_por_id])
    entregas: Mapped[list["Entrega"]] = relationship(
        "Entrega",
        back_populates="atividade",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def to_dict(self) -> dict[str, Any]:
        """Campos gravados; os derivados ficam em `atividade_service`."""
        return {
            "id": self.id,
            "projeto_id": self.projeto_id,
            "titulo": self.titulo,
            "descricao": self.descricao,
            "tipo": self.tipo.value,
            "status": self.status.value,
            "prazo": iso(self.prazo),
            "responsavel_id": self.responsavel_id,
            "criado_por_id": self.criado_por_id,
            "link_material": self.link_material,
            "concluida_em": iso(self.concluida_em),
            "criado_em": iso(self.criado_em),
        }


class Entrega(db.Model):
    __tablename__ = "entregas"
    __table_args__ = (
        UniqueConstraint("atividade_id", "numero", name="uq_entregas_atividade_numero"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atividade_id: Mapped[int] = mapped_column(
        ForeignKey("atividades.id", ondelete="CASCADE"), nullable=False, index=True
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    numero: Mapped[int] = mapped_column(nullable=False)
    descricao: Mapped[str] = mapped_column(db.Text, nullable=False)
    link: Mapped[str] = mapped_column(db.String(500), nullable=False)
    enviada_em: Mapped[datetime] = mapped_column(default=agora, nullable=False)
    resultado: Mapped[EntregaResultado] = mapped_column(
        enum_col(EntregaResultado),
        default=EntregaResultado.AGUARDANDO_AVALIACAO,
        nullable=False,
    )
    comentario_feedback: Mapped[str | None] = mapped_column(db.Text)
    avaliador_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    avaliada_em: Mapped[datetime | None] = mapped_column()
    criado_em: Mapped[datetime] = mapped_column(default=agora, nullable=False)

    atividade: Mapped[Atividade] = relationship("Atividade", back_populates="entregas")
    usuario: Mapped[Usuario] = relationship("Usuario", foreign_keys=[usuario_id])
    avaliador: Mapped[Usuario | None] = relationship("Usuario", foreign_keys=[avaliador_id])

    def to_dict(self) -> dict[str, Any]:
        feedback = None
        if self.avaliada_em is not None:
            feedback = {
                "comentario": self.comentario_feedback,
                "coordenador": self.avaliador.resumo() if self.avaliador else None,
                "avaliado_em": iso(self.avaliada_em),
            }
        return {
            "id": self.id,
            "numero": self.numero,
            "enviado_em": iso(self.enviada_em),
            "descricao": self.descricao,
            "link": self.link,
            "resultado": self.resultado.value,
            "autor": self.usuario.resumo(),
            "feedback": feedback,
        }


class TarefaPessoal(db.Model):
    __tablename__ = "tarefas_pessoais"
    __table_args__ = (
        Index("ix_tarefas_pessoais_usuario_prazo", "usuario_id", "prazo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    titulo: Mapped[str] = mapped_column(db.String(150), nullable=False)
    descricao: Mapped[str | None] = mapped_column(db.Text)
    prazo: Mapped[datetime | None] = mapped_column()
    status: Mapped[AtividadeStatus] = mapped_column(
        enum_col(AtividadeStatus), default=AtividadeStatus.A_FAZER, nullable=False
    )
    concluida_em: Mapped[datetime | None] = mapped_column()
    criado_em: Mapped[datetime] = mapped_column(default=agora, nullable=False)

    usuario: Mapped[Usuario] = relationship("Usuario", back_populates="tarefas_pessoais")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "titulo": self.titulo,
            "descricao": self.descricao,
            "prazo": iso(self.prazo),
            "status": self.status.value,
            "concluida_em": iso(self.concluida_em),
            "criado_em": iso(self.criado_em),
        }