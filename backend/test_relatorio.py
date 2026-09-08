import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.services.despesas_viagens_service import DespesasViagensService
import traceback

def test():
    db = SessionLocal()
    try:
        service = DespesasViagensService(db)
        filtros = {
            "data_inicio": None,
            "data_fim": None,
            "id_empresa": None,
            "id_colaborador": None,
            "id_centro_custo": None
        }
        res = service.obter_relatorio(filtros)
        print("Success!", len(res.get("detalhesMatrizOriginal", [])))
    except Exception as e:
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test()
