from sqlalchemy import Column, Integer, Float, DateTime, String, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Movimentacao(Base):
    __tablename__ = "movimentacoes"

    idMovimentacoes = Column(Integer, primary_key=True, index=True, autoincrement=True)
    idCategoria = Column(Integer, ForeignKey("categorias.idCategorias"), nullable=False)
    idColaborador = Column(Integer, ForeignKey("colaboradores.idColaborador"), nullable=False)
    idEmpresa = Column(Integer, ForeignKey("empresas.idEmpresas"), nullable=False)
    idImportacoes = Column(Integer, ForeignKey("importacoes.idImportacoes"), nullable=True)
    nroDocumento = Column(String(100), nullable=True)
    valor = Column(Float(precision=18, decimal_return_scale=2), nullable=False)
    createdAt = Column(DateTime, default=func.now(), nullable=False)
    updatedAte = Column(DateTime, nullable=True, onupdate=func.now())

    importacao = relationship("Importacao", back_populates="movimentacoes")
