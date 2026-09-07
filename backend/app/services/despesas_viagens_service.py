from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
from app.models.movimentacao import Movimentacao
from app.models.importacao import Importacao
from app.repositories.categoria_repository import CategoriaRepository
from app.repositories.colaborador_repository import ColaboradorRepository
from app.repositories.empresa_repository import EmpresaRepository
from app.repositories.colaborador_alias_repository import ColaboradorAliasRepository
from app.schemas.despesas_viagens import SalvarDespesaViagemPayload

class DespesasViagensService:
    def __init__(self, db: Session):
        self.db = db
        self.cat_repo = CategoriaRepository(db)
        self.colab_repo = ColaboradorRepository(db)
        self.emp_repo = EmpresaRepository(db)
        self.alias_repo = ColaboradorAliasRepository(db)

    def salvar_importacao(self, payload: SalvarDespesaViagemPayload):
        extensao = payload.nomeArquivo.split('.')[-1] if '.' in payload.nomeArquivo else ''
        
        id_empresa_importacao = None
        if payload.despesas:
            emp = self.emp_repo.get_by_nome(payload.despesas[0].empresa)
            if emp:
                id_empresa_importacao = emp.idEmpresas

        nova_importacao = Importacao(
            nomeArquivo=payload.nomeArquivo,
            extensaoArquivo=extensao,
            idEmpresa=id_empresa_importacao,
            tipo="IA_DESPESAS",
            idUserInc=payload.idUserInc
        )
        self.db.add(nova_importacao)
        self.db.flush()

        for d in payload.despesas:
            cat = self.cat_repo.get_by_nome(d.categoria)
            if not cat:
                raise HTTPException(status_code=400, detail=f"Categoria não encontrada: {d.categoria}")
                
            emp = self.emp_repo.get_by_nome(d.empresa)
            if not emp:
                raise HTTPException(status_code=400, detail=f"Empresa não encontrada: {d.empresa}")
                
            nome_pdf = d.colaborador.strip()
            colab = None
            
            alias = self.alias_repo.get_by_nome_divergente(nome_pdf)
            if alias:
                colab = self.colab_repo.get_by_id(alias.idColaborador)
                
            if not colab:
                colab = self.colab_repo.get_by_nome_normalizado(nome_pdf)
                
            if not colab:
                raise HTTPException(status_code=400, detail=f"Colaborador não encontrado e não mapeado: {d.colaborador}")
                
            if colab.nome != nome_pdf:
                 self.alias_repo.create_or_update(colab.idColaborador, nome_pdf)

            data_despesa_obj = None
            if d.data:
                try:
                    data_despesa_obj = datetime.strptime(d.data, "%Y-%m-%d")
                except ValueError:
                    pass

            nova_mov = Movimentacao(
                idCategoria=cat.idCategorias,
                idColaborador=colab.idColaborador,
                idEmpresa=emp.idEmpresas,
                idImportacoes=nova_importacao.idImportacoes,
                valor=d.valor
                # data_despesa=data_despesa_obj # Habilitar após migration do banco
            )
            self.db.add(nova_mov)
            
        self.db.commit()
        return {"sucesso": True, "idImportacoes": nova_importacao.idImportacoes}

    def obter_visao_geral(self, filtros):
        return {"kpis": {}, "graficos": {}}

    def obter_visao_comercial(self, filtros):
        return {"kpis": {}, "graficos": {}}
