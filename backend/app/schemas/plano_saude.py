from pydantic import BaseModel
from typing import List, Optional

class RelatorioGeralRow(BaseModel):
    competencia: str
    unidade: Optional[str] = None
    empresa: Optional[str] = None
    nome: Optional[str] = None
    centro_custo: Optional[str] = None
    total: float

class RelatorioGeralResponse(BaseModel):
    items: List[RelatorioGeralRow]
    total: int
    total_valor: float
    page: int
    size: int

class ConciliacaoRow(BaseModel):
    unidade_codigo: str
    unidade_descricao: str
    empresa_abrev: str
    total_planilha: float
    total_sistema: float
    diferenca: float
    status: str

class ConciliacaoResponse(BaseModel):
    competencia: str
    linhas: List[ConciliacaoRow]
    total_divergencias: int
    total_processado: int

class DependentConfirmar(BaseModel):
    nome: str
    valor: float

class TitularConfirmar(BaseModel):
    nome_pdf: str
    nome_db: str
    valor_titular: float
    dependentes: List[DependentConfirmar]
    valor_total: float
    centro_custo: Optional[str] = "N/D"
    documento: Optional[str] = None
    id_db: Optional[int] = None

class ConfirmarImportacaoSorrisoPayload(BaseModel):
    nomeArquivo: str
    titulares: List[TitularConfirmar]
    idEmpresa: Optional[int] = None
    idUnidade: int
    idUserInc: Optional[int] = None
    dataCompetencia: Optional[str] = None

class ExportarSorrisoExcelPayload(BaseModel):
    titulares: List[TitularConfirmar]

class DependentConfirmarUnimed(BaseModel):
    nome: str
    tipo: Optional[str] = "D"
    valor: float

class TitularConfirmarUnimed(BaseModel):
    nome_pdf: str
    nome_db: str
    matricula: Optional[str] = ""
    valor_titular: float
    dependentes: List[DependentConfirmarUnimed]
    valor_total: float
    centro_custo: Optional[str] = "N/D"
    documento: Optional[str] = None
    id_db: Optional[int] = None

class ConfirmarImportacaoUnimedPayload(BaseModel):
    nomeArquivo: str
    titulares: List[TitularConfirmarUnimed]
    idEmpresa: Optional[int] = None
    idUnidade: int
    idUserInc: Optional[int] = None
    dataCompetencia: Optional[str] = None

class ExportarUnimedExcelPayload(BaseModel):
    titulares: List[TitularConfirmarUnimed]
