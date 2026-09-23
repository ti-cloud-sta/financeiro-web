from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import or_
from typing import List, Tuple
from app.models.importacao import Importacao

class ImportacaoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, page: int = 1, size: int = 10, search: str = None, categoria: str = None) -> Tuple[List[Importacao], int]:
        query = self.db.query(Importacao)
        
        if categoria:
            # Aceita vários tipos separados por vírgula (ex.: "PENDENCIAS,Importação DATASUL")
            categorias = [c.strip() for c in categoria.split(",") if c.strip()]
            query = query.filter(or_(*[Importacao.tipo.ilike(f"{c}%") for c in categorias]))
            
        if search:
            query = query.filter(
                or_(
                    Importacao.nomeArquivo.ilike(f"%{search}%"),
                    Importacao.tipo.ilike(f"%{search}%")
                )
            )
            
        total = query.count()
        offset = (page - 1) * size
        # Order by idImportacoes desc to show latest first
        items = (
            query.options(
                joinedload(Importacao.empresa),
                selectinload(Importacao.movimentacoes)
            )
            .order_by(Importacao.idImportacoes.desc())
            .offset(offset)
            .limit(size)
            .all()
        )
        
        return items, total

    def delete(self, id_importacao: int) -> bool:
        from sqlalchemy import text
        # Desvincular as pendências da importação antes de deletar
        # Isso previne que a restrição ON DELETE CASCADE apague as pendências e
        # falhe por causa de mensagens vinculadas (IntegrityError).
        self.db.execute(
            text("UPDATE nfpendencias SET idImportacoes = NULL WHERE idImportacoes = :id"),
            {"id": id_importacao}
        )
        self.db.flush()

        importacao = self.db.query(Importacao).filter(Importacao.idImportacoes == id_importacao).first()
        if importacao:
            self.db.delete(importacao)
            self.db.commit()
            return True
        return False
