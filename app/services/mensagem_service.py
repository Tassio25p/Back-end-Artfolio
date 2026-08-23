from typing import List, Optional
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.mensagem_model import Mensagem
from app.models.conversa_model import Conversa
from app.schemas.mensagem_schema import (
    ConversaResposta,
    MensagemResposta,
    ConversaUsuarioResposta,
    MensagemCriar
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

        destinatario_usuario = UsuarioRepository.buscar_por_id(db, destinatario_id)
        destinatario_schema = None
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
                enviado_por_mim=(msg.idRemetente == usuario_id)
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
                enviado_por_mim=(ultima_msg.idRemetente == usuario_id)
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
    def enviar_mensagem(db: Session, remetente_id: int, conversa_id: int, dados: MensagemCriar) -> MensagemResposta:
        """
        Envia uma nova mensagem na conversa especificada.
        Valida se a conversa existe, se o remetente participa e se há conteúdo/anexo.
        Notifica os demais participantes automaticamente.
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

        # Notificar participantes (exceto o próprio remetente)
        remetente_usuario = UsuarioRepository.buscar_por_id(db, remetente_id)
        nome_remetente = remetente_usuario.nome if remetente_usuario else "Um usuário"

        texto_notificacao = conteudo_limpo if conteudo_limpo else "Enviou um anexo."
        if len(texto_notificacao) > 80:
            texto_notificacao = texto_notificacao[:80] + "..."

        for part in participantes:
            if part.idUsuario != remetente_id:
                NotificacaoService.criar_notificacao(
                    db=db,
                    id_usuario=part.idUsuario,
                    tipo="MESSAGE",
                    titulo=f"Nova mensagem de {nome_remetente}",
                    mensagem=texto_notificacao,
                    id_remetente=remetente_id,
                    id_conversa=conversa_id
                )

        return MensagemResposta(
            id=mensagem_salva.id,
            idConversa=mensagem_salva.idConversa,
            idRemetente=mensagem_salva.idRemetente,
            conteudo=mensagem_salva.conteudo,
            arquivoUrl=mensagem_salva.arquivoUrl,
            dataEnvio=mensagem_salva.dataEnvio,
            deletado=mensagem_salva.deletado,
            enviado_por_mim=True
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
