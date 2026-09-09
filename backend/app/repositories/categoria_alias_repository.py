from sqlalchemy.orm import Session
from app.models.categoria_alias import CategoriaAlias

class CategoriaAliasRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_alias(self, alias: str):
        return self.db.query(CategoriaAlias).filter(
            CategoriaAlias.alias == alias
        ).first()

    def create_or_update(self, id_categoria: int, alias: str):
        # Verifica se já existe esse alias
        existing = self.get_by_alias(alias)

        if existing:
            if existing.idCategoria != id_categoria:
                existing.idCategoria = id_categoria
                self.db.commit()
                self.db.refresh(existing)
            return existing

        new_alias = CategoriaAlias(
            idCategoria=id_categoria,
            alias=alias
        )
        self.db.add(new_alias)
        self.db.commit()
        self.db.refresh(new_alias)
        return new_alias
