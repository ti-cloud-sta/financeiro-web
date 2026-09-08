from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.unidade import UnidadeCreate, UnidadeUpdate, UnidadeResponse, UnidadePaginatedResponse
from app.services.unidade_service import unidade_service
import math

router = APIRouter()

@router.get("", response_model=UnidadePaginatedResponse)
def read_unidades(page: int = 1, page_size: int = 100, search: str = None, db: Session = Depends(get_db)):
    skip = (page - 1) * page_size
    limit = page_size
    items, total = unidade_service.get_unidades(db, skip=skip, limit=limit, search=search)
    total_pages = math.ceil(total / limit) if limit > 0 else 1
    return {
        "items": items,
        "page": page,
        "page_size": limit,
        "total": total,
        "total_pages": total_pages
    }

@router.post("", response_model=UnidadeResponse, status_code=status.HTTP_201_CREATED)
def create_unidade(unidade: UnidadeCreate, db: Session = Depends(get_db)):
    return unidade_service.create_unidade(db=db, obj_in=unidade)

@router.get("/{id}", response_model=UnidadeResponse)
def read_unidade(id: int, db: Session = Depends(get_db)):
    db_obj = unidade_service.get_unidade(db, id=id)
    if db_obj is None:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")
    return db_obj

@router.put("/{id}", response_model=UnidadeResponse)
def update_unidade(id: int, unidade: UnidadeUpdate, db: Session = Depends(get_db)):
    db_obj = unidade_service.update_unidade(db, id=id, obj_in=unidade)
    if db_obj is None:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")
    return db_obj

@router.delete("/{id}")
def delete_unidade(id: int, db: Session = Depends(get_db)):
    db_obj = unidade_service.delete_unidade(db, id=id)
    if db_obj is None:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")
    return {"detail": "Unidade excluída com sucesso"}
