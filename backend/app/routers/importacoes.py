from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
import pandas as pd
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.importacao import ImportacaoPaginatedResponse
from app.services.importacao_service import ImportacaoService
from app.services.ia_service import IAService
from app.services.inadimplencia_service import InadimplenciaService
from app.repositories.categoria_repository import CategoriaRepository
from app.repositories.colaborador_repository import ColaboradorRepository
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from app.routers.plano_saude_ia import router as plano_saude_ia_router

router = APIRouter()

# Rotas de extração/confirmação/exportação de Plano de Saúde (Sorriso, Unimed Odonto
# e a rota universal por regex) vivem em app/routers/plano_saude_ia.py + PlanoSaudeIAService,
# mas seguem montadas aqui para preservar o contrato de URL
# (/api/v1/importacoes/plano-saude/...) já usado pelo frontend.
router.include_router(plano_saude_ia_router, prefix="/plano-saude")

def get_service(db: Session = Depends(get_db)):
    return ImportacaoService(db)

@router.get("", response_model=ImportacaoPaginatedResponse)
def get_importacoes(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    search: str = Query(None, description="Busca por nome de arquivo ou tipo"),
    categoria: str = Query(None, description="Categoria exata (ex: Composição, Prorrogação)"),
    service: ImportacaoService = Depends(get_service)
):
    return service.listar_importacoes(page=page, size=size, search=search, categoria=categoria)



@router.get("/inadimplencia/pendencias")
def listar_pendencias_inadimplencia(
    data_inicio: Optional[date] = Query(None, description="Filtra vencimento >= data_inicio (YYYY-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Filtra vencimento <= data_fim (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    try:
        return InadimplenciaService(db).listar_pendencias(data_inicio, data_fim)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/inadimplencia/janela-regra-dia")
def obter_janela_regra_dia_inadimplencia(db: Session = Depends(get_db)):
    try:
        return InadimplenciaService(db).obter_janela_regra_dia()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AlterarFasePayload(BaseModel):
    fase: str

class AlterarStatusPayload(BaseModel):
    status: str

@router.patch("/inadimplencia/pendencias/{id_nf}/fase")
def alterar_fase_pendencia(
    id_nf: int,
    payload: AlterarFasePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        return InadimplenciaService(db).alterar_fase(id_nf, payload.fase, current_user.iduser)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except LookupError as le:
        raise HTTPException(status_code=404, detail=str(le))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/inadimplencia/pendencias/{id_nf}/status")
def alterar_status_pendencia(
    id_nf: int,
    payload: AlterarStatusPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        return InadimplenciaService(db).alterar_status(id_nf, payload.status, current_user.iduser)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except LookupError as le:
        raise HTTPException(status_code=404, detail=str(le))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CriarTratativaPayload(BaseModel):
    conteudo: str

class EditarTratativaPayload(BaseModel):
    conteudo: str

@router.get("/inadimplencia/pendencias/{id_nf}/tratativas")
def listar_tratativas_pendencia(id_nf: int, db: Session = Depends(get_db)):
    try:
        return InadimplenciaService(db).listar_tratativas(id_nf)
    except LookupError as le:
        raise HTTPException(status_code=404, detail=str(le))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/inadimplencia/pendencias/{id_nf}/tratativas")
def criar_tratativa_pendencia(
    id_nf: int,
    payload: CriarTratativaPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        return InadimplenciaService(db).criar_tratativa(id_nf, payload.conteudo, current_user.iduser)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except LookupError as le:
        raise HTTPException(status_code=404, detail=str(le))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/inadimplencia/tratativas/{id_tratativa}")
def editar_tratativa_pendencia(id_tratativa: int, payload: EditarTratativaPayload, db: Session = Depends(get_db)):
    try:
        return InadimplenciaService(db).editar_tratativa(id_tratativa, payload.conteudo)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except LookupError as le:
        raise HTTPException(status_code=404, detail=str(le))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CriarHistoricoPayload(BaseModel):
    tipo: str
    observacao: str

@router.get("/inadimplencia/pendencias/{id_nf}/historico")
def listar_historico_pendencia(id_nf: int, db: Session = Depends(get_db)):
    try:
        return InadimplenciaService(db).listar_historico(id_nf)
    except LookupError as le:
        raise HTTPException(status_code=404, detail=str(le))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/inadimplencia/pendencias/{id_nf}/historico")
def criar_historico_pendencia(
    id_nf: int,
    payload: CriarHistoricoPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        return InadimplenciaService(db).registrar_historico(id_nf, payload.tipo, payload.observacao, current_user.iduser)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except LookupError as le:
        raise HTTPException(status_code=404, detail=str(le))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/inadimplencia/importar-pendencias")
async def importar_pendencias_inadimplencia(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo inválido")

    try:
        conteudo = await file.read()
        resultado = InadimplenciaService(db).importar_pendencias(conteudo, file.filename, current_user.iduser)
        return resultado
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{id_importacao}")
def excluir_importacao(
    id_importacao: int,
    db: Session = Depends(get_db)
):
    try:
        service = ImportacaoService(db)
        sucesso = service.excluir_importacao(id_importacao)
        if not sucesso:
            raise HTTPException(status_code=404, detail="Importação não encontrada")
        return {"sucesso": True, "mensagem": "Importação e movimentações vinculadas excluídas com sucesso"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


import re
import io
import zipfile
import pandas as pd
from fastapi.responses import StreamingResponse
from html.parser import HTMLParser

class AtacadaoHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.current_table = []
        self.current_row = []
        self.current_cell = []
        self.in_table = False
        self.in_tr = False
        self.in_td_or_th = False

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.in_table = True
            self.current_table = []
        elif tag == 'tr' and self.in_table:
            self.in_tr = True
            self.current_row = []
        elif tag in ('td', 'th') and self.in_tr:
            self.in_td_or_th = True
            self.current_cell = []

    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_table = False
            if self.current_table:
                self.tables.append(self.current_table)
        elif tag == 'tr' and self.in_table:
            self.in_tr = False
            if self.current_row:
                self.current_table.append(self.current_row)
        elif tag in ('td', 'th') and self.in_tr:
            self.in_td_or_th = False
            cell_text = "".join(self.current_cell).strip()
            self.current_row.append(cell_text)

    def handle_data(self, data):
        if self.in_td_or_th:
            self.current_cell.append(data)


async def conciliar_composicao_ws(wb, acr_file, rows_to_export, font_header, font_body, align_center, align_left, align_right):
    if not acr_file or not acr_file.filename:
        return
    acr_bytes = await acr_file.read()
    import io
    import pandas as pd
    from openpyxl.styles import PatternFill
    import logging
    debug_logger = logging.getLogger("composicao_debug")
    debug_logger.setLevel(logging.DEBUG)
    debug_logger.handlers = []
    debug_logger.addHandler(logging.NullHandler())

    debug_logger.info("--- INICIANDO CONCILIACAO COMPOSICAO ---")
    debug_logger.info(f"acr_file.filename: {acr_file.filename}")
    debug_logger.info(f"rows_to_export count: {len(rows_to_export)}")
    if rows_to_export:
        debug_logger.info(f"Exemplo item export: {rows_to_export[0]}")

    try:
        df_acr = pd.read_excel(io.BytesIO(acr_bytes), header=None)
        debug_logger.info("Lido com read_excel")
    except Exception as ex:
        debug_logger.error(f"Erro read_excel: {str(ex)}")
        acr_text = acr_bytes.decode('utf-8', errors='ignore')
        sep = ';' if ';' in acr_text else ','
        df_acr = pd.read_csv(io.StringIO(acr_text), sep=sep, header=None)
        debug_logger.info(f"Lido com read_csv, sep={sep}")
        
    debug_logger.info(f"df_acr shape: {df_acr.shape}")
    debug_logger.info(f"Primeiras 10 linhas do df_acr:\n{df_acr.head(10).to_string()}")
        
    col_titulo = -1
    col_parcela = -1
    col_saldo = -1
    
    # 1. Busca pelo nome no cabeçalho
    for idx, row in df_acr.head(30).iterrows():
        row_strs = [str(x).strip().lower() for x in row.values]
        for c_idx, val in enumerate(row_strs):
            if val == 'titulo' or val == 'título' or 'titulo' in val or 'título' in val:
                if col_titulo == -1: col_titulo = c_idx
            if val == '/p' or val == 'parcela' or '/p' in val or 'parcela' in val:
                if col_parcela == -1: col_parcela = c_idx
            if val == 'saldo' or 'saldo' in val or 'valor l' in val:
                if col_saldo == -1: col_saldo = c_idx
        if col_titulo != -1 and col_parcela != -1 and col_saldo != -1:
            break
            
    debug_logger.info(f"Apos busca de cabeçalho: col_titulo={col_titulo}, col_parcela={col_parcela}, col_saldo={col_saldo}")
            
    # 2. Heurística Robusta: auto-detecção cruzando NFs e valores
    comp_map = {}
    for item in rows_to_export:
        nf = str(item.get('Nota Fiscal') or item.get('nf')).strip()
        if nf:
            v = abs(item.get('Valor Liquido') or item.get('valor_liquido') or 0.0)
            if v > 0:
                comp_map[nf.lstrip('0')] = v
                
    debug_logger.info(f"comp_map (NFs da Composicao lstrip): {list(comp_map.keys())[:10]}")
    debug_logger.info(f"comp_map values: {list(comp_map.values())[:10]}")
                
    possible_titulo_cols = {}
    possible_saldo_cols = {}
    
    for idx, row in df_acr.iterrows():
        row_vals = list(row.values)
        for c_idx, val in enumerate(row_vals):
            if pd.isna(val):
                continue
            val_str = str(val).strip().split('.')[0]
            if val_str.endswith('.0'): val_str = val_str[:-2]
            val_clean = val_str.lstrip('0')
            
            if val_clean in comp_map:
                possible_titulo_cols[c_idx] = possible_titulo_cols.get(c_idx, 0) + 1
                expected_val = comp_map[val_clean]
                for val_c_idx, val_cell in enumerate(row_vals):
                    try:
                        if isinstance(val_cell, str):
                            val_cell_clean = val_cell.replace('R$', '').replace('.', '').replace(',', '.').strip()
                            val_cell_float = abs(float(val_cell_clean))
                        else:
                            val_cell_float = abs(float(val_cell))
                        if val_cell_float > 0 and abs(val_cell_float - expected_val) < 0.01:
                            possible_saldo_cols[val_c_idx] = possible_saldo_cols.get(val_c_idx, 0) + 1
                    except Exception:
                        pass
                        
    debug_logger.info(f"possible_titulo_cols: {possible_titulo_cols}")
    debug_logger.info(f"possible_saldo_cols: {possible_saldo_cols}")
                        
    if col_titulo == -1 and possible_titulo_cols:
        col_titulo = max(possible_titulo_cols, key=possible_titulo_cols.get)
    if col_saldo == -1 and possible_saldo_cols:
        col_saldo = max(possible_saldo_cols, key=possible_saldo_cols.get)
        
    # Fallbacks finais baseados nos formatos mais comuns
    if col_titulo == -1:
        col_titulo = 2 # Coluna C
    if col_parcela == -1:
        if col_titulo != -1 and col_titulo + 1 < df_acr.shape[1]:
            col_parcela = col_titulo + 1
        else:
            col_parcela = 3 # Coluna D
    if col_saldo == -1:
        col_saldo = 21 # Coluna V
        
    debug_logger.info(f"FINAL col_titulo={col_titulo}, col_parcela={col_parcela}, col_saldo={col_saldo}")

    acr_data = {}
    for idx, row in df_acr.iterrows():
        if len(row) <= col_titulo or len(row) <= col_saldo:
            continue
            
        val_d_raw = row[col_titulo]
        if pd.isna(val_d_raw):
            continue
            
        titulo = str(val_d_raw).strip().split('.')[0]
        if not any(char.isdigit() for char in titulo):
            continue
            
        if titulo.endswith('.0'):
            titulo = titulo[:-2]
            
        # Pular se o titulo lstrip for vazio ou não numérico
        titulo_clean = titulo.lstrip('0')
        if not titulo_clean:
            continue
            
        if col_parcela < len(row):
            parcela_val = str(row[col_parcela]).strip().split('.')[0]
            try:
                # Filtrar apenas Parcela 01 (igual nas Prorrogações)
                if int(parcela_val) != 1:
                    continue
            except ValueError:
                pass
                
        saldo_val = row[col_saldo]
        try:
            if isinstance(saldo_val, str):
                saldo_val = saldo_val.replace('R$', '').replace('.', '').replace(',', '.').strip()
            saldo_float = float(saldo_val)
            acr_data[titulo_clean] = abs(saldo_float)
        except ValueError:
            continue
            
    debug_logger.info(f"acr_data count: {len(acr_data)}")
    debug_logger.info(f"Exemplo acr_data: {list(acr_data.items())[:10]}")
            
    ws2 = wb.create_sheet(title="Conciliação")
    headers2 = ['Nota Fiscal', 'Parcela', 'Status NF', 'Valor Composição', 'Valor ACR', 'Status Valor', 'Diferença']
    ws2.append(headers2)
    for col_idx, col_name in enumerate(headers2, start=1):
        cell = ws2.cell(row=1, column=col_idx)
        cell.font = font_header
        cell.alignment = align_left if col_idx <= 3 else align_right
    fill_ok = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
    fill_err = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
    accounting_format = '_("R$"* #,##0.00_);_("R$"* (#,##0.00);_("R$"* "-"_);_(@_)'
    
    for i, item in enumerate(rows_to_export):
        nf = item.get('Nota Fiscal') or item.get('nf')
        if not nf:
            continue
        nf_str = str(nf).strip()
        val_comp = item.get('Valor Liquido') or item.get('valor_liquido') or 0.0
        
        status_nf = 'Não Encontrado'
        status_val = '-'
        val_acr = 0.0
        
        nf_clean = nf_str.lstrip('0')
        if nf_clean.endswith('T') or nf_clean.endswith('t'):
            nf_base = nf_clean[:-1]
        else:
            nf_base = nf_clean
            
        found_key = None
        if nf_clean in acr_data:
            found_key = nf_clean
        elif nf_base in acr_data:
            found_key = nf_base
                    
        if found_key:
            status_nf = 'Encontrado'
            val_acr = acr_data[found_key]
            if abs(abs(val_comp) - val_acr) < 0.01:
                status_val = 'OK'
            else:
                status_val = 'Divergente'
                
        r_idx = i + 2
        ws2.cell(row=r_idx, column=1, value=nf_str).font = font_body
        ws2.cell(row=r_idx, column=1).alignment = align_left
        ws2.cell(row=r_idx, column=2, value="01").font = font_body
        ws2.cell(row=r_idx, column=2).alignment = align_left
        ws2.cell(row=r_idx, column=3, value=status_nf).font = font_body
        ws2.cell(row=r_idx, column=3).alignment = align_left
        c4 = ws2.cell(row=r_idx, column=4, value=val_comp)
        c4.font = font_body
        c4.number_format = accounting_format
        c4.alignment = align_right
        c5 = ws2.cell(row=r_idx, column=5, value=val_acr if status_nf == 'Encontrado' else None)
        c5.font = font_body
        c5.number_format = accounting_format
        c5.alignment = align_right
        c6 = ws2.cell(row=r_idx, column=6, value=status_val)
        c6.font = font_body
        c6.alignment = align_right
        diferenca_val = (val_comp - val_acr) if status_val == 'Divergente' else None
        c7 = ws2.cell(row=r_idx, column=7, value=diferenca_val)
        c7.font = font_body
        c7.number_format = accounting_format
        c7.alignment = align_right
        if status_nf == 'Encontrado' and status_val == 'OK':
            for c in range(1, 8):
                ws2.cell(row=r_idx, column=c).fill = fill_ok
        else:
            for c in range(1, 8):
                ws2.cell(row=r_idx, column=c).fill = fill_err
    ws2.column_dimensions['A'].width = 16
    ws2.column_dimensions['B'].width = 10
    ws2.column_dimensions['C'].width = 18
    ws2.column_dimensions['D'].width = 18
    ws2.column_dimensions['E'].width = 18
    ws2.column_dimensions['F'].width = 16
    ws2.column_dimensions['G'].width = 18

@router.post("/atacadao/extrair")
async def extrair_atacadao(file: UploadFile = File(...), acr_file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo inválido")
        
    try:
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8", errors="ignore")
        
        parser = AtacadaoHTMLParser()
        parser.feed(content)
        
        def parse_float(val_str):
            if not val_str:
                return 0.0
            cleaned = val_str.replace('.', '').replace(',', '.').strip()
            try:
                return float(cleaned)
            except ValueError:
                return 0.0

        # Extrair o Total do Depósito do texto do HTML
        total_deposito = 0.0
        match_total = re.search(r'Total do Dep&oacute;sito:\s*([\d\.,]+)', content, re.IGNORECASE)
        if not match_total:
            match_total = re.search(r'Total do Depósito:\s*([\d\.,]+)', content, re.IGNORECASE)
        if match_total:
            total_deposito = parse_float(match_total.group(1))

        rows_to_export = []
        for table in parser.tables:
            if not table:
                continue
            headers = [h.strip() for h in table[0]]
            if 'N Fiscal' not in headers:
                continue
            
            n_fiscal_idx = headers.index('N Fiscal')
            val_idx = headers.index('Valor') if 'Valor' in headers else None
            abat_idx = headers.index('Abatimento') if 'Abatimento' in headers else None
            liq_idx = headers.index('Vlr liquido') if 'Vlr liquido' in headers else None
            
            for row in table[1:]:
                if len(row) <= n_fiscal_idx:
                    continue
                
                n_fiscal_raw = row[n_fiscal_idx].strip()
                if not n_fiscal_raw or n_fiscal_raw.lower() == 'total' or 'total' in n_fiscal_raw.lower():
                    continue
                
                # Filtro: Apenas notas fiscais que comecem com '0000'
                if not n_fiscal_raw.startswith('0000'):
                    continue
                
                # Formatação: Remover os dois primeiros zeros (de 4 zeros para 2 zeros)
                n_fiscal_formatted = n_fiscal_raw[2:]
                
                # Parcela:
                # Se terminar com 'T', Parcela '02', senão '01'
                parcela = '02' if n_fiscal_raw.endswith('T') else '01'
                
                valor_total = parse_float(row[val_idx]) if val_idx is not None and val_idx < len(row) else 0.0
                abatimento = parse_float(row[abat_idx]) if abat_idx is not None and abat_idx < len(row) else 0.0
                
                if liq_idx is not None and liq_idx < len(row):
                    valor_liquido = parse_float(row[liq_idx])
                else:
                    valor_liquido = valor_total
                    
                rows_to_export.append({
                    'Nota Fiscal': n_fiscal_formatted,
                    'Parcela': parcela,
                    'Abatimento': abatimento if abatimento != 0.0 else None,
                    'Valor Liquido': valor_liquido,
                    'Valor Total': valor_total
                })
        
        if not rows_to_export:
            raise HTTPException(status_code=400, detail="Nenhum dado de Nota Fiscal começando com '0000' foi encontrado no HTML.")
            
        # Caso não consiga extrair o total do depósito via texto, calcula a soma do valor líquido
        if total_deposito == 0.0:
            total_deposito = sum((r['Valor Liquido'] or 0.0) for r in rows_to_export)

        # Geração do arquivo Excel formatado com openpyxl
        import openpyxl
        from openpyxl.styles import Font, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Composição de Pagamento"
        
        # Ativar linhas de grade
        ws.views.sheetView[0].showGridLines = True

        # Cabeçalhos exatamente conforme o print
        headers = ['Nota Fiscal', 'Parcela', 'Abatimento', 'Valor Líquido', '', '', 'Valor Total']
        ws.append(headers)

        # Preenchimento das linhas
        for i, item in enumerate(rows_to_export):
            # Apenas a linha 2 da coluna G possui o total geral
            val_total = total_deposito if i == 0 else None
            
            ws.append([
                item['Nota Fiscal'],
                item['Parcela'],
                item['Abatimento'],
                item['Valor Liquido'],
                '',
                '',
                val_total
            ])

        # Definição das fontes e alinhamento
        font_header = Font(name='Calibri', size=11, bold=True)
        font_body = Font(name='Calibri', size=11, bold=False)
        align_center = Alignment(horizontal='center', vertical='center')
        align_right = Alignment(horizontal='right', vertical='center')
        align_left = Alignment(horizontal='left', vertical='center')

        # Formato contábil do Excel (R$ e valor alinhados nas extremidades da célula)
        accounting_format = '_("R$"* #,##0.00_);_("R$"* (#,##0.00);_("R$"* "-"_);_(@_)'

        # Estilizar cabeçalho
        for col_idx, col_name in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = font_header
            if col_idx in [1, 2]:
                cell.alignment = align_left
            elif col_idx in [3, 4, 7]:
                cell.alignment = align_right

        # Estilizar o corpo e aplicar formatação de números
        for r_idx in range(2, len(rows_to_export) + 2):
            # Nota Fiscal (Col 1)
            cell_nf = ws.cell(row=r_idx, column=1)
            cell_nf.font = font_body
            cell_nf.number_format = '@' # Formato Texto
            cell_nf.alignment = align_left
            
            # Parcela (Col 2)
            cell_par = ws.cell(row=r_idx, column=2)
            cell_par.font = font_body
            cell_par.number_format = '@' # Formato Texto
            cell_par.alignment = align_left
            
            # Abatimento (Col 3)
            cell_ab = ws.cell(row=r_idx, column=3)
            cell_ab.font = font_body
            cell_ab.number_format = accounting_format
            cell_ab.alignment = align_right
            
            # Valor Líquido (Col 4)
            cell_liq = ws.cell(row=r_idx, column=4)
            cell_liq.font = font_body
            cell_liq.number_format = accounting_format
            cell_liq.alignment = align_right
            
            # Valor Total (Col 7)
            cell_tot = ws.cell(row=r_idx, column=7)
            cell_tot.font = font_body
            if cell_tot.value is not None:
                cell_tot.number_format = accounting_format
                cell_tot.alignment = align_right

        # Definir larguras de coluna estáticas para se adequar ao print
        ws.column_dimensions['A'].width = 16
        ws.column_dimensions['B'].width = 10
        ws.column_dimensions['C'].width = 16
        ws.column_dimensions['D'].width = 18
        ws.column_dimensions['E'].width = 5
        ws.column_dimensions['F'].width = 5
        ws.column_dimensions['G'].width = 20

        await conciliar_composicao_ws(wb, acr_file, rows_to_export, font_header, font_body, align_center, align_left, align_right)

        # Salvar em buffer
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = file.filename.rsplit('.', 1)[0] + "_extraido.xlsx"
        
        # Registrar no banco
        ImportacaoService(db).registrar_importacao(filename, "xlsx", "Composição - Atacadão", id_user_inc=current_user.iduser)
        
        headers_response = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers_response
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sendas/extrair")
async def extrair_sendas(file: UploadFile = File(...), acr_file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo inválido")
        
    try:
        content_bytes = await file.read()
        
        # Load the spreadsheet
        df = pd.read_excel(io.BytesIO(content_bytes), header=None)
        
        # Resolve H and X column names/indices (H is 8th column -> index 7, X is 24th column -> index 23)
        if df.shape[1] < 24:
            raise HTTPException(
                status_code=400, 
                detail=f"A planilha importada precisa ter pelo menos 24 colunas (até a coluna X). Colunas encontradas: {df.shape[1]}."
            )
            
        h_col_idx = 7
        x_col_idx = 23
        
        def parse_float(val):
            if pd.isna(val):
                return 0.0
            if isinstance(val, (int, float)):
                return float(val)
            cleaned = str(val).replace('.', '').replace(',', '.').replace('R$', '').strip()
            try:
                return float(cleaned)
            except ValueError:
                return 0.0

        notas_fiscais = []
        devolucoes = []
        abatimentos = []

        # Iterate rows starting from index 0 or 1 depending on header detection
        for idx, row in df.iterrows():
            val_h_raw = row[h_col_idx]
            val_x_raw = row[x_col_idx]
            
            if pd.isna(val_h_raw):
                continue
                
            val_h = str(val_h_raw).strip()
            # Remove decimal part .0 if auto-formatted as float
            if val_h.endswith('.0'):
                val_h = val_h[:-2]
                
            val_x = parse_float(val_x_raw)
            
            # Filtro: Ignorar linhas e dados onde a coluna X estiver com 0
            if val_x == 0.0:
                continue

            # Skip header rows
            if val_h.lower() in ('h', 'código', 'nota fiscal', 'portador', 'n fiscal', 'tipo'):
                continue

            # Apply rules:
            # 1. Nota Fiscal: starts with 1 or 2 AND ends with 2
            if val_h.startswith(('1', '2')) and val_h.endswith('2'):
                # Formatação: Remover espaços e o último caractere '2', e preencher com zeros à esquerda até obter 7 dígitos
                cleaned_h = val_h.replace(' ', '')
                if cleaned_h.endswith('2'):
                    cleaned_h = cleaned_h[:-1]
                formatted_nf = cleaned_h.zfill(7)
                notas_fiscais.append((formatted_nf, val_x))
            # 2. Abatimento: starts with "AC"
            elif val_h.startswith('AC'):
                abatimentos.append((val_h, val_x))
            # 3. Devolução: starts with any number AND ends with "300"
            elif val_h.endswith('300') and val_h[0].isdigit():
                devolucoes.append((val_h, val_x))
                
        if not notas_fiscais and not devolucoes and not abatimentos:
            raise HTTPException(
                status_code=400, 
                detail="Nenhum registro correspondente aos filtros de Nota Fiscal, Devolução ou Abatimento foi encontrado na coluna H."
            )

        # Generate excel with openpyxl to match the layout
        import openpyxl
        from openpyxl.styles import Font, Alignment
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Filtro Sendas"
        ws.views.sheetView[0].showGridLines = True

        # Headers exactly as requested
        # Col A: Nota fiscal, Col B: Valor Total
        # Col D: Valor Total, Col E: Devolução
        # Col I: Abatimento, Col J: Valor Total
        # Col L: Soma Total
        ws.cell(row=1, column=1, value="Nota fiscal")
        ws.cell(row=1, column=2, value="Valor Total")
        ws.cell(row=1, column=4, value="Valor Total")
        ws.cell(row=1, column=5, value="Devolução")
        ws.cell(row=1, column=9, value="Abatimento")
        ws.cell(row=1, column=10, value="Valor Total")
        ws.cell(row=1, column=12, value="Soma Total")

        max_rows = max(len(notas_fiscais), len(devolucoes), len(abatimentos))

        for r_idx in range(max_rows):
            row_num = r_idx + 2
            
            # 1. Nota Fiscal (Col A, B)
            if r_idx < len(notas_fiscais):
                nf_code, nf_val = notas_fiscais[r_idx]
                ws.cell(row=row_num, column=1, value=nf_code)
                ws.cell(row=row_num, column=2, value=nf_val)
                
            # 2. Devolução (Col E, D)
            if r_idx < len(devolucoes):
                dev_code, dev_val = devolucoes[r_idx]
                ws.cell(row=row_num, column=5, value=dev_code)
                ws.cell(row=row_num, column=4, value=dev_val)
                
            # 3. Abatimento (Col I, J)
            if r_idx < len(abatimentos):
                ab_code, ab_val = abatimentos[r_idx]
                ws.cell(row=row_num, column=9, value=ab_code)
                ws.cell(row=row_num, column=10, value=ab_val)

        # Write Soma total on Row 2 of Column L
        soma_nf = sum(v for _, v in notas_fiscais)
        soma_dev = sum(v for _, v in devolucoes)
        soma_abat = sum(v for _, v in abatimentos)
        soma_total = soma_nf + soma_dev + soma_abat

        ws.cell(row=2, column=12, value=soma_total)

        # Formatting
        font_header = Font(name='Calibri', size=11, bold=True)
        font_body = Font(name='Calibri', size=11, bold=False)
        align_center = Alignment(horizontal='center', vertical='center')
        align_right = Alignment(horizontal='right', vertical='center')
        align_left = Alignment(horizontal='left', vertical='center')
        accounting_format = '_("R$"* #,##0.00_);_("R$"* (#,##0.00);_("R$"* "-"_);_(@_)'

        # Format Headers
        active_cols = [1, 2, 4, 5, 9, 10, 12]
        for col_idx in active_cols:
            cell = ws.cell(row=1, column=col_idx)
            cell.font = font_header
            if col_idx in [1, 5, 9]:
                cell.alignment = align_left
            elif col_idx in [2, 4, 10, 12]:
                cell.alignment = align_right

        # Format Body
        for r_idx in range(2, max_rows + 2):
            # Nota Fiscal (Col 1)
            cell_nf = ws.cell(row=r_idx, column=1)
            cell_nf.font = font_body
            cell_nf.number_format = '@'
            cell_nf.alignment = align_left
            
            # NF Valor (Col 2)
            c_nf_val = ws.cell(row=r_idx, column=2)
            c_nf_val.font = font_body
            if c_nf_val.value is not None:
                c_nf_val.number_format = accounting_format
                c_nf_val.alignment = align_right
                
            # Devolução Valor (Col 4)
            c_dev_val = ws.cell(row=r_idx, column=4)
            c_dev_val.font = font_body
            if c_dev_val.value is not None:
                c_dev_val.number_format = accounting_format
                c_dev_val.alignment = align_right
                
            # Devolução Código (Col 5)
            cell_dev = ws.cell(row=r_idx, column=5)
            cell_dev.font = font_body
            cell_dev.number_format = '@'
            cell_dev.alignment = align_left
            
            # Abatimento Código (Col 9)
            cell_ab = ws.cell(row=r_idx, column=9)
            cell_ab.font = font_body
            cell_ab.number_format = '@'
            cell_ab.alignment = align_left
            
            # Abatimento Valor (Col 10)
            c_ab_val = ws.cell(row=r_idx, column=10)
            c_ab_val.font = font_body
            if c_ab_val.value is not None:
                c_ab_val.number_format = accounting_format
                c_ab_val.alignment = align_right

        # Format Soma total (Col 12, Row 2)
        c_soma = ws.cell(row=2, column=12)
        c_soma.font = font_body
        c_soma.number_format = accounting_format
        c_soma.alignment = align_right

        # Column widths
        ws.column_dimensions['A'].width = 16
        ws.column_dimensions['B'].width = 16
        ws.column_dimensions['C'].width = 5
        ws.column_dimensions['D'].width = 16
        ws.column_dimensions['E'].width = 16
        ws.column_dimensions['F'].width = 5
        ws.column_dimensions['G'].width = 5
        ws.column_dimensions['H'].width = 5
        ws.column_dimensions['I'].width = 16
        ws.column_dimensions['J'].width = 16
        ws.column_dimensions['K'].width = 5
        ws.column_dimensions['L'].width = 20

        # Transform notas_fiscais + abatimentos for conciliar (we need "Nota Fiscal" and "Valor Liquido")
        all_items = []
        for n in notas_fiscais:
            all_items.append({"Nota Fiscal": n[0], "Valor Liquido": n[1]})
        for a in abatimentos:
            all_items.append({"Nota Fiscal": a[0], "Valor Liquido": a[1]})
        await conciliar_composicao_ws(wb, acr_file, all_items, font_header, font_body, align_center, align_left, align_right)

        # Save to buffer
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = file.filename.rsplit('.', 1)[0] + "_extraido.xlsx"
        
        # Registrar no banco
        ImportacaoService(db).registrar_importacao(filename, "xlsx", "Composição - Sendas", id_user_inc=current_user.iduser)
        
        headers_response = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers_response
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/atacadao/conciliar")
async def conciliar_atacadao(
    html_files: List[UploadFile] = File(...),
    csv_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not html_files or not csv_file.filename:
        raise HTTPException(status_code=400, detail="Arquivos inválidos")
        
    try:
        # 1. Parse HTML files
        invoices_html = []
        for h_file in html_files:
            html_bytes = await h_file.read()
            html_content = html_bytes.decode('utf-8', errors='ignore')
            
            parser = AtacadaoHTMLParser()
            parser.feed(html_content)
            
            for table in parser.tables:
                if not table:
                    continue
                headers = [h.strip() for h in table[0]]
                if 'N Fiscal' not in headers or 'Prorrog.' not in headers:
                    continue
                
                n_fiscal_idx = headers.index('N Fiscal')
                prorrog_idx = headers.index('Prorrog.')
                
                for row in table[1:]:
                    if len(row) <= max(n_fiscal_idx, prorrog_idx):
                        continue
                    n_fiscal_raw = row[n_fiscal_idx].strip()
                    prorrog_raw = row[prorrog_idx].strip()
                    
                    if not n_fiscal_raw or n_fiscal_raw.lower() == 'total' or 'total' in n_fiscal_raw.lower():
                        continue
                        
                    # Trim leading 2 zeros (000017059 -> 0017059)
                    n_fiscal_formatted = n_fiscal_raw[2:] if n_fiscal_raw.startswith('0000') else n_fiscal_raw
                    
                    invoices_html.append({
                        'raw_nf': n_fiscal_raw,
                        'nf': n_fiscal_formatted,
                        'prorrogacao': prorrog_raw
                    })
                
        if not invoices_html:
            raise HTTPException(
                status_code=400,
                detail="Nenhum registro de prorrogação encontrado no arquivo HTML informado."
            )
            
        # 2. Parse CSV/Excel file
        csv_bytes = await csv_file.read()
        
        import io
        import pandas as pd
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        import datetime

        # Load dynamic CSV/Excel
        try:
            df_csv = pd.read_excel(io.BytesIO(csv_bytes), header=None)
        except Exception:
            csv_text = csv_bytes.decode('utf-8', errors='ignore')
            sep = ';' if ';' in csv_text else ','
            df_csv = pd.read_csv(io.StringIO(csv_text), sep=sep, header=None)
            
        # Process and filter CSV data:
        # Col A (0): filter only 104
        # Col D (3): invoice number
        # Col E (4): parcela (must be 01)
        # Col P (15): due date (data de vencimento)
        csv_data_by_int = {}
        for idx, row in df_csv.iterrows():
            if len(row) < 16:
                continue
            val_a = str(row[0]).strip().split('.')[0]
            if val_a != '104':
                continue
            val_b = str(row[1]).strip().upper()
            if val_b != 'DP':
                continue
            val_d = str(row[3]).strip().split('.')[0]
            
            # Filtro da Coluna E (Parcela) - sempre 01
            val_e = str(row[4]).strip().split('.')[0]
            try:
                if int(val_e) != 1:
                    continue
            except ValueError:
                continue
                
            val_p = str(row[15]).strip()
            
            # Remove time component if present
            if ' ' in val_p:
                val_p = val_p.split()[0]
                
            try:
                csv_data_by_int[int(val_d)] = val_p
            except ValueError:
                continue
                
        # Helper to parse dates
        def parse_date(date_str):
            if not date_str:
                return None
            date_str = str(date_str).strip()
            for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d/%m/%y', '%Y/%m/%d %H:%M:%S', '%d/%m/%Y %H:%M:%S'):
                try:
                    return datetime.datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            return date_str

        def format_date_to_br(date_str):
            if not date_str:
                return ""
            d = parse_date(date_str)
            if isinstance(d, datetime.date):
                return d.strftime('%d/%m/%Y')
            return str(date_str)

        # 3. Create Excel workbook with two sheets
        wb = openpyxl.Workbook()

        # Sheet 1: Prorrogações Atacadão
        ws1 = wb.active
        ws1.title = "Prorrogações Atacadão"
        ws1.views.sheetView[0].showGridLines = True

        ws1.cell(row=1, column=1, value="Nota Fiscal")
        ws1.cell(row=1, column=2, value="Data de Prorrogação")

        for i, inv in enumerate(invoices_html):
            row_num = i + 2
            ws1.cell(row=row_num, column=1, value=inv['nf'])
            ws1.cell(row=row_num, column=2, value=format_date_to_br(inv['prorrogacao']))

        # Sheet 2: Conciliação
        ws2 = wb.create_sheet(title="Conciliação")
        ws2.views.sheetView[0].showGridLines = True

        ws2.cell(row=1, column=1, value="Nota Fiscal")
        ws2.cell(row=1, column=2, value="Data HTML (Prorrogação)")
        ws2.cell(row=1, column=3, value="Data CSV (Vencimento)")
        ws2.cell(row=1, column=4, value="Status")

        # Fonts, alignments and colors
        font_header = Font(name='Calibri', size=11, bold=True)
        font_body = Font(name='Calibri', size=11, bold=False)
        align_left = Alignment(horizontal='left', vertical='center')
        align_center = Alignment(horizontal='center', vertical='center')
        
        fill_ok = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid") # soft green
        fill_div = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid") # soft orange

        # Format Sheet 1 Headers
        for col_idx in [1, 2]:
            cell = ws1.cell(row=1, column=col_idx)
            cell.font = font_header
            cell.alignment = align_left

        # Format Sheet 1 Body
        for r_idx in range(2, len(invoices_html) + 2):
            c1 = ws1.cell(row=r_idx, column=1)
            c1.font = font_body
            c1.number_format = '@'
            c1.alignment = align_left
            
            c2 = ws1.cell(row=r_idx, column=2)
            c2.font = font_body
            c2.alignment = align_center

        ws1.column_dimensions['A'].width = 16
        ws1.column_dimensions['B'].width = 24

        # Conciliate and populate Sheet 2
        for i, inv in enumerate(invoices_html):
            row_num = i + 2
            nf_str = inv['nf']
            date_html_str = inv['prorrogacao']
            
            try:
                nf_int = int(inv['raw_nf'])
            except ValueError:
                nf_int = None
                
            date_csv_str = ""
            status = "Não encontrado no CSV"
            status_fill = None
            
            if nf_int is not None and nf_int in csv_data_by_int:
                date_csv_str = csv_data_by_int[nf_int]
                d_html = parse_date(date_html_str)
                d_csv = parse_date(date_csv_str)
                
                # Check for equivalence or string match
                if d_html and d_csv:
                    if d_html == d_csv:
                        status = "OK"
                        status_fill = fill_ok
                    else:
                        status = "Divergente"
                        status_fill = fill_div
                else:
                    if str(date_html_str).strip() == str(date_csv_str).strip():
                        status = "OK"
                        status_fill = fill_ok
                    else:
                        status = "Divergente"
                        status_fill = fill_div
                        
            ws2.cell(row=row_num, column=1, value=nf_str)
            ws2.cell(row=row_num, column=2, value=format_date_to_br(date_html_str))
            ws2.cell(row=row_num, column=3, value=format_date_to_br(date_csv_str))
            
            status_cell = ws2.cell(row=row_num, column=4, value=status)
            if status_fill:
                status_cell.fill = status_fill

        # Format Sheet 2 Headers
        for col_idx in [1, 2, 3, 4]:
            cell = ws2.cell(row=1, column=col_idx)
            cell.font = font_header
            cell.alignment = align_left

        # Format Sheet 2 Body
        for r_idx in range(2, len(invoices_html) + 2):
            ws2.cell(row=r_idx, column=1).font = font_body
            ws2.cell(row=r_idx, column=1).number_format = '@'
            ws2.cell(row=r_idx, column=1).alignment = align_left
            
            ws2.cell(row=r_idx, column=2).font = font_body
            ws2.cell(row=r_idx, column=2).alignment = align_center
            
            ws2.cell(row=r_idx, column=3).font = font_body
            ws2.cell(row=r_idx, column=3).alignment = align_center
            
            ws2.cell(row=r_idx, column=4).font = font_body
            ws2.cell(row=r_idx, column=4).alignment = align_center

        ws2.column_dimensions['A'].width = 16
        ws2.column_dimensions['B'].width = 24
        ws2.column_dimensions['C'].width = 24
        ws2.column_dimensions['D'].width = 24

        # Save workbook to memory buffer
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = html_files[0].filename.rsplit('.', 1)[0] + "_conciliado.xlsx"
        
        # Registrar no banco
        ImportacaoService(db).registrar_importacao(filename, "xlsx", "Prorrogação - Atacadão", id_user_inc=current_user.iduser)
        
        headers_response = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers_response
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sendas/conciliar")
async def conciliar_sendas(
    sendas_file: UploadFile = File(...),
    acr_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not sendas_file.filename or not acr_file.filename:
        raise HTTPException(status_code=400, detail="Arquivos inválidos")
        
    try:
        # Load Sendas file
        sendas_bytes = await sendas_file.read()
        import io
        import pandas as pd
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        import datetime

        try:
            df_sendas = pd.read_excel(io.BytesIO(sendas_bytes), header=None)
        except Exception:
            csv_text = sendas_bytes.decode('utf-8', errors='ignore')
            sep = ';' if ';' in csv_text else ','
            df_sendas = pd.read_csv(io.StringIO(csv_text), sep=sep, header=None)

        if df_sendas.shape[1] < 13:
            raise HTTPException(
                status_code=400,
                detail=f"O arquivo Sendas precisa ter pelo menos 13 colunas (até a coluna M). Colunas encontradas: {df_sendas.shape[1]}."
            )

        # Parse Sendas data
        h_col_idx = 7 # Column H
        m_col_idx = 12 # Column M
        
        invoices_sendas = []
        for idx, row in df_sendas.iterrows():
            val_h_raw = row[h_col_idx]
            val_m_raw = row[m_col_idx]
            
            if pd.isna(val_h_raw) or pd.isna(val_m_raw):
                continue
                
            val_h = str(val_h_raw).strip()
            if val_h.endswith('.0'):
                val_h = val_h[:-2]
                
            # Filter starts with 1 or 2 and ends with 2
            if val_h.startswith(('1', '2')) and val_h.endswith('2'):
                # Format: remove spaces, remove final '2', pad to 7 characters
                cleaned_h = val_h.replace(' ', '')
                if cleaned_h.endswith('2'):
                    cleaned_h = cleaned_h[:-1]
                formatted_nf = cleaned_h.zfill(7)
                
                date_m = str(val_m_raw).strip()
                if ' ' in date_m:
                    date_m = date_m.split()[0]
                    
                invoices_sendas.append({
                    'raw_nf': val_h,
                    'nf': formatted_nf,
                    'vencimento': date_m
                })
                
        if not invoices_sendas:
            raise HTTPException(
                status_code=400,
                detail="Nenhum registro correspondente ao padrão Sendas foi encontrado na coluna H."
            )

        # Load ACR file
        acr_bytes = await acr_file.read()
        try:
            df_acr = pd.read_excel(io.BytesIO(acr_bytes), header=None)
        except Exception:
            csv_text = acr_bytes.decode('utf-8', errors='ignore')
            sep = ';' if ';' in csv_text else ','
            df_acr = pd.read_csv(io.StringIO(csv_text), sep=sep, header=None)

        if df_acr.shape[1] < 16:
            raise HTTPException(
                status_code=400,
                detail=f"O arquivo ACR precisa ter pelo menos 16 colunas (até a coluna P). Colunas encontradas: {df_acr.shape[1]}."
            )

        # Parse ACR data
        d_col_idx = 3 # Column D
        p_col_idx = 15 # Column P
        
        acr_data_by_int = {}
        for idx, row in df_acr.iterrows():
            val_d_raw = row[d_col_idx]
            val_p_raw = row[p_col_idx]
            
            if pd.isna(val_d_raw) or pd.isna(val_p_raw):
                continue
                
            val_d = str(val_d_raw).strip().split('.')[0]
            val_p = str(val_p_raw).strip()
            if ' ' in val_p:
                val_p = val_p.split()[0]
                
            try:
                acr_data_by_int[int(val_d)] = val_p
            except ValueError:
                continue

        # Helper to parse dates
        def parse_date(date_str):
            if not date_str:
                return None
            date_str = str(date_str).strip()
            for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d/%m/%y', '%Y/%m/%d %H:%M:%S', '%d/%m/%Y %H:%M:%S'):
                try:
                    return datetime.datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            return date_str

        def format_date_to_br(date_str):
            if not date_str:
                return ""
            d = parse_date(date_str)
            if isinstance(d, datetime.date):
                return d.strftime('%d/%m/%Y')
            return str(date_str)

        # Create Workbook
        wb = openpyxl.Workbook()
        
        # Tab 1
        ws1 = wb.active
        ws1.title = "Prorrogações Sendas"
        ws1.views.sheetView[0].showGridLines = True
        
        ws1.cell(row=1, column=1, value="Nota Fiscal")
        ws1.cell(row=1, column=2, value="Data de Vencimento")
        
        for i, inv in enumerate(invoices_sendas):
            row_num = i + 2
            ws1.cell(row=row_num, column=1, value=inv['nf'])
            ws1.cell(row=row_num, column=2, value=format_date_to_br(inv['vencimento']))
            
        # Tab 2
        ws2 = wb.create_sheet(title="Conciliação")
        ws2.views.sheetView[0].showGridLines = True
        
        ws2.cell(row=1, column=1, value="Nota Fiscal")
        ws2.cell(row=1, column=2, value="Data Sendas (Vencimento)")
        ws2.cell(row=1, column=3, value="Data ACR (Vencimento)")
        ws2.cell(row=1, column=4, value="Status")

        # Fonts, alignments and colors
        font_header = Font(name='Calibri', size=11, bold=True)
        font_body = Font(name='Calibri', size=11, bold=False)
        align_left = Alignment(horizontal='left', vertical='center')
        align_center = Alignment(horizontal='center', vertical='center')
        
        fill_ok = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
        fill_div = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")

        # Format Tab 1 Headers
        for col_idx in [1, 2]:
            cell = ws1.cell(row=1, column=col_idx)
            cell.font = font_header
            cell.alignment = align_left

        # Format Tab 1 Body
        for r_idx in range(2, len(invoices_sendas) + 2):
            c1 = ws1.cell(row=r_idx, column=1)
            c1.font = font_body
            c1.number_format = '@'
            c1.alignment = align_left
            
            c2 = ws1.cell(row=r_idx, column=2)
            c2.font = font_body
            c2.alignment = align_center

        ws1.column_dimensions['A'].width = 16
        ws1.column_dimensions['B'].width = 24

        # Conciliate
        for i, inv in enumerate(invoices_sendas):
            row_num = i + 2
            nf_str = inv['nf']
            date_sendas_str = inv['vencimento']
            
            try:
                raw_nf_cleaned = inv['raw_nf'].replace(' ', '')
                if raw_nf_cleaned.endswith('2'):
                    raw_nf_cleaned = raw_nf_cleaned[:-1]
                nf_int = int(raw_nf_cleaned)
            except ValueError:
                nf_int = None
                
            date_acr_str = ""
            status = "Não encontrado no ACR"
            status_fill = None
            
            if nf_int is not None and nf_int in acr_data_by_int:
                date_acr_str = acr_data_by_int[nf_int]
                d_sendas = parse_date(date_sendas_str)
                d_acr = parse_date(date_acr_str)
                
                if d_sendas and d_acr:
                    if d_sendas == d_acr:
                        status = "OK"
                        status_fill = fill_ok
                    else:
                        status = "Divergente"
                        status_fill = fill_div
                else:
                    if str(date_sendas_str).strip() == str(date_acr_str).strip():
                        status = "OK"
                        status_fill = fill_ok
                    else:
                        status = "Divergente"
                        status_fill = fill_div
                        
            ws2.cell(row=row_num, column=1, value=nf_str)
            ws2.cell(row=row_num, column=2, value=format_date_to_br(date_sendas_str))
            ws2.cell(row=row_num, column=3, value=format_date_to_br(date_acr_str))
            
            status_cell = ws2.cell(row=row_num, column=4, value=status)
            if status_fill:
                status_cell.fill = status_fill

        # Format Tab 2 Headers
        for col_idx in [1, 2, 3, 4]:
            cell = ws2.cell(row=1, column=col_idx)
            cell.font = font_header
            cell.alignment = align_left

        # Format Tab 2 Body
        for r_idx in range(2, len(invoices_sendas) + 2):
            ws2.cell(row=r_idx, column=1).font = font_body
            ws2.cell(row=r_idx, column=1).number_format = '@'
            ws2.cell(row=r_idx, column=1).alignment = align_left
            
            ws2.cell(row=r_idx, column=2).font = font_body
            ws2.cell(row=r_idx, column=2).alignment = align_center
            
            ws2.cell(row=r_idx, column=3).font = font_body
            ws2.cell(row=r_idx, column=3).alignment = align_center
            
            ws2.cell(row=r_idx, column=4).font = font_body
            ws2.cell(row=r_idx, column=4).alignment = align_center

        ws2.column_dimensions['A'].width = 16
        ws2.column_dimensions['B'].width = 24
        ws2.column_dimensions['C'].width = 24
        ws2.column_dimensions['D'].width = 24

        # Save Workbook
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = sendas_file.filename.rsplit('.', 1)[0] + "_conciliado.xlsx"
        
        # Registrar no banco
        ImportacaoService(db).registrar_importacao(filename, "xlsx", "Prorrogação - Sendas", id_user_inc=current_user.iduser)
        
        headers_response = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers_response
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/martminas/conciliar")
async def conciliar_martminas(
    martminas_file: UploadFile = File(...),
    acr_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not martminas_file.filename or not acr_file.filename:
        raise HTTPException(status_code=400, detail="Arquivos inválidos")
        
    try:
        # Load Mart Minas file
        martminas_bytes = await martminas_file.read()
        import io
        import pandas as pd
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        import datetime

        try:
            df_mm = pd.read_excel(io.BytesIO(martminas_bytes), header=None)
        except Exception:
            csv_text = martminas_bytes.decode('utf-8', errors='ignore')
            sep = ';' if ';' in csv_text else ','
            df_mm = pd.read_csv(io.StringIO(csv_text), sep=sep, header=None)

        if df_mm.shape[1] < 5:
            raise HTTPException(
                status_code=400,
                detail=f"O arquivo Mart Minas precisa ter pelo menos 5 colunas (até a coluna E). Colunas encontradas: {df_mm.shape[1]}."
            )

        # Parse Mart Minas data
        # Col E (4): nro documento
        # Col D (3): vencimento
        e_col_idx = 4
        d_col_idx = 3
        
        invoices_mm = []
        for idx, row in df_mm.iterrows():
            val_e_raw = row[e_col_idx]
            val_d_raw = row[d_col_idx]
            
            if pd.isna(val_e_raw) or pd.isna(val_d_raw):
                continue
                
            val_e = str(val_e_raw).strip()
            if val_e.endswith('.0'):
                val_e = val_e[:-2]
                
            # Skip header rows or non-numeric document numbers
            try:
                val_e_clean = val_e.replace(' ', '')
                if not val_e_clean:
                    continue
                int(val_e_clean)
            except ValueError:
                continue
                
            # Formatting: zfill to 7 characters
            formatted_nf = val_e.zfill(7)
            
            date_d = str(val_d_raw).strip()
            if ' ' in date_d:
                date_d = date_d.split()[0]
                
            invoices_mm.append({
                'raw_nf': val_e,
                'nf': formatted_nf,
                'vencimento': date_d
            })
            
        if not invoices_mm:
            raise HTTPException(
                status_code=400,
                detail="Nenhum registro correspondente ao padrão Mart Minas foi encontrado na coluna E."
            )

        # Load ACR file
        acr_bytes = await acr_file.read()
        try:
            df_acr = pd.read_excel(io.BytesIO(acr_bytes), header=None)
        except Exception:
            csv_text = acr_bytes.decode('utf-8', errors='ignore')
            sep = ';' if ';' in csv_text else ','
            df_acr = pd.read_csv(io.StringIO(csv_text), sep=sep, header=None)

        if df_acr.shape[1] < 16:
            raise HTTPException(
                status_code=400,
                detail=f"O arquivo ACR precisa ter pelo menos 16 colunas (até a coluna P). Colunas encontradas: {df_acr.shape[1]}."
            )

        # Parse ACR data
        acr_d_col_idx = 3 # Column D
        acr_p_col_idx = 15 # Column P
        
        acr_data_by_int = {}
        for idx, row in df_acr.iterrows():
            val_d_raw = row[acr_d_col_idx]
            val_p_raw = row[acr_p_col_idx]
            
            if pd.isna(val_d_raw) or pd.isna(val_p_raw):
                continue
                
            val_d = str(val_d_raw).strip().split('.')[0]
            val_p = str(val_p_raw).strip()
            if ' ' in val_p:
                val_p = val_p.split()[0]
                
            try:
                acr_data_by_int[int(val_d)] = val_p
            except ValueError:
                continue

        # Helper to parse dates
        def parse_date(date_str):
            if not date_str:
                return None
            date_str = str(date_str).strip()
            for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d/%m/%y', '%Y/%m/%d %H:%M:%S', '%d/%m/%Y %H:%M:%S'):
                try:
                    return datetime.datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            return date_str

        def format_date_to_br(date_str):
            if not date_str:
                return ""
            d = parse_date(date_str)
            if isinstance(d, datetime.date):
                return d.strftime('%d/%m/%Y')
            return str(date_str)

        # Create Workbook
        wb = openpyxl.Workbook()
        
        # Tab 1
        ws1 = wb.active
        ws1.title = "Prorrogações Mart Minas"
        ws1.views.sheetView[0].showGridLines = True
        
        ws1.cell(row=1, column=1, value="Nota Fiscal")
        ws1.cell(row=1, column=2, value="Vencimento")
        
        for i, inv in enumerate(invoices_mm):
            row_num = i + 2
            ws1.cell(row=row_num, column=1, value=inv['nf'])
            ws1.cell(row=row_num, column=2, value=format_date_to_br(inv['vencimento']))
            
        # Tab 2
        ws2 = wb.create_sheet(title="Conciliação")
        ws2.views.sheetView[0].showGridLines = True
        
        ws2.cell(row=1, column=1, value="Nota Fiscal")
        ws2.cell(row=1, column=2, value="Vencimento Mart Minas")
        ws2.cell(row=1, column=3, value="Vencimento ACR")
        ws2.cell(row=1, column=4, value="Status")

        # Fonts, alignments and colors
        font_header = Font(name='Calibri', size=11, bold=True)
        font_body = Font(name='Calibri', size=11, bold=False)
        align_left = Alignment(horizontal='left', vertical='center')
        align_center = Alignment(horizontal='center', vertical='center')
        
        fill_ok = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
        fill_div = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")

        # Format Tab 1 Headers
        for col_idx in [1, 2]:
            cell = ws1.cell(row=1, column=col_idx)
            cell.font = font_header
            cell.alignment = align_left

        # Format Tab 1 Body
        for r_idx in range(2, len(invoices_mm) + 2):
            c1 = ws1.cell(row=r_idx, column=1)
            c1.font = font_body
            c1.number_format = '@'
            c1.alignment = align_left
            
            c2 = ws1.cell(row=r_idx, column=2)
            c2.font = font_body
            c2.alignment = align_center

        ws1.column_dimensions['A'].width = 16
        ws1.column_dimensions['B'].width = 24

        # Conciliate
        for i, inv in enumerate(invoices_mm):
            row_num = i + 2
            nf_str = inv['nf']
            date_mm_str = inv['vencimento']
            
            try:
                raw_nf_cleaned = inv['raw_nf'].replace(' ', '')
                nf_int = int(raw_nf_cleaned)
            except ValueError:
                nf_int = None
                
            date_acr_str = ""
            status = "Não encontrado no ACR"
            status_fill = None
            
            if nf_int is not None and nf_int in acr_data_by_int:
                date_acr_str = acr_data_by_int[nf_int]
                d_mm = parse_date(date_mm_str)
                d_acr = parse_date(date_acr_str)
                
                if d_mm and d_acr:
                    if d_mm == d_acr:
                        status = "OK"
                        status_fill = fill_ok
                    else:
                        status = "Divergente"
                        status_fill = fill_div
                else:
                    if str(date_mm_str).strip() == str(date_acr_str).strip():
                        status = "OK"
                        status_fill = fill_ok
                    else:
                        status = "Divergente"
                        status_fill = fill_div
                        
            ws2.cell(row=row_num, column=1, value=nf_str)
            ws2.cell(row=row_num, column=2, value=format_date_to_br(date_mm_str))
            ws2.cell(row=row_num, column=3, value=format_date_to_br(date_acr_str))
            
            status_cell = ws2.cell(row=row_num, column=4, value=status)
            if status_fill:
                status_cell.fill = status_fill

        # Format Tab 2 Headers
        for col_idx in [1, 2, 3, 4]:
            cell = ws2.cell(row=1, column=col_idx)
            cell.font = font_header
            cell.alignment = align_left

        # Format Tab 2 Body
        for r_idx in range(2, len(invoices_mm) + 2):
            ws2.cell(row=r_idx, column=1).font = font_body
            ws2.cell(row=r_idx, column=1).number_format = '@'
            ws2.cell(row=r_idx, column=1).alignment = align_left
            
            ws2.cell(row=r_idx, column=2).font = font_body
            ws2.cell(row=r_idx, column=2).alignment = align_center
            
            ws2.cell(row=r_idx, column=3).font = font_body
            ws2.cell(row=r_idx, column=3).alignment = align_center
            
            ws2.cell(row=r_idx, column=4).font = font_body
            ws2.cell(row=r_idx, column=4).alignment = align_center

        ws2.column_dimensions['A'].width = 16
        ws2.column_dimensions['B'].width = 24
        ws2.column_dimensions['C'].width = 24
        ws2.column_dimensions['D'].width = 24

        # Save Workbook
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = martminas_file.filename.rsplit('.', 1)[0] + "_conciliado.xlsx"
        
        # Registrar no banco
        ImportacaoService(db).registrar_importacao(filename, "xlsx", "Prorrogação - Mart Minas", id_user_inc=current_user.iduser)
        
        headers_response = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers_response
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/savegnago/conciliar")
async def conciliar_savegnago(
    savegnago_file: UploadFile = File(...),
    acr_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not savegnago_file.filename or not acr_file.filename:
        raise HTTPException(status_code=400, detail="Arquivos inválidos")
        
    try:
        # Load Savegnago file
        savegnago_bytes = await savegnago_file.read()
        import io
        import pandas as pd
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        import datetime
        import re

        try:
            df_sav = pd.read_excel(io.BytesIO(savegnago_bytes), header=None)
        except Exception:
            csv_text = savegnago_bytes.decode('utf-8', errors='ignore')
            sep = ';' if ';' in csv_text else ','
            df_sav = pd.read_csv(io.StringIO(csv_text), sep=sep, header=None)

        if df_sav.shape[1] < 9:
            raise HTTPException(
                status_code=400,
                detail=f"O arquivo Savegnago precisa ter pelo menos 9 colunas (até a coluna I). Colunas encontradas: {df_sav.shape[1]}."
            )

        # Helper to parse dates
        def parse_date(date_str):
            if not date_str:
                return None
            if isinstance(date_str, datetime.datetime):
                return date_str.date()
            if isinstance(date_str, datetime.date):
                return date_str
            date_str = str(date_str).strip()
            if hasattr(pd, 'Timestamp') and isinstance(date_str, pd.Timestamp):
                return date_str.date()
            for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d/%m/%y', '%Y/%m/%d %H:%M:%S', '%d/%m/%Y %H:%M:%S'):
                try:
                    return datetime.datetime.strptime(date_str.split()[0] if ' ' in date_str else date_str, fmt).date()
                except ValueError:
                    continue
            return None

        # Helper to adjust Savegnago date
        def adjust_savegnago_date(d_val):
            d = parse_date(d_val)
            if not isinstance(d, datetime.date):
                return d_val
            day = d.day
            month = d.month
            year = d.year
            
            if day == 31 or (1 <= day <= 9):
                new_day = 10
                if day == 31:
                    if month == 12:
                        month = 1
                        year += 1
                    else:
                        month += 1
            elif 11 <= day <= 19:
                new_day = 20
            elif 21 <= day <= 29:
                new_day = 30
            else:
                new_day = day
                
            try:
                adjusted = datetime.date(year, month, new_day)
                return adjusted
            except ValueError:
                if month == 2:
                    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
                    last_day = 29 if is_leap else 28
                    if new_day > last_day:
                        return datetime.date(year, month, last_day)
                return d

        def format_date_to_br(date_val):
            if not date_val:
                return ""
            if isinstance(date_val, datetime.date):
                return date_val.strftime('%d/%m/%Y')
            d = parse_date(date_val)
            if isinstance(d, datetime.date):
                return d.strftime('%d/%m/%Y')
            return str(date_val)

        # Parse Savegnago data
        d_col_idx = 3
        i_col_idx = 8
        
        invoices_sav = []
        for idx, row in df_sav.iterrows():
            val_d_raw = row[d_col_idx]
            val_i_raw = row[i_col_idx]
            
            if pd.isna(val_d_raw) or pd.isna(val_i_raw):
                continue
                
            val_d_str = str(val_d_raw).strip()
            if val_d_str.endswith('.0'):
                val_d_str = val_d_str[:-2]
                
            segment = val_d_str.split('-')[0]
            clean_segment = re.sub(r'^[a-zA-Z]+', '', segment)
            
            try:
                int(clean_segment)
            except ValueError:
                continue
                
            formatted_nf = clean_segment.zfill(7)
            
            parcela = ""
            qp_match = re.search(r'QP(\d+)', val_d_str)
            if qp_match:
                parcela = str(qp_match.group(1)).zfill(2)
            
            date_raw = str(val_i_raw).strip()
            if ' ' in date_raw:
                date_raw = date_raw.split()[0]
                
            adjusted_date = adjust_savegnago_date(date_raw)
            
            invoices_sav.append({
                'raw_nf': clean_segment,
                'nf': formatted_nf,
                'parcela': parcela,
                'vencimento': adjusted_date
            })
            
        if not invoices_sav:
            raise HTTPException(
                status_code=400,
                detail="Nenhum registro correspondente ao padrão Savegnago foi encontrado na coluna D."
            )

        # Load ACR file
        acr_bytes = await acr_file.read()
        try:
            df_acr = pd.read_excel(io.BytesIO(acr_bytes), header=None)
        except Exception:
            csv_text = acr_bytes.decode('utf-8', errors='ignore')
            sep = ';' if ';' in csv_text else ','
            df_acr = pd.read_csv(io.StringIO(csv_text), sep=sep, header=None)

        if df_acr.shape[1] < 16:
            raise HTTPException(
                status_code=400,
                detail=f"O arquivo ACR precisa ter pelo menos 16 colunas (até a coluna P). Colunas encontradas: {df_acr.shape[1]}."
            )

        # Parse ACR data
        acr_d_col_idx = 3 # Column D
        acr_e_col_idx = 4 # Column E (Parcela)
        acr_p_col_idx = 15 # Column P
        
        acr_data_by_key = {}
        for idx, row in df_acr.iterrows():
            if len(row) < 16:
                continue
                
            val_d_raw = row[acr_d_col_idx]
            val_e_raw = row[acr_e_col_idx]
            val_p_raw = row[acr_p_col_idx]
            
            if pd.isna(val_d_raw) or pd.isna(val_p_raw):
                continue
                
            val_d_str = str(val_d_raw).strip().split('.')[0]
            val_e_str = str(val_e_raw).strip().split('.')[0]
            
            val_e = val_e_str.zfill(2) if val_e_str.isdigit() else val_e_str
            
            val_p = str(val_p_raw).strip()
            if ' ' in val_p:
                val_p = val_p.split()[0]
                
            try:
                nf_int = int(val_d_str)
                acr_data_by_key[(nf_int, val_e)] = parse_date(val_p) or val_p
            except ValueError:
                continue

        # Create Workbook
        wb = openpyxl.Workbook()
        
        # Tab 1
        ws1 = wb.active
        ws1.title = "Prorrogações Savegnago"
        ws1.views.sheetView[0].showGridLines = True
        
        ws1.cell(row=1, column=1, value="Nota Fiscal")
        ws1.cell(row=1, column=2, value="Parcela")
        ws1.cell(row=1, column=3, value="Vencimento")
        
        for i, inv in enumerate(invoices_sav):
            row_num = i + 2
            ws1.cell(row=row_num, column=1, value=inv['nf'])
            ws1.cell(row=row_num, column=2, value=inv['parcela'])
            ws1.cell(row=row_num, column=3, value=format_date_to_br(inv['vencimento']))
            
        # Tab 2
        ws2 = wb.create_sheet(title="Conciliação")
        ws2.views.sheetView[0].showGridLines = True
        
        ws2.cell(row=1, column=1, value="Nota Fiscal")
        ws2.cell(row=1, column=2, value="Parcela")
        ws2.cell(row=1, column=3, value="Vencimento Savegnago")
        ws2.cell(row=1, column=4, value="Vencimento ACR")
        ws2.cell(row=1, column=5, value="Status")

        # Fonts, alignments and colors
        font_header = Font(name='Calibri', size=11, bold=True)
        font_body = Font(name='Calibri', size=11, bold=False)
        align_left = Alignment(horizontal='left', vertical='center')
        align_center = Alignment(horizontal='center', vertical='center')
        
        fill_ok = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
        fill_div = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")

        # Format Tab 1 Headers
        for col_idx in [1, 2, 3]:
            cell = ws1.cell(row=1, column=col_idx)
            cell.font = font_header
            cell.alignment = align_left

        # Format Tab 1 Body
        for r_idx in range(2, len(invoices_sav) + 2):
            c1 = ws1.cell(row=r_idx, column=1)
            c1.font = font_body
            c1.number_format = '@'
            c1.alignment = align_left
            
            c2 = ws1.cell(row=r_idx, column=2)
            c2.font = font_body
            c2.number_format = '@'
            c2.alignment = align_center
            
            c3 = ws1.cell(row=r_idx, column=3)
            c3.font = font_body
            c3.alignment = align_center

        ws1.column_dimensions['A'].width = 16
        ws1.column_dimensions['B'].width = 10
        ws1.column_dimensions['C'].width = 24

        # Conciliate
        for i, inv in enumerate(invoices_sav):
            row_num = i + 2
            nf_str = inv['nf']
            parcela_str = inv['parcela']
            date_sav_val = inv['vencimento']
            
            try:
                nf_int = int(inv['raw_nf'])
            except ValueError:
                nf_int = None
                
            date_acr_str = ""
            status = "Não encontrado no ACR"
            status_fill = None
            
            search_key = (nf_int, parcela_str)
            if nf_int is not None and search_key in acr_data_by_key:
                date_acr_str = acr_data_by_key[search_key]
                
                if isinstance(date_sav_val, datetime.date):
                    d_sav = date_sav_val
                else:
                    d_sav = parse_date(date_sav_val)
                    
                d_acr = parse_date(date_acr_str) if not isinstance(date_acr_str, datetime.date) else date_acr_str
                
                if d_sav and d_acr:
                    if d_sav == d_acr:
                        status = "OK"
                        status_fill = fill_ok
                    else:
                        status = "Divergente"
                        status_fill = fill_div
                else:
                    if str(format_date_to_br(date_sav_val)).strip() == str(format_date_to_br(date_acr_str)).strip():
                        status = "OK"
                        status_fill = fill_ok
                    else:
                        status = "Divergente"
                        status_fill = fill_div
                        
            ws2.cell(row=row_num, column=1, value=nf_str)
            ws2.cell(row=row_num, column=2, value=parcela_str)
            ws2.cell(row=row_num, column=3, value=format_date_to_br(date_sav_val))
            ws2.cell(row=row_num, column=4, value=format_date_to_br(date_acr_str))
            
            status_cell = ws2.cell(row=row_num, column=5, value=status)
            if status_fill:
                status_cell.fill = status_fill

        # Format Tab 2 Headers
        for col_idx in [1, 2, 3, 4, 5]:
            cell = ws2.cell(row=1, column=col_idx)
            cell.font = font_header
            cell.alignment = align_left

        # Format Tab 2 Body
        for r_idx in range(2, len(invoices_sav) + 2):
            ws2.cell(row=r_idx, column=1).font = font_body
            ws2.cell(row=r_idx, column=1).number_format = '@'
            ws2.cell(row=r_idx, column=1).alignment = align_left
            
            ws2.cell(row=r_idx, column=2).font = font_body
            ws2.cell(row=r_idx, column=2).number_format = '@'
            ws2.cell(row=r_idx, column=2).alignment = align_center
            
            ws2.cell(row=r_idx, column=3).font = font_body
            ws2.cell(row=r_idx, column=3).alignment = align_center
            
            ws2.cell(row=r_idx, column=4).font = font_body
            ws2.cell(row=r_idx, column=4).alignment = align_center
            
            ws2.cell(row=r_idx, column=5).font = font_body
            ws2.cell(row=r_idx, column=5).alignment = align_center

        ws2.column_dimensions['A'].width = 16
        ws2.column_dimensions['B'].width = 10
        ws2.column_dimensions['C'].width = 24
        ws2.column_dimensions['D'].width = 24
        ws2.column_dimensions['E'].width = 24

        # Save Workbook
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = savegnago_file.filename.rsplit('.', 1)[0] + "_conciliado.xlsx"
        
        from app.services.importacao_service import ImportacaoService
        ImportacaoService(db).registrar_importacao(filename, "xlsx", "Prorrogação - Savegnago", id_user_inc=current_user.iduser)
        
        headers_response = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers_response
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mateus/conciliar")
async def conciliar_mateus(
    mateus_file: UploadFile = File(...),
    acr_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not mateus_file.filename or not acr_file.filename:
        raise HTTPException(status_code=400, detail="Arquivos inválidos")
        
    try:
        import io
        import pandas as pd
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        import datetime
        import math
        
        # 1. Parse Mateus File
        mateus_bytes = await mateus_file.read()
        try:
            df_mat = pd.read_excel(io.BytesIO(mateus_bytes), header=None)
        except Exception:
            raise HTTPException(status_code=400, detail="Arquivo Mateus deve ser Excel.")
            
        def parse_date(date_str):
            if not date_str:
                return None
            if isinstance(date_str, datetime.datetime):
                return date_str.date()
            if isinstance(date_str, datetime.date):
                return date_str
            date_str = str(date_str).strip()
            if hasattr(pd, 'Timestamp') and isinstance(date_str, pd.Timestamp):
                return date_str.date()
            for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%y', '%Y/%m/%d %H:%M:%S', '%d/%m/%Y %H:%M:%S'):
                try:
                    return datetime.datetime.strptime(date_str.split()[0] if ' ' in date_str else date_str, fmt).date()
                except ValueError:
                    continue
            return None

        mateus_invoices = []
        for idx, row in df_mat.iterrows():
            if len(row) < 6:
                continue
            
            nf_raw = str(row[2]).strip() # Col C (index 2)
            date_raw = row[5] # Col F (index 5)
            
            if not nf_raw or nf_raw.lower() in ('nan', 'none', 'nota fiscal', 'nota', 'nota_fiscal'):
                continue
                
            nf_clean = nf_raw.split('/')[0].strip()
            
            if not nf_clean:
                continue
                
            if not any(char.isdigit() for char in nf_clean):
                continue
            
            try:
                nf_clean = str(int(float(nf_clean))).zfill(7)
            except ValueError:
                nf_clean = nf_clean.zfill(7)
            
            d_parsed = parse_date(date_raw)
            d_adjusted = d_parsed if d_parsed else date_raw
            
            mateus_invoices.append({
                'raw_nf': nf_raw,
                'nf': nf_clean,
                'prorrogacao': d_adjusted
            })
            
        if not mateus_invoices:
            raise HTTPException(status_code=400, detail="Nenhuma nota fiscal encontrada no arquivo Mateus.")

        # 2. Parse ACR File
        acr_bytes = await acr_file.read()
        try:
            df_acr = pd.read_excel(io.BytesIO(acr_bytes), header=None)
        except Exception:
            acr_text = acr_bytes.decode('utf-8', errors='ignore')
            sep = ';' if ';' in acr_text else ','
            df_acr = pd.read_csv(io.StringIO(acr_text), sep=sep, header=None)
            
        acr_data_by_int = {}
        for idx, row in df_acr.iterrows():
            if len(row) < 16:
                continue
                
            val_d_raw = str(row[3]).strip()
            if not val_d_raw or val_d_raw.lower() in ('nan', 'none'):
                continue
                
            val_d = val_d_raw.split('.')[0]
            val_p = str(row[15]).strip()
            if ' ' in val_p:
                val_p = val_p.split()[0]
                
            try:
                acr_data_by_int[int(val_d)] = parse_date(val_p) or val_p
            except ValueError:
                continue
                
        # 3. Create Excel
        def format_date_to_br(d):
            if isinstance(d, datetime.date):
                return d.strftime('%d/%m/%Y')
            return str(d) if d else ""

        wb = openpyxl.Workbook()
        ws1 = wb.active
        ws1.title = "Prorrogações Mateus"
        ws1.views.sheetView[0].showGridLines = True
        
        ws1.cell(row=1, column=1, value="Nota Fiscal")
        ws1.cell(row=1, column=2, value="Data de Prorrogação")
        
        for i, inv in enumerate(mateus_invoices):
            ws1.cell(row=i+2, column=1, value=inv['nf'])
            ws1.cell(row=i+2, column=2, value=format_date_to_br(inv['prorrogacao']))
            
        ws2 = wb.create_sheet(title="Conciliação")
        ws2.views.sheetView[0].showGridLines = True
        ws2.cell(row=1, column=1, value="Nota Fiscal")
        ws2.cell(row=1, column=2, value="Data Mateus (Prorrogação)")
        ws2.cell(row=1, column=3, value="Data ACR (Vencimento)")
        ws2.cell(row=1, column=4, value="Status")
        
        font_header = Font(name='Calibri', size=11, bold=True)
        font_body = Font(name='Calibri', size=11, bold=False)
        align_left = Alignment(horizontal='left', vertical='center')
        align_center = Alignment(horizontal='center', vertical='center')
        
        fill_ok = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
        fill_div = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
        
        for col_idx in [1, 2]:
            cell = ws1.cell(row=1, column=col_idx)
            cell.font = font_header
            cell.alignment = align_left
            
        for r_idx in range(2, len(mateus_invoices) + 2):
            ws1.cell(row=r_idx, column=1).font = font_body
            ws1.cell(row=r_idx, column=1).number_format = '@'
            ws1.cell(row=r_idx, column=1).alignment = align_left
            ws1.cell(row=r_idx, column=2).font = font_body
            ws1.cell(row=r_idx, column=2).alignment = align_center
            
        ws1.column_dimensions['A'].width = 16
        ws1.column_dimensions['B'].width = 24
        
        for i, inv in enumerate(mateus_invoices):
            row_num = i + 2
            nf_str = inv['nf']
            d_mat = inv['prorrogacao']
            
            try:
                nf_int = int(nf_str)
            except ValueError:
                nf_int = None
                
            d_acr = None
            status = "Não encontrado no ACR"
            status_fill = None
            
            if nf_int is not None and nf_int in acr_data_by_int:
                d_acr = acr_data_by_int[nf_int]
                
                if isinstance(d_mat, datetime.date) and isinstance(d_acr, datetime.date):
                    if d_mat == d_acr:
                        status = "OK"
                        status_fill = fill_ok
                    else:
                        status = "Divergente"
                        status_fill = fill_div
                else:
                    if str(format_date_to_br(d_mat)).strip() == str(format_date_to_br(d_acr)).strip():
                        status = "OK"
                        status_fill = fill_ok
                    else:
                        status = "Divergente"
                        status_fill = fill_div
                        
            ws2.cell(row=row_num, column=1, value=nf_str)
            ws2.cell(row=row_num, column=2, value=format_date_to_br(d_mat))
            ws2.cell(row=row_num, column=3, value=format_date_to_br(d_acr))
            
            status_cell = ws2.cell(row=row_num, column=4, value=status)
            if status_fill:
                status_cell.fill = status_fill

        for col_idx in [1, 2, 3, 4]:
            cell = ws2.cell(row=1, column=col_idx)
            cell.font = font_header
            cell.alignment = align_left
            
        for r_idx in range(2, len(mateus_invoices) + 2):
            ws2.cell(row=r_idx, column=1).font = font_body
            ws2.cell(row=r_idx, column=1).number_format = '@'
            ws2.cell(row=r_idx, column=1).alignment = align_left
            ws2.cell(row=r_idx, column=2).font = font_body
            ws2.cell(row=r_idx, column=2).alignment = align_center
            ws2.cell(row=r_idx, column=3).font = font_body
            ws2.cell(row=r_idx, column=3).alignment = align_center
            ws2.cell(row=r_idx, column=4).font = font_body
            ws2.cell(row=r_idx, column=4).alignment = align_center
            
        ws2.column_dimensions['A'].width = 16
        ws2.column_dimensions['B'].width = 28
        ws2.column_dimensions['C'].width = 28
        ws2.column_dimensions['D'].width = 24
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = mateus_file.filename.rsplit('.', 1)[0] + "_conciliado.xlsx"
        
        from app.services.importacao_service import ImportacaoService
        ImportacaoService(db).registrar_importacao(filename, "xlsx", "Prorrogação - Mateus", id_user_inc=current_user.iduser)
        
        headers_response = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers_response
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/drogaraia/conciliar")
async def conciliar_drogaraia(
    drogaraia_file: UploadFile = File(...),
    acr_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not drogaraia_file.filename or not acr_file.filename:
        raise HTTPException(status_code=400, detail="Arquivos inválidos")
        
    try:
        import io
        import pandas as pd
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        import datetime
        import math
        
        # 1. Parse Droga Raia File
        drogaraia_bytes = await drogaraia_file.read()
        try:
            df_dr = pd.read_excel(io.BytesIO(drogaraia_bytes), header=None)
        except Exception:
            try:
                dr_text = drogaraia_bytes.decode('utf-8', errors='ignore')
                sep = ';' if ';' in dr_text else ','
                df_dr = pd.read_csv(io.StringIO(dr_text), sep=sep, header=None)
            except Exception:
                try:
                    dr_text = drogaraia_bytes.decode('utf-8', errors='ignore')
                    dfs = pd.read_html(io.StringIO(dr_text), header=None)
                    df_dr = dfs[0]
                except Exception:
                    file_head = drogaraia_bytes[:100].decode('utf-8', errors='ignore')
                    raise HTTPException(status_code=400, detail=f"Arquivo desconhecido. Início do arquivo: {file_head[:50]}")
            
        def parse_date(date_str):
            if not date_str:
                return None
            if isinstance(date_str, datetime.datetime):
                return date_str.date()
            if isinstance(date_str, datetime.date):
                return date_str
            date_str = str(date_str).strip()
            if hasattr(pd, 'Timestamp') and isinstance(date_str, pd.Timestamp):
                return date_str.date()
                
            # Tratamento para datas em português ("4 de set de 2026")
            import re
            pt_months = {
                'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
                'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
            }
            pt_match = re.match(r'^(\d{1,2})\s+de\s+([a-zA-Z]{3,4})\s+de\s+(\d{4})$', date_str.lower())
            if pt_match:
                day = int(pt_match.group(1))
                month_str = pt_match.group(2)[:3]
                year = int(pt_match.group(3))
                if month_str in pt_months:
                    return datetime.date(year, pt_months[month_str], day)
                    
            for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%y', '%Y/%m/%d %H:%M:%S', '%d/%m/%Y %H:%M:%S'):
                try:
                    return datetime.datetime.strptime(date_str.split()[0] if ' ' in date_str else date_str, fmt).date()
                except ValueError:
                    continue
            return None

        drogaraia_invoices = []
        for idx, row in df_dr.iterrows():
            if len(row) < 7:
                continue
            
            nf_raw = str(row[4]).strip() # Col E (index 4)
            date_raw = row[6] # Col G (index 6)
            
            if not nf_raw or nf_raw.lower() in ('nan', 'none', 'nota fiscal', 'nota', 'nota_fiscal'):
                continue
                
            nf_clean = nf_raw.split('/')[0].strip()
            
            if not nf_clean:
                continue
                
            if not any(char.isdigit() for char in nf_clean):
                continue
            
            try:
                nf_clean = str(int(float(nf_clean))).zfill(7)
            except ValueError:
                nf_clean = nf_clean.zfill(7)
            
            d_parsed = parse_date(date_raw)
            d_adjusted = d_parsed if d_parsed else date_raw
            
            drogaraia_invoices.append({
                'raw_nf': nf_raw,
                'nf': nf_clean,
                'prorrogacao': d_adjusted
            })
            
        if not drogaraia_invoices:
            raise HTTPException(status_code=400, detail="Nenhuma nota fiscal encontrada no arquivo Droga Raia.")

        # 2. Parse ACR File
        acr_bytes = await acr_file.read()
        try:
            df_acr = pd.read_excel(io.BytesIO(acr_bytes), header=None)
        except Exception:
            acr_text = acr_bytes.decode('utf-8', errors='ignore')
            sep = ';' if ';' in acr_text else ','
            df_acr = pd.read_csv(io.StringIO(acr_text), sep=sep, header=None)
            
        acr_data_by_int = {}
        for idx, row in df_acr.iterrows():
            if len(row) < 16:
                continue
                
            val_d_raw = str(row[3]).strip()
            if not val_d_raw or val_d_raw.lower() in ('nan', 'none'):
                continue
                
            val_d = val_d_raw.split('.')[0]
            val_p = str(row[15]).strip()
            if ' ' in val_p:
                val_p = val_p.split()[0]
                
            try:
                acr_data_by_int[int(val_d)] = parse_date(val_p) or val_p
            except ValueError:
                continue
                
        # 3. Create Excel
        def format_date_to_br(d):
            if isinstance(d, datetime.date):
                return d.strftime('%d/%m/%Y')
            return str(d) if d else ""

        wb = openpyxl.Workbook()
        ws1 = wb.active
        ws1.title = "Prorrogações Droga Raia"
        ws1.views.sheetView[0].showGridLines = True
        
        ws1.cell(row=1, column=1, value="Nota Fiscal")
        ws1.cell(row=1, column=2, value="Data de Prorrogação")
        
        for i, inv in enumerate(drogaraia_invoices):
            ws1.cell(row=i+2, column=1, value=inv['nf'])
            ws1.cell(row=i+2, column=2, value=format_date_to_br(inv['prorrogacao']))
            
        ws2 = wb.create_sheet(title="Conciliação")
        ws2.views.sheetView[0].showGridLines = True
        ws2.cell(row=1, column=1, value="Nota Fiscal")
        ws2.cell(row=1, column=2, value="Data Droga Raia (Prorrogação)")
        ws2.cell(row=1, column=3, value="Data ACR (Vencimento)")
        ws2.cell(row=1, column=4, value="Status")
        
        font_header = Font(name='Calibri', size=11, bold=True)
        font_body = Font(name='Calibri', size=11, bold=False)
        align_left = Alignment(horizontal='left', vertical='center')
        align_center = Alignment(horizontal='center', vertical='center')
        
        fill_ok = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
        fill_div = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
        
        for col_idx in [1, 2]:
            cell = ws1.cell(row=1, column=col_idx)
            cell.font = font_header
            cell.alignment = align_left
            
        for r_idx in range(2, len(drogaraia_invoices) + 2):
            ws1.cell(row=r_idx, column=1).font = font_body
            ws1.cell(row=r_idx, column=1).number_format = '@'
            ws1.cell(row=r_idx, column=1).alignment = align_left
            ws1.cell(row=r_idx, column=2).font = font_body
            ws1.cell(row=r_idx, column=2).alignment = align_center
            
        ws1.column_dimensions['A'].width = 16
        ws1.column_dimensions['B'].width = 24
        
        for i, inv in enumerate(drogaraia_invoices):
            row_num = i + 2
            nf_str = inv['nf']
            d_dr = inv['prorrogacao']
            
            try:
                nf_int = int(nf_str)
            except ValueError:
                nf_int = None
                
            d_acr = None
            status = "Não encontrado no ACR"
            status_fill = None
            
            if nf_int is not None and nf_int in acr_data_by_int:
                d_acr = acr_data_by_int[nf_int]
                
                if isinstance(d_dr, datetime.date) and isinstance(d_acr, datetime.date):
                    if d_dr == d_acr:
                        status = "OK"
                        status_fill = fill_ok
                    else:
                        status = "Divergente"
                        status_fill = fill_div
                else:
                    if str(format_date_to_br(d_dr)).strip() == str(format_date_to_br(d_acr)).strip():
                        status = "OK"
                        status_fill = fill_ok
                    else:
                        status = "Divergente"
                        status_fill = fill_div
                        
            ws2.cell(row=row_num, column=1, value=nf_str)
            ws2.cell(row=row_num, column=2, value=format_date_to_br(d_dr))
            ws2.cell(row=row_num, column=3, value=format_date_to_br(d_acr))
            
            status_cell = ws2.cell(row=row_num, column=4, value=status)
            if status_fill:
                status_cell.fill = status_fill

        for col_idx in [1, 2, 3, 4]:
            cell = ws2.cell(row=1, column=col_idx)
            cell.font = font_header
            cell.alignment = align_left
            
        for r_idx in range(2, len(drogaraia_invoices) + 2):
            ws2.cell(row=r_idx, column=1).font = font_body
            ws2.cell(row=r_idx, column=1).number_format = '@'
            ws2.cell(row=r_idx, column=1).alignment = align_left
            ws2.cell(row=r_idx, column=2).font = font_body
            ws2.cell(row=r_idx, column=2).alignment = align_center
            ws2.cell(row=r_idx, column=3).font = font_body
            ws2.cell(row=r_idx, column=3).alignment = align_center
            ws2.cell(row=r_idx, column=4).font = font_body
            ws2.cell(row=r_idx, column=4).alignment = align_center
            
        ws2.column_dimensions['A'].width = 16
        ws2.column_dimensions['B'].width = 32
        ws2.column_dimensions['C'].width = 28
        ws2.column_dimensions['D'].width = 24
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = drogaraia_file.filename.rsplit('.', 1)[0] + "_conciliado.xlsx"
        
        from app.services.importacao_service import ImportacaoService
        ImportacaoService(db).registrar_importacao(filename, "xlsx", "Prorrogação - Droga Raia", id_user_inc=current_user.iduser)
        
        headers_response = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers_response
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conciliacao-pagamentos/ler-apb")
async def ler_apb_planilha(file: UploadFile = File(...)):
    try:
        content = await file.read()
        xls = pd.ExcelFile(io.BytesIO(content))

        # A aba de dados é sempre a que começa com "Relatorio Geral" (o restante do
        # nome é uma data variável a cada exportação, ex: "Relatorio Geral 24.08.26").
        sheet_name = next(
            (s for s in xls.sheet_names if s.strip().startswith("Relatorio Geral")),
            None
        )
        if not sheet_name:
            raise HTTPException(
                status_code=400,
                detail="Não foi encontrada nenhuma aba iniciada com 'Relatorio Geral' na planilha."
            )

        # Linha 1 = cabeçalho, dados a partir da linha 2. Nome na coluna P (índice 15),
        # valor na coluna S (índice 18).
        df = xls.parse(sheet_name, header=0)

        if df.shape[1] < 19:
            raise HTTPException(
                status_code=400,
                detail=f"A aba '{sheet_name}' não possui as colunas P e S esperadas."
            )

        nomes = df.iloc[:, 15]
        valores = pd.to_numeric(df.iloc[:, 18], errors='coerce').fillna(0.0)

        # Consolida por nome, sem repetições, mantendo a ordem de primeira aparição na planilha.
        result = []
        seen = {}
        for nome_raw, valor in zip(nomes, valores):
            if nome_raw is None or (isinstance(nome_raw, float) and pd.isna(nome_raw)):
                continue
            nome = str(nome_raw).strip()
            if not nome:
                continue

            if nome in seen:
                result[seen[nome]]["valor"] += float(valor)
            else:
                seen[nome] = len(result)
                result.append({"nome": nome, "valor": float(valor)})

        # Print list to Python console as requested
        print(f"\n=== LISTA CONSOLIDADA (aba '{sheet_name}', coluna P x S) ===")
        for idx, item in enumerate(result):
            print(f"{idx+1}. {item['nome']}: R$ {item['valor']:.2f}")
        print("====================================================\n")

        return {"sucesso": True, "dados": result}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

from datetime import datetime
from typing import List


def _normalizar_nome(nome) -> str:
    """Normaliza um nome para comparação: remove acentos, colapsa espaços e ignora caixa."""
    import unicodedata
    texto = str(nome or "").strip().upper()
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'\s+', ' ', texto)


def _parse_valor_br(valor_str: str) -> float:
    """Converte um valor no formato brasileiro ('34.924,31') para float."""
    return float(valor_str.strip().replace('.', '').replace(',', '.'))


def _parse_banco_do_brasil(texto: str) -> list:
    """
    Extrai (nome, situacao, valor) das linhas de favorecidos de um PDF de
    'Pagamentos a Terceiros' do Banco do Brasil. O layout intermediário entre o
    nome e o valor varia (documento do título, ou banco/agência/conta), então
    a extração ignora esse trecho e captura apenas nome + situação + valor final.
    """
    linha_regex = re.compile(
        r'^(?P<nome>.+)\s*(?P<situacao>PENDENTE|REJEITADO)\s+.*?(?P<valor>\d{1,3}(?:\.\d{3})*,\d{2})\s*$'
    )
    entradas = []
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        m = linha_regex.match(linha)
        if not m:
            continue
        entradas.append({
            'nome': m.group('nome').strip(),
            'situacao': m.group('situacao'),
            'valor': _parse_valor_br(m.group('valor'))
        })
    return entradas


# Registro de parsers de extrato por banco. Identificação por nome do arquivo
# (ex: "Banco do Brasil-1.pdf", "Banco do Brasil-2.pdf"). Novos bancos/critérios
# são adicionados aqui, sem alterar o restante do endpoint.
BANK_PARSERS = [
    {
        'nome': 'Banco do Brasil',
        'match': lambda filename: 'banco do brasil' in (filename or '').lower(),
        'parse': _parse_banco_do_brasil,
        'codigos': {'PENDENTE': 'BB-LIB', 'REJEITADO': 'ERRO'}
    }
]


def _parse_bb_pendencias_pix(texto: str) -> list:
    """
    Extrai os valores das linhas 'Confirmação de Pagamento Instantâneo-PIX' do
    relatório 'Central de Pendências' do Banco do Brasil. A descrição de cada
    lançamento quebra em várias linhas no PDF (ex: '...PIX CEF\\nMATRIZ'), então
    a extração varre o texto inteiro (DOTALL) para juntar cada bloco antes do valor.
    """
    padrao = re.compile(
        r'Pagamento\s+(?P<desc>.+?)\s*\n\s*(?P<valor>\d{1,3}(?:\.\d{3})*,\d{2})\s+\d{2}/\d{2}/\d{4}\s+\d+\s+\d+',
        re.DOTALL
    )
    valores = []
    for m in padrao.finditer(texto):
        desc_norm = _normalizar_nome(m.group('desc'))
        if desc_norm.startswith('CONFIRMACAO DE PAGAMENTO INSTANTANEO-PIX'):
            valores.append(_parse_valor_br(m.group('valor')))
    return valores


def _parse_itau_salarios_rh(texto: str) -> list:
    """
    Extrai o 'Valor total (R$)' do resumo do lote de um PDF de pagamentos de
    Salários/RH do Itaú. O texto extraído do PDF vem fora de ordem (rótulos de
    coluna antes dos dados), mas o valor sempre aparece logo após a seção
    'Empresa pagadora'.
    """
    m = re.search(r'Empresa pagadora.*?(?P<valor>\d{1,3}(?:\.\d{3})*,\d{2})', texto, re.DOTALL)
    return [_parse_valor_br(m.group('valor'))] if m else []


# Registro de parsers "agregados": em vez de casar cada lançamento individualmente
# contra um nome extraído do PDF, somam-se todos os valores extraídos e comparam-se
# contra a soma de linhas-alvo na planilha. 'modo_alvo' define como as linhas-alvo são
# encontradas: 'exato' (nome normalizado igual a algum item de 'alvo') ou 'contem' (nome
# normalizado contém algum item de 'alvo' como substring). Se a soma não bater, grava-se
# 'codigo_erro' em todas as linhas-alvo (nunca deixa em branco).
AGGREGATE_PARSERS = [
    {
        'nome': 'Banco do Brasil - Pendências PIX (FGTS)',
        'match': lambda filename: 'bb-pendencias-pix' in (filename or '').lower(),
        'extrair_valores': _parse_bb_pendencias_pix,
        'modo_alvo': 'exato',
        'alvo': ['FGTS FOLHA', 'FGTS - FOLHA DE PAGAMENTO'],
        'codigo_ok': 'BB-PIX',
        'codigo_erro': 'ERRO'
    },
    {
        'nome': 'Itaú - Salários e RH',
        'match': lambda filename: 'itau-salarios' in (filename or '').lower(),
        'extrair_valores': _parse_itau_salarios_rh,
        'modo_alvo': 'contem',
        'alvo': ['RESCISAO', 'RESCICAO', 'FOLHA PAGTO', 'FERIAS'],
        'codigo_ok': 'ITAU-CP',
        'codigo_erro': 'ERRO'
    }
]


def _localizar_sheet_xml(conteudo_planilha: bytes, prefixo_nome: str):
    """
    Resolve o caminho interno do XML (ex: 'xl/worksheets/sheet5.xml') da primeira aba
    cujo nome comece com `prefixo_nome`, lendo diretamente workbook.xml/workbook.xml.rels
    (sem passar pelo openpyxl) — usado para editar a planilha em bytes, preservando 100%
    do restante do arquivo (pivot tables, gráficos, etc.), que o openpyxl não sabe
    reserializar sem perdas.
    """
    # Os atributos de <sheet> e <Relationship> podem vir em qualquer ordem dependendo de
    # quem gerou o arquivo (Excel escreve name/r:id e Id/Target; o openpyxl pode escrever
    # Target antes de Id, e usar path absoluto "/xl/..." em vez de relativo) — por isso cada
    # atributo é extraído individualmente do trecho da tag, em vez de assumir uma ordem fixa.
    import xml.sax.saxutils as saxutils
    with zipfile.ZipFile(io.BytesIO(conteudo_planilha)) as z:
        workbook_xml = z.read('xl/workbook.xml').decode('utf-8')
        rels_xml = z.read('xl/_rels/workbook.xml.rels').decode('utf-8')

    r_id_alvo = None
    nome_aba_encontrada = None
    for m in re.finditer(r'<sheet\s+([^>]*?)/?>', workbook_xml):
        atributos = m.group(1)
        nome_m = re.search(r'name="([^"]*)"', atributos)
        rid_m = re.search(r'r:id="([^"]+)"', atributos)
        if not nome_m or not rid_m:
            continue
        nome_aba = saxutils.unescape(nome_m.group(1)).strip()
        if nome_aba.startswith(prefixo_nome):
            r_id_alvo = rid_m.group(1)
            nome_aba_encontrada = nome_aba
            break

    if not r_id_alvo:
        return None, None

    for m in re.finditer(r'<Relationship\s+([^>]*?)/?>', rels_xml):
        atributos = m.group(1)
        id_m = re.search(r'Id="([^"]+)"', atributos)
        target_m = re.search(r'Target="([^"]+)"', atributos)
        if not id_m or not target_m or id_m.group(1) != r_id_alvo:
            continue
        target = target_m.group(1)
        # Target absoluto ("/xl/worksheets/sheetN.xml") é relativo à raiz do pacote;
        # relativo ("worksheets/sheetN.xml") é relativo à pasta do próprio .rels ("xl/").
        sheet_path = target.lstrip('/') if target.startswith('/') else f"xl/{target}"
        return sheet_path, nome_aba_encontrada

    return None, None


def _definir_celula_coluna_a(sheet_xml: str, row_idx: int, valor: str) -> str:
    """
    Insere (ou substitui) a célula da coluna A na linha `row_idx`, editando o XML da
    planilha diretamente como texto. Não usa openpyxl para não arriscar corromper
    pivot tables/gráficos ao reserializar o restante do arquivo.
    """
    import xml.sax.saxutils as saxutils
    valor_escapado = saxutils.escape(valor)
    nova_celula = f'<c r="A{row_idx}" t="inlineStr"><is><t>{valor_escapado}</t></is></c>'

    padrao_linha = re.compile(rf'(<row r="{row_idx}"[^>]*>)(.*?)(</row>)', re.DOTALL)
    m = padrao_linha.search(sheet_xml)
    if not m:
        # Linha sem nenhuma célula no XML (não deveria acontecer para linhas com dados).
        return sheet_xml

    abertura, conteudo, fechamento = m.group(1), m.group(2), m.group(3)

    # 'spans' é só uma dica opcional de intervalo de colunas; garantimos que inclua a coluna A.
    abertura = re.sub(
        r'spans="(\d+):(\d+)"',
        lambda sm: f'spans="{min(int(sm.group(1)), 1)}:{sm.group(2)}"',
        abertura
    )

    padrao_cel_a = re.compile(rf'<c r="A{row_idx}"[^>]*?(?:/>|>.*?</c>)', re.DOTALL)
    if padrao_cel_a.search(conteudo):
        novo_conteudo = padrao_cel_a.sub(lambda _: nova_celula, conteudo, count=1)
    else:
        novo_conteudo = nova_celula + conteudo

    linha_nova = abertura + novo_conteudo + fechamento
    return sheet_xml[:m.start()] + linha_nova + sheet_xml[m.end():]


def _gravar_codigos_na_planilha(conteudo_planilha: bytes, sheet_xml_path: str, codigos_por_linha: dict) -> bytes:
    """
    Retorna os bytes de um novo .xlsx idêntico ao original, exceto pela aba indicada em
    `sheet_xml_path`, onde as linhas de `codigos_por_linha` (row -> código) recebem o
    valor na coluna A. Todos os outros arquivos do pacote (pivot tables, pivot caches,
    gráficos, sharedStrings, calcChain, etc.) são copiados byte a byte, sem qualquer
    reserialização — é isso que evita o aviso de 'arquivo corrompido' do Excel.
    """
    with zipfile.ZipFile(io.BytesIO(conteudo_planilha)) as z_in:
        sheet_xml = z_in.read(sheet_xml_path).decode('utf-8')
        for row_idx, codigo in codigos_por_linha.items():
            sheet_xml = _definir_celula_coluna_a(sheet_xml, row_idx, codigo)

        saida = io.BytesIO()
        with zipfile.ZipFile(saida, 'w', zipfile.ZIP_DEFLATED) as z_out:
            for item in z_in.infolist():
                dados = z_in.read(item.filename)
                if item.filename == sheet_xml_path:
                    dados = sheet_xml.encode('utf-8')
                z_out.writestr(item, dados)

        return saida.getvalue()


@router.post("/conciliacao-pagamentos/conciliar-bancos")
async def conciliar_bancos(
    planilha: UploadFile = File(...),
    extratos: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        import openpyxl

        # 1. Carrega a planilha original só para LEITURA (identificar nomes/valores e
        # decidir os códigos). A gravação final NÃO passa pelo openpyxl: reserializar o
        # arquivo inteiro com ele corrompe pivot tables/gráficos (o Excel acusa "problema
        # no conteúdo" ao abrir) — por isso a coluna A é escrita depois via edição direta
        # do XML original, preservando o restante do arquivo byte a byte.
        conteudo_planilha = await planilha.read()
        # (Sem read_only=True: no modo leitura-rápida o openpyxl confia cegamente no
        # <dimension> declarado no XML, que nesta planilha está inflado até a linha
        # 1.048.576 — faria o loop abaixo varrer mais de 1 milhão de linhas à toa.)
        wb = openpyxl.load_workbook(io.BytesIO(conteudo_planilha), data_only=True)

        sheet_name = next(
            (s for s in wb.sheetnames if s.strip().startswith("Relatorio Geral")),
            None
        )
        if not sheet_name:
            raise HTTPException(
                status_code=400,
                detail="Não foi encontrada nenhuma aba iniciada com 'Relatorio Geral' na planilha."
            )
        ws = wb[sheet_name]

        sheet_xml_path, _ = _localizar_sheet_xml(conteudo_planilha, "Relatorio Geral")
        if not sheet_xml_path:
            raise HTTPException(
                status_code=400,
                detail="Não foi possível localizar o XML interno da aba 'Relatorio Geral' na planilha."
            )

        # Linhas de dados a partir da linha 2. Nome na coluna P (16), Valor na coluna S (19).
        linhas_planilha = []
        for row_idx in range(2, ws.max_row + 1):
            nome_cel = ws.cell(row=row_idx, column=16).value
            if nome_cel is None or str(nome_cel).strip() == "":
                continue
            valor_cel = ws.cell(row=row_idx, column=19).value
            try:
                valor = float(valor_cel) if valor_cel is not None else 0.0
            except (TypeError, ValueError):
                valor = 0.0
            linhas_planilha.append({
                'row': row_idx,
                'nome': str(nome_cel).strip(),
                'nome_norm': _normalizar_nome(nome_cel),
                'valor': valor,
                'matched': False
            })

        # 2. Extrai os lançamentos/valores de cada PDF de extrato enviado. Cada arquivo é
        # roteado para um parser "de lote" (concilia linha a linha) ou "agregado" (soma
        # todos os valores e concilia contra nome(s) fixo(s) na planilha), conforme o nome.
        import pypdf
        import hashlib

        lancamentos = []
        agregados_por_parser = {}

        # Deduplica por conteúdo: se o mesmo PDF (bytes idênticos) for enviado mais de uma
        # vez (ex: usuário selecionou o mesmo arquivo duas vezes), ele é processado só uma
        # vez — do contrário um valor "agregado" (como o de PIX x FGTS) seria contado em
        # dobro e gerar um ERRO falso mesmo quando os valores realmente batem.
        hashes_vistos = {}

        for arquivo in extratos:
            parser_lote = next((p for p in BANK_PARSERS if p['match'](arquivo.filename)), None)
            parser_agregado = next((p for p in AGGREGATE_PARSERS if p['match'](arquivo.filename)), None)

            if not parser_lote and not parser_agregado:
                raise HTTPException(
                    status_code=400,
                    detail=f"Não foi possível identificar o banco/formato do arquivo '{arquivo.filename}'."
                )

            conteudo = await arquivo.read()
            hash_conteudo = hashlib.sha256(conteudo).hexdigest()
            if hash_conteudo in hashes_vistos:
                print(f"  - Arquivo '{arquivo.filename}' ignorado: conteúdo idêntico ao de '{hashes_vistos[hash_conteudo]}' já enviado nesta requisição.")
                continue
            hashes_vistos[hash_conteudo] = arquivo.filename

            leitor = pypdf.PdfReader(io.BytesIO(conteudo))
            texto = "\n".join(pagina.extract_text() or "" for pagina in leitor.pages)

            if parser_lote:
                for entrada in parser_lote['parse'](texto):
                    codigo = parser_lote['codigos'].get(entrada['situacao'])
                    if not codigo:
                        continue
                    lancamentos.append({
                        'arquivo': arquivo.filename,
                        'nome': entrada['nome'],
                        'nome_norm': _normalizar_nome(entrada['nome']),
                        'valor': entrada['valor'],
                        'codigo': codigo
                    })

            if parser_agregado:
                chave = parser_agregado['nome']
                grupo = agregados_por_parser.setdefault(chave, {'parser': parser_agregado, 'valores': []})
                grupo['valores'].extend(parser_agregado['extrair_valores'](texto))

        # 3. Concilia cada lançamento contra as linhas ainda não conciliadas da planilha.
        # Os códigos decididos aqui são só acumulados em memória (codigos_por_linha); a
        # gravação de fato acontece depois, direto no XML original (ver passo 4).
        #
        # Feito em duas passagens (e não uma única, lançamento a lançamento) porque um
        # mesmo fornecedor pode ter várias linhas na planilha pertencentes a títulos
        # diferentes (ex: título A dividido em 2 linhas + título B em 1 linha só). Se a
        # regra de soma (1 para N) fosse tentada linha a linha, na ordem em que os PDFs
        # aparecem, ela poderia somar linhas de títulos diferentes que ainda não bateram
        # 1 para 1 e nunca encontrar o valor certo — mesmo que o título B feche exato
        # pouco depois. Resolvendo primeiro TODOS os 1 para 1 (de qualquer título/PDF) e
        # só então tentando a soma no que restou, as linhas já batidas exatamente saem do
        # "pool" antes da soma ser calculada.
        TOLERANCIA = 0.01
        matched_1a1 = 0
        matched_soma = 0
        sem_match = []
        codigos_por_linha = {}

        # 3a. Regra 1 para 1 em todos os lançamentos primeiro.
        pendentes_soma = []
        for lanc in lancamentos:
            candidatos = [l for l in linhas_planilha if not l['matched'] and l['nome_norm'] == lanc['nome_norm']]
            if not candidatos:
                pendentes_soma.append(lanc)
                continue

            # Existe uma linha isolada (ainda não conciliada) com o mesmo valor.
            alvo = next((c for c in candidatos if abs(c['valor'] - lanc['valor']) < TOLERANCIA), None)
            if alvo:
                alvo['matched'] = True
                codigos_por_linha[alvo['row']] = lanc['codigo']
                matched_1a1 += 1
            else:
                pendentes_soma.append(lanc)

        # 3b. Regra 1 para N (soma) só no que sobrou, com o pool de linhas já livre das
        # que bateram exatamente na passagem acima.
        for lanc in pendentes_soma:
            candidatos = [l for l in linhas_planilha if not l['matched'] and l['nome_norm'] == lanc['nome_norm']]
            if not candidatos:
                sem_match.append(lanc)
                continue

            soma = sum(c['valor'] for c in candidatos)
            if abs(soma - lanc['valor']) < TOLERANCIA:
                for c in candidatos:
                    c['matched'] = True
                    codigos_por_linha[c['row']] = lanc['codigo']
                matched_soma += 1
                continue

            sem_match.append(lanc)

        # 3b. Concilia os critérios "agregados" (ex: PIX x FGTS, Itaú x Rescisão/Férias/Folha):
        # soma todos os valores extraídos do(s) PDF(s) daquele parser e compara contra a soma
        # das linhas-alvo ainda não conciliadas na planilha (por nome exato ou por conter uma
        # das palavras-chave, conforme 'modo_alvo'). Se não bater, grava 'codigo_erro' em
        # todas as linhas-alvo (nunca deixa em branco).
        agregados_resultado = []
        for chave, grupo in agregados_por_parser.items():
            parser_agregado = grupo['parser']
            soma_pdf = sum(grupo['valores'])
            alvo_norm = {_normalizar_nome(n) for n in parser_agregado['alvo']}

            if parser_agregado['modo_alvo'] == 'contem':
                candidatos = [
                    l for l in linhas_planilha
                    if not l['matched'] and any(kw in l['nome_norm'] for kw in alvo_norm)
                ]
            else:
                candidatos = [l for l in linhas_planilha if not l['matched'] and l['nome_norm'] in alvo_norm]

            if not candidatos:
                agregados_resultado.append((chave, soma_pdf, None, None))
                continue

            soma_excel = sum(c['valor'] for c in candidatos)
            codigo = parser_agregado['codigo_ok'] if abs(soma_excel - soma_pdf) < TOLERANCIA else parser_agregado['codigo_erro']
            for c in candidatos:
                c['matched'] = True
                codigos_por_linha[c['row']] = codigo
            agregados_resultado.append((chave, soma_pdf, soma_excel, codigo))

        print(f"\n=== CONCILIAÇÃO DE EXTRATOS BANCÁRIOS (aba '{sheet_name}') ===")
        print(f"Lançamentos extraídos dos PDFs: {len(lancamentos)}")
        print(f"Conciliados 1 para 1: {matched_1a1}")
        print(f"Conciliados por soma (1 para N): {matched_soma}")
        print(f"Sem correspondência: {len(sem_match)}")
        for item in sem_match:
            print(f"  - [{item['arquivo']}] {item['nome']} | R$ {item['valor']:.2f}")
        for chave, soma_pdf, soma_excel, codigo in agregados_resultado:
            if soma_excel is None:
                print(f"  - [{chave}] Nenhuma linha-alvo encontrada na planilha (soma PDF: R$ {soma_pdf:.2f})")
            else:
                print(f"  - [{chave}] Soma PDF: R$ {soma_pdf:.2f} | Soma planilha: R$ {soma_excel:.2f} | Código: {codigo}")
        print("====================================================\n")

        # 4. Retorna a mesma planilha original, apenas com a coluna A preenchida. A edição é
        # feita direto no XML original (não via wb.save()) para preservar 100% do restante
        # do arquivo — pivot tables, pivot cache, gráficos, etc. — que o openpyxl não
        # consegue reserializar sem perdas (o que fazia o Excel acusar arquivo corrompido).
        conteudo_final = _gravar_codigos_na_planilha(conteudo_planilha, sheet_xml_path, codigos_por_linha)

        from urllib.parse import quote
        original_name = planilha.filename or "planilha.xlsx"
        extensao = original_name.rsplit('.', 1)[-1] if '.' in original_name else 'xlsx'

        # Registra a importação para aparecer no histórico da tela — sem gravar nenhuma
        # movimentação, só o registro da importação em si (como já é feito nas outras
        # rotas de conciliação/extração deste arquivo).
        ImportacaoService(db).registrar_importacao(original_name, extensao, "Conciliação Bancária", id_user_inc=current_user.iduser)

        nome_encoded = quote(original_name)
        return StreamingResponse(
            io.BytesIO(conteudo_final),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=\"planilha_conciliada.xlsx\"; filename*=UTF-8''{nome_encoded}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cema/conciliar")
async def conciliar_cema(
    cema_file: UploadFile = File(...),
    acr_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not cema_file.filename or not acr_file.filename:
        raise HTTPException(status_code=400, detail="Arquivos inválidos")
        
    try:
        import io
        import pandas as pd
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        import datetime
        import math
        
        # 1. Parse Cema File
        cema_bytes = await cema_file.read()
        try:
            df_cema = pd.read_excel(io.BytesIO(cema_bytes), header=None)
        except Exception:
            raise HTTPException(status_code=400, detail="Arquivo Cema deve ser Excel.")
            
        # Parse Dates Helper
        def parse_date(date_str):
            if not date_str:
                return None
            if isinstance(date_str, datetime.datetime):
                return date_str.date()
            if isinstance(date_str, datetime.date):
                return date_str
            date_str = str(date_str).strip()
            if hasattr(pd, 'Timestamp') and isinstance(date_str, pd.Timestamp):
                return date_str.date()
            for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%y', '%Y/%m/%d %H:%M:%S', '%d/%m/%Y %H:%M:%S'):
                try:
                    return datetime.datetime.strptime(date_str.split()[0] if ' ' in date_str else date_str, fmt).date()
                except ValueError:
                    continue
            return None

        # Next Wednesday Helper
        def get_next_wednesday(d):
            if not isinstance(d, datetime.date):
                return d
            wd = d.weekday()
            if wd == 2:
                return d
            days_ahead = 2 - wd
            if days_ahead <= 0:
                days_ahead += 7
            return d + datetime.timedelta(days_ahead)

        cema_invoices = []
        for idx, row in df_cema.iterrows():
            if len(row) < 6:
                continue
            
            nf_raw = str(row[1]).strip() # Col B (index 1)
            date_raw = row[5] # Col F (index 5)
            
            if not nf_raw or nf_raw.lower() in ('nan', 'none', 'nota fiscal', 'nota', 'nota_fiscal'):
                continue
                
            nf_clean = nf_raw.split('/')[0].strip()
            
            if not nf_clean:
                continue
                
            if not any(char.isdigit() for char in nf_clean):
                continue
            
            try:
                nf_clean = str(int(float(nf_clean))).zfill(7)
            except ValueError:
                nf_clean = nf_clean.zfill(7)
            
            d_parsed = parse_date(date_raw)
            d_adjusted = get_next_wednesday(d_parsed) if d_parsed else date_raw
            
            cema_invoices.append({
                'raw_nf': nf_raw,
                'nf': nf_clean,
                'prorrogacao': d_adjusted
            })
            
        if not cema_invoices:
            raise HTTPException(status_code=400, detail="Nenhuma nota fiscal encontrada no arquivo Cema.")

        # 2. Parse ACR File
        acr_bytes = await acr_file.read()
        try:
            df_acr = pd.read_excel(io.BytesIO(acr_bytes), header=None)
        except Exception:
            acr_text = acr_bytes.decode('utf-8', errors='ignore')
            sep = ';' if ';' in acr_text else ','
            df_acr = pd.read_csv(io.StringIO(acr_text), sep=sep, header=None)
            
        acr_data_by_int = {}
        for idx, row in df_acr.iterrows():
            if len(row) < 16:
                continue
                
            # For Cema, just extract Nota (Col D / index 3) and Vencimento (Col P / index 15)
            # Remove strict 104, DP, and Parcela filters which could cause "Não encontrado"
            val_d_raw = str(row[3]).strip()
            if not val_d_raw or val_d_raw.lower() in ('nan', 'none'):
                continue
                
            val_d = val_d_raw.split('.')[0]
            val_p = str(row[15]).strip()
            if ' ' in val_p:
                val_p = val_p.split()[0]
                
            try:
                acr_data_by_int[int(val_d)] = parse_date(val_p) or val_p
            except ValueError:
                continue
                
        # 3. Create Excel
        def format_date_to_br(d):
            if isinstance(d, datetime.date):
                return d.strftime('%d/%m/%Y')
            return str(d) if d else ""

        wb = openpyxl.Workbook()
        ws1 = wb.active
        ws1.title = "Prorrogações Cema"
        ws1.views.sheetView[0].showGridLines = True
        
        ws1.cell(row=1, column=1, value="Nota Fiscal")
        ws1.cell(row=1, column=2, value="Data de Prorrogação")
        
        for i, inv in enumerate(cema_invoices):
            ws1.cell(row=i+2, column=1, value=inv['nf'])
            ws1.cell(row=i+2, column=2, value=format_date_to_br(inv['prorrogacao']))
            
        ws2 = wb.create_sheet(title="Conciliação")
        ws2.views.sheetView[0].showGridLines = True
        ws2.cell(row=1, column=1, value="Nota Fiscal")
        ws2.cell(row=1, column=2, value="Data Cema (Prorrogação)")
        ws2.cell(row=1, column=3, value="Data ACR (Vencimento)")
        ws2.cell(row=1, column=4, value="Status")
        
        font_header = Font(name='Calibri', size=11, bold=True)
        font_body = Font(name='Calibri', size=11, bold=False)
        align_left = Alignment(horizontal='left', vertical='center')
        align_center = Alignment(horizontal='center', vertical='center')
        
        fill_ok = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
        fill_div = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
        
        for col_idx in [1, 2]:
            cell = ws1.cell(row=1, column=col_idx)
            cell.font = font_header
            cell.alignment = align_left
            
        for r_idx in range(2, len(cema_invoices) + 2):
            ws1.cell(row=r_idx, column=1).font = font_body
            ws1.cell(row=r_idx, column=1).number_format = '@'
            ws1.cell(row=r_idx, column=1).alignment = align_left
            ws1.cell(row=r_idx, column=2).font = font_body
            ws1.cell(row=r_idx, column=2).alignment = align_center
            
        ws1.column_dimensions['A'].width = 16
        ws1.column_dimensions['B'].width = 24
        
        for i, inv in enumerate(cema_invoices):
            row_num = i + 2
            nf_str = inv['nf']
            d_cema = inv['prorrogacao']
            
            try:
                nf_int = int(nf_str)
            except ValueError:
                nf_int = None
                
            d_acr = None
            status = "Não encontrado no CSV"
            status_fill = None
            
            if nf_int is not None and nf_int in acr_data_by_int:
                d_acr = acr_data_by_int[nf_int]
                
                if isinstance(d_cema, datetime.date) and isinstance(d_acr, datetime.date):
                    if d_cema == d_acr:
                        status = "OK"
                        status_fill = fill_ok
                    else:
                        status = "Divergente"
                        status_fill = fill_div
                else:
                    if str(d_cema).strip() == str(d_acr).strip():
                        status = "OK"
                        status_fill = fill_ok
                    else:
                        status = "Divergente"
                        status_fill = fill_div
                        
            ws2.cell(row=row_num, column=1, value=nf_str)
            ws2.cell(row=row_num, column=2, value=format_date_to_br(d_cema))
            ws2.cell(row=row_num, column=3, value=format_date_to_br(d_acr))
            
            status_cell = ws2.cell(row=row_num, column=4, value=status)
            if status_fill:
                status_cell.fill = status_fill
                
        for col_idx in [1, 2, 3, 4]:
            cell = ws2.cell(row=1, column=col_idx)
            cell.font = font_header
            cell.alignment = align_left
            
        for r_idx in range(2, len(cema_invoices) + 2):
            ws2.cell(row=r_idx, column=1).font = font_body
            ws2.cell(row=r_idx, column=1).number_format = '@'
            ws2.cell(row=r_idx, column=1).alignment = align_left
            ws2.cell(row=r_idx, column=2).font = font_body
            ws2.cell(row=r_idx, column=2).alignment = align_center
            ws2.cell(row=r_idx, column=3).font = font_body
            ws2.cell(row=r_idx, column=3).alignment = align_center
            ws2.cell(row=r_idx, column=4).font = font_body
            ws2.cell(row=r_idx, column=4).alignment = align_left
            
        ws2.column_dimensions['A'].width = 16
        ws2.column_dimensions['B'].width = 24
        ws2.column_dimensions['C'].width = 24
        ws2.column_dimensions['D'].width = 24
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = cema_file.filename.rsplit('.', 1)[0] + "_extraido.xlsx"
        
        from app.services.importacao_service import ImportacaoService
        ImportacaoService(db).registrar_importacao(filename, "xlsx", "Prorrogação - Cema", id_user_inc=current_user.iduser)
        
        headers_response = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers_response
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
