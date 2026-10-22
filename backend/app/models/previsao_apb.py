from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class PrevisaoApb(Base):
    __tablename__ = "previsao_apb"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    arquivo = Column(String(50), nullable=True)
    data = Column(Date, nullable=True, index=True)
    cod_tp_fluxo = Column(String(20), nullable=True)
    ent_sai = Column(String(10), nullable=True)
    prev_real = Column(String(10), nullable=True, index=True)
    modulo = Column(String(20), nullable=True, index=True)
    vlr_cam_2 = Column(Numeric(15, 2), nullable=True)
    trans = Column(String(100), nullable=True)
    emp = Column(String(10), nullable=True)
    estab = Column(String(10), nullable=True)
    esp = Column(String(10), nullable=True)
    serie = Column(String(20), nullable=True)
    n_titulo = Column(String(50), nullable=True, index=True)
    parcela = Column(String(10), nullable=True)
    numero_fornecedor = Column(String(30), nullable=True, index=True)
    nome_abrev = Column(String(100), nullable=True)
    valor_fluxo = Column(Numeric(15, 2), nullable=True)
    valor = Column(Numeric(15, 2), nullable=True)
    nome_emitente = Column(String(255), nullable=True)

    # Colunas de auditoria e controle de importação
    idImportacoes = Column(Integer, ForeignKey("importacoes.idImportacoes", ondelete="CASCADE"), nullable=True, index=True)
    data_criacao = Column(DateTime, nullable=False, default=func.now())
    usuario_inclusao = Column(String(100), nullable=True)

    # Relacionamento com a tabela de importacoes
    importacao = relationship("Importacao")


class VwPrevisaoApb(Base):
    __tablename__ = "vw_previsao_apb"

    id = Column(Integer, primary_key=True)
    idImportacoes = Column(Integer, nullable=True)
    arquivo = Column(String(50), nullable=True)
    data = Column(Date, nullable=True)
    cod_tp_fluxo = Column(String(20), nullable=True)
    ent_sai = Column(String(10), nullable=True)
    prev_real = Column(String(10), nullable=True)
    modulo = Column(String(20), nullable=True)
    vlr_cam_2 = Column(Numeric(15, 2), nullable=True)
    trans = Column(String(100), nullable=True)
    emp = Column(String(10), nullable=True)
    estab = Column(String(10), nullable=True)
    esp = Column(String(10), nullable=True)
    serie = Column(String(20), nullable=True)
    n_titulo = Column(String(50), nullable=True)
    parcela = Column(String(10), nullable=True)
    numero_fornecedor = Column(String(30), nullable=True)
    nome_abrev = Column(String(100), nullable=True)
    valor_fluxo = Column(Numeric(15, 2), nullable=True)
    valor = Column(Numeric(15, 2), nullable=True)
    nome_emitente = Column(String(255), nullable=True)
    data_criacao = Column(DateTime, nullable=True)
    usuario_inclusao = Column(String(100), nullable=True)

    # Colunas calculadas pela view
    tipo_conta = Column(String(20), nullable=True)      # 'REAL' ou 'PROVISAO'
    banco_destino = Column(String(20), nullable=True)   # 'PROVISAO', 'BANCO_DO_BRASIL' ou 'ITAU'

