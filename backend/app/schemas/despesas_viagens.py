from pydantic import BaseModel
from typing import List, Optional

class DespesaExtraida(BaseModel):
    empresa: str
    colaborador: str
    colaborador_original: Optional[str] = None
    categoria: str
    categoria_original: Optional[str] = None
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
    idUnidade: Optional[int] = None        # Adicionado campo Unidade
    isManualEntry: Optional[bool] = False   # True = lançamento manual (sem importação)
    idEmpresaManual: Optional[int] = None  # empresa selecionada no modal manual


class ConciliacaoViagemUnidadeRow(BaseModel):
    unidade_codigo: str
    unidade_descricao: str
    total_planilha: float
    total_sistema: float
    diferenca: float
    status: str
    observacao: Optional[str] = None


class ConciliacaoViagemEmpresaRow(BaseModel):
    unidade_codigo: str
    empresa_nome: str
    empresa_abrev: str
    total_planilha: float
    total_sistema: float
    diferenca: float
    status: str
    observacao: Optional[str] = None


class ConciliacaoViagemPessoaRow(BaseModel):
    unidade_codigo: str
    colaborador_nome: str
    nome_abrev: str
    total_planilha: float
    total_sistema_rdv: float
    total_sistema_geral: float
    diferenca: float
    status: str
    observacao: Optional[str] = None


class ConciliacaoViagensResponse(BaseModel):
    competencia: str
    total_planilha: float
    total_sistema: float
    diferenca_total: float
    status_geral: str
    total_empresas_planilha: float
    total_pessoas_planilha: float
    soma_empresas_pessoas_planilha: float
    unidades: List[ConciliacaoViagemUnidadeRow]
    empresas: List[ConciliacaoViagemEmpresaRow]
    pessoas: List[ConciliacaoViagemPessoaRow]
    total_processado: int
    total_divergencias: int
