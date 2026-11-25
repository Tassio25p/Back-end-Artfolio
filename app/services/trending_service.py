import json
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.redis_client import redis_client

logger = logging.getLogger(__name__)

CACHE_KEY_TRENDING = "artfolio:trending:top50"
CACHE_TTL_TRENDING = 1800  # 30 minutos


class TrendingService:
    """
    Serviço de inteligência de Trending (Em Alta / Vitrine Global).
    Calcula matematicamente o Time Decay diretamente sobre as tabelas base,
    ranqueando as 50 obras mais quentes e armazenando o resultado no Redis.
    """

    @staticmethod
    def calcular_e_salvar_trending(db: Session) -> List[Dict[str, Any]]:
        """
        Executa a query matemática de Time Decay no PostgreSQL e atualiza o Cache Redis.
        Fórmula: Score = (totalCurtidas + totalComentarios * 1.5) / ((Idade_em_Horas + 2) ^ 1.8)
        """
        # CTE otimizada que substitui a view e já inclui agregação e plano do artista
        sql = text("""
            WITH postagem_stats AS (
                SELECT 
                    p.id AS idpostagem,
                    p.idusuario,
                    u.nome AS nomeusuario,
                    u.fotoperfil AS fotoperfilusuario,
                    u.tipo_conta,
                    u.mostrar_moldura_led,
                    u.mostrar_badge_plano,
                    u.cor_led_hex,
                    p.legenda,
                    p.arquivourl,
                    p.datapostagem,
                    COALESCE(p.visualizacoes, 0) AS visualizacoes,
                    COALESCE((
                        SELECT string_agg(cat.nomecategoria, ', ')
                        FROM postagem_categoria pc
                        JOIN categoria cat ON cat.id = pc.idcategoria
                        WHERE pc.idpostagem = p.id
                    ), '') AS categorias_nomes,
                    (SELECT COUNT(*) FROM curtida cur WHERE cur.idpostagem = p.id)::int AS totalcurtidas,
                    (SELECT COUNT(*) FROM comentario com WHERE com.idpostagem = p.id AND com.deletado = false)::int AS totalcomentarios,
                    (SELECT COUNT(*) FROM obra_salva os WHERE os.idpostagem = p.id)::int AS totalsalvos,
                    (
                        SELECT pl.tipo 
                        FROM assinatura a 
                        JOIN plano pl ON pl.id = a.idplano 
                        WHERE a.idusuario = p.idusuario 
                          AND a.ativa = true 
                          AND (a.deletado = false OR a.deletado IS NULL)
                        ORDER BY a.id DESC 
                        LIMIT 1
                    ) AS plano_tipo
                FROM postagem p
                JOIN usuario u ON u.id = p.idusuario
                WHERE p.deletado = false
            )
            SELECT 
                s.*,
                (s.totalcurtidas + s.totalcomentarios * 1.5) / 
                POWER(GREATEST(0, EXTRACT(EPOCH FROM (NOW() - s.datapostagem)) / 3600.0) + 2.0, 1.8) AS score
            FROM postagem_stats s
            ORDER BY score DESC, s.datapostagem DESC
            LIMIT 50;
        """)

        resultados = db.execute(sql).fetchall()
        obras_trending: List[Dict[str, Any]] = []

        for row in resultados:
            plano_bruto = str(row.plano_tipo or "").strip().lower()
            if "boost" in plano_bruto:
                plano_tipo = "Boost"
            elif "pro" in plano_bruto:
                plano_tipo = "Pro"
            else:
                plano_tipo = "Free"

            categorias_lista = []
            if row.categorias_nomes:
                for cat_nome in str(row.categorias_nomes).split(","):
                    cat_nome_limpo = cat_nome.strip()
                    if cat_nome_limpo:
                        categorias_lista.append({"id": 0, "nomeCategoria": cat_nome_limpo})

            item = {
                "id": row.idpostagem,
                "idUsuario": row.idusuario,
                "legenda": row.legenda,
                "arquivoUrl": row.arquivourl,
                "dataPostagem": row.datapostagem.isoformat() if row.datapostagem else None,
                "visualizacoes": int(row.visualizacoes or 0),
                "totalCurtidas": int(row.totalcurtidas or 0),
                "totalComentarios": int(row.totalcomentarios or 0),
                "totalSalvos": int(row.totalsalvos or 0),
                "score": float(row.score or 0.0),
                "destaque_boost": plano_tipo == "Boost",
                "usuario": {
                    "id": row.idusuario,
                    "nome": row.nomeusuario or "Artista",
                    "fotoPerfil": row.fotoperfilusuario,
                    "tipo_conta": row.tipo_conta or "artista",
                    "plano": plano_tipo,
                    "mostrar_moldura_led": True if row.mostrar_moldura_led is None else bool(row.mostrar_moldura_led),
                    "mostrar_badge_plano": True if row.mostrar_badge_plano is None else bool(row.mostrar_badge_plano),
                    "cor_led_hex": row.cor_led_hex or "#E17055"
                },
                "categoria": categorias_lista[0] if categorias_lista else None,
                "categorias": categorias_lista,
                "curtido_por_mim": False,
                "salvo_por_mim": False
            }
            obras_trending.append(item)

        # Atualizar Cache Redis
        try:
            redis_client.set(CACHE_KEY_TRENDING, json.dumps(obras_trending), expira_segundos=CACHE_TTL_TRENDING)
        except Exception as e:
            logger.warning(f"[Trending] Falha ao gravar cache no Redis: {e}")

        return obras_trending

    @staticmethod
    def obter_em_alta(db: Session, usuario_atual_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retorna as 50 obras em alta diretamente do Cache Redis (em milissegundos).
        Se o cache estiver vazio, recalcula e popula o Redis.
        Faz a checagem de curtidas e salvos em lote (apenas 2 queries no banco).
        """
        obras: List[Dict[str, Any]] = []

        try:
            cached_data = redis_client.get(CACHE_KEY_TRENDING)
            if cached_data:
                obras = json.loads(cached_data)
        except Exception as e:
            logger.warning(f"[Trending] Falha ao ler cache do Redis: {e}")
            obras = []

        # Se não encontrou no cache, calcula e salva
        if not obras:
            obras = TrendingService.calcular_e_salvar_trending(db)

        # Se o usuário está logado, resolve as interações em BATCH (2 queries apenas)
        if usuario_atual_id and obras:
            post_ids = [item["id"] for item in obras if item.get("id")]

            if post_ids:
                # 1. Consulta em lote das postagens que o usuário curtiu
                curtidas_sql = text("""
                    SELECT idpostagem FROM curtida 
                    WHERE idusuario = :uid AND idpostagem = ANY(:pids)
                """)
                curtidas_res = db.execute(curtidas_sql, {"uid": usuario_atual_id, "pids": post_ids}).fetchall()
                curtidos_set = {r[0] for r in curtidas_res}

                # 2. Consulta em lote das postagens que o usuário salvou
                salvos_sql = text("""
                    SELECT idpostagem FROM obra_salva 
                    WHERE idusuario = :uid AND idpostagem = ANY(:pids)
                """)
                salvos_res = db.execute(salvos_sql, {"uid": usuario_atual_id, "pids": post_ids}).fetchall()
                salvos_set = {r[0] for r in salvos_res}

                # Aplica as flags em memória O(1)
                for item in obras:
                    pid = item.get("id")
                    item["curtido_por_mim"] = pid in curtidos_set
                    item["salvo_por_mim"] = pid in salvos_set

        return obras