from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.centro_custo import CentroCustoCreate, CentroCustoUpdate, CentroCustoResponse, CentroCustoPaginatedResponse
from app.services.centro_custo_service import centro_custo_service
import math

router = APIRouter()

@router.get("", response_model=CentroCustoPaginatedResponse)
def read_centros_custo(page: int = 1, page_size: int = 100, search: str = None, db: Session = Depends(get_db)):
    skip = (page - 1) * page_size
    limit = page_size
    items, total = centro_custo_service.get_centros_custo(db, skip=skip, limit=limit, search=search)
    total_pages = math.ceil(total / limit) if limit > 0 else 1
    return {
        "items": items,
        "page": page,
        "page_size": limit,
        "total": total,
        "total_pages": total_pages
    }

@router.post("", response_model=CentroCustoResponse, status_code=status.HTTP_201_CREATED)
def create_centro_custo(centro_custo: CentroCustoCreate, db: Session = Depends(get_db)):
    return centro_custo_service.create_centro_custo(db=db, obj_in=centro_custo)

@router.get("/{id}", response_model=CentroCustoResponse)
def read_centro_custo(id: int, db: Session = Depends(get_db)):
    db_obj = centro_custo_service.get_centro_custo(db, id=id)
    if db_obj is None:
        raise HTTPException(status_code=404, detail="Centro de Custo não encontrado")
    return db_obj

@router.put("/{id}", response_model=CentroCustoResponse)
def update_centro_custo(id: int, centro_custo: CentroCustoUpdate, db: Session = Depends(get_db)):
    db_obj = centro_custo_service.update_centro_custo(db, id=id, obj_in=centro_custo)
    if db_obj is None:
        raise HTTPException(status_code=404, detail="Centro de Custo não encontrado")
    return db_obj

@router.delete("/{id}")
def delete_centro_custo(id: int, db: Session = Depends(get_db)):
    db_obj = centro_custo_service.delete_centro_custo(db, id=id)
    if db_obj is None:
        raise HTTPException(status_code=404, detail="Centro de Custo não encontrado")
    return {"detail": "Centro de Custo excluído com sucesso"}
