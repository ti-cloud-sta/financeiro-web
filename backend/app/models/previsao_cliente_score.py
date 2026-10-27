from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class PrevisaoClienteScore(Base):
    __tablename__ = "previsao_cliente_score"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_matriz = Column(Integer, nullable=False, unique=True, index=True)
    codigo_matriz = Column(String(100), nullable=True, index=True)
    nome_matriz = Column(String(255), nullable=True)
    cliente = Column(String(50), nullable=True)
    nome_cliente = Column(String(255), nullable=True)
    
    score_final = Column(Numeric(5, 2), nullable=False, default=60.00, index=True)
    pontos_ultimos_5 = Column(Numeric(5, 2), nullable=False, default=0.00)
    pontos_recorrencia = Column(Numeric(5, 2), nullable=False, default=0.00)
    pontos_media_geral = Column(Numeric(5, 2), nullable=False, default=0.00)
    
    classificacao_media = Column(String(20), nullable=True)
    total_titulos_historico = Column(Integer, nullable=False, default=0)
    titulos_em_dia = Column(Integer, nullable=False, default=0)
    titulos_em_atraso = Column(Integer, nullable=False, default=0)
    media_dias_atraso = Column(Numeric(5, 2), nullable=False, default=0.00)
    valor_total_liquidado = Column(Numeric(15, 2), nullable=False, default=0.00)
    ultimos_5_em_dia = Column(Integer, nullable=False, default=0)
    ultimos_5_total = Column(Integer, nullable=False, default=0)
    
    data_atualizacao = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    idImportacoes = Column(Integer, ForeignKey("importacoes.idImportacoes", ondelete="SET NULL"), nullable=True)

    importacao = relationship("Importacao")
