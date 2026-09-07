from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User

from app.repositories.categoria_repository import CategoriaRepository
from app.repositories.colaborador_repository import ColaboradorRepository

from app.schemas.despesas_viagens import SalvarDespesaViagemPayload
from app.services.despesas_viagens_parser_service import DespesasViagensParserService
from app.services.despesas_viagens_service import DespesasViagensService

router = APIRouter()

@router.post("/analisar-arquivo")
async def analisar_arquivo_despesas(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    empresa_nome: str = Form(...),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo inválido")
        
    try:
        content = await file.read()
        
        cat_repo = CategoriaRepository(db)
        colab_repo = ColaboradorRepository(db)
        
        categorias_db, _ = cat_repo.get_all(limit=1000)
        nomes_categorias = [c.nome for c in categorias_db]
        
        colabs_db, _ = colab_repo.get_all(limit=5000)
        nomes_colaboradores = [c.nome for c in colabs_db]
        
        parser_service = DespesasViagensParserService()
        resultado = await parser_service.analisar_arquivo(
            file_content=content,
            file_name=file.filename,
            categorias=nomes_categorias,
            colaboradores=nomes_colaboradores,
            empresa_context=empresa_nome,
            db=db
        )
        
        despesas_brutas = resultado.get("despesas", [])
        file_to_delete = resultado.get("file_name_to_delete")
        
        if file_to_delete:
            background_tasks.add_task(parser_service.deletar_arquivo, file_to_delete)
            
        consolidadas = {}
        for d in despesas_brutas:
            chave = f"{d['colaborador']}|{d['categoria']}"
            if chave not in consolidadas:
                consolidadas[chave] = d
            else:
                consolidadas[chave]['valor'] += d['valor']
                
        resultado_final = list(consolidadas.values())
        
        return {"sucesso": True, "dados": resultado_final, "metrics": resultado.get("metrics")}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/confirmar-importacao")
def confirmar_importacao_despesas(
    payload: SalvarDespesaViagemPayload,
    db: Session = Depends(get_db)
):
    try:
        service = DespesasViagensService(db)
        return service.salvar_importacao(payload)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/visao-geral")
def get_dashboard_visao_geral(
    data_inicio: str = Query(None),
    data_fim: str = Query(None),
    id_empresa: int = Query(None),
    id_colaborador: int = Query(None),
    id_categoria: int = Query(None),
    db: Session = Depends(get_db)
):
    try:
        service = DespesasViagensService(db)
        filtros = {
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "id_empresa": id_empresa,
            "id_colaborador": id_colaborador,
            "id_categoria": id_categoria
        }
        return service.obter_visao_geral(filtros)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/comercial")
def get_dashboard_comercial(
    data_inicio: str = Query(None),
    data_fim: str = Query(None),
    id_empresa: int = Query(None),
    id_colaborador: int = Query(None),
    id_categoria: int = Query(None),
    db: Session = Depends(get_db)
):
    try:
        service = DespesasViagensService(db)
        filtros = {
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "id_empresa": id_empresa,
            "id_colaborador": id_colaborador,
            "id_categoria": id_categoria
        }
        return service.obter_visao_comercial(filtros)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
