from sqlalchemy import Column, Integer, String, Date, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class NfPendencia(Base):
    __tablename__ = "nfpendencias"

    idnfpendencias = Column(Integer, primary_key=True, index=True, autoincrement=True)
    idUnidade = Column(Integer, ForeignKey("Unidade.idUnidade"), nullable=True)       # Coluna A - Est (via lookup em unidade.codigo)
    especie = Column(String(5), nullable=True)                                        # Coluna B - Esp (DP, AD, AN)
    serie = Column(Integer, nullable=True)                                            # Coluna C - Ser
    titulo = Column(String(50), nullable=True)                                        # Coluna D - Título (ex.: "0017356", "270826-3")
    parccela = Column(Float, nullable=True)                                           # Coluna E - /P
    nrPedidoCliente = Column(Integer, nullable=True)                                  # Coluna F - Nr Pedcli
    tipoPedido = Column(String(45), nullable=True)                                    # Coluna G - Tipo Pedido (PV, ER, E1, PX)
    idCliente = Column(Integer, ForeignKey("clientes.idclientes"), nullable=True)
    idClienteMatriz = Column(Integer, ForeignKey("matrizcliente.idmatrizCliente"), nullable=True)
    portador = Column(Integer, nullable=True)                                         # Coluna L - Port
    carteira = Column(String(45), nullable=True)                                      # Coluna M - Cart (DEV, CAR, DES, SIM, VIN)
    dtEmissao = Column(Date, nullable=True)                                           # Coluna N - Emissão
    dtEntrega = Column(Date, nullable=True)                                           # Coluna O - Dt Entrega
    dtVencimento = Column(Date, nullable=True)                                        # Coluna P - Vencto
    valorOriginal = Column(Float(precision=18, decimal_return_scale=2), nullable=True)  # Coluna T - Val Original
    valorSaldo = Column(Float(precision=18, decimal_return_scale=2), nullable=True)     # Coluna U - Saldo

    idImportacoes = Column(Integer, ForeignKey("importacoes.idImportacoes"), nullable=True)
    createdAt = Column(DateTime, nullable=True, default=func.now())
    encerrado = Column(String(1), server_default='S')
    fase = Column(String(100), nullable=True)
    status = Column(String(100), nullable=True)

    unidade_rel = relationship("Unidade")
    cliente = relationship("Cliente")
    matriz_cliente = relationship("MatrizCliente")
    importacao = relationship("Importacao")

class VwNfPendenciaFase(Base):
    __tablename__ = "vw_nfpendencias_fase"
    
    idnfpendencias = Column(Integer, primary_key=True)
    titulo = Column(String(50))
    dtVencimento = Column(Date)
    createdAt = Column(DateTime)
    idCliente = Column(Integer, ForeignKey("clientes.idclientes"))
    fase = Column(String(100))
    status = Column(String(100))
    especie = Column(String(5))
    carteira = Column(String(45))
    
    idUnidade = Column(Integer)
    serie = Column(String(10))
    parccela = Column(String(5))
    portador = Column(String(45))
    dtEmissao = Column(Date)
    dtEntrega = Column(Date)
    valorOriginal = Column(Float)
    valorSaldo = Column(Float)
    
    cliente = relationship("Cliente")
