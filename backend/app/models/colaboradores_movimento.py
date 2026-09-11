from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class ColaboradoresMovimento(Base):
    __tablename__ = "colaboradoresmovimento"

    idcolaboradoresmovimento = Column(Integer, primary_key=True, index=True, autoincrement=True)
    idColaboradores = Column(Integer, ForeignKey("colaboradores.idColaborador"), nullable=False, index=True)
    origem = Column(String(100), nullable=False, comment='IMPORTACORES, ATUALIZACAO_BASE, MANUAL')
    userCreatedId = Column(Integer, nullable=False)
    tipoMovimento = Column(String(45), nullable=False, comment='ATIVACAO, DESATIVACAO')
    createdAt = Column(DateTime, nullable=False, default=func.now())

    colaborador = relationship("Colaborador")
