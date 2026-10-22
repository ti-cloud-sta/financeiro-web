from sqlalchemy import Column, Integer, String
from app.core.database import Base

class MatrizCliente(Base):
    __tablename__ = "matrizcliente"

    idmatrizCliente = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codigo = Column(String(200), nullable=True)
    nome = Column(String(100), nullable=True)

