from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class CategoriaAlias(Base):
    __tablename__ = "categoria_aliases"

    idcategoria_aliases = Column(Integer, primary_key=True, index=True, autoincrement=True)
    idCategoria = Column(Integer, ForeignKey("categorias.idCategorias"), nullable=False)
    alias = Column(String(45), nullable=False, unique=True, index=True)

    categoria = relationship("Categoria")
