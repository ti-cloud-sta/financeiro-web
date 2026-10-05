from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class TurnoverPlanoSaude(Base):
    __tablename__ = "turnover_planos_saude"
    
    idTurnoverPlano = Column(Integer, primary_key=True, index=True, autoincrement=True)
    idColaborador = Column(Integer, ForeignKey("colaboradores.idColaborador"), nullable=False, index=True)
    idEmpresa = Column(Integer, ForeignKey("empresas.idEmpresas"), nullable=False, index=True)
    idImportacao = Column(Integer, ForeignKey("importacoes.idImportacoes"), nullable=False, index=True)
    competencia = Column(String(7), nullable=True)
    valor = Column(Numeric(10, 2), nullable=True)
    resolvido = Column(String(1), default='N', nullable=True)
    createdAt = Column(DateTime, nullable=False, default=func.now())

    colaborador = relationship("Colaborador")
    empresa = relationship("Empresa")
    importacao = relationship("Importacao")
