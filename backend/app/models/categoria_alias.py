from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class CategoriaAlias(Base):
    __tablename__ = "categorias_aliases"

    idcategorias_aliases = Column(Integer, primary_key=True, index=True, autoincrement=True)
    idCategoria = Column(Integer, ForeignKey("categorias.idCategorias"), nullable=False)
    alias = Column(String(45), nullable=False)

    categoria = relationship("Categoria")
