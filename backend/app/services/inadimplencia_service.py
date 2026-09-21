import datetime
import math
import io
import json
from typing import Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, cast, Date, desc

from app.models.cliente import Cliente
from app.models.matriz_cliente import MatrizCliente
from app.models.unidade import Unidade
from app.models.nf_pendencia import NfPendencia, VwNfPendenciaFase
from app.models.tratativa import Tratativa
from app.models.cliente_representante import ClienteRepresentante
from app.models.colaborador import Colaborador
from app.models.historico_pendencia import HistoricoPendencia
from app.models.pendencia_mensagem import PendenciaMensagem
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
    "ACORDO", "AD", "AN", "ANALISAR", "ATRASADO", "CART-DES", "COMISSAO", "DES",
    "DEVOLUCAO", "EXPORTACAO", "MARTINS", "MERCADINHO", "OK", "PERDAS",
    "PR", "PRORROGADO", "PROTESTADO", "RJ", "SEM DATA DE ENTREGA"
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
        atualizadas = 0
        ignoradas_sem_cliente = 0
        ignoradas_sem_vencimento = 0
        ignoradas_duplicadas = 0
        sem_unidade_encontrada = 0
        clientes_criados = 0
        matrizes_criadas = 0

        ids_processados_planilha: set[int] = set()
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

                pendencia_existente = self._obter_pendencia_existente(
                    id_unidade=id_unidade,
                    serie=serie,
                    titulo=titulo,
                    parcela=parcela,
                    especie=especie,
                    carteira=carteira,
                    ids_ja_processados=ids_processados_planilha
                )
                if pendencia_existente:
                    ids_processados_planilha.add(pendencia_existente.idnfpendencias)
                    mudancas = []
                    mudou_saldo = False
                    mudou_carteira = False

                    # 1. Verifica vencimento e prorrogação
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

                    is_prorrogacao = (venc_db is not None and venc_excel is not None and venc_excel > venc_db)
                    if is_prorrogacao:
                        data_inicial_str = venc_db.strftime('%d/%m/%Y')
                        data_nova_str = venc_excel.strftime('%d/%m/%Y')
                        mudancas.append(f"Vencimento: de {data_inicial_str} para {data_nova_str}")
                        pendencia_existente.dtVencimento = venc_excel
                        pendencia_existente.encerrado = 'P'
                    elif venc_db is not None and venc_excel is not None and venc_excel != venc_db:
                        data_inicial_str = venc_db.strftime('%d/%m/%Y')
                        data_nova_str = venc_excel.strftime('%d/%m/%Y')
                        mudancas.append(f"Vencimento: de {data_inicial_str} para {data_nova_str}")
                        pendencia_existente.dtVencimento = venc_excel

                    # 2. Verifica Saldo
                    saldo_db = pendencia_existente.valorSaldo
                    if saldo is not None and (saldo_db is None or round(float(saldo), 2) != round(float(saldo_db), 2)):
                        saldo_ant_str = f"R$ {float(saldo_db):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if saldo_db is not None else "R$ 0,00"
                        saldo_novo_str = f"R$ {float(saldo):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        mudancas.append(f"Saldo: de {saldo_ant_str} para {saldo_novo_str}")
                        pendencia_existente.valorSaldo = saldo
                        mudou_saldo = True

                    # 3. Verifica Carteira (Coluna M)
                    carteira_ant = pendencia_existente.carteira
                    if carteira and carteira != carteira_ant:
                        mudancas.append(f"Carteira: de {carteira_ant or '-'} para {carteira}")
                        pendencia_existente.carteira = carteira
                        mudou_carteira = True
                        # A mudança de carteira reinicia a classificação manual para a view aplicar as novas regras
                        pendencia_existente.fase = None
                        pendencia_existente.status = None

                    # 4. Outras atualizações cadastrais
                    entrega_db = pendencia_existente.dtEntrega
                    if isinstance(entrega_db, datetime.datetime):
                        entrega_db = entrega_db.date()
                    elif isinstance(entrega_db, str):
                        try:
                            entrega_db = datetime.datetime.strptime(entrega_db.split('T')[0].split(' ')[0], '%Y-%m-%d').date()
                        except:
                            entrega_db = None

                    if data_entrega is not None and data_entrega != entrega_db:
                        entrega_ant_str = entrega_db.strftime('%d/%m/%Y') if entrega_db else "Sem Data"
                        entrega_nova_str = data_entrega.strftime('%d/%m/%Y')
                        mudancas.append(f"Data de Entrega: de {entrega_ant_str} para {entrega_nova_str}")
                        pendencia_existente.dtEntrega = data_entrega

                    val_orig_db = pendencia_existente.valorOriginal
                    if valor_original is not None and (val_orig_db is None or round(float(valor_original), 2) != round(float(val_orig_db), 2)):
                        orig_ant_str = f"R$ {float(val_orig_db):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if val_orig_db is not None else "R$ 0,00"
                        orig_novo_str = f"R$ {float(valor_original):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        mudancas.append(f"Valor Original: de {orig_ant_str} para {orig_novo_str}")
                        pendencia_existente.valorOriginal = valor_original

                    if tipo_pedido and tipo_pedido != pendencia_existente.tipoPedido:
                        mudancas.append(f"Tipo Pedido: de {pendencia_existente.tipoPedido or '-'} para {tipo_pedido}")
                        pendencia_existente.tipoPedido = tipo_pedido

                    portador_novo = _to_int(row.iloc[self.COL_PORTADOR])
                    if portador_novo is not None and portador_novo != pendencia_existente.portador:
                        mudancas.append(f"Portador: de {pendencia_existente.portador or '-'} para {portador_novo}")
                        pendencia_existente.portador = portador_novo

                    nr_ped_novo = _to_int(row.iloc[self.COL_NR_PEDIDO_CLIENTE])
                    if nr_ped_novo is not None and nr_ped_novo != pendencia_existente.nrPedidoCliente:
                        mudancas.append(f"Nº Pedido: de {pendencia_existente.nrPedidoCliente or '-'} para {nr_ped_novo}")
                        pendencia_existente.nrPedidoCliente = nr_ped_novo

                    emissao_nova = _excel_serial_to_date(row.iloc[self.COL_EMISSAO])
                    emissao_db = pendencia_existente.dtEmissao
                    if isinstance(emissao_db, datetime.datetime):
                        emissao_db = emissao_db.date()
                    if emissao_nova is not None and emissao_nova != emissao_db:
                        emissao_ant_str = emissao_db.strftime('%d/%m/%Y') if emissao_db else "Sem Data"
                        emissao_nova_str = emissao_nova.strftime('%d/%m/%Y')
                        mudancas.append(f"Emissão: de {emissao_ant_str} para {emissao_nova_str}")
                        pendencia_existente.dtEmissao = emissao_nova

                    if id_cliente is not None and id_cliente != pendencia_existente.idCliente:
                        pendencia_existente.idCliente = id_cliente

                    if id_matriz is not None and id_matriz != pendencia_existente.idClienteMatriz:
                        pendencia_existente.idClienteMatriz = id_matriz

                    # Se a pendência estava marcada como encerrada por ausência anterior mas voltou na planilha
                    if not is_prorrogacao and pendencia_existente.encerrado == 'S':
                        pendencia_existente.encerrado = 'N'
                        mudancas.append("Status de encerramento reaberto para ativo")

                    # Efetivação e gravação de histórico
                    pendencia_existente.idImportacoes = importacao.idImportacoes
                    self.db.flush()

                    if is_prorrogacao:
                        descricao_hist = "Título prorrogado. Alterações: " + "; ".join(mudancas)
                        self._novo_historico(
                            pendencia_existente.idnfpendencias,
                            "Título Prorrogado",
                            descricao_hist,
                            14 # system
                        )
                        self._novo_historico(
                            pendencia_existente.idnfpendencias,
                            "Resolução",
                            "Pendência finalizada devido à prorrogação do título.",
                            14 # system
                        )
                        prorrogadas += 1
                    elif len(mudancas) > 0:


                        # Histórico de Saldo se mudou
                        if mudou_saldo:
                            self._novo_historico(
                                pendencia_existente.idnfpendencias,
                                "Atualização de Saldo",
                                f"Saldo atualizado de {saldo_ant_str} para {saldo_novo_str} na planilha '{nome_arquivo}'.",
                                14 # system
                            )

                        # Histórico de Carteira se mudou
                        if mudou_carteira:
                            self._novo_historico(
                                pendencia_existente.idnfpendencias,
                                "Atualização de Carteira",
                                f"Carteira alterada de {carteira_ant or '-'} para {carteira} na planilha '{nome_arquivo}'.",
                                14 # system
                            )

                        # Outras alterações cadastrais
                        outras_mudancas = [m for m in mudancas if not m.startswith("Saldo:") and not m.startswith("Carteira:")]
                        if outras_mudancas:
                            self._novo_historico(
                                pendencia_existente.idnfpendencias,
                                "Atualização Cadastral",
                                f"Dados atualizados na planilha '{nome_arquivo}': " + "; ".join(outras_mudancas),
                                14 # system
                            )

                        # Reclassificação via View após a alteração de carteira ou saldo
                        if mudou_carteira or mudou_saldo:
                            vw = self.db.query(VwNfPendenciaFase).filter_by(idnfpendencias=pendencia_existente.idnfpendencias).first()
                            if vw:
                                self._novo_historico(
                                    pendencia_existente.idnfpendencias,
                                    "Classificação",
                                    f"Titulo reclassificado como pendência {vw.fase} e status {vw.status}.",
                                    14 # system
                                )

                        atualizadas += 1
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
                    ids_processados_planilha.add(nf.idnfpendencias)
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
                        "atualizadas": atualizadas,
                        "ignoradas_duplicadas": ignoradas_duplicadas
                    }) + "\n"

            baixadas = 0
            if total_com_especie > 0:
                pendencias_ativas = self.db.query(NfPendencia).filter(
                    (NfPendencia.encerrado == 'N') | (NfPendencia.encerrado == None)
                ).all()
                for p_ativa in pendencias_ativas:
                    if p_ativa.idnfpendencias not in ids_processados_planilha:
                        p_ativa.encerrado = 'S'
                        p_ativa.idImportacoes = importacao.idImportacoes
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
                "atualizadas": atualizadas,
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

    def alterar_fase(self, id_nf: int, nova_fase: str, id_user: Optional[int] = None, novo_status: Optional[str] = None) -> dict:
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
        
        hist_detalhes = f"Fase alterada de '{fase_anterior}' para '{nova_fase}'."

        if nova_fase == "FINALIZADO":
            nf.status = "OK"
            nf.encerrado = "S"
            hist_detalhes += " Status definido para 'OK' e título encerrado."
        elif fase_anterior == "FINALIZADO" and nova_fase != "FINALIZADO":
            nf.encerrado = "N"
            hist_detalhes += " Título reaberto."
            if novo_status:
                novo_status = novo_status.strip().upper()
                nf.status = novo_status
                hist_detalhes += f" Novo status: '{novo_status}'."

        self._novo_historico(
            id_nf, "Alteração de Fase",
            hist_detalhes,
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

    def _novo_historico(
        self,
        id_nf: int,
        tipo: str,
        observacao: Optional[str],
        id_user: Optional[int],
        thread_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> HistoricoPendencia:
        """Cria o registro e adiciona à sessão sem commitar - quem chama decide quando
        commitar (normalmente junto com a alteração principal, na mesma transação)."""
        
        # Fazemos um flush para garantir que alterações recentes (ex: nf.fase = 'NOVA_FASE')
        # sejam enviadas ao banco, para que a view vw_nfpendencias_fase reflita a realidade atual.
        self.db.flush()
        
        # Captura o estado atual da pendência na View
        vw = self.db.query(VwNfPendenciaFase).filter_by(idnfpendencias=id_nf).first()
        fase_atual = vw.fase if vw else None
        status_atual = vw.status if vw else None
        vencimento_atual = vw.dtVencimento if vw else None

        historico = HistoricoPendencia(
            idNfPendencias=id_nf,
            tipo=tipo,
            observacao=(observacao or "")[:500],
            fase=fase_atual,
            status=status_atual,
            dtVencimento=vencimento_atual,
            idUserCreated=id_user,
            thread_id=thread_id,
            message_id=message_id,
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
            "thread_id": h.thread_id,
            "message_id": h.message_id,
        }

    def enviar_email_pendencia(
        self,
        id_nf: int,
        destinatarios: str,
        assunto: str,
        corpo: str,
        copia: Optional[str] = None,
        anexos: Optional[list] = None,
        user: Optional[User] = None,
    ) -> dict:
        """
        Envia e-mail de cobranca/aviso da pendencia via Gmail API (OAuth 2.0)
        e registra o envio no historico da pendencia.
        """
        from app.services.google_auth_service import GoogleAuthService
        from app.services.gmail_service import GmailService

        nf = self.db.query(NfPendencia).filter(NfPendencia.idnfpendencias == id_nf).first()
        if not nf:
            raise LookupError(f"Pendencia {id_nf} nao encontrada.")

        if not user:
            raise ValueError("Usuario nao identificado.")

        # 1. Obter o access_token valido junto ao Google OAuth
        access_token = GoogleAuthService.obter_access_token_valido(user, self.db)

        # 2. Enviar a mensagem utilizando o GmailService
        # O corpo HTML ja contem a URL publica da assinatura (enviada pelo frontend) —
        # nenhuma conversao de imagem e necessaria no backend.
        resultado_envio = GmailService.enviar_email(
            access_token=access_token,
            destinatarios=destinatarios,
            assunto=assunto,
            corpo_html=corpo,
            copia=copia,
            anexos=anexos,
            remetente_email=user.email if user else None,
        )


        # 3. Registrar o envio no histórico padrão
        obs = f"E-mail enviado via Gmail para: {destinatarios}. Assunto: {assunto}."
        if copia:
            obs += f" Cc: {copia}."
        if anexos:
            nomes_anexos = ", ".join([a.filename for a in anexos if getattr(a, "filename", None)])
            if nomes_anexos:
                obs += f" Anexos: {nomes_anexos}."

        historico = self._novo_historico(
            id_nf=id_nf,
            tipo="Email Enviado",
            observacao=obs[:500],
            id_user=user.iduser,
            thread_id=resultado_envio.get("threadId"),
            message_id=resultado_envio.get("messageId"),
        )
        
        # 4. Gravar a mensagem na tabela dedicada de mensagens
        lista_anexos = [{"nome": a.filename, "tamanho": 0} for a in anexos] if anexos else []
        import json
        nova_msg = PendenciaMensagem(
            idNfPendencias=id_nf,
            mensagem_id=resultado_envio.get("messageId"),
            thread_id=resultado_envio.get("threadId"),
            de=user.email if user else "Você",
            para=destinatarios,
            copia=copia,
            assunto=assunto,
            conteudo=corpo,
            anexos=lista_anexos,
            idUserCreated=user.iduser,
            minha_mensagem="S"
        )
        self.db.add(nova_msg)
        self.db.commit()
        self.db.refresh(historico)

        return {
            "sucesso": True,
            "messageId": resultado_envio.get("messageId"),
            "threadId": resultado_envio.get("threadId"),
        }

    def _sincronizar_respostas(self, id_nf: int, user: "User"):
        """Busca mensagens novas das threads vinculadas e salva na base de dados."""
        import base64
        import httpx
        from app.services.google_auth_service import GoogleAuthService

        if not user or not user.refresh_token_google:
            return

        threads = self.db.query(PendenciaMensagem.thread_id).filter(
            PendenciaMensagem.idNfPendencias == id_nf,
            PendenciaMensagem.thread_id.isnot(None)
        ).distinct().all()
        
        thread_ids = [t[0] for t in threads]
        if not thread_ids:
            return
            
        try:
            access_token = GoogleAuthService.obter_access_token_valido(user, self.db)
        except Exception:
            return
            
        headers_api = {"Authorization": f"Bearer {access_token}"}
        
        # Buscar message_ids já salvos no banco para não duplicar
        msgs_existentes = self.db.query(PendenciaMensagem.mensagem_id).filter(
            PendenciaMensagem.idNfPendencias == id_nf,
            PendenciaMensagem.mensagem_id.isnot(None)
        ).all()
        existentes_set = {m[0] for m in msgs_existentes}
        
        def _get_header(headers_list: list, name: str) -> str:
            for h in headers_list:
                if h.get("name", "").lower() == name.lower():
                    return h.get("value", "")
            return ""

        def _decodificar_base64(data: str) -> str:
            try:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            except Exception:
                return ""

        def _extrair_corpo(payload: dict) -> tuple:
            mime = payload.get("mimeType", "")
            body_data = payload.get("body", {}).get("data", "")
            if mime == "text/html" and body_data:
                return _decodificar_base64(body_data), ""
            if mime == "text/plain" and body_data:
                return "", _decodificar_base64(body_data)
            html_acc, plain_acc = "", ""
            for part in payload.get("parts", []):
                h, p = _extrair_corpo(part)
                if h: html_acc = h
                if p: plain_acc = p
            return html_acc, plain_acc

        def _extrair_anexos(payload: dict) -> list:
            result = []
            disposition = ""
            for h in payload.get("headers", []):
                if h.get("name", "").lower() == "content-disposition":
                    disposition = h.get("value", "")
            filename = payload.get("filename", "")
            if filename and "attachment" in disposition.lower():
                result.append({"nome": filename, "tamanho": payload.get("body", {}).get("size", 0)})
            for part in payload.get("parts", []):
                result.extend(_extrair_anexos(part))
            return result

        from datetime import datetime
        novas_mensagens = []
        
        with httpx.Client(timeout=httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=5.0)) as client:
            for thread_id in thread_ids:
                try:
                    res = client.get(
                        f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}",
                        params={"format": "full"},
                        headers=headers_api,
                    )
                    if res.status_code != 200:
                        continue
                    
                    thread_data = res.json()
                    for msg in thread_data.get("messages", []):
                        msg_id = msg.get("id")
                        if not msg_id or msg_id in existentes_set:
                            continue
                            
                        payload = msg.get("payload", {})
                        hdrs = payload.get("headers", [])
                        
                        de = _get_header(hdrs, "From")
                        para = _get_header(hdrs, "To")
                        assunto = _get_header(hdrs, "Subject")
                        
                        corpo_html, corpo_texto = _extrair_corpo(payload)
                        anexos = _extrair_anexos(payload)
                        
                        minha_mensagem = "S" if (user.email and user.email.lower() in de.lower()) else "N"
                        internal_date = int(msg.get("internalDate", 0)) / 1000
                        
                        nova_msg = PendenciaMensagem(
                            idNfPendencias=id_nf,
                            mensagem_id=msg_id,
                            thread_id=thread_id,
                            de=de,
                            para=para,
                            copia="",
                            assunto=assunto,
                            conteudo=corpo_html or corpo_texto.replace("\n", "<br>"),
                            anexos=anexos,
                            dataEnvio=datetime.fromtimestamp(internal_date),
                            minha_mensagem=minha_mensagem
                        )
                        novas_mensagens.append(nova_msg)
                except Exception as e:
                    logger.warning("Erro ao sincronizar thread %s: %s", thread_id, e)
                    continue
                    
        if novas_mensagens:
            self.db.add_all(novas_mensagens)
            for m in novas_mensagens:
                if m.minha_mensagem == "N":
                    historico = self._novo_historico(
                        id_nf=id_nf,
                        tipo="Email Recebido",
                        observacao=f"Resposta recebida de: {m.de}. Assunto: {m.assunto}",
                        id_user=user.iduser,
                        thread_id=m.thread_id,
                        message_id=m.mensagem_id,
                    )
            self.db.commit()

    def listar_mensagens_thread(self, id_nf: int, user: "User") -> list:
        """
        Retorna as mensagens gravadas na base.
        Antes de ler, faz um sync com a Gmail API para buscar respostas do cliente.
        """
        # Sincroniza com Gmail
        self._sincronizar_respostas(id_nf, user)
        
        # Busca todas as mensagens da tabela nova
        mensagens_db = (
            self.db.query(PendenciaMensagem)
            .filter(PendenciaMensagem.idNfPendencias == id_nf)
            .order_by(PendenciaMensagem.dataEnvio.asc())
            .all()
        )
        
        mensagens = []
        for m in mensagens_db:
            ts = m.dataEnvio.timestamp() if m.dataEnvio else 0.0
            mensagens.append({
                "id": m.mensagem_id or f"db-{m.idmensagem}",
                "thread_id": m.thread_id,
                "de": m.de,
                "para": m.para,
                "assunto": m.assunto,
                "data": m.dataEnvio.strftime("%a, %d %b %Y %H:%M:%S +0000") if m.dataEnvio else "",
                "internal_date": ts,
                "corpo_html": m.conteudo,
                "corpo_texto": "",
                "anexos": m.anexos or [],
                "minha_mensagem": m.minha_mensagem == "S",
            })

        # (Migração dos legados está sendo tratada em script de conversão isolado)
        # 4. Fallback para e-mails legados (temporário caso a conversão não rode de imediato)
        registros_legados = (
            self.db.query(HistoricoPendencia)
            .filter(
                HistoricoPendencia.idNfPendencias == id_nf,
                HistoricoPendencia.tipo == "Email Enviado",
            )
            .all()
        )
        # Filtra os que não tem correspondente em mensagens_db por data aproximada
        import re as _re
        for r in registros_legados:
            ts_leg = r.createdAt.timestamp() if r.createdAt else 0.0
            ja_tem = any(abs(m["internal_date"] - ts_leg) < 60 for m in mensagens)
            if ja_tem: continue

            obs = r.observacao or ""
            assunto_match = _re.search(r"Assunto:\s*(.*?)(?:\.\s*Cc:|\.\s*Anexos:|\.\s*$|$)", obs, _re.IGNORECASE)
            assunto_leg = assunto_match.group(1).strip() if assunto_match else "E-mail enviado"
            para_match = _re.search(r"para:\s*(.*?)(?:\.\s*Assunto:|$)", obs, _re.IGNORECASE)
            para_leg = para_match.group(1).strip() if para_match else ""
            cc_match = _re.search(r"Cc:\s*(.*?)(?:\.\s*Anexos:|\.\s*$|$)", obs, _re.IGNORECASE)
            cc_leg = cc_match.group(1).strip() if cc_match else ""
            
            cabecalho_html = ""
            if para_leg: cabecalho_html += f"<strong>Para:</strong> {para_leg}"
            if cc_leg: cabecalho_html += f" | <strong>Cc:</strong> {cc_leg}"
            if cabecalho_html: cabecalho_html = f'<div style="font-size:0.75rem;opacity:0.8;margin-bottom:0.35rem">{cabecalho_html}</div>'

            mensagens.append({
                "id": f"legacy-{r.idhistoricopendencia}",
                "thread_id": None,
                "de": r.usuario.name if r.usuario else (user.email or "Você"),
                "para": para_leg,
                "assunto": assunto_leg,
                "data": r.createdAt.strftime("%a, %d %b %Y %H:%M:%S +0000") if r.createdAt else "",
                "internal_date": ts_leg,
                "corpo_html": f"{cabecalho_html}<div><em>(Conteúdo do e-mail não disponível)</em></div>",
                "corpo_texto": "",
                "anexos": [],
                "minha_mensagem": True,
            })

        mensagens.sort(key=lambda m: m["internal_date"])
        return mensagens

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
        especie: Optional[str] = None,
        carteira: Optional[str] = None,
        ids_ja_processados: Optional[set[int]] = None,
    ) -> Optional[NfPendencia]:
        if titulo is None:
            return None

        filtros = [
            NfPendencia.idUnidade == id_unidade,
            NfPendencia.serie == serie,
            NfPendencia.titulo == titulo,
        ]
        if parcela is not None:
            filtros.append(NfPendencia.parccela == parcela)
        else:
            filtros.append(NfPendencia.parccela.is_(None))

        base_query = self.db.query(NfPendencia).filter(*filtros)

        # Filtro estrito por espécie
        if especie:
            query_esp = base_query.filter(NfPendencia.especie == especie)
        else:
            query_esp = base_query.filter((NfPendencia.especie.is_(None)) | (NfPendencia.especie == ''))

        # Tentativa 1: Match exato de carteira
        if carteira:
            query_exata = query_esp.filter(NfPendencia.carteira == carteira)
        else:
            query_exata = query_esp.filter((NfPendencia.carteira.is_(None)) | (NfPendencia.carteira == ''))

        candidatos_exatos = query_exata.all()
        for cand in candidatos_exatos:
            if ids_ja_processados is None or cand.idnfpendencias not in ids_ja_processados:
                return cand

        # Tentativa 2: Mesma espécie mas carteira mudou (para permitir a atualização de carteira)
        # Só considera registros que ainda não foram vinculados a outra linha desta importação
        candidatos_esp = query_esp.all()
        for cand in candidatos_esp:
            if ids_ja_processados is None or cand.idnfpendencias not in ids_ja_processados:
                return cand

        return None

    # ---------------- DASHBOARDS ----------------
    def get_dashboard_visao_geral(self) -> dict:
        from sqlalchemy import func, extract, case, text, desc
        from app.models.nf_pendencia import NfPendencia, VwNfPendenciaFase
        from app.models.historico_pendencia import HistoricoPendencia
        from app.models.cliente import Cliente
        from app.models.colaborador import Colaborador
        from app.models.cliente_representante import ClienteRepresentante
        import datetime
        from dateutil.relativedelta import relativedelta

        data_atual = datetime.date.today()
        
        # 1. Gráfico Anual de títulos pagos fora do prazo (por mês do vencimento)
        # Usaremos encerrado='S'
        doze_meses_atras = data_atual - relativedelta(months=11)
        doze_meses_atras = doze_meses_atras.replace(day=1)
        
        pagos_fora = (
            self.db.query(
                extract('month', NfPendencia.dtVencimento).label('mes'),
                func.count(NfPendencia.idnfpendencias).label('qtd')
            )
            .filter(
                NfPendencia.encerrado == 'S',
                NfPendencia.dtVencimento >= doze_meses_atras
            )
            .group_by(extract('month', NfPendencia.dtVencimento))
            .all()
        )
        
        pagos_fora_dict = {int(p.mes): p.qtd for p in pagos_fora}
        
        # Construir array de 12 meses
        meses_nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        labels_anual = []
        dados_anual = []
        for i in range(12):
            dt = doze_meses_atras + relativedelta(months=i)
            labels_anual.append(f"{meses_nomes[dt.month-1]}/{str(dt.year)[-2:]}")
            dados_anual.append(pagos_fora_dict.get(dt.month, 0))

        # 2. Gráfico Pizza: vencidos faixas
        pendencias_abertas = self.db.query(NfPendencia).filter(
            NfPendencia.encerrado == 'N',
            NfPendencia.dtVencimento < data_atual
        ).all()
        
        range_5 = 0
        range_15 = 0
        range_30_mais = 0
        for p in pendencias_abertas:
            if not p.dtVencimento: continue
            dias_atraso = (data_atual - p.dtVencimento).days
            if dias_atraso <= 5:
                range_5 += 1
            elif dias_atraso <= 15:
                range_15 += 1
            else:
                range_30_mais += 1
                
        # 3. Gráfico Semestral Títulos Protestados (fase='CARTÓRIO' ou status='PROTESTO')
        seis_meses_atras = data_atual - relativedelta(months=5)
        seis_meses_atras = seis_meses_atras.replace(day=1)
        
        protestados = (
            self.db.query(
                extract('month', VwNfPendenciaFase.dtVencimento).label('mes'),
                func.count(VwNfPendenciaFase.idnfpendencias).label('qtd')
            )
            .filter(
                VwNfPendenciaFase.dtVencimento >= seis_meses_atras,
                (VwNfPendenciaFase.status == 'PROTESTO') | (VwNfPendenciaFase.carteira == 'PRO')
            )
            .group_by(extract('month', VwNfPendenciaFase.dtVencimento))
            .all()
        )
        protestados_dict = {int(p.mes): p.qtd for p in protestados}
        
        labels_semestral = []
        dados_semestral = []
        for i in range(6):
            dt = seis_meses_atras + relativedelta(months=i)
            labels_semestral.append(f"{meses_nomes[dt.month-1]}")
            dados_semestral.append(protestados_dict.get(dt.month, 0))
            
        # 4. Ranking Clientes Atraso
        top_clientes = (
            self.db.query(
                Cliente.nome.label('nome'),
                func.count(NfPendencia.idnfpendencias).label('qtd')
            )
            .join(NfPendencia, NfPendencia.idCliente == Cliente.idclientes)
            .filter(NfPendencia.encerrado == 'N', NfPendencia.dtVencimento < data_atual)
            .group_by(Cliente.idclientes)
            .order_by(desc('qtd'))
            .limit(10)
            .all()
        )
        
        # 5. Ranking Representantes Atraso
        top_reps = (
            self.db.query(
                Colaborador.nome.label('nome'),
                func.count(NfPendencia.idnfpendencias).label('qtd')
            )
            .join(ClienteRepresentante, ClienteRepresentante.idRepresentante == Colaborador.idColaborador)
            .join(NfPendencia, NfPendencia.idCliente == ClienteRepresentante.idCliente)
            .filter(NfPendencia.encerrado == 'N', NfPendencia.dtVencimento < data_atual)
            .group_by(Colaborador.idColaborador)
            .order_by(desc('qtd'))
            .limit(10)
            .all()
        )
        
        # 6. Top 20 Maiores Atrasos (Grid)
        maiores_atrasos = (
            self.db.query(
                NfPendencia.titulo,
                Cliente.nome.label('cliente_nome'),
                NfPendencia.dtVencimento,
                NfPendencia.valorSaldo,
                VwNfPendenciaFase.fase,
                VwNfPendenciaFase.status
            )
            .outerjoin(Cliente, Cliente.idclientes == NfPendencia.idCliente)
            .outerjoin(VwNfPendenciaFase, VwNfPendenciaFase.idnfpendencias == NfPendencia.idnfpendencias)
            .filter(NfPendencia.encerrado == 'N', NfPendencia.dtVencimento < data_atual)
            .order_by(desc(NfPendencia.valorSaldo))
            .limit(20)
            .all()
        )

        return {
            "graficoAnualAtrasos": {
                "labels": labels_anual,
                "data": dados_anual
            },
            "graficoFaixasAtraso": [
                {"name": "Até 5 dias", "value": range_5},
                {"name": "Até 15 dias", "value": range_15},
                {"name": "Acima de 30 dias", "value": range_30_mais}
            ],
            "graficoProtestos": {
                "labels": labels_semestral,
                "data": dados_semestral
            },
            "rankingClientes": [{"nome": c.nome, "qtd": c.qtd} for c in top_clientes],
            "rankingGerentes": [{"nome": r.nome, "qtd": r.qtd} for r in top_reps],
            "maioresAtrasos": [
                {
                    "titulo": a.titulo,
                    "cliente": a.cliente_nome,
                    "vencimento": a.dtVencimento.isoformat() if a.dtVencimento else None,
                    "valor": float(a.valorSaldo or 0),
                    "fase": a.fase,
                    "status": a.status
                } for a in maiores_atrasos
            ]
        }

    def get_dashboard_logistica(self) -> dict:
        from sqlalchemy import func, extract, case, text, desc
        from app.models.nf_pendencia import NfPendencia, VwNfPendenciaFase
        from app.models.cliente import Cliente
        import datetime
        from dateutil.relativedelta import relativedelta
        
        data_atual = datetime.date.today()
        doze_meses_atras = data_atual - relativedelta(months=11)
        doze_meses_atras = doze_meses_atras.replace(day=1)
        meses_nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        labels_anual = []
        for i in range(12):
            dt = doze_meses_atras + relativedelta(months=i)
            labels_anual.append(f"{meses_nomes[dt.month-1]}/{str(dt.year)[-2:]}")

        # KPIs
        valor_sem_entrega = self.db.query(func.sum(NfPendencia.valorSaldo)).filter(NfPendencia.encerrado == 'N', NfPendencia.dtEntrega.is_(None)).scalar() or 0
        valor_devolucao = self.db.query(func.sum(NfPendencia.valorSaldo)).join(VwNfPendenciaFase, VwNfPendenciaFase.idnfpendencias == NfPendencia.idnfpendencias).filter(NfPendencia.encerrado == 'N', VwNfPendenciaFase.carteira == 'DEV').scalar() or 0

        # Graficos
        sem_entrega = (
            self.db.query(
                extract('month', NfPendencia.dtEmissao).label('mes'),
                func.count(NfPendencia.idnfpendencias).label('qtd')
            )
            .filter(NfPendencia.dtEntrega.is_(None), NfPendencia.dtEmissao >= doze_meses_atras)
            .group_by(extract('month', NfPendencia.dtEmissao))
            .all()
        )
        se_dict = {int(p.mes): p.qtd for p in sem_entrega}
        
        devolucao = (
            self.db.query(
                extract('month', VwNfPendenciaFase.dtEmissao).label('mes'),
                func.count(VwNfPendenciaFase.idnfpendencias).label('qtd')
            )
            .filter(VwNfPendenciaFase.carteira == 'DEV', VwNfPendenciaFase.dtEmissao >= doze_meses_atras)
            .group_by(extract('month', VwNfPendenciaFase.dtEmissao))
            .all()
        )
        dev_dict = {int(p.mes): p.qtd for p in devolucao}
        
        dados_se = []
        dados_dev = []
        for i in range(12):
            dt = doze_meses_atras + relativedelta(months=i)
            dados_se.append(se_dict.get(dt.month, 0))
            dados_dev.append(dev_dict.get(dt.month, 0))
            
        # Grid
        grid_data = (
            self.db.query(
                NfPendencia.titulo,
                Cliente.nome.label('cliente_nome'),
                NfPendencia.dtEmissao,
                NfPendencia.valorSaldo,
                VwNfPendenciaFase.carteira
            )
            .outerjoin(Cliente, Cliente.idclientes == NfPendencia.idCliente)
            .outerjoin(VwNfPendenciaFase, VwNfPendenciaFase.idnfpendencias == NfPendencia.idnfpendencias)
            .filter(NfPendencia.encerrado == 'N', (NfPendencia.dtEntrega.is_(None)) | (VwNfPendenciaFase.carteira == 'DEV'))
            .order_by(desc(NfPendencia.valorSaldo))
            .limit(50)
            .all()
        )

        return {
            "kpiSemEntrega": float(valor_sem_entrega),
            "kpiDevolucao": float(valor_devolucao),
            "graficoSemEntrega": {"labels": labels_anual, "data": dados_se},
            "graficoDevolucao": {"labels": labels_anual, "data": dados_dev},
            "gridLogs": [
                {
                    "titulo": g.titulo,
                    "cliente": g.cliente_nome,
                    "emissao": g.dtEmissao.isoformat() if g.dtEmissao else None,
                    "valor": float(g.valorSaldo or 0),
                    "carteira": g.carteira
                } for g in grid_data
            ]
        }

    def get_dashboard_comercial(self) -> dict:
        from sqlalchemy import func, extract, case, text, desc
        from app.models.nf_pendencia import NfPendencia, VwNfPendenciaFase
        from app.models.cliente import Cliente
        import datetime
        from dateutil.relativedelta import relativedelta
        
        data_atual = datetime.date.today()
        doze_meses_atras = data_atual - relativedelta(months=11)
        doze_meses_atras = doze_meses_atras.replace(day=1)
        meses_nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        labels_anual = []
        for i in range(12):
            dt = doze_meses_atras + relativedelta(months=i)
            labels_anual.append(f"{meses_nomes[dt.month-1]}/{str(dt.year)[-2:]}")

        # Acordos (fase='ACORDO' ou status='ACORDO COMERCIAL') - assumindo fase ACORDO
        kpi_total = self.db.query(func.sum(NfPendencia.valorSaldo)).join(VwNfPendenciaFase, VwNfPendenciaFase.idnfpendencias == NfPendencia.idnfpendencias).filter(NfPendencia.encerrado == 'N', (VwNfPendenciaFase.fase == 'ACORDO') | (VwNfPendenciaFase.status == 'ACORDO')).scalar() or 0
        
        top_acordos = (
            self.db.query(
                NfPendencia.titulo,
                Cliente.nome.label('cliente_nome'),
                NfPendencia.valorSaldo
            )
            .outerjoin(Cliente, Cliente.idclientes == NfPendencia.idCliente)
            .join(VwNfPendenciaFase, VwNfPendenciaFase.idnfpendencias == NfPendencia.idnfpendencias)
            .filter(NfPendencia.encerrado == 'N', (VwNfPendenciaFase.fase == 'ACORDO') | (VwNfPendenciaFase.status == 'ACORDO'))
            .order_by(desc(NfPendencia.valorSaldo))
            .limit(5)
            .all()
        )
        
        ocorrencias = (
            self.db.query(
                extract('month', VwNfPendenciaFase.createdAt).label('mes'),
                func.count(VwNfPendenciaFase.idnfpendencias).label('qtd')
            )
            .filter((VwNfPendenciaFase.fase == 'ACORDO') | (VwNfPendenciaFase.status == 'ACORDO'), VwNfPendenciaFase.createdAt >= doze_meses_atras)
            .group_by(extract('month', VwNfPendenciaFase.createdAt))
            .all()
        )
        oco_dict = {int(p.mes): p.qtd for p in ocorrencias}
        dados_anual = [oco_dict.get((doze_meses_atras + relativedelta(months=i)).month, 0) for i in range(12)]
        
        grid_data = (
            self.db.query(
                NfPendencia.titulo,
                Cliente.nome.label('cliente_nome'),
                NfPendencia.dtVencimento,
                NfPendencia.valorSaldo,
                VwNfPendenciaFase.fase,
                VwNfPendenciaFase.status
            )
            .outerjoin(Cliente, Cliente.idclientes == NfPendencia.idCliente)
            .join(VwNfPendenciaFase, VwNfPendenciaFase.idnfpendencias == NfPendencia.idnfpendencias)
            .filter(NfPendencia.encerrado == 'N', (VwNfPendenciaFase.fase == 'ACORDO') | (VwNfPendenciaFase.status == 'ACORDO'))
            .order_by(desc(NfPendencia.valorSaldo))
            .limit(50)
            .all()
        )
        
        return {
            "kpiTotal": float(kpi_total),
            "rankingAcordos": [
                {"titulo": g.titulo, "cliente": g.cliente_nome, "valor": float(g.valorSaldo or 0)} for g in top_acordos
            ],
            "graficoAcordos": {"labels": labels_anual, "data": dados_anual},
            "gridAcordos": [
                {
                    "titulo": g.titulo,
                    "cliente": g.cliente_nome,
                    "vencimento": g.dtVencimento.isoformat() if g.dtVencimento else None,
                    "valor": float(g.valorSaldo or 0),
                    "fase": g.fase,
                    "status": g.status
                } for g in grid_data
            ]
        }

    def get_dashboard_visao_geral(self) -> dict:
        from sqlalchemy import func, extract, desc
        import datetime

        hoje = datetime.date.today()
        ano = hoje.year
        mes = hoje.month - 11
        if mes <= 0:
            ano -= 1
            mes += 12
        doze_meses_atras = datetime.date(ano, mes, 1)
        hoje_datetime = datetime.datetime(hoje.year, hoje.month, hoje.day)

        # 1. KPI Vencido (Fase FINANCEIRO)
        kpi_vencido = self.db.query(func.sum(VwNfPendenciaFase.valorSaldo)).filter(
            VwNfPendenciaFase.fase == 'FINANCEIRO',
            VwNfPendenciaFase.dtVencimento < hoje_datetime
        ).scalar() or 0.0

        # 2. KPI Protestado (Status PROTESTADO)
        kpi_protestado = self.db.query(func.sum(VwNfPendenciaFase.valorSaldo)).filter(
            VwNfPendenciaFase.status == 'PROTESTADO',
            VwNfPendenciaFase.dtVencimento < hoje_datetime
        ).scalar() or 0.0

        # 3. KPI Total Clientes Inadimplentes (Fase FINANCEIRO)
        kpi_clientes = self.db.query(func.count(func.distinct(VwNfPendenciaFase.idCliente))).filter(
            VwNfPendenciaFase.fase == 'FINANCEIRO',
            VwNfPendenciaFase.dtVencimento < hoje_datetime
        ).scalar() or 0

        # 4. Evoluções (Mockadas temporariamente até termos dados históricos fechados)
        kpi_vencido_evolucao = 5.2
        kpi_protestado_evolucao = -2.1
        kpi_clientes_evolucao = 1.5

        # 5. Ranking Clientes Atraso
        top_clientes_atraso = (
            self.db.query(
                Cliente.nome.label('cliente'),
                func.count(VwNfPendenciaFase.idnfpendencias).label('qtd'),
                func.sum(VwNfPendenciaFase.valorSaldo).label('valor')
            )
            .join(VwNfPendenciaFase, VwNfPendenciaFase.idCliente == Cliente.idclientes)
            .filter(VwNfPendenciaFase.fase == 'FINANCEIRO', VwNfPendenciaFase.dtVencimento < hoje_datetime)
            .group_by(Cliente.nome)
            .order_by(desc('valor'))
            .limit(10)
            .all()
        )
        ranking_clientes_atraso = [{"cliente": r.cliente, "qtd": r.qtd, "valor": float(r.valor)} for r in top_clientes_atraso]

        # 6. Ranking Clientes Protesto
        top_clientes_protesto = (
            self.db.query(
                Cliente.nome.label('cliente'),
                func.count(VwNfPendenciaFase.idnfpendencias).label('qtd'),
                func.sum(VwNfPendenciaFase.valorSaldo).label('valor')
            )
            .join(VwNfPendenciaFase, VwNfPendenciaFase.idCliente == Cliente.idclientes)
            .filter(VwNfPendenciaFase.status == 'PROTESTADO', VwNfPendenciaFase.dtVencimento < hoje_datetime)
            .group_by(Cliente.nome)
            .order_by(desc('valor'))
            .limit(10)
            .all()
        )
        ranking_clientes_protesto = [{"cliente": r.cliente, "qtd": r.qtd, "valor": float(r.valor)} for r in top_clientes_protesto]

        # 7. Rankings Gerentes e Representantes
        ranking_gerentes_atraso = []
        ranking_gerentes_protesto = []
        
        rep_atraso_db = (
            self.db.query(Colaborador.nome, func.count(VwNfPendenciaFase.idnfpendencias).label('qtd'), func.sum(VwNfPendenciaFase.valorSaldo).label('valor'))
            .select_from(VwNfPendenciaFase)
            .join(ClienteRepresentante, ClienteRepresentante.idCliente == VwNfPendenciaFase.idCliente)
            .join(Colaborador, Colaborador.idColaborador == ClienteRepresentante.idRepresentante)
            .filter(VwNfPendenciaFase.fase == 'FINANCEIRO', VwNfPendenciaFase.dtVencimento < hoje_datetime)
            .group_by(Colaborador.nome)
            .order_by(desc('valor'))
            .limit(10).all()
        )
        ranking_representantes_atraso = [{"nome": r.nome, "qtd": r.qtd, "valor": float(r.valor or 0)} for r in rep_atraso_db]

        rep_protesto_db = (
            self.db.query(Colaborador.nome, func.count(VwNfPendenciaFase.idnfpendencias).label('qtd'), func.sum(VwNfPendenciaFase.valorSaldo).label('valor'))
            .select_from(VwNfPendenciaFase)
            .join(ClienteRepresentante, ClienteRepresentante.idCliente == VwNfPendenciaFase.idCliente)
            .join(Colaborador, Colaborador.idColaborador == ClienteRepresentante.idRepresentante)
            .filter(VwNfPendenciaFase.status == 'PROTESTADO', VwNfPendenciaFase.dtVencimento < hoje_datetime)
            .group_by(Colaborador.nome)
            .order_by(desc('valor'))
            .limit(10).all()
        )
        ranking_representantes_protesto = [{"nome": r.nome, "qtd": r.qtd, "valor": float(r.valor or 0)} for r in rep_protesto_db]

        # 8. Dashboard Comercial - Acordos
        kpi_total_acordos = self.db.query(func.sum(VwNfPendenciaFase.valorSaldo)).filter(
            VwNfPendenciaFase.status == 'ACORDO'
        ).scalar() or 0

        top_acordos_db = (
            self.db.query(
                VwNfPendenciaFase.titulo,
                Cliente.nome.label('cliente_nome'),
                VwNfPendenciaFase.valorSaldo
            )
            .outerjoin(Cliente, Cliente.idclientes == VwNfPendenciaFase.idCliente)
            .filter(VwNfPendenciaFase.status == 'ACORDO')
            .order_by(desc(VwNfPendenciaFase.valorSaldo))
            .limit(5).all()
        )
        ranking_acordos = [{"titulo": r.titulo, "cliente": r.cliente_nome, "valor": float(r.valorSaldo or 0)} for r in top_acordos_db]

        # 9. Grid de Títulos em Atraso (Todos os títulos da fase FINANCEIRO)
        grid_financeiro_db = (
            self.db.query(
                VwNfPendenciaFase.idnfpendencias,
                VwNfPendenciaFase.titulo,
                Cliente.nome.label('cliente_nome'),
                VwNfPendenciaFase.dtVencimento,
                VwNfPendenciaFase.valorSaldo,
                VwNfPendenciaFase.fase,
                VwNfPendenciaFase.status
            )
            .outerjoin(Cliente, Cliente.idclientes == VwNfPendenciaFase.idCliente)
            .filter(VwNfPendenciaFase.fase == 'FINANCEIRO', VwNfPendenciaFase.dtVencimento < hoje_datetime)
            .order_by(desc(VwNfPendenciaFase.valorSaldo))
            .limit(1000) # Previne payloads excessivamente gigantes
            .all()
        )
        
        faixas_atraso_count = {"ate5": 0, "ate15": 0, "ate30": 0, "acima30": 0}
        
        # Contagem total de títulos em atraso por cliente
        qtd_titulos_db = (
            self.db.query(
                Cliente.nome.label('cliente'),
                func.count(VwNfPendenciaFase.idnfpendencias).label('qtd')
            )
            .join(VwNfPendenciaFase, VwNfPendenciaFase.idCliente == Cliente.idclientes)
            .filter(VwNfPendenciaFase.fase == 'FINANCEIRO', VwNfPendenciaFase.dtVencimento < hoje_datetime)
            .group_by(Cliente.nome)
            .all()
        )
        qtd_titulos_cliente = {r.cliente: r.qtd for r in qtd_titulos_db}

        grid_financeiro = []
        for g in grid_financeiro_db:
            if g.dtVencimento:
                dt_venc = g.dtVencimento
                if isinstance(dt_venc, datetime.datetime):
                    dt_venc = dt_venc.date()
                elif isinstance(dt_venc, str):
                    dt_venc = datetime.datetime.strptime(dt_venc.split('T')[0], '%Y-%m-%d').date()
                
                dias_atraso = (hoje - dt_venc).days
                if dias_atraso <= 5:
                    faixas_atraso_count["ate5"] += 1
                elif dias_atraso <= 15:
                    faixas_atraso_count["ate15"] += 1
                elif dias_atraso <= 30:
                    faixas_atraso_count["ate30"] += 1
                else:
                    faixas_atraso_count["acima30"] += 1

            grid_financeiro.append({
                "id": g.idnfpendencias,
                "titulo": g.titulo,
                "cliente": g.cliente_nome,
                "vencimento": g.dtVencimento.isoformat() if g.dtVencimento else None,
                "valor": float(g.valorSaldo or 0),
                "fase": g.fase,
                "status": g.status,
                "qtd": qtd_titulos_cliente.get(g.cliente_nome, 1)
            })

        grid_sem_entrega_db = self.db.query(VwNfPendenciaFase, Cliente.nome.label('cliente_nome')).outerjoin(Cliente, Cliente.idclientes == VwNfPendenciaFase.idCliente).filter(VwNfPendenciaFase.fase == 'LOGISTICA', VwNfPendenciaFase.status == 'SEM DATA DE ENTREGA', VwNfPendenciaFase.dtVencimento < hoje_datetime).order_by(desc(VwNfPendenciaFase.valorSaldo)).all()
        grid_sem_entrega = [{"id": r[0].idnfpendencias, "titulo": r[0].titulo, "cliente": r.cliente_nome, "vencimento": r[0].dtVencimento.isoformat() if r[0].dtVencimento else None, "valor": float(r[0].valorSaldo or 0)} for r in grid_sem_entrega_db]

        grid_devolucao_db = self.db.query(VwNfPendenciaFase, Cliente.nome.label('cliente_nome')).outerjoin(Cliente, Cliente.idclientes == VwNfPendenciaFase.idCliente).filter(VwNfPendenciaFase.fase == 'LOGISTICA', VwNfPendenciaFase.status == 'DEVOLUÇÃO', VwNfPendenciaFase.dtVencimento < hoje_datetime).order_by(desc(VwNfPendenciaFase.valorSaldo)).all()
        grid_devolucao = [{"id": r[0].idnfpendencias, "titulo": r[0].titulo, "cliente": r.cliente_nome, "vencimento": r[0].dtVencimento.isoformat() if r[0].dtVencimento else None, "valor": float(r[0].valorSaldo or 0)} for r in grid_devolucao_db]

        grid_acordos_db = (
            self.db.query(
                VwNfPendenciaFase.idnfpendencias,
                VwNfPendenciaFase.titulo,
                Cliente.nome.label('cliente_nome'),
                VwNfPendenciaFase.dtVencimento,
                VwNfPendenciaFase.valorSaldo,
                VwNfPendenciaFase.fase,
                VwNfPendenciaFase.status
            )
            .outerjoin(Cliente, Cliente.idclientes == VwNfPendenciaFase.idCliente)
            .filter(VwNfPendenciaFase.status == 'ACORDO')
            .order_by(desc(VwNfPendenciaFase.valorSaldo))
            .limit(1000)
            .all()
        )
        grid_acordos = [
            {
                "id": g.idnfpendencias,
                "titulo": g.titulo,
                "cliente": g.cliente_nome,
                "vencimento": g.dtVencimento.isoformat() if g.dtVencimento else None,
                "valor": float(g.valorSaldo or 0),
                "fase": g.fase,
                "status": g.status
            }
            for g in grid_acordos_db
        ]

        kpi_sem_entrega = sum(item['valor'] for item in grid_sem_entrega)
        kpi_devolucao = sum(item['valor'] for item in grid_devolucao)
        # 10. Evolução Logística (Mês a Mês)
        meses_logistica_labels = []
        valores_sem_entrega = []
        valores_devolucao = []
        
        meses_labels = []
        meses_valores_atraso = []
        meses_valores_protesto = []
        valores_acordos = []
        
        meses_nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        
        for i in range(5, -1, -1):
            m = hoje.month - i
            y = hoje.year
            if m <= 0:
                m += 12
                y -= 1
            label_mes = f"{meses_nomes[m-1]}/{str(y)[2:]}"
            meses_logistica_labels.append(label_mes)
            
            count_sem_entrega = self.db.query(func.count(func.distinct(VwNfPendenciaFase.idnfpendencias))).join(
                HistoricoPendencia, HistoricoPendencia.idNfPendencias == VwNfPendenciaFase.idnfpendencias
            ).filter(
                HistoricoPendencia.fase == 'LOGISTICA',
                HistoricoPendencia.status == 'SEM DATA DE ENTREGA',
                HistoricoPendencia.dtVencimento < cast(HistoricoPendencia.createdAt, Date),
                func.extract('year', HistoricoPendencia.createdAt) == y,
                func.extract('month', HistoricoPendencia.createdAt) == m
            ).scalar() or 0
            
            count_devolucao = self.db.query(func.count(func.distinct(VwNfPendenciaFase.idnfpendencias))).join(
                HistoricoPendencia, HistoricoPendencia.idNfPendencias == VwNfPendenciaFase.idnfpendencias
            ).filter(
                HistoricoPendencia.fase == 'LOGISTICA',
                or_(HistoricoPendencia.status == 'DEVOLUÇÃO', HistoricoPendencia.status == 'DEVOLUCAO'),
                HistoricoPendencia.dtVencimento < cast(HistoricoPendencia.createdAt, Date),
                func.extract('year', HistoricoPendencia.createdAt) == y,
                func.extract('month', HistoricoPendencia.createdAt) == m
            ).scalar() or 0
            
            valores_sem_entrega.append(count_sem_entrega)
            valores_devolucao.append(count_devolucao)
            
            # Evolução Financeira / Comercial
            count_protesto = self.db.query(func.count(func.distinct(VwNfPendenciaFase.idnfpendencias))).join(
                HistoricoPendencia, HistoricoPendencia.idNfPendencias == VwNfPendenciaFase.idnfpendencias
            ).filter(
                HistoricoPendencia.fase == 'FINANCEIRO',
                HistoricoPendencia.status == 'PROTESTADO',
                HistoricoPendencia.dtVencimento < cast(HistoricoPendencia.createdAt, Date),
                func.extract('year', HistoricoPendencia.createdAt) == y,
                func.extract('month', HistoricoPendencia.createdAt) == m
            ).scalar() or 0

            count_atraso = self.db.query(func.count(func.distinct(VwNfPendenciaFase.idnfpendencias))).join(
                HistoricoPendencia, HistoricoPendencia.idNfPendencias == VwNfPendenciaFase.idnfpendencias
            ).filter(
                HistoricoPendencia.fase == 'FINANCEIRO',
                HistoricoPendencia.status == 'ATRASADO',
                HistoricoPendencia.dtVencimento < cast(HistoricoPendencia.createdAt, Date),
                func.extract('year', HistoricoPendencia.createdAt) == y,
                func.extract('month', HistoricoPendencia.createdAt) == m
            ).scalar() or 0

            count_acordo = self.db.query(func.count(func.distinct(VwNfPendenciaFase.idnfpendencias))).join(
                HistoricoPendencia, HistoricoPendencia.idNfPendencias == VwNfPendenciaFase.idnfpendencias
            ).filter(
                HistoricoPendencia.status == 'ACORDO',
                func.extract('year', HistoricoPendencia.createdAt) == y,
                func.extract('month', HistoricoPendencia.createdAt) == m
            ).scalar() or 0

            meses_labels.append(label_mes)
            meses_valores_atraso.append(count_atraso)
            meses_valores_protesto.append(count_protesto)
            valores_acordos.append(count_acordo)

        # 11. Composição da Carteira
        composicao_db = self.db.query(VwNfPendenciaFase.status, func.count(VwNfPendenciaFase.idnfpendencias)).filter(
            VwNfPendenciaFase.fase == 'FINANCEIRO'
        ).group_by(VwNfPendenciaFase.status).all()
        
        composicao_carteira = [{"name": r[0] or 'Indefinido', "value": r[1]} for r in composicao_db]

        return {
            "kpiVencido": float(kpi_vencido),
            "kpiVencidoEvolucao": kpi_vencido_evolucao,
            "kpiProtestado": float(kpi_protestado),
            "kpiProtestadoEvolucao": kpi_protestado_evolucao,
            "kpiTotalClientes": kpi_clientes,
            "kpiTotalClientesEvolucao": kpi_clientes_evolucao,
            
            "rankingClientesAtraso": ranking_clientes_atraso,
            "rankingClientesProtesto": ranking_clientes_protesto,
            "rankingGerentesAtraso": ranking_gerentes_atraso,
            "rankingGerentesProtesto": ranking_gerentes_protesto,
            "rankingRepresentantesAtraso": ranking_representantes_atraso,
            "rankingRepresentantesProtesto": ranking_representantes_protesto,
            
            "evolucaoAtraso": {
                "labels": meses_labels,
                "values": meses_valores_atraso
            },
            "evolucaoProtesto": {
                "labels": meses_labels,
                "values": meses_valores_protesto
            },
            
            "faixasAtraso": faixas_atraso_count,
            "composicaoCarteira": composicao_carteira,
            "gridFinanceiro": grid_financeiro,
            
            "evolucaoLogisticaSemEntrega": {
                "labels": meses_logistica_labels,
                "values": valores_sem_entrega
            },
            "evolucaoLogisticaDevolucao": {
                "labels": meses_logistica_labels,
                "values": valores_devolucao
            },
            
            "kpiSemEntrega": kpi_sem_entrega,
            "kpiDevolucao": kpi_devolucao,
            "gridSemEntrega": grid_sem_entrega,
            "gridDevolucao": grid_devolucao,
            "gridAcordos": grid_acordos,

            "kpiTotalAcordos": float(kpi_total_acordos),
            "rankingAcordos": ranking_acordos,
            "evolucaoAcordos": {
                "labels": meses_logistica_labels,
                "values": valores_acordos
            }
        }
