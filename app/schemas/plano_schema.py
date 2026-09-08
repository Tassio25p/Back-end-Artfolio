from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class PlanoResposta(BaseModel):
    id: int
    tipo: str
    precoPlano: Optional[float] = Field(None, alias="precoPlano")
    descricao: Optional[str] = None
    isAtivo: bool = Field(True, alias="isAtivo")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class AssinaturaResposta(BaseModel):
    id: int
    idUsuario: int = Field(..., alias="idUsuario")
    idPlano: int = Field(..., alias="idPlano")
    dataInicio: Optional[datetime] = Field(None, alias="dataInicio")
    dataFim: Optional[datetime] = Field(None, alias="dataFim")
    ativa: bool = True
    plano: Optional[PlanoResposta] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class MeuPlanoResposta(BaseModel):
    tipo: str = "Free"
    nomeExibicao: str = "Artfolio Free"
    cor: str = "artGreen"
    precoPlano: float = 0.00
    mostrar_moldura_led: bool = True
    mensagem_cta: Optional[str] = None
    limiteArquivosPorPost: int = 1
    permiteCarrossel: bool = False
    permiteAnalytics: bool = False
    permiteDestaqueFeed: bool = False
    assinatura: Optional[AssinaturaResposta] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
