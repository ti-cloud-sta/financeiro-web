from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

class PrevisaoApbItemSchema(BaseModel):
    id: Optional[int] = None
    arquivo: Optional[str] = None
    data: Optional[date] = None
    cod_tp_fluxo: Optional[str] = None
    ent_sai: Optional[str] = None
    prev_real: Optional[str] = None
    modulo: Optional[str] = None
    vlr_cam_2: Optional[float] = None
    trans: Optional[str] = None
    emp: Optional[str] = None
    estab: Optional[str] = None
    esp: Optional[str] = None
    serie: Optional[str] = None
    n_titulo: Optional[str] = None
    parcela: Optional[str] = None
    numero_fornecedor: Optional[str] = None
    nome_abrev: Optional[str] = None
    valor_fluxo: Optional[float] = None
    valor: Optional[float] = None
    nome_emitente: Optional[str] = None
    idImportacoes: Optional[int] = None
    data_criacao: Optional[datetime] = None
    usuario_inclusao: Optional[str] = None

    class Config:
        from_attributes = True

class ImportacaoApbResponse(BaseModel):
    sucesso: bool
    mensagem: str
    idImportacoes: int
    nomeArquivo: str
    totalRegistros: int
    totalValor: float

class PrevisaoAcrItemSchema(BaseModel):
    id: Optional[int] = None
    est: Optional[str] = None
    esp: Optional[str] = None
    ser: Optional[str] = None
    titulo: Optional[str] = None
    parcela: Optional[str] = None
    un_neg: Optional[str] = None
    nr_pedcli: Optional[str] = None
    tipo_pedido: Optional[str] = None
    cliente: Optional[str] = None
    nome_abrev: Optional[str] = None
    nome_cliente: Optional[str] = None
    grp_cliente: Optional[str] = None
    cliente_matriz: Optional[str] = None
    port: Optional[str] = None
    cart: Optional[str] = None
    repres: Optional[str] = None
    emissao: Optional[date] = None
    dt_entrega: Optional[date] = None
    vencto: Optional[date] = None
    dt_agdnto: Optional[date] = None
    liquidac: Optional[date] = None
    refer: Optional[str] = None
    tit_banco: Optional[str] = None
    moeda: Optional[str] = None
    val_original: Optional[float] = None
    saldo: Optional[float] = None
    saldo_apresentacao: Optional[float] = None
    cond_pagto: Optional[str] = None
    vl_descto: Optional[float] = None
    vl_abat: Optional[float] = None
    dias: Optional[int] = None
    pedido_venda: Optional[str] = None
    data_indic: Optional[date] = None
    cond_cobr: Optional[str] = None
    cidade: Optional[str] = None
    telefone: Optional[str] = None
    cidade_cobranca_cliente: Optional[str] = None
    id_federal: Optional[str] = None
    unid_federac: Optional[str] = None
    idImportacoes: Optional[int] = None
    data_criacao: Optional[datetime] = None
    usuario_inclusao: Optional[str] = None

    class Config:
        from_attributes = True

class ImportacaoAcrResponse(BaseModel):
    sucesso: bool
    mensagem: str
    idImportacoes: int
    nomeArquivo: str
    totalRegistros: int
    totalValor: float

class ImportacaoTitulosLiquidadosResponse(BaseModel):
    sucesso: bool
    mensagem: str
    idImportacoes: int
    nomeArquivo: str
    totalRegistros: int
    totalValor: float

class ContaPagarItemDto(BaseModel):
    id: int
    banco: str
    favorecido: str
    categoria: str
    descricao: str
    valor: float
    dataVencimento: str
    tipo: str
    status: str = 'PROGRAMADO'
    numeroDocumento: Optional[str] = None
    idMatriz: Optional[int] = None
    codigoMatriz: Optional[str] = None
    nomeMatriz: Optional[str] = None
    clienteCodigo: Optional[int] = None
    clienteNome: Optional[str] = None

class MatrizAgrupadaTituloDto(BaseModel):
    id: int
    numeroDocumento: Optional[str] = None
    valor: float
    clienteCodigo: Optional[int] = None
    clienteNome: Optional[str] = None
    dataVencimento: Optional[str] = None
    banco: Optional[str] = None
    categoria: Optional[str] = None
    descricao: Optional[str] = None

class MatrizAgrupadaDto(BaseModel):
    idMatriz: Optional[int] = None
    codigoMatriz: Optional[str] = None
    nomeMatriz: str
    banco: str
    tipo: str
    valorTotal: float
    qtdTitulos: int
    titulos: List[MatrizAgrupadaTituloDto] = []

class DashboardVisaoGeralResponse(BaseModel):
    data_referencia: str
    data_formatada: str
    is_hoje: bool

    # KPIs Contas a Pagar
    total_provisao: float
    qtd_provisoes: int
    total_pagar: float
    qtd_pagar_real: int
    total_bb: float
    total_itau: float

    # Listas Contas a Pagar
    contas_bb: List[ContaPagarItemDto] = []
    contas_itau: List[ContaPagarItemDto] = []
    contas_provisao: List[ContaPagarItemDto] = []

    # Matrizes agrupadas para cards
    matrizes_agrupadas: List[MatrizAgrupadaDto] = []

    # Demais campos da Visão Geral
    total_receber: float = 0.0
    qtd_receber: int = 0
    total_receber_carteira: float = 0.0
    total_receber_boleto: float = 0.0
    receber_menor_igual_90: float = 0.0
    receber_maior_90: float = 0.0
    receber_menor_igual_80: float = 0.0
    receber_maior_80: float = 0.0
    saldo_previsibilidade: float = 0.0
    saldo_real_nominal: float = 0.0
    valor_investido_resgatavel: float = 0.0
    contas_receber: List[dict] = []
    matrizes_receber: List[dict] = []
    matrizes_carteira: List[dict] = []
    matrizes_boleto: List[dict] = []


