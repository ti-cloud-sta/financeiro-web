import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings

logger = logging.getLogger("santamaria")

# Swagger/ReDoc/OpenAPI só ficam expostos em ambiente de desenvolvimento
# (ENVIRONMENT=development no .env). Em produção (padrão) ficam desligados.
_docs_enabled = settings.ENVIRONMENT == "development"

app = FastAPI(
    title="SantaMaria API",
    description="API REST para gestão do ERP SantaMaria.",
    version="1.0.0",
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

# Configuração de CORS (permitir todos os origens por padrão para desenvolvimento).
# allow_credentials fica False: a autenticação é via header "Authorization: Bearer <token>"
# (não usa cookies), então não há necessidade de credentials e evita a combinação
# allow_origins=["*"] + allow_credentials=True, que expõe requisições autenticadas
# vindas de qualquer origem.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code >= 500:
        logger.exception("Erro interno em %s %s: %s", request.method, request.url.path, exc.detail)
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno no servidor. Tente novamente mais tarde."},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Exceção não tratada em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno no servidor. Tente novamente mais tarde."},
    )


@app.get("/", tags=["Root"])
def root():
    if _docs_enabled:
        return {"message": "SantaMaria API is running. Acesso a documentação em /docs"}
    return {"message": "SantaMaria API is running."}

from fastapi import Depends
from app.api.deps import get_current_user
from app.routers import (
    auth, categorias, empresas, cargos_colaboradores,
    colaboradores, centros_custo, unidades, importacoes, users,
    plano_saude, despesas_viagens
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Autenticação"])
app.include_router(categorias.router, prefix="/api/v1/categorias", tags=["Categorias"], dependencies=[Depends(get_current_user)])
app.include_router(empresas.router, prefix="/api/v1/empresas", tags=["Empresas"], dependencies=[Depends(get_current_user)])
app.include_router(cargos_colaboradores.router, prefix="/api/v1/cargos-colaboradores", tags=["Cargos de Colaboradores"], dependencies=[Depends(get_current_user)])
app.include_router(colaboradores.router, prefix="/api/v1/colaboradores", tags=["Colaboradores"], dependencies=[Depends(get_current_user)])
app.include_router(centros_custo.router, prefix="/api/v1/centros-custo", tags=["Centros de Custo"], dependencies=[Depends(get_current_user)])
app.include_router(unidades.router, prefix="/api/v1/unidades", tags=["Unidades"], dependencies=[Depends(get_current_user)])
app.include_router(importacoes.router, prefix="/api/v1/importacoes", tags=["Importações"], dependencies=[Depends(get_current_user)])
app.include_router(users.router, prefix="/api/v1/users", tags=["Usuários"], dependencies=[Depends(get_current_user)])
app.include_router(plano_saude.router, prefix="/api/v1/plano-saude", tags=["Plano de Saúde"], dependencies=[Depends(get_current_user)])
app.include_router(despesas_viagens.router, prefix="/api/v1/despesas-viagens", tags=["Despesas de Viagens"], dependencies=[Depends(get_current_user)])
