from typing import List, Optional, Any
import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
# Modelos e repositórios temporariamente isolados até implementação completa no banco
try:
    # pyrefly: ignore [missing-import]
    from app.models.assistente_conversa_model import AssistenteConversa
    # pyrefly: ignore [missing-import]
    from app.models.assistente_mensagem_model import AssistenteMensagem
    # pyrefly: ignore [missing-import]
    from app.repositories.assistente_repository import AssistenteRepository 
except ImportError:
    class _AssistenteConversaStub:
        pass

    class _AssistenteMensagemStub:
        pass

    class _AssistenteRepositoryStub:
        @staticmethod
        def buscar_conversa_por_id(*args: Any, **kwargs: Any) -> Any:
            raise NotImplementedError("AssistenteRepository ainda não implementado no banco.")

        @staticmethod
        def criar_conversa(*args: Any, **kwargs: Any) -> Any:
            raise NotImplementedError("AssistenteRepository ainda não implementado no banco.")

        @staticmethod
        def criar_mensagem(*args: Any, **kwargs: Any) -> Any:
            raise NotImplementedError("AssistenteRepository ainda não implementado no banco.")

        @staticmethod
        def atualizar_conversa(*args: Any, **kwargs: Any) -> Any:
            raise NotImplementedError("AssistenteRepository ainda não implementado no banco.")

        @staticmethod
        def listar_conversas(*args: Any, **kwargs: Any) -> Any:
            raise NotImplementedError("AssistenteRepository ainda não implementado no banco.")

        @staticmethod
        def encerrar_conversa(*args: Any, **kwargs: Any) -> Any:
            raise NotImplementedError("AssistenteRepository ainda não implementado no banco.")

        @staticmethod
        def deletar_conversa(*args: Any, **kwargs: Any) -> Any:
            raise NotImplementedError("AssistenteRepository ainda não implementado no banco.")

    AssistenteConversa: Any = _AssistenteConversaStub
    AssistenteMensagem: Any = _AssistenteMensagemStub
    AssistenteRepository: Any = _AssistenteRepositoryStub


# URL do webhook do agente IA no n8n
N8N_WEBHOOK_URL = "http://localhost:5678/webhook/artfolio-agent"


class AssistenteService:
    """
    Serviço contendo as regras de negócio do Assistente de IA.
    Orquestra a criação de conversas, envio de mensagens ao n8n,
    e persistência de todo o histórico no banco de dados.
    """

    @staticmethod
    async def enviar_mensagem(
        db: Session,
        id_usuario: int,
        texto: str,
        id_conversa: Optional[int] = None
    ) -> dict:
        """
        Processa uma mensagem do usuário:
        1. Cria ou reutiliza uma conversa
        2. Salva a mensagem do usuário no banco
        3. Envia ao webhook do n8n e aguarda resposta
        4. Salva a resposta da IA no banco
        5. Retorna os dados para o frontend
        """
        # 1. Criar ou reutilizar conversa
        if id_conversa:
            conversa = AssistenteRepository.buscar_conversa_por_id(db, id_conversa)
            if not conversa:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversa não encontrada."
                )
            if conversa.idUsuario != id_usuario:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Você não tem permissão para acessar esta conversa."
                )
        else:
            # Gera título a partir das primeiras palavras da mensagem
            titulo = texto[:50] + ("..." if len(texto) > 50 else "")
            conversa = AssistenteRepository.criar_conversa(db, id_usuario, titulo)

        # 2. Salvar mensagem do usuário
        msg_usuario = AssistenteRepository.criar_mensagem(
            db=db,
            id_conversa=conversa.id,
            remetente="usuario",
            mensagem=texto,
        )

        # 3. Chamar o webhook do n8n
        resposta_ia_texto = "Desculpe, não consegui processar sua mensagem."
        resposta_json_bruta = None

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    N8N_WEBHOOK_URL,
                    json={"message": texto},
                )
                response.raise_for_status()

                resposta_json_bruta = response.json()

                # Extrair texto da resposta (n8n pode retornar array ou objeto)
                data = resposta_json_bruta
                if isinstance(data, list):
                    data = data[0] if data else {}

                resposta_ia_texto = (
                    data.get("output")
                    or data.get("response")
                    or data.get("message")
                    or data.get("text")
                    or (data.get("data", {}).get("output") if isinstance(data.get("data"), dict) else None)
                    or (data.get("data", {}).get("response") if isinstance(data.get("data"), dict) else None)
                    or str(data)
                )

        except httpx.HTTPStatusError as e:
            resposta_ia_texto = f"Erro ao se comunicar com o assistente (HTTP {e.response.status_code})."
        except Exception as e:
            resposta_ia_texto = "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente."

        # 4. Salvar resposta da IA
        msg_assistente = AssistenteRepository.criar_mensagem(
            db=db,
            id_conversa=conversa.id,
            remetente="assistente",
            mensagem=resposta_ia_texto,
            resposta_json=resposta_json_bruta if isinstance(resposta_json_bruta, dict) else None,
        )

        # 5. Atualizar data de atualização da conversa
        AssistenteRepository.atualizar_conversa(db, conversa)

        return {
            "idConversa": conversa.id,
            "resposta": resposta_ia_texto,
            "mensagemUsuario": msg_usuario,
            "mensagemAssistente": msg_assistente,
        }

    @staticmethod
    def listar_conversas(db: Session, id_usuario: int) -> List[AssistenteConversa]:
        """
        Retorna todas as conversas ativas do usuário com o assistente.
        """
        return AssistenteRepository.listar_conversas(db, id_usuario)

    @staticmethod
    def buscar_conversa(db: Session, conversa_id: int, id_usuario: int) -> AssistenteConversa:
        """
        Busca uma conversa com seu histórico de mensagens.
        Valida que a conversa pertence ao usuário solicitante.
        """
        conversa = AssistenteRepository.buscar_conversa_por_id(db, conversa_id)
        if not conversa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversa não encontrada."
            )
        if conversa.idUsuario != id_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar esta conversa."
            )
        return conversa

    @staticmethod
    def encerrar_conversa(db: Session, conversa_id: int, id_usuario: int) -> AssistenteConversa:
        """
        Marca uma conversa como encerrada (inativa).
        """
        conversa = AssistenteRepository.buscar_conversa_por_id(db, conversa_id)
        if not conversa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversa não encontrada."
            )
        if conversa.idUsuario != id_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar esta conversa."
            )
        return AssistenteRepository.encerrar_conversa(db, conversa)

    @staticmethod
    def deletar_conversa(db: Session, conversa_id: int, id_usuario: int) -> None:
        """
        Realiza soft delete de uma conversa.
        """
        conversa = AssistenteRepository.buscar_conversa_por_id(db, conversa_id)
        if not conversa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversa não encontrada."
            )
        if conversa.idUsuario != id_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar esta conversa."
            )
        AssistenteRepository.deletar_conversa(db, conversa)
