from pydantic import BaseModel
from typing import Optional, List

class ClienteBase(BaseModel):
    codigo: Optional[int] = None
    nome: Optional[str] = None

class ClienteResponse(ClienteBase):
    idclientes: int
    linked: bool = False

    class Config:
        from_attributes = True

class VincularClientesRequest(BaseModel):
    ids_clientes: List[int]
