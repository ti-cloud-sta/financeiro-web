from pydantic import BaseModel
from typing import List, Optional

class DespesaExtraida(BaseModel):
    empresa: str
    colaborador: str
    colaborador_original: Optional[str] = None
    categoria: str
    valor: float
    data: Optional[str] = None
    nroDocumento: Optional[str] = None

class EstruturaExtracaoIADespesas(BaseModel):
    despesas: List[DespesaExtraida]

class SalvarDespesaViagemPayload(BaseModel):
    nomeArquivo: str
    despesas: List[DespesaExtraida]
    idUserInc: Optional[int] = None
    dataCompetencia: Optional[str] = None  # YYYY-MM-DD — data do form para o createdAt
    isManualEntry: Optional[bool] = False   # True = lançamento manual (sem importação)
    idEmpresaManual: Optional[int] = None  # empresa selecionada no modal manual
