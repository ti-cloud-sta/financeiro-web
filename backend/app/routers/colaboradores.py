from fastapi import APIRouter, Depends, status, UploadFile, File
from app.api.deps import get_current_user
from app.models.user import User
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from app.core.database import get_db
from app.schemas.colaborador import ColaboradorResponse, ColaboradorCreate, ColaboradorUpdate, ColaboradorPaginatedResponse
from app.schemas.colaborador_import import ImportPreviewResponse, ImportProcessarRequest, ImportProcessarResponse
from app.services.colaborador_service import ColaboradorService
from app.services.colaborador_import_service import ColaboradorImportService
from app.services import colaborador_movimento_service
from app.models.importacao import Importacao

router = APIRouter()

def get_service(db: Session = Depends(get_db)):
    return ColaboradorService(db)

def get_import_service(db: Session = Depends(get_db)):
    return ColaboradorImportService(db)

@router.get("/movimentos")
def listar_movimentos(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    tipo: Optional[str] = None,
    origem: Optional[str] = None,
    page: int = 1,
    size: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return colaborador_movimento_service.listar_movimentos(
        db=db, data_inicio=data_inicio, data_fim=data_fim,
        tipo=tipo, origem=origem, page=page, size=size
    )

@router.get("", response_model=ColaboradorPaginatedResponse)
def list_colaboradores(
    page: int = 1,
    page_size: int = 20,
    q: Optional[str] = None,
    service: ColaboradorService = Depends(get_service)
):
    return service.get_colaboradores(page=page, page_size=page_size, search=q)

@router.post("", response_model=ColaboradorResponse, status_code=status.HTTP_201_CREATED)
def create_colaborador(
    colab_in: ColaboradorCreate,
    service: ColaboradorService = Depends(get_service),
    current_user: User = Depends(get_current_user)
):
    return service.create_colaborador(colab_in, current_user.iduser)

@router.post("/importar/preview", response_model=ImportPreviewResponse)
async def preview_importacao_colaboradores(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    service: ColaboradorImportService = Depends(get_import_service)
):
    conteudo = await file.read()

    nome_arquivo = file.filename or "desconhecido.xlsx"
    extensao = nome_arquivo.split('.')[-1] if '.' in nome_arquivo else ''
    db.add(Importacao(nomeArquivo=nome_arquivo, extensaoArquivo=extensao, idEmpresa=None, tipo="COLABORADORES"))
    db.commit()

    return service.preview(conteudo)

@router.post("/importar/processar", response_model=ImportProcessarResponse)
def processar_importacao_colaboradores(
    payload: ImportProcessarRequest,
    service: ColaboradorImportService = Depends(get_import_service),
    current_user: User = Depends(get_current_user)
):
    return service.processar(payload, current_user.iduser)

@router.get("/{id}", response_model=ColaboradorResponse)
def get_colaborador(
    id: int,
    service: ColaboradorService = Depends(get_service)
):
    return service.get_colaborador(id)

@router.put("/{id}", response_model=ColaboradorResponse)
def update_colaborador(
    id: int,
    colab_in: ColaboradorUpdate,
    service: ColaboradorService = Depends(get_service)
):
    return service.update_colaborador(id, colab_in)

@router.patch("/{id}", response_model=ColaboradorResponse)
def patch_colaborador(
    id: int,
    colab_in: ColaboradorUpdate,
    service: ColaboradorService = Depends(get_service)
):
    return service.update_colaborador(id, colab_in)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_colaborador(
    id: int,
    service: ColaboradorService = Depends(get_service),
    current_user: User = Depends(get_current_user)
):
    service.delete_colaborador(id, current_user.iduser)
