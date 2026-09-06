from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.plano_saude import RelatorioGeralResponse
from app.services.plano_saude_service import PlanoSaudeService

router = APIRouter()

@router.get("/relatorio-geral", response_model=RelatorioGeralResponse)
def get_relatorio_geral(
    mes: int = Query(..., description="Mês da competência"),
    ano: int = Query(..., description="Ano da competência"),
    search: str = Query(None, description="Busca por nome, empresa ou unidade"),
    id_empresa: int = Query(None, description="Filtro opcional por empresa"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        service = PlanoSaudeService(db)
        return service.obter_relatorio_geral(mes=mes, ano=ano, search=search, id_empresa=id_empresa, page=page, size=size)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/relatorio-geral/exportar")
def exportar_relatorio_geral(
    mes: int = Query(..., description="Mês da competência"),
    ano: int = Query(..., description="Ano da competência"),
    search: str = Query(None, description="Busca por nome, empresa ou unidade"),
    id_empresa: int = Query(None, description="Filtro opcional por empresa"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        service = PlanoSaudeService(db)
        return service.exportar_relatorio_geral(mes=mes, ano=ano, search=search, id_empresa=id_empresa)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/relatorio-geral/contabilidade")
def gerar_relatorio_contabilidade(
    mes: int = Query(..., description="Mês da competência"),
    ano: int = Query(..., description="Ano da competência"),
    search: str = Query(None, description="Busca por nome, empresa ou unidade"),
    id_empresa: int = Query(None, description="Filtro opcional por empresa"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        service = PlanoSaudeService(db)
        return service.gerar_relatorio_contabilidade(mes=mes, ano=ano, search=search, id_empresa=id_empresa)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/relatorio-geral/contabilidade-txt")
def gerar_relatorio_contabilidade_txt(
    mes: int = Query(..., description="Mês da competência"),
    ano: int = Query(..., description="Ano da competência"),
    search: str = Query(None, description="Busca por nome, empresa ou unidade"),
    id_empresa: int = Query(None, description="Filtro opcional por empresa"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        service = PlanoSaudeService(db)
        return service.gerar_relatorio_contabilidade_txt(mes=mes, ano=ano, search=search, id_empresa=id_empresa)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/relatorio-geral/conciliar")
def conciliar_relatorio_geral(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        service = PlanoSaudeService(db)
        return service.conciliar_planilha(file)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) or "Falha ao processar a planilha de conciliação.")
