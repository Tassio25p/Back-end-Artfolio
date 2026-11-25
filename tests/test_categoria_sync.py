"""
Testes de sincronização inicial da tabela 'categoria' (Desafios Semanais e catálogo oficial).
Garante que as inserções SQL satisfaçam todas as restrições NOT NULL (como desafio_ativo e prazo_dias)
mesmo em tabelas criadas sem server_default no banco.
"""

import unittest

from sqlalchemy import create_engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.models.categoria_model import Categoria


class TestCategoriaSync(unittest.TestCase):
    def _criar_tabela_categoria_sem_server_default(self, engine):
        """
        Recria o esquema exato da tabela 'categoria' gerada originalmente por Base.metadata.create_all()
        sem DEFAULT no banco, reproduzindo o NotNullViolation em desafio_ativo e prazo_dias.
        """
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE categoria (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nomecategoria VARCHAR(50) NOT NULL UNIQUE,
                        is_desafio BOOLEAN NOT NULL,
                        desafio_ativo BOOLEAN NOT NULL,
                        data_inicio_desafio TIMESTAMP,
                        prazo_dias INTEGER NOT NULL,
                        data_fim_desafio TIMESTAMP,
                        deletado BOOLEAN NOT NULL,
                        datadelecao TIMESTAMP
                    )
                    """
                )
            )

    def test_sincronizar_categorias_popula_desafios_e_catalogo_em_tabela_not_null_sem_defaults(self):
        from app.main import SUBCATEGORIAS_OFICIAIS, sincronizar_categorias

        engine = create_engine("sqlite:///:memory:")
        self._criar_tabela_categoria_sem_server_default(engine)

        with engine.connect() as conn:
            sincronizar_categorias(conn)

            total_desafios = conn.execute(
                text("SELECT COUNT(*) FROM categoria WHERE is_desafio = TRUE AND deletado = FALSE")
            ).scalar()
            total_desafios_ativos = conn.execute(
                text("SELECT COUNT(*) FROM categoria WHERE is_desafio = TRUE AND desafio_ativo = TRUE")
            ).scalar()
            total_catalogo = conn.execute(
                text("SELECT COUNT(*) FROM categoria WHERE is_desafio = FALSE AND deletado = FALSE")
            ).scalar()
            pintura = conn.execute(
                text(
                    "SELECT nomecategoria, is_desafio, desafio_ativo, prazo_dias, deletado "
                    "FROM categoria WHERE nomecategoria = 'Pintura'"
                )
            ).fetchone()

        self.assertEqual(total_desafios, 7)
        self.assertEqual(total_desafios_ativos, 1)
        self.assertEqual(total_catalogo, len(SUBCATEGORIAS_OFICIAIS))
        self.assertIsNotNone(pintura)
        self.assertEqual(pintura[0], "Pintura")
        self.assertFalse(bool(pintura[1]))
        self.assertFalse(bool(pintura[2]))
        self.assertEqual(pintura[3], 7)
        self.assertFalse(bool(pintura[4]))

    def test_sincronizar_categorias_eh_idempotente_e_respeita_soft_delete(self):
        from app.main import SUBCATEGORIAS_OFICIAIS, sincronizar_categorias

        engine = create_engine("sqlite:///:memory:")
        self._criar_tabela_categoria_sem_server_default(engine)

        with engine.connect() as conn:
            # Simula categoria oficial previamente marcada como deletada (unique constraint ativa)
            conn.execute(
                text(
                    "INSERT INTO categoria (nomecategoria, is_desafio, desafio_ativo, prazo_dias, deletado) "
                    "VALUES ('Pintura', FALSE, FALSE, 7, TRUE)"
                )
            )
            conn.commit()

            sincronizar_categorias(conn)
            sincronizar_categorias(conn)

            total = conn.execute(text("SELECT COUNT(*) FROM categoria")).scalar()

        self.assertEqual(total, 7 + len(SUBCATEGORIAS_OFICIAIS))

    def test_modelo_categoria_define_server_defaults_no_ddl_postgres(self):
        ddl = str(CreateTable(Categoria.__table__).compile(dialect=postgresql.dialect())).lower()
        self.assertIn("is_desafio boolean default false not null", ddl)
        self.assertIn("desafio_ativo boolean default false not null", ddl)
        self.assertIn("prazo_dias integer default 7 not null", ddl)
        self.assertIn("deletado boolean default false not null", ddl)


if __name__ == "__main__":
    unittest.main()
