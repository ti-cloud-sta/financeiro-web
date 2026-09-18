from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.categoria import Categoria

class CategoriaAlias(Base):
    __tablename__ = "categorias_aliases"

    idcategorias_aliases = Column(Integer, primary_key=True, index=True, autoincrement=True)
    idCategoria = Column(Integer, ForeignKey("categorias.idCategorias"), nullable=False)
    alias = Column(String(45), nullable=False, unique=True, index=True)

    categoria = relationship("Categoria")
