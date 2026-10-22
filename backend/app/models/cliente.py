from sqlalchemy import Column, Integer, String, ForeignKey
from app.core.database import Base

class Cliente(Base):
    __tablename__ = "clientes"

    idclientes = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codigo = Column(Integer, nullable=True)
    nome = Column(String(100), nullable=True)
    nome_abrev = Column(String(100), nullable=True)
    idMatriz = Column(Integer, ForeignKey("matrizcliente.idmatrizCliente"), nullable=True)
    idRepresentante = Column(Integer, ForeignKey("representantes.idRepresentante"), nullable=True)
