from typing import List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.mensagem_model import Mensagem
from app.models.conversa_model import Conversa
from app.schemas.mensagem_schema import (
    ConversaResposta,
    MensagemResposta,
    ConversaUsuarioResposta,
    MensagemCriar,
    MensagemEditar,
    DenunciaChatCriar,
    DenunciaChatResposta
)
from app.repositories.conversa_repository import ConversaRepository
from app.repositories.mensagem_repository import MensagemRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.notificacao_service import NotificacaoService

class MensagemService:
    """
    Serviço contendo as regras de negócio para Mensagens e Conversas.

    Encapsula o fluxo de listar conversas, criar/obter conversas, enviar mensagens,
    limpar histórico de conversas e deletar mensagens individuais (soft delete por usuário).
    """

    @staticmethod
    def _montar_conversa_resposta(db: Session, conversa: Conversa, usuario_id: int) -> ConversaResposta:
        """
        Função auxiliar para construir o schema ConversaResposta a partir de um modelo Conversa,
        carregando os dados do destinatário, mensagens ativas e a última mensagem visível.
        """
        participantes = ConversaRepository.buscar_participantes(db, conversa.id)
        
        # Identificar o outro participante (destinatário)
        destinatario_id = None
        for part in participantes:
            if part.idUsuario != usuario_id:
                destinatario_id = part.idUsuario
                break
        
        # Se não houver outro participante (caso de borda), usa o próprio usuário
        if destinatario_id is None:
            destinatario_id = usuario_id

        destinatario_schema = None
        if destinatario_id:
            destinatario_usuario = UsuarioRepository.buscar_por_id(db, destinatario_id)
            if destinatario_usuario:
                destinatario_schema = ConversaUsuarioResposta(
                    id=destinatario_usuario.id,
                    nome=destinatario_usuario.nome,
                    fotoPerfil=destinatario_usuario.fotoPerfil,
                    tipo_conta=getattr(destinatario_usuario, "tipo_conta", "artista")
                )

        # Buscar mensagens ativas visíveis para este usuário
        mensagens_db = MensagemRepository.listar_mensagens_conversa(db, conversa.id, usuario_id)
        mensagens_resposta = [
            MensagemResposta(
                id=msg.id,
                idConversa=msg.idConversa,
                idRemetente=msg.idRemetente,
                conteudo=msg.conteudo,
                arquivoUrl=msg.arquivoUrl,
                dataEnvio=msg.dataEnvio,
                deletado=msg.deletado,
                enviado_por_mim=(msg.idRemetente == usuario_id),
                lida=getattr(msg, "lida", False),
                editado_em=getattr(msg, "editado_em", None),
                deletado_em=getattr(msg, "deletado_em", None),
                deletado_por_id=getattr(msg, "deletado_por_id", None)
            )
            for msg in mensagens_db
        ]

        # Buscar última mensagem visível
        ultima_msg = MensagemRepository.buscar_ultima_mensagem(db, conversa.id, usuario_id)
        ultima_mensagem_resposta = None
        if ultima_msg:
            ultima_mensagem_resposta = MensagemResposta(
                id=ultima_msg.id,
                idConversa=ultima_msg.idConversa,
                idRemetente=ultima_msg.idRemetente,
                conteudo=ultima_msg.conteudo,
                arquivoUrl=ultima_msg.arquivoUrl,
                dataEnvio=ultima_msg.dataEnvio,
                deletado=ultima_msg.deletado,
                enviado_por_mim=(ultima_msg.idRemetente == usuario_id),
                lida=getattr(ultima_msg, "lida", False),
                editado_em=getattr(ultima_msg, "editado_em", None),
                deletado_em=getattr(ultima_msg, "deletado_em", None),
                deletado_por_id=getattr(ultima_msg, "deletado_por_id", None)
            )

        return ConversaResposta(
            id=conversa.id,
            dataCriacao=conversa.dataCriacao,
            destinatario=destinatario_schema,
            ultimaMensagem=ultima_mensagem_resposta,
            mensagens=mensagens_resposta
        )

    @staticmethod
    def listar_conversas(db: Session, usuario_id: int) -> List[ConversaResposta]:
        """
        Retorna todas as conversas ativas das quais o usuário autenticado participa.
        As conversas são ordenadas pela atividade/mensagem mais recente.
        """
        conversas = ConversaRepository.listar_conversas_usuario(db, usuario_id)
        resultado: List[ConversaResposta] = []

        for conversa in conversas:
            resposta = MensagemService._montar_conversa_resposta(db, conversa, usuario_id)
            if resposta.mensagens or resposta.ultimaMensagem:
                resultado.append(resposta)

        # Ordenar conversas pela data da última mensagem (ou data de criação caso não haja mensagens)
        def obter_chave_ordenacao(c: ConversaResposta) -> datetime:
            if c.ultimaMensagem and c.ultimaMensagem.dataEnvio:
                return c.ultimaMensagem.dataEnvio
            if c.dataCriacao:
                return c.dataCriacao
            return datetime.min

        resultado.sort(key=obter_chave_ordenacao, reverse=True)
        return resultado

    @staticmethod
    def obter_ou_criar_conversa(db: Session, usuario_id: int, destinatario_id: int) -> ConversaResposta:
        """
        Retorna a conversa existente com o destinatário ou cria uma nova se ainda não existir.
        Garante que o usuário não crie conversa consigo mesmo e que o destinatário exista.
        """
        if usuario_id == destinatario_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível iniciar uma conversa consigo mesmo."
            )

        destinatario = UsuarioRepository.buscar_por_id(db, destinatario_id)
        if not destinatario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário destinatário não encontrado."
            )

        conversa = ConversaRepository.buscar_conversa_entre_usuarios(db, usuario_id, destinatario_id)
        if conversa:
            # Reativa a participação caso o usuário tenha ocultado a conversa anteriormente
            ConversaRepository.reativar_participacao(db, conversa.id, usuario_id)
        else:
            conversa = ConversaRepository.criar_conversa(db, usuario_id, destinatario_id)

        return MensagemService._montar_conversa_resposta(db, conversa, usuario_id)

    @staticmethod
    async def enviar_mensagem(db: Session, remetente_id: int, conversa_id: int, dados: MensagemCriar) -> MensagemResposta:
        """
        Envia uma nova mensagem na conversa especificada.
        Valida se a conversa existe, se o remetente participa e se há conteúdo/anexo.
        Emite broadcast via WebSocket/Redis com payload padronizado 'NOVA_MENSAGEM'
        para todos os participantes (remetente e destinatário).
        """
        conversa = ConversaRepository.buscar_por_id(db, conversa_id)
        if not conversa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversa não encontrada."
            )

        if not ConversaRepository.usuario_participa(db, conversa_id, remetente_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para enviar mensagens nesta conversa."
            )

        conteudo_limpo = dados.conteudo.strip() if dados.conteudo else None
        arquivo_url_limpo = dados.arquivoUrl.strip() if dados.arquivoUrl else None

        if not conteudo_limpo and not arquivo_url_limpo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A mensagem deve conter ao menos um texto ou um anexo."
            )

        # Reativa a conversa para todos os participantes (caso o destinatário a tenha ocultado)
        participantes = ConversaRepository.buscar_participantes(db, conversa_id)
        for part in participantes:
            ConversaRepository.reativar_participacao(db, conversa_id, part.idUsuario)

        # Criar e salvar mensagem
        nova_mensagem = Mensagem(
            idRemetente=remetente_id,
            idConversa=conversa_id,
            conteudo=conteudo_limpo,
            arquivoUrl=arquivo_url_limpo
        )
        mensagem_salva = MensagemRepository.criar_mensagem(db, nova_mensagem)

        # Montar dados completos da mensagem serializada
        mensagem_dict = {
            "id": mensagem_salva.id,
            "idConversa": mensagem_salva.idConversa,
            "conversa_id": mensagem_salva.idConversa,
            "idRemetente": mensagem_salva.idRemetente,
            "remetente_id": mensagem_salva.idRemetente,
            "conteudo": mensagem_salva.conteudo,
            "mensagem": mensagem_salva.conteudo,
            "arquivoUrl": mensagem_salva.arquivoUrl,
            "dataEnvio": mensagem_salva.dataEnvio.isoformat() if mensagem_salva.dataEnvio else None,
            "deletado": mensagem_salva.deletado,
            "lida": getattr(mensagem_salva, "lida", False),
            "editado_em": mensagem_salva.editado_em.isoformat() if getattr(mensagem_salva, "editado_em", None) else None,
            "deletado_em": mensagem_salva.deletado_em.isoformat() if getattr(mensagem_salva, "deletado_em", None) else None,
            "deletado_por_id": getattr(mensagem_salva, "deletado_por_id", None),
        }

        # Payload de broadcast padronizado da Fase 3
        evento_payload = {
            "tipo": "NOVA_MENSAGEM",
            "conversa_id": conversa_id,
            "conversaId": conversa_id,
            "id_conversa": conversa_id,
            "idConversa": conversa_id,
            "mensagem": mensagem_dict,
            # Campos flat para compatibilidade e tolerância do cliente
            "id": mensagem_salva.id,
            "idRemetente": mensagem_salva.idRemetente,
            "remetente_id": mensagem_salva.idRemetente,
            "conteudo": mensagem_salva.conteudo,
            "dataEnvio": mensagem_salva.dataEnvio.isoformat() if mensagem_salva.dataEnvio else None,
        }

        import json
        from app.redis_client import redis_client
        from app.core.websocket_manager import manager

        # 1. Emitir broadcast para as conexões ativas de AMBOS os participantes (remetente e destinatário)
        for part in participantes:
            canal = f"notificacoes:{part.idUsuario}"
            try:
                redis_client.publish(canal, json.dumps(evento_payload, ensure_ascii=False))
            except Exception:
                pass
            try:
                await manager.send_personal_message(part.idUsuario, evento_payload)
            except Exception:
                pass

        # 2. Notificar destinatários via central de notificações persistida no banco
        remetente_usuario = UsuarioRepository.buscar_por_id(db, remetente_id)
        nome_remetente = remetente_usuario.nome if remetente_usuario else "Um usuário"

        texto_notificacao = conteudo_limpo if conteudo_limpo else "Enviou um anexo."
        if len(texto_notificacao) > 80:
            texto_notificacao = texto_notificacao[:80] + "..."

        for part in participantes:
            if part.idUsuario != remetente_id:
                try:
                    NotificacaoService.criar_notificacao(
                        db=db,
                        id_usuario=part.idUsuario,
                        tipo="MESSAGE",
                        titulo=f"Nova mensagem de {nome_remetente}",
                        mensagem=texto_notificacao,
                        id_remetente=remetente_id,
                        id_conversa=conversa_id,
                        publicar_ws=False  # Já emitido via broadcast direto acima
                    )
                except Exception:
                    pass

        return MensagemResposta(
            id=mensagem_salva.id,
            idConversa=mensagem_salva.idConversa,
            idRemetente=mensagem_salva.idRemetente,
            conteudo=mensagem_salva.conteudo,
            arquivoUrl=mensagem_salva.arquivoUrl,
            dataEnvio=mensagem_salva.dataEnvio,
            deletado=mensagem_salva.deletado,
            enviado_por_mim=True,
            lida=False
        )

    @staticmethod
    def limpar_conversa(db: Session, usuario_id: int, conversa_id: int) -> dict:
        """
        Oculta todo o histórico de mensagens da conversa exclusivamente para o usuário autenticado,
        além de ocultar a conversa de sua lista até que uma nova mensagem chegue.
        """
        conversa = ConversaRepository.buscar_por_id(db, conversa_id)
        if not conversa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversa não encontrada."
            )

        if not ConversaRepository.usuario_participa(db, conversa_id, usuario_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para alterar esta conversa."
            )

        # Ocultar todas as mensagens ativas da conversa para este usuário
        mensagens = MensagemRepository.listar_mensagens_conversa(db, conversa_id, usuario_id)
        total_participantes = len(ConversaRepository.buscar_participantes(db, conversa_id))

        for msg in mensagens:
            MensagemRepository.ocultar_mensagem_para_usuario(db, msg, usuario_id, total_participantes)

        # Ocultar a conversa da lista do usuário
        ConversaRepository.ocultar_conversa_usuario(db, conversa_id, usuario_id)

        return {"message": "Histórico de mensagens da conversa limpo com sucesso."}

    @staticmethod
    def deletar_mensagem_individual(db: Session, usuario_id: int, mensagem_id: int) -> dict:
        """
        Oculta uma mensagem individual exclusivamente para o usuário autenticado.
        """
        mensagem = MensagemRepository.buscar_por_id(db, mensagem_id)
        if not mensagem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mensagem não encontrada."
            )

        if not ConversaRepository.usuario_participa(db, mensagem.idConversa, usuario_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para excluir esta mensagem."
            )

        total_participantes = len(ConversaRepository.buscar_participantes(db, mensagem.idConversa))
        MensagemRepository.ocultar_mensagem_para_usuario(db, mensagem, usuario_id, total_participantes)

        return {"message": "Mensagem excluída com sucesso."}

    @staticmethod
    async def marcar_como_lida(db: Session, usuario_id: int, conversa_id: int) -> dict:
        """
        Marca todas as mensagens recebidas da conversa como lidas (lida = True).
        Emite evento via WebSocket/Redis Pub/Sub para atualizar os dois traços visuais em tempo real.
        """
        conversa = ConversaRepository.buscar_por_id(db, conversa_id)
        if not conversa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversa não encontrada."
            )

        if not ConversaRepository.usuario_participa(db, conversa_id, usuario_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para alterar esta conversa."
            )

        # Atualiza mensagens onde remetente != usuario_atual e lida == False
        total = db.query(Mensagem).filter(
            Mensagem.idConversa == conversa_id,
            Mensagem.idRemetente != usuario_id,
            Mensagem.deletado == False,
            Mensagem.lida == False
        ).update({"lida": True}, synchronize_session=False)

        db.commit()

        # Emitir evento MENSAGENS_LIDAS para os participantes via WebSocket / Redis
        participantes = ConversaRepository.buscar_participantes(db, conversa_id)
        evento_payload = {
            "tipo": "MENSAGENS_LIDAS",
            "conversa_id": conversa_id,
            "id_conversa": conversa_id,
            "leitor_id": usuario_id,
            "mensagens_atualizadas": total
        }

        import json
        from app.redis_client import redis_client
        from app.core.websocket_manager import manager

        for part in participantes:
            canal = f"notificacoes:{part.idUsuario}"
            try:
                redis_client.publish(canal, json.dumps(evento_payload, ensure_ascii=False))
            except Exception:
                pass
            try:
                await manager.send_personal_message(part.idUsuario, evento_payload)
            except Exception:
                pass

        return {
            "status": "sucesso",
            "mensagens_atualizadas": total
        }

    @staticmethod
    async def editar_mensagem(db: Session, usuario_id: int, mensagem_id: int, dados: MensagemEditar) -> MensagemResposta:
        """
        Permite a edição do conteúdo de uma mensagem enviada há no máximo 15 minutos pelo autor.
        Emite evento via WebSocket: { "tipo": "MENSAGEM_EDITADA", "conversa_id": ..., "mensagem_id": ..., "novo_conteudo": ..., "editado_em": ... }
        """
        mensagem = db.query(Mensagem).filter(Mensagem.id == mensagem_id).first()
        if not mensagem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mensagem não encontrada."
            )

        if mensagem.idRemetente != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você só pode editar suas próprias mensagens."
            )

        if getattr(mensagem, "deletado_em", None) is not None or mensagem.deletado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível editar uma mensagem que foi apagada."
            )

        # Validação da janela de 15 minutos
        if mensagem.dataEnvio:
            agora_utc = datetime.now(timezone.utc)
            envio_time = mensagem.dataEnvio
            if envio_time.tzinfo is not None:
                diferenca = (datetime.now(timezone.utc) - envio_time).total_seconds()
            else:
                diferenca = (agora_utc.replace(tzinfo=None) - envio_time).total_seconds()

            if diferenca > 15 * 60:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A mensagem só pode ser editada em até 15 minutos após o envio."
                )

        agora = datetime.now(timezone.utc)
        mensagem.conteudo = dados.conteudo
        mensagem.editado_em = agora
        db.commit()
        db.refresh(mensagem)

        evento_payload = {
            "tipo": "MENSAGEM_EDITADA",
            "conversa_id": mensagem.idConversa,
            "id_conversa": mensagem.idConversa,
            "mensagem_id": mensagem.id,
            "id": mensagem.id,
            "novo_conteudo": mensagem.conteudo,
            "conteudo": mensagem.conteudo,
            "editado_em": agora.isoformat()
        }

        import json
        from app.redis_client import redis_client
        from app.core.websocket_manager import manager

        participantes = ConversaRepository.buscar_participantes(db, mensagem.idConversa)
        for part in participantes:
            canal = f"notificacoes:{part.idUsuario}"
            try:
                redis_client.publish(canal, json.dumps(evento_payload, ensure_ascii=False))
            except Exception:
                pass
            try:
                await manager.send_personal_message(part.idUsuario, evento_payload)
            except Exception:
                pass

        return MensagemResposta(
            id=mensagem.id,
            idConversa=mensagem.idConversa,
            idRemetente=mensagem.idRemetente,
            conteudo=mensagem.conteudo,
            arquivoUrl=mensagem.arquivoUrl,
            dataEnvio=mensagem.dataEnvio,
            deletado=mensagem.deletado,
            enviado_por_mim=True,
            lida=getattr(mensagem, "lida", False),
            editado_em=mensagem.editado_em,
            deletado_em=mensagem.deletado_em,
            deletado_por_id=mensagem.deletado_por_id
        )

    @staticmethod
    async def soft_delete_mensagem(db: Session, usuario_id: int, mensagem_id: int) -> dict:
        """
        Aplica Soft Delete na mensagem sem remover a linha do banco.
        Seta deletado_em = datetime.now(timezone.utc) e deletado_por_id = usuario_atual.id.
        Emite evento via WebSocket: { "tipo": "MENSAGEM_EXCLUIDA", "conversa_id": ..., "mensagem_id": ... }
        """
        mensagem = db.query(Mensagem).filter(Mensagem.id == mensagem_id).first()
        if not mensagem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mensagem não encontrada."
            )

        if mensagem.idRemetente != usuario_id:
            if not ConversaRepository.usuario_participa(db, mensagem.idConversa, usuario_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Você não tem permissão para excluir esta mensagem."
                )

        agora = datetime.now(timezone.utc)
        mensagem.deletado_em = agora
        mensagem.deletado_por_id = usuario_id
        db.commit()
        db.refresh(mensagem)

        evento_payload = {
            "tipo": "MENSAGEM_EXCLUIDA",
            "conversa_id": mensagem.idConversa,
            "id_conversa": mensagem.idConversa,
            "mensagem_id": mensagem.id,
            "id": mensagem.id,
            "deletado_em": agora.isoformat(),
            "deletado_por_id": usuario_id
        }

        import json
        from app.redis_client import redis_client
        from app.core.websocket_manager import manager

        participantes = ConversaRepository.buscar_participantes(db, mensagem.idConversa)
        for part in participantes:
            canal = f"notificacoes:{part.idUsuario}"
            try:
                redis_client.publish(canal, json.dumps(evento_payload, ensure_ascii=False))
            except Exception:
                pass
            try:
                await manager.send_personal_message(part.idUsuario, evento_payload)
            except Exception:
                pass

        return {
            "message": "Mensagem apagada com sucesso.",
            "mensagem_id": mensagem.id,
            "deletado_em": agora.isoformat()
        }

    @staticmethod
    def criar_denuncia_chat(db: Session, denunciante_id: int, dados: DenunciaChatCriar) -> DenunciaChatResposta:
        """
        Registra uma nova denúncia de usuário ou conversa.
        Valida que o usuário não denuncie a si mesmo e participe da conversa.
        """
        if denunciante_id == dados.denunciado_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Você não pode denunciar a si mesmo."
            )

        if not ConversaRepository.usuario_participa(db, dados.conversa_id, denunciante_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não participa desta conversa para registrar uma denúncia."
            )

        from app.repositories.denuncia_chat_repository import DenunciaChatRepository
        from app.models.denuncia_chat_model import DenunciaChat

        denuncia = DenunciaChat(
            denunciante_id=denunciante_id,
            denunciado_id=dados.denunciado_id,
            conversa_id=dados.conversa_id,
            motivo=dados.motivo.strip(),
            descricao=dados.descricao.strip() if dados.descricao else None,
            status="pendente"
        )
        salva = DenunciaChatRepository.criar(db, denuncia)
        return DenunciaChatResposta(
            id=salva.id,
            denunciante_id=salva.denunciante_id,
            denunciado_id=salva.denunciado_id,
            conversa_id=salva.conversa_id,
            motivo=salva.motivo,
            descricao=salva.descricao,
            status=salva.status,
            criado_em=salva.criado_em
        )

