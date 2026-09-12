from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.repositories.colaborador_repository import ColaboradorRepository
from app.repositories.cargo_colaborador_repository import CargoColaboradorRepository
from app.schemas.colaborador import ColaboradorCreate, ColaboradorUpdate, ColaboradorPaginatedResponse
from app.models.colaboradores_movimento import ColaboradoresMovimento

class ColaboradorService:
    def __init__(self, db: Session):
        self.repository = ColaboradorRepository(db)
        self.cargo_repo = CargoColaboradorRepository(db)

    def get_colaborador(self, colab_id: int):
        colab = self.repository.get_by_id(colab_id)
        if not colab:
            raise HTTPException(status_code=404, detail="Colaborador não encontrado.")
        return colab

    def get_colaboradores(self, page: int = 1, page_size: int = 20, search: str = None):
        if page < 1:
            page = 1
        if page_size > 2000:
            page_size = 2000
            
        skip = (page - 1) * page_size
        items, total = self.repository.get_all(skip=skip, limit=page_size, search=search)
        
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        return ColaboradorPaginatedResponse(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages
        )

    def _validate_fk(self, id_cargo_colaborador: int):
        if not self.cargo_repo.get_by_id(id_cargo_colaborador):
            raise HTTPException(status_code=400, detail="Cargo de colaborador informado não encontrado.")

    def create_colaborador(self, colab_in: ColaboradorCreate, user_id: int):
        self._validate_fk(colab_in.idCargoColaborador)
        
        existente = None
        if getattr(colab_in, "documento", None):
            existente = self.repository.get_by_documento(colab_in.documento)
            
        if existente:
            update_data = colab_in.model_dump(exclude_unset=True, exclude={"origem"})
            for field, value in update_data.items():
                setattr(existente, field, value)
            existente.snAtivo = 'S'
            self.repository.db.commit()
            self.repository.db.refresh(existente)
            novo_colab = existente
        else:
            novo_colab = self.repository.create(colab_in)
        
        movimento = ColaboradoresMovimento(
            idColaboradores=novo_colab.idColaborador,
            origem=colab_in.origem,
            userCreatedId=user_id,
            tipoMovimento='ATIVACAO'
        )
        self.repository.db.add(movimento)
        self.repository.db.commit()
        
        return novo_colab

    def update_colaborador(self, colab_id: int, colab_in: ColaboradorUpdate):
        db_obj = self.get_colaborador(colab_id)
        if colab_in.idCargoColaborador is not None and colab_in.idCargoColaborador != db_obj.idCargoColaborador:
            self._validate_fk(colab_in.idCargoColaborador)
            
        return self.repository.update(db_obj, colab_in)

    def delete_colaborador(self, colab_id: int, user_id: int):
        db_obj = self.get_colaborador(colab_id)
        
        db_obj.snAtivo = 'N'
        
        movimento = ColaboradoresMovimento(
            idColaboradores=db_obj.idColaborador,
            origem='MANUAL',
            userCreatedId=user_id,
            tipoMovimento='DESATIVACAO'
        )
        self.repository.db.add(movimento)
        self.repository.db.commit()
