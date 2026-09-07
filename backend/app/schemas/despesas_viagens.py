from pydantic import BaseModel
from typing import List, Optional

class DespesaExtraida(BaseModel):
    empresa: str
    colaborador: str
    categoria: str
    valor: float
    data: Optional[str] = None

class EstruturaExtracaoIADespesas(BaseModel):
    despesas: List[DespesaExtraida]

class SalvarDespesaViagemPayload(BaseModel):
    nomeArquivo: str
    despesas: List[DespesaExtraida]
    idUserInc: Optional[int] = None
