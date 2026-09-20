from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.schemas.cliente import ClienteResponse, VincularClientesRequest
from app.services.cliente_service import ClienteService
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/", response_model=List[ClienteResponse])
def get_clientes(
    id_representante: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return ClienteService.get_clientes(db, id_representante)

@router.post("/representante/{id_representante}/vincular")
def vincular_clientes(
    id_representante: int,
    payload: VincularClientesRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        ClienteService.vincular_clientes(db, id_representante, payload.ids_clientes)
        return {"message": "Vínculos atualizados com sucesso."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
