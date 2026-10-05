from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from datetime import date
from app.models.colaboradores_movimento import ColaboradoresMovimento
from app.models.colaborador import Colaborador
from app.models.user import User


def listar_movimentos(
    db: Session,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    tipo: Optional[str] = None,
    origem: Optional[str] = None,
    page: int = 1,
    size: int = 50,
) -> dict:
    query = (
        db.query(ColaboradoresMovimento)
        .options(
            joinedload(ColaboradoresMovimento.colaborador)
        )
        .join(Colaborador, ColaboradoresMovimento.idColaboradores == Colaborador.idColaborador)
        .outerjoin(User, ColaboradoresMovimento.userCreatedId == User.iduser)
    )

    if data_inicio:
        query = query.filter(func.date(ColaboradoresMovimento.createdAt) >= data_inicio)
    if data_fim:
        query = query.filter(func.date(ColaboradoresMovimento.createdAt) <= data_fim)
    if tipo:
        query = query.filter(ColaboradoresMovimento.tipoMovimento == tipo)
    if origem:
        query = query.filter(ColaboradoresMovimento.origem == origem)

    total = query.with_entities(func.count(ColaboradoresMovimento.idcolaboradoresmovimento)).scalar()

    query = query.order_by(ColaboradoresMovimento.createdAt.desc())
    offset = (page - 1) * size
    items = query.offset(offset).limit(size).all()

    # Buscar nomes de usuários separadamente para evitar conflito de join
    user_ids = list({m.userCreatedId for m in items if m.userCreatedId})
    users_map = {}
    if user_ids:
        users = db.query(User).filter(User.iduser.in_(user_ids)).all()
        users_map = {u.iduser: u.name for u in users}

    result = []
    for m in items:
        colab = m.colaborador
        result.append({
            "id": m.idcolaboradoresmovimento,
            "idColaborador": m.idColaboradores,
            "colaboradorNome": colab.nome if colab else "—",
            "colaboradorDocumento": colab.documento if colab else None,
            "tipoMovimento": m.tipoMovimento,
            "origem": m.origem,
            "userNome": users_map.get(m.userCreatedId, "—"),
            "createdAt": m.createdAt.isoformat() if m.createdAt else None,
        })

    return {
        "items": result,
        "total": total,
        "page": page,
        "size": size,
        "total_pages": (total + size - 1) // size if total > 0 else 0,
    }

def listar_alertas_plano_saude(
    db: Session,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    page: int = 1,
    size: int = 50,
) -> dict:
    from app.models.turnover_plano_saude import TurnoverPlanoSaude
    from app.models.empresa import Empresa
    from app.models.importacao import Importacao

    query = (
        db.query(TurnoverPlanoSaude)
        .options(
            joinedload(TurnoverPlanoSaude.colaborador),
            joinedload(TurnoverPlanoSaude.empresa),
            joinedload(TurnoverPlanoSaude.importacao)
        )
    )

    if data_inicio:
        query = query.filter(func.date(TurnoverPlanoSaude.createdAt) >= data_inicio)
    if data_fim:
        query = query.filter(func.date(TurnoverPlanoSaude.createdAt) <= data_fim)

    total = query.with_entities(func.count(TurnoverPlanoSaude.idTurnoverPlano)).scalar()

    query = query.order_by(TurnoverPlanoSaude.createdAt.desc())
    offset = (page - 1) * size
    items = query.offset(offset).limit(size).all()

    result = []
    for a in items:
        colab = a.colaborador
        empresa = a.empresa
        importacao = a.importacao
        result.append({
            "id": a.idTurnoverPlano,
            "idColaborador": a.idColaborador,
            "colaboradorNome": colab.nome if colab else "—",
            "colaboradorDocumento": colab.documento if colab else None,
            "empresaNome": empresa.nomeAbrev or empresa.nome if empresa else "—",
            "competencia": a.competencia,
            "valor": float(a.valor) if a.valor is not None else None,
            "resolvido": a.resolvido,
            "importacaoArquivo": importacao.nomeArquivo if importacao else "—",
            "createdAt": a.createdAt.isoformat() if a.createdAt else None,
        })

    return {
        "items": result,
        "total": total,
        "page": page,
        "size": size,
        "total_pages": (total + size - 1) // size if total > 0 else 0,
    }

