from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class Empresa(Base):
    __tablename__ = "empresas"

    idEmpresas = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String(80), nullable=False)
    nomeAbrev = Column(String(45), nullable=True)
    descricao = Column(String(200), nullable=True)
    tipo = Column(String(100), nullable=True)
    createdAt = Column(DateTime, default=func.now())
    updatedAte = Column(DateTime, nullable=True)
