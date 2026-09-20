from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class ClienteRepresentante(Base):
    __tablename__ = "clienterepresentante"

    idclienterepresentante = Column(Integer, primary_key=True, index=True, autoincrement=True)
    idCliente = Column(Integer, ForeignKey("clientes.idclientes"), nullable=False)
    idRepresentante = Column(Integer, ForeignKey("colaboradores.idColaborador"), nullable=False)

    # cliente = relationship("Cliente")
    # representante = relationship("Colaborador")
