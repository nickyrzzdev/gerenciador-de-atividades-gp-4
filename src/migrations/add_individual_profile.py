"""Adiciona o perfil individual à restrição SQLite da tabela usuarios.

Execute de dentro de src com `python -m migrations.add_individual_profile`.
Faça um backup do arquivo do banco antes de executar em dados importantes.
"""

from __future__ import annotations

import re

from sqlalchemy.engine import Engine


def upgrade(engine: Engine) -> bool:
    """Reconstrói usuarios preservando linhas, colunas, índices e gatilhos."""
    if engine.dialect.name != "sqlite":
        raise RuntimeError("Esta migração suporta apenas SQLite")

    connection = engine.raw_connection()
    cursor = connection.cursor()
    try:
        linha = cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'usuarios'"
        ).fetchone()
        if linha is None:
            raise RuntimeError("A tabela usuarios não existe neste banco")

        ddl = linha[0]
        if re.search(r"'individual'", ddl, re.IGNORECASE):
            return False

        ddl_atualizado, ocorrencias = re.subn(
            r"CHECK\s*\(\s*perfil\s+IN\s*\(\s*'coordenador'\s*,\s*'bolsista'\s*\)\s*\)",
            "CHECK (perfil IN ('coordenador', 'bolsista', 'individual'))",
            ddl,
            count=1,
            flags=re.IGNORECASE,
        )
        if ocorrencias != 1:
            raise RuntimeError(
                "Não foi possível localizar a restrição de perfil esperada em usuarios"
            )

        ddl_nova_tabela, ocorrencias = re.subn(
            r"^(CREATE\s+TABLE\s+)(?:\"usuarios\"|`usuarios`|\[usuarios\]|usuarios)(\s*\()",
            r'\1"usuarios_individual_new"\2',
            ddl_atualizado,
            count=1,
            flags=re.IGNORECASE,
        )
        if ocorrencias != 1:
            raise RuntimeError("Não foi possível preparar a reconstrução da tabela usuarios")

        colunas = [
            linha[1]
            for linha in cursor.execute('PRAGMA table_info("usuarios")').fetchall()
        ]
        if not colunas:
            raise RuntimeError("A tabela usuarios não possui colunas")
        colunas_sql = ", ".join(f'"{coluna}"' for coluna in colunas)

        objetos = cursor.execute(
            """
            SELECT sql FROM sqlite_master
            WHERE tbl_name = 'usuarios'
              AND type IN ('index', 'trigger')
              AND sql IS NOT NULL
            ORDER BY type, name
            """
        ).fetchall()

        cursor.execute("PRAGMA foreign_keys = OFF")
        cursor.execute("BEGIN IMMEDIATE")
        try:
            cursor.execute(ddl_nova_tabela)
            cursor.execute(
                f'INSERT INTO "usuarios_individual_new" ({colunas_sql}) '
                f'SELECT {colunas_sql} FROM "usuarios"'
            )
            cursor.execute('DROP TABLE "usuarios"')
            cursor.execute(
                'ALTER TABLE "usuarios_individual_new" RENAME TO "usuarios"'
            )
            for (sql,) in objetos:
                cursor.execute(sql)

            violacoes_fk = cursor.execute("PRAGMA foreign_key_check").fetchall()
            if violacoes_fk:
                raise RuntimeError(
                    f"A migração causaria violações de chave estrangeira: {violacoes_fk}"
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.execute("PRAGMA foreign_keys = ON")
        return True
    finally:
        cursor.close()
        connection.close()


def main() -> None:
    from app import app

    with app.app_context():
        alterou = upgrade(app.engine)
    print("Perfil individual adicionado." if alterou else "A migração já está aplicada.")


if __name__ == "__main__":
    main()
