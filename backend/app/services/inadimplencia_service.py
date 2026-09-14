import datetime
import math
import io
import json
from typing import Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.cliente import Cliente
from app.models.matriz_cliente import MatrizCliente
from app.models.unidade import Unidade
from app.models.nf_pendencia import NfPendencia, VwNfPendenciaFase
from app.models.tratativa import Tratativa
from app.models.historico_pendencia import HistoricoPendencia
from app.models.user import User
from app.services.importacao_service import ImportacaoService

# Excel armazena datas como número de dias a partir de 1899-12-30 (compatibilidade com o bug histórico do Lotus 1-2-3)
EXCEL_EPOCH = datetime.date(1899, 12, 30)

WEEKDAY_NOMES = [
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo"
]

# Mesmas fases usadas como colunas do Kanban de Pendências (tela) e mesmos status
# disponíveis no select do modal de detalhes - mantidos em sincronia com o frontend.
FASE_OPTIONS = ["PENDENCIAS", "LOGISTICA", "FISCAL", "COMERCIAL", "FINANCEIRO", "FINALIZADO"]
STATUS_OPTIONS = [
    "DEVOLUCAO", "SEM DATA DE ENTREGA", "ACORDO", "COMISSAO",
    "EXPORTACAO", "MARTINS", "MERCADINHO", "CART-DES", "ATRASADO", "ANALISAR",
    "PROTESTADO", "PERDAS"
]


def _excel_serial_to_date(value) -> Optional[datetime.date]:
    """
    Converte uma célula de data da planilha para datetime.date.
    """
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        value_str = value.strip()
        if not value_str:
            return None
        # Tenta os formatos comuns no Brasil
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
            try:
                return datetime.datetime.strptime(value_str, fmt).date()
            except ValueError:
                pass
    try:
        return EXCEL_EPOCH + datetime.timedelta(days=int(value))
    except (ValueError, OverflowError, TypeError):
        return None


def _clean_str(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    texto = str(value).strip()
    return texto or None


def _to_float(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value) -> Optional[int]:
    valor_float = _to_float(value)
    if valor_float is None:
        return None
    return int(round(valor_float))


def _clean_titulo(value) -> Optional[str]:
    """Título é texto (ex.: '0017356', '270826-3') - preserva zeros à esquerda e sufixos,
    só removendo o '.0' que aparece quando a célula é lida como número puro pelo pandas."""
    texto = _clean_str(value)
    if texto is None:
        return None
    if texto.endswith(".0"):
        texto = texto[:-2]
    return texto or None


def resolver_intervalo_vencimento(hoje: datetime.date) -> Tuple[datetime.date, datetime.date]:
    """
    Primeiro critério de importação: a janela de datas de vencimento (coluna P) elegível
    depende do dia da semana em que a importação é executada.
      - Segunda-feira: sexta-feira anterior (último dia útil antes do fim de semana).
      - Terça-feira: sábado anterior até segunda anterior (fim de semana + segunda que antecedem a terça).
      - Quarta, quinta ou sexta-feira: exatamente o dia anterior.
    Sábado e domingo não têm regra definida e devem bloquear a importação.
    """
    dia_semana = hoje.weekday()  # 0=segunda ... 6=domingo
    if dia_semana == 0:  # segunda-feira
        sexta_anterior = hoje - datetime.timedelta(days=3)
        return sexta_anterior, sexta_anterior
    if dia_semana == 1:  # terça-feira
        inicio = hoje - datetime.timedelta(days=3)  # sábado anterior
        fim = hoje - datetime.timedelta(days=1)  # segunda anterior
        return inicio, fim
    if dia_semana in (2, 3, 4):  # quarta, quinta, sexta
        ontem = hoje - datetime.timedelta(days=1)
        return ontem, ontem
    raise ValueError(
        f"Importação de pendências não definida para {WEEKDAY_NOMES[dia_semana]}. "
        "As regras cobrem segunda-feira (sexta-feira anterior), terça-feira (fim de semana "
        "anterior) e quarta, quinta ou sexta-feira (dia anterior)."
    )



class InadimplenciaService:
    # Índices das colunas (0-based) no layout fixo da planilha "Base pendencias.xlsx"
    COL_ESTABELECIMENTO = 0   # A - Est (mapeia para unidade.codigo)
    COL_ESPECIE = 1           # B - Esp
    COL_SERIE = 2             # C - Ser
    COL_TITULO = 3            # D - Título
    COL_PARCELA = 4           # E - /P
    COL_NR_PEDIDO_CLIENTE = 5  # F - Nr Pedcli
    COL_TIPO_PEDIDO = 6       # G - Tipo Pedido
    COL_CLIENTE_CODIGO = 7    # H - Cliente
    COL_NOME_CLIENTE = 9      # J - Nome Cliente
    COL_MATRIZ_CODIGO = 10    # K - Cliente Matriz
    COL_PORTADOR = 11         # L - Port
    COL_CARTEIRA = 12         # M - Cart
    COL_EMISSAO = 13          # N - Emissão
    COL_DATA_ENTREGA = 14     # O - Dt Entrega
    COL_VENCIMENTO = 15       # P - Vencto
    COL_VALOR_ORIGINAL = 19   # T - Val Original
    COL_SALDO = 20            # U - Saldo

    MIN_COLUNAS = 21  # até a coluna U

    def __init__(self, db: Session):
        self.db = db
        self._cache_clientes: dict[int, int] = {}
        self._cache_matrizes: dict[int, int] = {}
        self._cache_unidades: dict[int, Optional[int]] = {}

    def importar_pendencias(self, conteudo: bytes, nome_arquivo: str, id_user: Optional[int] = None):
        import json
        try:
            df = pd.read_excel(io.BytesIO(conteudo), sheet_name="Resumo", header=0)
        except Exception as exc:
            yield json.dumps({"erro": f"Não foi possível ler a planilha: {exc}"}) + "\n"
            return

        if df.shape[1] < self.MIN_COLUNAS:
            yield json.dumps({"erro": f"A planilha precisa ter pelo menos {self.MIN_COLUNAS} colunas (até a coluna U). Colunas encontradas: {df.shape[1]}."}) + "\n"
            return

        total_com_especie = 0
        importadas = 0
        prorrogadas = 0
        ignoradas_sem_cliente = 0
        ignoradas_sem_vencimento = 0
        ignoradas_duplicadas = 0
        sem_unidade_encontrada = 0
        clientes_criados = 0
        matrizes_criadas = 0

        chaves_presentes_planilha: set[Tuple[Optional[int], Optional[int], Optional[str], Optional[float]]] = set()
        extensao = nome_arquivo.rsplit(".", 1)[-1].lower() if "." in nome_arquivo else "xlsx"

        try:
            importacao = ImportacaoService(self.db).registrar_importacao(
                nome_arquivo=nome_arquivo,
                extensao=extensao,
                tipo="PENDENCIAS",
                id_user_inc=id_user
            )
            self.db.commit() # Garante que a importação exista
        except Exception as e:
            yield json.dumps({"erro": f"Erro ao registrar importação: {e}"}) + "\n"
            return

        total_rows = len(df)
        
        try:
            for idx, row in df.iterrows():
                especie = _clean_str(row.iloc[self.COL_ESPECIE])
                if especie:
                    especie = especie.upper()
                if not especie:
                    continue  # linha em branco / separador / rodapé do relatório

                total_com_especie += 1

                codigo_estabelecimento = _to_int(row.iloc[self.COL_ESTABELECIMENTO])
                id_unidade = self._buscar_unidade(codigo_estabelecimento)
                if codigo_estabelecimento is not None and id_unidade is None:
                    sem_unidade_encontrada += 1

                serie = _to_int(row.iloc[self.COL_SERIE])
                titulo = _clean_titulo(row.iloc[self.COL_TITULO])
                parcela = _to_float(row.iloc[self.COL_PARCELA])
                if titulo is not None:
                    chaves_presentes_planilha.add((id_unidade, serie, titulo, parcela))

                vencimento = _excel_serial_to_date(row.iloc[self.COL_VENCIMENTO])
                if vencimento is None:
                    ignoradas_sem_vencimento += 1
                    continue

                tipo_pedido = _clean_str(row.iloc[self.COL_TIPO_PEDIDO])
                if tipo_pedido:
                    tipo_pedido = tipo_pedido.upper()
                carteira = _clean_str(row.iloc[self.COL_CARTEIRA])
                if carteira:
                    carteira = carteira.upper()
                data_entrega = _excel_serial_to_date(row.iloc[self.COL_DATA_ENTREGA])
                valor_original = _to_float(row.iloc[self.COL_VALOR_ORIGINAL])
                saldo = _to_float(row.iloc[self.COL_SALDO])

                codigo_cliente = _to_int(row.iloc[self.COL_CLIENTE_CODIGO])
                nome_cliente = _clean_str(row.iloc[self.COL_NOME_CLIENTE])

                if codigo_cliente is None or not nome_cliente:
                    ignoradas_sem_cliente += 1
                    continue

                id_cliente, criado_cliente = self._obter_ou_criar_cliente(codigo_cliente, nome_cliente)
                if criado_cliente:
                    clientes_criados += 1

                codigo_matriz = _to_int(row.iloc[self.COL_MATRIZ_CODIGO])
                id_matriz = None
                if codigo_matriz is not None:
                    id_matriz, criado_matriz = self._obter_ou_criar_matriz(codigo_matriz)
                    if criado_matriz:
                        matrizes_criadas += 1

                pendencia_existente = self._obter_pendencia_existente(id_unidade, serie, titulo, parcela)
                if pendencia_existente:
                    if getattr(pendencia_existente, 'encerrado', None) == 'S':
                        pendencia_existente.encerrado = 'N'
                        
                    if vencimento is not None:
                        venc_db = pendencia_existente.dtVencimento
                        
                        if isinstance(venc_db, datetime.datetime):
                            venc_db = venc_db.date()
                        elif isinstance(venc_db, str):
                            try:
                                venc_db = datetime.datetime.strptime(venc_db.split('T')[0].split(' ')[0], '%Y-%m-%d').date()
                            except:
                                venc_db = None
                                
                        venc_excel = vencimento
                        if isinstance(venc_excel, datetime.datetime):
                            venc_excel = venc_excel.date()

                        if venc_db is None or venc_excel > venc_db:
                            data_inicial_str = venc_db.strftime('%d/%m/%Y') if venc_db else "Sem Vencimento"
                            data_nova_str = venc_excel.strftime('%d/%m/%Y')
                            
                            pendencia_existente.dtVencimento = venc_excel
                            if saldo is not None:
                                pendencia_existente.valorSaldo = saldo
                            
                            foi_encerrado_agora = False
                            if getattr(pendencia_existente, 'encerrado', 'N') != 'S':
                                pendencia_existente.encerrado = 'S'
                                foi_encerrado_agora = True
                            
                            self.db.flush()
                            self._novo_historico(
                                pendencia_existente.idnfpendencias,
                                "Título Prorrogado",
                                f"Titulo {titulo} prorrogado de {data_inicial_str} para {data_nova_str}",
                                14 # system
                            )
                            
                            if foi_encerrado_agora:
                                self._novo_historico(
                                    pendencia_existente.idnfpendencias,
                                    "Resolução",
                                    "Pendência finalizada devido à prorrogação do título.",
                                    14 # system
                                )
                                
                            prorrogadas += 1
                        else:
                            ignoradas_duplicadas += 1
                    else:
                        ignoradas_duplicadas += 1
                else:
                    nf = NfPendencia(
                        idUnidade=id_unidade,
                        idImportacoes=importacao.idImportacoes,
                        especie=especie,
                        serie=serie,
                        titulo=titulo,
                        parccela=parcela,
                        nrPedidoCliente=_to_int(row.iloc[self.COL_NR_PEDIDO_CLIENTE]),
                        tipoPedido=tipo_pedido,
                        idCliente=id_cliente,
                        idClienteMatriz=id_matriz,
                        portador=_to_int(row.iloc[self.COL_PORTADOR]),
                        carteira=carteira,
                        dtEmissao=_excel_serial_to_date(row.iloc[self.COL_EMISSAO]),
                        dtEntrega=data_entrega,
                        dtVencimento=vencimento,
                        valorOriginal=valor_original,
                        valorSaldo=saldo,
                        encerrado='N'
                    )
                    self.db.add(nf)
                    self.db.flush()
                    self._novo_historico(
                        nf.idnfpendencias,
                        "Pendencia Importada",
                        f"Título {titulo} importado da planilha '{nome_arquivo}'.",
                        id_user,
                    )
                    
                    # Consulta a view para pegar fase e status e gravar novo histórico
                    vw = self.db.query(VwNfPendenciaFase).filter_by(idnfpendencias=nf.idnfpendencias).first()
                    if vw:
                        self._novo_historico(
                            nf.idnfpendencias,
                            "Classificação",
                            f"Titulo classificado como pendência {vw.fase} e status {vw.status}.",
                            14
                        )
                        
                    importadas += 1

                # Batch commit every 50 records
                if total_com_especie % 50 == 0:
                    self.db.commit()
                    yield json.dumps({
                        "progresso": int(idx),
                        "total": total_rows,
                        "importadas": importadas,
                        "prorrogadas": prorrogadas,
                        "ignoradas_duplicadas": ignoradas_duplicadas
                    }) + "\n"

            baixadas = 0
            if total_com_especie > 0:
                pendencias_ativas = self.db.query(NfPendencia).filter(
                    (NfPendencia.encerrado == 'N') | (NfPendencia.encerrado == None)
                ).all()
                for p_ativa in pendencias_ativas:
                    chave_ativa = (p_ativa.idUnidade, p_ativa.serie, p_ativa.titulo, p_ativa.parccela)
                    if chave_ativa not in chaves_presentes_planilha:
                        p_ativa.encerrado = 'S'
                        self.db.flush()
                        self._novo_historico(
                            p_ativa.idnfpendencias,
                            "Pendência finalizada",
                            "Pendência finalizada",
                            14 # system
                        )
                        baixadas += 1

            # Final commit
            self.db.commit()
            
            yield json.dumps({
                "sucesso": True,
                "arquivo": nome_arquivo,
                "idImportacao": importacao.idImportacoes,
                "totalLinhasComEspecie": total_com_especie,
                "importadas": importadas,
                "prorrogadas": prorrogadas,
                "baixadas": baixadas,
                "ignoradasSemCliente": ignoradas_sem_cliente,
                "ignoradasSemVencimento": ignoradas_sem_vencimento,
                "ignoradasDuplicadas": ignoradas_duplicadas,
                "semUnidadeEncontrada": sem_unidade_encontrada,
                "clientesCriados": clientes_criados,
                "matrizesCriadas": matrizes_criadas,
            }) + "\n"
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.db.rollback()
            yield json.dumps({"erro": f"Falha no processamento: {str(e)}"}) + "\n"

    def listar_pendencias(
        self,
        vencimento_inicio: Optional[datetime.date] = None,
        vencimento_fim: Optional[datetime.date] = None,
    ) -> list[dict]:
        """
        Lista as nfpendencias já classificadas para alimentar o Kanban, já com o nome do
        cliente resolvido (join com clientes). Não pagina - o board mostra o total do filtro.

        Sem parâmetros, mostra o padrão da tela: tudo com vencimento menor que hoje (vencido).
        Com vencimento_inicio/vencimento_fim, filtra pelo intervalo informado (ex.: o atalho
        "Regra do Dia" ou um período personalizado escolhido na tela).
        """
        query = self.db.query(VwNfPendenciaFase, Cliente.nome).outerjoin(
            Cliente, VwNfPendenciaFase.idCliente == Cliente.idclientes
        )

        if vencimento_inicio is None and vencimento_fim is None:
            query = query.filter(VwNfPendenciaFase.dtVencimento < datetime.date.today())
        else:
            if vencimento_inicio is not None:
                query = query.filter(VwNfPendenciaFase.dtVencimento >= vencimento_inicio)
            if vencimento_fim is not None:
                query = query.filter(VwNfPendenciaFase.dtVencimento <= vencimento_fim)

        registros = query.order_by(VwNfPendenciaFase.dtVencimento.asc()).all()

        resultados = []
        for vw, nome_cliente in registros:
            resultados.append({
                "idnfpendencias": vw.idnfpendencias,
                "titulo": vw.titulo,
                "fase": vw.fase,
                "status": vw.status,
                "devolucao": "S" if vw.status == 'DEVOLUCAO' else "N",
                "clienteNome": nome_cliente,
                "idCliente": vw.idCliente,
                "dtVencimento": vw.dtVencimento.isoformat() if vw.dtVencimento else None,
                "createdAt": vw.createdAt.isoformat() if vw.createdAt else None,
                "especie": vw.especie,
                "carteira": vw.carteira,
                "idUnidade": vw.idUnidade,
                "serie": vw.serie,
                "parccela": vw.parccela,
                "portador": vw.portador,
                "dtEmissao": vw.dtEmissao.isoformat() if vw.dtEmissao else None,
                "dtEntrega": vw.dtEntrega.isoformat() if vw.dtEntrega else None,
                "valorOriginal": vw.valorOriginal,
                "valorSaldo": vw.valorSaldo,
            })
        return resultados

    def obter_janela_regra_dia(self) -> dict:
        """
        Expõe a mesma regra de dia da semana (critério 1) como uma janela de datas pronta
        para o atalho "Regra do Dia" do filtro de período - não bloqueia mais a importação,
        só informa qual seria a janela de vencimento "do dia" hoje, se houver uma definida.
        """
        hoje = datetime.date.today()
        try:
            inicio, fim = resolver_intervalo_vencimento(hoje)
        except ValueError:
            return {
                "aplicavel": False,
                "diaSemanaHoje": WEEKDAY_NOMES[hoje.weekday()],
            }
        return {
            "aplicavel": True,
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "diaSemanaHoje": WEEKDAY_NOMES[hoje.weekday()],
        }

    def alterar_fase(self, id_nf: int, nova_fase: str, id_user: Optional[int] = None) -> dict:
        nova_fase = (nova_fase or "").strip().upper()
        if nova_fase not in FASE_OPTIONS:
            raise ValueError(
                f"Fase inválida: '{nova_fase}'. Valores aceitos: {', '.join(FASE_OPTIONS)}."
            )

        nf = self.db.query(NfPendencia).filter(NfPendencia.idnfpendencias == id_nf).first()
        if not nf:
            raise LookupError(f"Pendência {id_nf} não encontrada.")

        fase_anterior = nf.fase or "-"
        nf.fase = nova_fase
        self._novo_historico(
            id_nf, "Alteração de Fase",
            f"Fase alterada de '{fase_anterior}' para '{nova_fase}'.",
            id_user,
        )
        self.db.commit()
        self.db.refresh(nf)
        return {"idnfpendencias": nf.idnfpendencias, "fase": nf.fase}

    def alterar_status(self, id_nf: int, novo_status: str, id_user: Optional[int] = None) -> dict:
        novo_status = (novo_status or "").strip().upper()
        if novo_status not in STATUS_OPTIONS:
            raise ValueError(
                f"Status inválido: '{novo_status}'. Valores aceitos: {', '.join(STATUS_OPTIONS)}."
            )

        nf = self.db.query(NfPendencia).filter(NfPendencia.idnfpendencias == id_nf).first()
        if not nf:
            raise LookupError(f"Pendência {id_nf} não encontrada.")

        status_anterior = nf.status or "-"
        nf.status = novo_status
        self._novo_historico(
            id_nf, "Alteração de Status",
            f"Status alterado de '{status_anterior}' para '{novo_status}'.",
            id_user,
        )
        self.db.commit()
        self.db.refresh(nf)
        return {"idnfpendencias": nf.idnfpendencias, "status": nf.status}

    # ------------------------------------------------------------
    # Tratativas
    # ------------------------------------------------------------
    def listar_tratativas(self, id_nf: int) -> list[dict]:
        nf = self.db.query(NfPendencia).filter(NfPendencia.idnfpendencias == id_nf).first()
        if not nf:
            raise LookupError(f"Pendência {id_nf} não encontrada.")

        tratativas = (
            self.db.query(Tratativa)
            .filter(Tratativa.idNfPendencias == id_nf)
            .order_by(Tratativa.createdAt.desc())
            .all()
        )
        return [self._serializar_tratativa(t) for t in tratativas]

    def criar_tratativa(self, id_nf: int, conteudo: str, id_user: Optional[int]) -> dict:
        conteudo = (conteudo or "").strip()
        if not conteudo:
            raise ValueError("O conteúdo da tratativa não pode ser vazio.")

        nf = self.db.query(NfPendencia).filter(NfPendencia.idnfpendencias == id_nf).first()
        if not nf:
            raise LookupError(f"Pendência {id_nf} não encontrada.")

        tratativa = Tratativa(idNfPendencias=id_nf, conteudo=conteudo, idCreatedUser=id_user)
        self.db.add(tratativa)
        self._novo_historico(id_nf, "Tratativa Registrada", conteudo, id_user)
        self.db.commit()
        self.db.refresh(tratativa)
        return self._serializar_tratativa(tratativa)

    def editar_tratativa(self, id_tratativa: int, novo_conteudo: str) -> dict:
        novo_conteudo = (novo_conteudo or "").strip()
        if not novo_conteudo:
            raise ValueError("O conteúdo da tratativa não pode ser vazio.")

        tratativa = self.db.query(Tratativa).filter(Tratativa.idtratativas == id_tratativa).first()
        if not tratativa:
            raise LookupError(f"Tratativa {id_tratativa} não encontrada.")

        tratativa.conteudo = novo_conteudo
        self.db.commit()
        self.db.refresh(tratativa)
        return self._serializar_tratativa(tratativa)

    def _serializar_tratativa(self, t: Tratativa) -> dict:
        return {
            "idtratativas": t.idtratativas,
            "idNfPendencias": t.idNfPendencias,
            "conteudo": t.conteudo,
            "createdAt": t.createdAt.isoformat() if t.createdAt else None,
            "autor": t.usuario.name if t.usuario else None,
        }

    # ------------------------------------------------------------
    # Histórico
    # ------------------------------------------------------------
    def listar_historico(self, id_nf: int) -> list[dict]:
        nf = self.db.query(NfPendencia).filter(NfPendencia.idnfpendencias == id_nf).first()
        if not nf:
            raise LookupError(f"Pendência {id_nf} não encontrada.")

        eventos = (
            self.db.query(HistoricoPendencia)
            .filter(HistoricoPendencia.idNfPendencias == id_nf)
            .order_by(HistoricoPendencia.createdAt.asc())
            .all()
        )
        return [self._serializar_historico(h) for h in eventos]

    def registrar_historico(self, id_nf: int, tipo: str, observacao: str, id_user: Optional[int] = None) -> dict:
        """Endpoint público para registrar um evento manualmente (uso avulso, fora do fluxo
        automático já plugado em importação/alteração de fase-status/tratativa)."""
        tipo = (tipo or "").strip()
        if not tipo:
            raise ValueError("O tipo do evento de histórico é obrigatório.")

        nf = self.db.query(NfPendencia).filter(NfPendencia.idnfpendencias == id_nf).first()
        if not nf:
            raise LookupError(f"Pendência {id_nf} não encontrada.")

        historico = self._novo_historico(id_nf, tipo, observacao, id_user)
        self.db.commit()
        self.db.refresh(historico)
        return self._serializar_historico(historico)

    def _novo_historico(self, id_nf: int, tipo: str, observacao: Optional[str], id_user: Optional[int]) -> HistoricoPendencia:
        """Cria o registro e adiciona à sessão sem commitar - quem chama decide quando
        commitar (normalmente junto com a alteração principal, na mesma transação)."""
        historico = HistoricoPendencia(
            idNfPendencias=id_nf,
            tipo=tipo,
            observacao=(observacao or "")[:500],
            idUserCreated=id_user,
        )
        self.db.add(historico)
        return historico

    def _serializar_historico(self, h: HistoricoPendencia) -> dict:
        return {
            "idhistoricopendencia": h.idhistoricopendencia,
            "idNfPendencias": h.idNfPendencias,
            "tipo": h.tipo,
            "observacao": h.observacao,
            "createdAt": h.createdAt.isoformat() if h.createdAt else None,
            "autor": h.usuario.name if h.usuario else None,
        }

    def _obter_ou_criar_cliente(self, codigo: int, nome: str) -> Tuple[int, bool]:
        if codigo in self._cache_clientes:
            return self._cache_clientes[codigo], False

        cliente = self.db.query(Cliente).filter(Cliente.codigo == codigo).first()
        if cliente:
            self._cache_clientes[codigo] = cliente.idclientes
            return cliente.idclientes, False

        cliente = Cliente(codigo=codigo, nome=nome)
        self.db.add(cliente)
        self.db.flush()
        self._cache_clientes[codigo] = cliente.idclientes
        return cliente.idclientes, True

    def _obter_ou_criar_matriz(self, codigo: int) -> Tuple[int, bool]:
        if codigo in self._cache_matrizes:
            return self._cache_matrizes[codigo], False

        matriz = self.db.query(MatrizCliente).filter(MatrizCliente.codigo == codigo).first()
        if matriz:
            self._cache_matrizes[codigo] = matriz.idmatrizCliente
            return matriz.idmatrizCliente, False

        matriz = MatrizCliente(codigo=codigo)
        self.db.add(matriz)
        self.db.flush()
        self._cache_matrizes[codigo] = matriz.idmatrizCliente
        return matriz.idmatrizCliente, True

    def _buscar_unidade(self, codigo_estabelecimento: Optional[int]) -> Optional[int]:
        """Apenas consulta - não cadastra unidade automaticamente (fora do escopo pedido)."""
        if codigo_estabelecimento is None:
            return None
        if codigo_estabelecimento in self._cache_unidades:
            return self._cache_unidades[codigo_estabelecimento]

        unidade = self.db.query(Unidade).filter(Unidade.codigo == codigo_estabelecimento).first()
        id_unidade = unidade.idUnidade if unidade else None
        self._cache_unidades[codigo_estabelecimento] = id_unidade
        return id_unidade

    def _obter_pendencia_existente(
        self,
        id_unidade: Optional[int],
        serie: Optional[int],
        titulo: Optional[str],
        parcela: Optional[float],
    ) -> Optional[NfPendencia]:
        if titulo is None:
            return None
        return self.db.query(NfPendencia).filter(
            NfPendencia.idUnidade == id_unidade,
            NfPendencia.serie == serie,
            NfPendencia.titulo == titulo,
            NfPendencia.parccela == parcela,
        ).first()
