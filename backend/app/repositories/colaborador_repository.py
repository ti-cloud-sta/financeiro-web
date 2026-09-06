import re
import unicodedata
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import List, Tuple, Optional
from datetime import datetime
from app.models.colaborador import Colaborador
from app.models.colaborador_unidade import ColaboradorUnidade
from app.models.unidade import Unidade  # necessário para registrar o mapper usado por ColaboradorUnidade.unidade
from app.models.centro_custo import CentroCusto
from app.models.cargo_colaborador import CargoColaborador
from app.schemas.colaborador import ColaboradorCreate, ColaboradorUpdate

class ColaboradorRepository:
    def __init__(self, db: Session):
        self.db = db

    def _base_query(self):
        return self.db.query(Colaborador).options(
            joinedload(Colaborador.cargo_colaborador),
            joinedload(Colaborador.centro_custo).joinedload(CentroCusto.centro_estados),
            joinedload(Colaborador.colaborador_unidades).joinedload(ColaboradorUnidade.unidade)
        )

    def get_by_id(self, idColaborador: int) -> Optional[Colaborador]:
        return self._base_query().filter(Colaborador.idColaborador == idColaborador).first()

    def get_by_nome(self, nome: str) -> Optional[Colaborador]:
        return self.db.query(Colaborador).filter(Colaborador.nome == nome).first()

    @staticmethod
    def _normaliza_nome(nome: str) -> str:
        # Maiúsculas, sem acento, sem espaço duplicado — comparação EXATA (não
        # aproximada) usada apenas quando não há nenhum CPF disponível no documento.
        sem_acento = unicodedata.normalize('NFKD', nome or '').encode('ascii', 'ignore').decode('ascii')
        return re.sub(r'\s+', ' ', sem_acento).strip().upper()

    def get_by_nome_normalizado(self, nome: str) -> Optional[Colaborador]:
        alvo = self._normaliza_nome(nome)
        if not alvo:
            return None
        for c in self._base_query().all():
            if self._normaliza_nome(c.nome) == alvo:
                return c
        return None

    @staticmethod
    def _normaliza_cpf(documento) -> str:
        # Normaliza para 11 dígitos antes de comparar: o banco pode guardar o CPF
        # formatado ("112.342.117-00") ou sem formatação ("11234211700"), e tanto o
        # PDF quanto o cadastro podem ter perdido de 1 a 3 zeros à esquerda ao passar
        # por algum sistema que trata o CPF como número.
        digitos = re.sub(r'\D', '', str(documento or ''))
        if 8 <= len(digitos) <= 11:
            digitos = digitos.zfill(11)
        return digitos

    def get_by_documento(self, documento: str) -> Optional[Colaborador]:
        doc_normalizado = self._normaliza_cpf(documento)
        results = self._base_query().all()
        for c in results:
            if c.documento and self._normaliza_cpf(c.documento) == doc_normalizado:
                return c
        return None

    def get_documentos_ativos(self) -> List[str]:
        rows = self.db.query(Colaborador.documento).filter(
            Colaborador.snAtivo != 'N', Colaborador.documento.isnot(None)
        ).all()
        return [r[0] for r in rows]

    def get_all(self, skip: int = 0, limit: int = 20, search: Optional[str] = None) -> Tuple[List[Colaborador], int]:
        query = self.db.query(Colaborador).outerjoin(CentroCusto).outerjoin(CargoColaborador)

        if search:
            search_term = f"%{search}%"
            try:
                search_codigo = int(search)
                cc_codigo_filter = CentroCusto.codigo == search_codigo
            except ValueError:
                cc_codigo_filter = False

            query = query.filter(
                or_(
                    Colaborador.nome.ilike(search_term),
                    Colaborador.documento.ilike(search_term),
                    CentroCusto.nome.ilike(search_term),
                    cc_codigo_filter,
                    CargoColaborador.nome.ilike(search_term)
                )
            )

        total = query.with_entities(func.count(Colaborador.idColaborador)).scalar()

        items = query.options(
            joinedload(Colaborador.cargo_colaborador),
            joinedload(Colaborador.centro_custo).joinedload(CentroCusto.centro_estados),
            joinedload(Colaborador.colaborador_unidades).joinedload(ColaboradorUnidade.unidade)
        ).offset(skip).limit(limit).all()

        return items, total

    def sync_unidades(self, db_obj: Colaborador, unidade_ids: List[int]) -> None:
        unidade_ids = set(unidade_ids or [])
        atuais = {cu.idUnidade: cu for cu in db_obj.colaborador_unidades}

        for id_unidade, cu in atuais.items():
            if id_unidade not in unidade_ids:
                self.db.delete(cu)

        for id_unidade in unidade_ids:
            if id_unidade not in atuais:
                self.db.add(ColaboradorUnidade(idColaborador=db_obj.idColaborador, idUnidade=id_unidade))

    def create(self, colab_in: ColaboradorCreate) -> Colaborador:
        data = colab_in.model_dump(exclude_unset=True, exclude={"unidadeIds"})
        db_obj = Colaborador(**data)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)

        if colab_in.unidadeIds:
            self.sync_unidades(db_obj, colab_in.unidadeIds)
            self.db.commit()

        return self.get_by_id(db_obj.idColaborador)

    def update(self, db_obj: Colaborador, colab_in: ColaboradorUpdate) -> Colaborador:
        update_data = colab_in.model_dump(exclude_unset=True, exclude={"unidadeIds"})
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db_obj.updatedAt = datetime.now()

        if colab_in.unidadeIds is not None:
            self.sync_unidades(db_obj, colab_in.unidadeIds)

        self.db.commit()
        self.db.refresh(db_obj)
        return self.get_by_id(db_obj.idColaborador)

    def delete(self, db_obj: Colaborador) -> None:
        self.db.delete(db_obj)
        self.db.commit()
