from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class PendenciaMensagem(Base):
    __tablename__ = "nfpendencias_mensagens"

    idmensagem = Column(Integer, primary_key=True, index=True, autoincrement=True)
    idNfPendencias = Column(Integer, ForeignKey("nfpendencias.idnfpendencias"), nullable=False)
    mensagem_id = Column(String(200), nullable=True)
    thread_id = Column(String(100), nullable=True)
    de = Column(String(255), nullable=False)
    para = Column(String(500), nullable=False)
    copia = Column(String(500), nullable=True)
    assunto = Column(String(255), nullable=False)
    conteudo = Column(Text, nullable=False)
    anexos = Column(JSON, nullable=True)
    dataEnvio = Column(DateTime, nullable=True, default=func.now())
    idUserCreated = Column(Integer, ForeignKey("users.iduser"), nullable=True)
    minha_mensagem = Column(String(1), default="S")

    nf_pendencia = relationship("NfPendencia")
    usuario = relationship("User")
