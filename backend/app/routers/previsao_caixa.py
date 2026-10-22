import logging
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.importacao import Importacao
from app.schemas.previsao_caixa import (
    ImportacaoApbResponse,
    ImportacaoAcrResponse,
    ImportacaoTitulosLiquidadosResponse,
    DashboardVisaoGeralResponse
)
from app.services.previsao_caixa_service import PrevisaoCaixaService

logger = logging.getLogger("santamaria")

router = APIRouter()

def get_previsao_caixa_service(db: Session = Depends(get_db)) -> PrevisaoCaixaService:
    return PrevisaoCaixaService(db)

@router.post(
    "/importar-apb",
    response_model=ImportacaoApbResponse,
    summary="Importa a planilha APB (Contas a Pagar)",
    description="Cria o registro em 'importacoes' e insere em lote todos os registros da aba DADOS na tabela 'previsao_apb'."
)
async def importar_apb(
    file: UploadFile = File(..., description="Arquivo Excel (.xlsx ou .xls) com a aba DADOS"),
    service: PrevisaoCaixaService = Depends(get_previsao_caixa_service),
    current_user: User = Depends(get_current_user)
):
    try:
        return await service.importar_planilha_apb(file=file, current_user=current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro inesperado no endpoint /importar-apb: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Erro interno no processamento do arquivo: {str(e)}")

@router.post(
    "/importar-acr",
    response_model=ImportacaoAcrResponse,
    summary="Importa a planilha ACR (Contas a Receber)",
    description="Cria o registro em 'importacoes' e insere em lote todos os registros da aba ACR/Resumo na tabela 'previsao_acr'."
)
async def importar_acr(
    file: UploadFile = File(..., description="Arquivo Excel (.xlsx ou .xls) com a aba ACR ou Resumo"),
    service: PrevisaoCaixaService = Depends(get_previsao_caixa_service),
    current_user: User = Depends(get_current_user)
):
    try:
        return await service.importar_planilha_acr(file=file, current_user=current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro inesperado no endpoint /importar-acr: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Erro interno no processamento do arquivo: {str(e)}")

@router.post(
    "/importar-titulos-liquidados",
    response_model=ImportacaoTitulosLiquidadosResponse,
    summary="Importa a planilha de Títulos Liquidados",
    description="Cria o registro em 'importacoes' e insere em lote todos os registros da aba liquidados na tabela 'previsao_titulos_liquidados'."
)
async def importar_titulos_liquidados(
    file: UploadFile = File(..., description="Arquivo Excel (.xlsx ou .xls) com a aba liquidados"),
    service: PrevisaoCaixaService = Depends(get_previsao_caixa_service),
    current_user: User = Depends(get_current_user)
):
    try:
        return await service.importar_planilha_titulos_liquidados(file=file, current_user=current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro inesperado no endpoint /importar-titulos-liquidados: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Erro interno no processamento do arquivo: {str(e)}")

@router.get(
    "/importacoes",
    summary="Lista o histórico de importações de previsão de caixa",
    description="Retorna as importações do tipo CONTAS A PAGAR (APB) ou tipos de previsão de caixa."
)
def listar_importacoes_previsao(
    tipo: Optional[str] = Query(None, description="Filtra por tipo específico (ex: CONTAS A PAGAR (APB))"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tipos_padrao = [
        "CONTAS A PAGAR (APB)",
        "CONTAS A RECEBER (ACR)",
        "TITULOS LIQUIDADOS",
        "INVESTIMENTOS"
    ]
    query = db.query(Importacao)
    if tipo:
        query = query.filter(Importacao.tipo == tipo)
    else:
        query = query.filter(Importacao.tipo.in_(tipos_padrao))
    
    itens = query.order_by(Importacao.idImportacoes.desc()).all()
    
    resultado = []
    for item in itens:
        autor_nome = item.usuario.name if item.usuario and item.usuario.name else (item.usuario.email if item.usuario else "Sistema")
        data_hora_str = item.createdAt.strftime("%d/%m/%Y %H:%M") if item.createdAt else "-"
        resultado.append({
            "id": f"IMP-{item.idImportacoes}",
            "idImportacoes": item.idImportacoes,
            "dataHora": data_hora_str,
            "nomeArquivo": item.nomeArquivo,
            "tipo": item.tipo,
            "autor": autor_nome
        })
    return resultado

@router.delete(
    "/importacoes/{id_importacao}",
    summary="Exclui uma importação e seus registros vinculados em cascata"
)
def excluir_importacao_previsao(
    id_importacao: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    importacao = db.query(Importacao).filter(Importacao.idImportacoes == id_importacao).first()
    if not importacao:
        raise HTTPException(status_code=404, detail="Importação não encontrada.")

    try:
        db.delete(importacao)
        db.commit()
        return {"sucesso": True, "mensagem": f"Importação {id_importacao} e registros associados foram excluídos com sucesso."}
    except Exception as e:
        db.rollback()
        logger.exception("Erro ao excluir importação %s: %s", id_importacao, str(e))
        raise HTTPException(status_code=500, detail=f"Erro ao excluir importação: {str(e)}")


@router.get(
    "/visao-geral",
    response_model=DashboardVisaoGeralResponse,
    summary="Dashboard consolidado de Visão Geral da Previsão de Caixa",
    description="Retorna indicadores e listas de Contas a Pagar e Receber para a data de referência (padrão: data atual)."
)
def get_dashboard_visao_geral(
    data: Optional[date] = Query(None, description="Data de referência (padrão: data atual)"),
    service: PrevisaoCaixaService = Depends(get_previsao_caixa_service),
    current_user: User = Depends(get_current_user)
):
    try:
        return service.get_visao_geral(data_ref=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro ao obter dashboard de visão geral: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Erro ao carregar dados de visão geral: {str(e)}")


