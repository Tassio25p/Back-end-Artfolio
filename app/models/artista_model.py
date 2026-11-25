"""
Módulo utilitário para consultas de Artistas.

No sistema Artfolio, 'artista' não é uma tabela separada no banco de dados.
Um artista é um Usuário com tipo_conta = 'artista'. Este módulo fornece
um atalho para facilitar consultas específicas de artistas.
"""
from app.models.usuario_model import Usuario

# Alias direto — Artista é um Usuário
Artista = Usuario

# Filtro padrão para consultas de artistas
FILTRO_ARTISTA = Usuario.tipo_conta.in_(["artista", "admin", "moderador"])
