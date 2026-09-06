from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

class EmpresaBase(BaseModel):
    nome: Optional[str] = Field(None, max_length=80)
    descricao: Optional[str] = Field(None, max_length=200)
    tipo: Optional[str] = Field(None, max_length=100)

class EmpresaCreate(EmpresaBase):
    nome: str = Field(..., max_length=80)
    modulo_id: Optional[int] = None
    modulo_ids: Optional[List[int]] = None

class EmpresaUpdate(EmpresaBase):
    modulo_ids: Optional[List[int]] = None

class EmpresaResponse(EmpresaBase):
    idEmpresas: int
    modulo_ids: Optional[List[int]] = None
    nome: str
    createdAt: Optional[datetime] = None
    updatedAte: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class EmpresaPaginatedResponse(BaseModel):
    items: List[EmpresaResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
