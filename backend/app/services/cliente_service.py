from sqlalchemy.orm import Session
from app.models.cliente import Cliente
from app.models.cliente_representante import ClienteRepresentante

class ClienteService:
    @staticmethod
    def get_clientes(db: Session, id_representante: int = None):
        clientes = db.query(Cliente).order_by(Cliente.nome.asc()).all()
        
        # Se não passou representante, todos os linked serão False implicitamente pelo schema
        # Porém, vamos formatar a resposta
        resultado = []
        linked_clientes_ids = set()
        if id_representante:
            vinculos = db.query(ClienteRepresentante.idCliente).filter(ClienteRepresentante.idRepresentante == id_representante).all()
            linked_clientes_ids = {v[0] for v in vinculos}

        for c in clientes:
            resultado.append({
                "idclientes": c.idclientes,
                "codigo": c.codigo,
                "nome": c.nome,
                "linked": c.idclientes in linked_clientes_ids
            })
        
        return resultado

    @staticmethod
    def vincular_clientes(db: Session, id_representante: int, ids_clientes: list[int]):
        # Limpar os atuais
        db.query(ClienteRepresentante).filter(ClienteRepresentante.idRepresentante == id_representante).delete(synchronize_session=False)
        
        # Inserir novos
        for id_cliente in ids_clientes:
            novo_vinculo = ClienteRepresentante(
                idCliente=id_cliente,
                idRepresentante=id_representante
            )
            db.add(novo_vinculo)
        
        db.commit()
        return True
