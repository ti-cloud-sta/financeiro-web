import io
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any

from fastapi import UploadFile, HTTPException
from sqlalchemy import func, cast, Integer, text
from sqlalchemy.orm import Session
import openpyxl

from app.models.importacao import Importacao
from app.models.previsao_apb import PrevisaoApb, VwPrevisaoApb
from app.models.previsao_acr import PrevisaoAcr
from app.models.previsao_titulos_liquidados import PrevisaoTitulosLiquidados
from app.models.previsao_cliente_score import PrevisaoClienteScore
from app.models.cliente import Cliente
from app.models.matriz_cliente import MatrizCliente
from app.models.user import User

logger = logging.getLogger("santamaria")

class PrevisaoCaixaService:
    def __init__(self, db: Session):
        self.db = db

    def _normalizar_header(self, h: Any) -> str:
        if not h:
            return ""
        s = str(h).strip().lower()
        # Remove caracteres especiais comuns
        s = s.replace("|", "").replace("-", "_").replace(" ", "_")
        return s

    def _parse_data(self, val: Any) -> Optional[date]:
        if val is None or val == "":
            return None
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, date):
            return val
        s = str(val).strip()
        if not s:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return None

    def _parse_decimal(self, val: Any) -> Optional[Decimal]:
        if val is None or val == "":
            return None
        if isinstance(val, (int, float, Decimal)):
            return Decimal(str(val))
        s = str(val).strip().replace("R$", "").replace(" ", "")
        if not s:
            return None
        # Formato brasileiro 1.234,56 -> 1234.56
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            s = s.replace(",", ".")
        try:
            return Decimal(s)
        except Exception:
            return None

    def _parse_str(self, val: Any, max_length: Optional[int] = None) -> Optional[str]:
        if val is None:
            return None
        s = str(val).strip()
        if not s:
            return None
        if max_length and len(s) > max_length:
            return s[:max_length]
        return s

    def _parse_int(self, val: Any) -> Optional[int]:
        if val is None or val == "":
            return None
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            return int(round(val))
        s = str(val).strip()
        if not s:
            return None
        if s.endswith(".0"):
            s = s[:-2]
        try:
            return int(s)
        except Exception:
            return None

    async def importar_planilha_apb(self, file: UploadFile, current_user: Optional[User] = None) -> Dict[str, Any]:
        """
        Processa e importa o arquivo APB.xlsx:
        1. Cria o registro na tabela importacoes (gerando idImportacoes).
        2. Lê a aba DADOS com formulas avaliadas (data_only=True).
        3. Realiza o insert em lote na tabela previsao_apb vinculado à importação.
        """
        filename = file.filename or "APB.xlsx"
        ext = filename.split(".")[-1].lower() if "." in filename else "xlsx"

        if ext not in ["xlsx", "xls"]:
            raise HTTPException(
                status_code=400,
                detail=f"Formato de arquivo inválido (.{ext}). Envie um arquivo Excel (.xlsx ou .xls)."
            )

        try:
            contents = await file.read()
            # data_only=True para ler valores calculados de fórmulas (ex: VLOOKUP em NOME EMITENTE)
            wb = openpyxl.load_workbook(io.BytesIO(contents), data_only=True, read_only=True)
        except Exception as e:
            logger.exception("Erro ao abrir arquivo Excel APB: %s", str(e))
            raise HTTPException(
                status_code=400,
                detail=f"Não foi possível abrir o arquivo Excel. Verifique se o arquivo não está corrompido: {str(e)}"
            )

        # Localiza a aba DADOS (ou busca case-insensitive)
        sheet_target = None
        for name in wb.sheetnames:
            if name.strip().upper() == "DADOS":
                sheet_target = name
                break
        
        if not sheet_target:
            # Fallback se houver apenas uma aba
            if len(wb.sheetnames) == 1:
                sheet_target = wb.sheetnames[0]
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"A aba 'DADOS' não foi encontrada na planilha. Abas disponíveis: {', '.join(wb.sheetnames)}"
                )

        sheet = wb[sheet_target]
        rows_iter = sheet.iter_rows(values_only=True)

        try:
            header_row = next(rows_iter)
        except StopIteration:
            raise HTTPException(status_code=400, detail="A planilha está vazia.")

        # Mapeamento dinâmico de cabeçalhos
        header_map: Dict[str, int] = {}
        for idx, col_name in enumerate(header_row):
            norm = self._normalizar_header(col_name)
            if norm:
                header_map[norm] = idx

        # Validação básica de colunas essenciais
        alias_dict = {
            "arquivo": ["arquivo"],
            "data": ["data"],
            "cod_tp_fluxo": ["cod_tp_fluxo"],
            "ent_sai": ["ent_sai"],
            "prev_real": ["prev_real"],
            "modulo": ["modulo"],
            "vlr_cam_2": ["vlr_cam_2"],
            "trans": ["trans"],
            "emp": ["emp"],
            "estab": ["estab"],
            "esp": ["esp"],
            "serie": ["serie"],
            "n_titulo": ["n_titulo", "numero_titulo", "titulo"],
            "parcela": ["parcela"],
            "numero_fornecedor": ["numero_fornecedor", "num_fornecedor", "fornecedor"],
            "nome_abrev": ["nome_abrev", "favorecido"],
            "valor_fluxo": ["valor_fluxo"],
            "valor": ["valor"],
            "nome_emitente": ["nome_emitente", "emitente"]
        }

        col_index: Dict[str, Optional[int]] = {}
        for field, aliases in alias_dict.items():
            col_index[field] = None
            for a in aliases:
                if a in header_map:
                    col_index[field] = header_map[a]
                    break

        user_name = current_user.name if current_user and current_user.name else "Sistema"
        user_id = current_user.iduser if current_user else None

        # 1. Criação do lote na tabela importacoes
        nova_importacao = Importacao(
            nomeArquivo=filename,
            extensaoArquivo=ext,
            tipo="CONTAS A PAGAR (APB)",
            idUserInc=user_id,
            createdAt=datetime.now()
        )
        self.db.add(nova_importacao)
        self.db.flush()  # Gera o idImportacoes

        id_importacao = nova_importacao.idImportacoes
        data_agora = datetime.now()

        # 2. Leitura e preparação dos registros
        registros_para_inserir: List[Dict[str, Any]] = []
        total_valor_somado = Decimal("0.00")

        for row in rows_iter:
            # Pula linhas totalmente vazias
            if not row or all(v is None for v in row):
                continue

            def get_val(f_name: str) -> Any:
                idx = col_index.get(f_name)
                if idx is not None and idx < len(row):
                    return row[idx]
                return None

            val_valor = self._parse_decimal(get_val("valor"))
            if val_valor:
                total_valor_somado += val_valor

            reg = {
                "arquivo": self._parse_str(get_val("arquivo"), 50),
                "data": self._parse_data(get_val("data")),
                "cod_tp_fluxo": self._parse_str(get_val("cod_tp_fluxo"), 20),
                "ent_sai": self._parse_str(get_val("ent_sai"), 10),
                "prev_real": self._parse_str(get_val("prev_real"), 10),
                "modulo": self._parse_str(get_val("modulo"), 20),
                "vlr_cam_2": self._parse_decimal(get_val("vlr_cam_2")),
                "trans": self._parse_str(get_val("trans"), 100),
                "emp": self._parse_str(get_val("emp"), 10),
                "estab": self._parse_str(get_val("estab"), 10),
                "esp": self._parse_str(get_val("esp"), 10),
                "serie": self._parse_str(get_val("serie"), 20),
                "n_titulo": self._parse_str(get_val("n_titulo"), 50),
                "parcela": self._parse_str(get_val("parcela"), 10),
                "numero_fornecedor": self._parse_str(get_val("numero_fornecedor"), 30),
                "nome_abrev": self._parse_str(get_val("nome_abrev"), 100),
                "valor_fluxo": self._parse_decimal(get_val("valor_fluxo")),
                "valor": val_valor,
                "nome_emitente": self._parse_str(get_val("nome_emitente"), 255),
                "idImportacoes": id_importacao,
                "data_criacao": data_agora,
                "usuario_inclusao": user_name
            }
            registros_para_inserir.append(reg)

        if not registros_para_inserir:
            self.db.rollback()
            raise HTTPException(status_code=400, detail="Nenhum registro válido foi encontrado na aba DADOS.")

        # 3. Inserção em lote de alta performance
        try:
            self.db.bulk_insert_mappings(PrevisaoApb, registros_para_inserir)
            self.db.commit()
            self.db.refresh(nova_importacao)
        except Exception as e:
            self.db.rollback()
            logger.exception("Erro ao persistir registros de PrevisaoApb: %s", str(e))
            raise HTTPException(status_code=500, detail=f"Erro ao salvar registros no banco de dados: {str(e)}")

        return {
            "sucesso": True,
            "mensagem": f"Planilha APB importada com sucesso ({len(registros_para_inserir)} registros inseridos).",
            "idImportacoes": id_importacao,
            "nomeArquivo": filename,
            "totalRegistros": len(registros_para_inserir),
            "totalValor": float(total_valor_somado)
        }

    async def importar_planilha_acr(self, file: UploadFile, current_user: Optional[User] = None) -> Dict[str, Any]:
        """
        Processa e importa o arquivo ACR.xlsx:
        1. Cria o registro na tabela importacoes (gerando idImportacoes).
        2. Lê a aba ACR (ou Resumo) com formulas avaliadas (data_only=True).
        3. Realiza o insert em lote na tabela previsao_acr vinculado à importação.
        """
        filename = file.filename or "ACR.xlsx"
        ext = filename.split(".")[-1].lower() if "." in filename else "xlsx"

        if ext not in ["xlsx", "xls"]:
            raise HTTPException(
                status_code=400,
                detail=f"Formato de arquivo inválido (.{ext}). Envie um arquivo Excel (.xlsx ou .xls)."
            )

        try:
            contents = await file.read()
            wb = openpyxl.load_workbook(io.BytesIO(contents), data_only=True, read_only=True)
        except Exception as e:
            logger.exception("Erro ao abrir arquivo Excel ACR: %s", str(e))
            raise HTTPException(
                status_code=400,
                detail=f"Não foi possível abrir o arquivo Excel. Verifique se o arquivo não está corrompido: {str(e)}"
            )

        # Localiza a aba Resumo (que contém Dt Entrega e Tipo Pedido) ou fallback para ACR/DADOS
        sheet_target = None
        for cand in ["RESUMO", "ACR", "DADOS"]:
            for name in wb.sheetnames:
                if name.strip().upper() == cand:
                    sheet_target = name
                    break
            if sheet_target:
                break

        if not sheet_target:
            sheet_target = wb.sheetnames[0]

        sheet = wb[sheet_target]
        rows_iter = sheet.iter_rows(values_only=True)

        try:
            header_row = next(rows_iter)
        except StopIteration:
            raise HTTPException(status_code=400, detail="A planilha está vazia.")

        header_map: Dict[str, int] = {}
        for idx, col_name in enumerate(header_row):
            norm = self._normalizar_header(col_name)
            if norm:
                header_map[norm] = idx

        alias_dict = {
            "est": ["est", "estab", "estabelecimento"],
            "esp": ["esp", "especie"],
            "ser": ["ser", "serie"],
            "titulo": ["titulo", "título", "t_tulo", "n_titulo", "numero_titulo"],
            "parcela": ["parcela", "_p", "/p", "p"],
            "un_neg": ["un_neg", "unneg", "unidade_negocio"],
            "nr_pedcli": ["nr_pedcli", "nrpedcli", "pedcli", "pedido_cliente"],
            "tipo_pedido": ["tipo_pedido", "tp_pedido"],
            "cliente": ["cliente", "cod_cliente", "codigo_cliente"],
            "nome_abrev": ["nome_abrev", "nome_abreviado"],
            "nome_cliente": ["nome_cliente", "cliente_nome", "razao_social"],
            "grp_cliente": ["grp_cliente", "grupo_cliente"],
            "cliente_matriz": ["cliente_matriz", "matriz"],
            "port": ["port", "portador"],
            "cart": ["cart", "carteira"],
            "repres": ["repres", "representante"],
            "emissao": ["emissao", "emissão", "emiss_o", "dt_emissao"],
            "dt_entrega": ["dt_entrega", "data_entrega"],
            "vencto": ["vencto", "vencimento", "dt_vencto"],
            "dt_agdnto": ["dt_agdnto", "agendamento"],
            "liquidac": ["liquidac", "liquidacao", "dt_liquidacao"],
            "refer": ["refer", "referencia"],
            "tit_banco": ["tit_banco", "titulo_banco"],
            "moeda": ["moeda"],
            "val_original": ["val_original", "valor_original", "vlr_original"],
            "saldo": ["saldo", "vlr_saldo"],
            "saldo_apresentacao": ["saldo_apresentacao", "saldo_apresenta_o", "saldo_apresentação"],
            "cond_pagto": ["cond_pagto", "condicao_pagamento"],
            "vl_descto": ["vl_descto", "desconto", "valor_desconto"],
            "vl_abat": ["vl_abat", "abatimento", "valor_abatimento"],
            "dias": ["dias"],
            "pedido_venda": ["pedido_venda", "ped_venda"],
            "data_indic": ["data_indic", "dt_indic"],
            "cond_cobr": ["cond_cobr", "condicao_cobranca"],
            "cidade": ["cidade"],
            "telefone": ["telefone"],
            "cidade_cobranca_cliente": ["cidade_cobranca_cliente", "cidade_cobranca", "cidade_cobran_a_cliente"],
            "id_federal": ["id_federal", "cnpj", "cpf", "cnpj_cpf"],
            "unid_federac": ["unid_federac", "uf", "estado"]
        }

        col_index: Dict[str, Optional[int]] = {}
        for field, aliases in alias_dict.items():
            col_index[field] = None
            for a in aliases:
                if a in header_map:
                    col_index[field] = header_map[a]
                    break

        user_name = current_user.name if current_user and current_user.name else "Sistema"
        user_id = current_user.iduser if current_user else None

        nova_importacao = Importacao(
            nomeArquivo=filename,
            extensaoArquivo=ext,
            tipo="CONTAS A RECEBER (ACR)",
            idUserInc=user_id,
            createdAt=datetime.now()
        )
        self.db.add(nova_importacao)
        self.db.flush()

        id_importacao = nova_importacao.idImportacoes
        data_agora = datetime.now()

        registros_para_inserir: List[Dict[str, Any]] = []
        total_valor_somado = Decimal("0.00")

        for row in rows_iter:
            if not row or all(v is None for v in row):
                continue

            def get_val(f_name: str) -> Any:
                idx = col_index.get(f_name)
                if idx is not None and idx < len(row):
                    return row[idx]
                return None

            val_saldo = self._parse_decimal(get_val("saldo"))
            val_original = self._parse_decimal(get_val("val_original"))
            if val_saldo:
                total_valor_somado += val_saldo
            elif val_original:
                total_valor_somado += val_original

            reg = {
                "est": self._parse_str(get_val("est"), 20),
                "esp": self._parse_str(get_val("esp"), 20),
                "ser": self._parse_str(get_val("ser"), 20),
                "titulo": self._parse_str(get_val("titulo"), 50),
                "parcela": self._parse_str(get_val("parcela"), 20),
                "un_neg": self._parse_str(get_val("un_neg"), 50),
                "nr_pedcli": self._parse_str(get_val("nr_pedcli"), 50),
                "tipo_pedido": self._parse_str(get_val("tipo_pedido"), 20),
                "cliente": self._parse_str(get_val("cliente"), 50),
                "nome_abrev": self._parse_str(get_val("nome_abrev"), 100),
                "nome_cliente": self._parse_str(get_val("nome_cliente"), 255),
                "grp_cliente": self._parse_str(get_val("grp_cliente"), 50),
                "cliente_matriz": self._parse_str(get_val("cliente_matriz"), 50),
                "port": self._parse_str(get_val("port"), 50),
                "cart": self._parse_str(get_val("cart"), 50),
                "repres": self._parse_str(get_val("repres"), 50),
                "emissao": self._parse_data(get_val("emissao")),
                "dt_entrega": self._parse_data(get_val("dt_entrega")),
                "vencto": self._parse_data(get_val("vencto")),
                "dt_agdnto": self._parse_data(get_val("dt_agdnto")),
                "liquidac": self._parse_data(get_val("liquidac")),
                "refer": self._parse_str(get_val("refer"), 100),
                "tit_banco": self._parse_str(get_val("tit_banco"), 50),
                "moeda": self._parse_str(get_val("moeda"), 20),
                "val_original": val_original,
                "saldo": val_saldo,
                "saldo_apresentacao": self._parse_decimal(get_val("saldo_apresentacao")),
                "cond_pagto": self._parse_str(get_val("cond_pagto"), 50),
                "vl_descto": self._parse_decimal(get_val("vl_descto")),
                "vl_abat": self._parse_decimal(get_val("vl_abat")),
                "dias": self._parse_int(get_val("dias")),
                "pedido_venda": self._parse_str(get_val("pedido_venda"), 50),
                "data_indic": self._parse_data(get_val("data_indic")),
                "cond_cobr": self._parse_str(get_val("cond_cobr"), 50),
                "cidade": self._parse_str(get_val("cidade"), 100),
                "telefone": self._parse_str(get_val("telefone"), 50),
                "cidade_cobranca_cliente": self._parse_str(get_val("cidade_cobranca_cliente"), 100),
                "id_federal": self._parse_str(get_val("id_federal"), 50),
                "unid_federac": self._parse_str(get_val("unid_federac"), 10),
                "idImportacoes": id_importacao,
                "data_criacao": data_agora,
                "usuario_inclusao": user_name
            }
            registros_para_inserir.append(reg)

        if not registros_para_inserir:
            self.db.rollback()
            raise HTTPException(status_code=400, detail="Nenhum registro válido foi encontrado na planilha ACR.")

        try:
            self.db.bulk_insert_mappings(PrevisaoAcr, registros_para_inserir)
            self.db.commit()
            self.db.refresh(nova_importacao)
        except Exception as e:
            self.db.rollback()
            logger.exception("Erro ao persistir registros de PrevisaoAcr: %s", str(e))
            raise HTTPException(status_code=500, detail=f"Erro ao salvar registros no banco de dados: {str(e)}")

        return {
            "sucesso": True,
            "mensagem": f"Planilha ACR importada com sucesso ({len(registros_para_inserir)} registros inseridos).",
            "idImportacoes": id_importacao,
            "nomeArquivo": filename,
            "totalRegistros": len(registros_para_inserir),
            "totalValor": float(total_valor_somado)
        }

    async def importar_planilha_titulos_liquidados(self, file: UploadFile, current_user: Optional[User] = None) -> Dict[str, Any]:
        """
        Processa e importa o arquivo Titulos liquidados.xlsx:
        1. Cria o registro na tabela importacoes (gerando idImportacoes).
        2. Lê a aba liquidados (ou primeira aba disponível) com formulas avaliadas (data_only=True).
        3. Realiza o insert em lote na tabela previsao_titulos_liquidados em batches de 5.000.
        """
        filename = file.filename or "Titulos_Liquidados.xlsx"
        ext = filename.split(".")[-1].lower() if "." in filename else "xlsx"

        if ext not in ["xlsx", "xls"]:
            raise HTTPException(
                status_code=400,
                detail=f"Formato de arquivo inválido (.{ext}). Envie um arquivo Excel (.xlsx ou .xls)."
            )

        try:
            contents = await file.read()
            wb = openpyxl.load_workbook(io.BytesIO(contents), data_only=True, read_only=True)
        except Exception as e:
            logger.exception("Erro ao abrir arquivo Excel Titulos Liquidados: %s", str(e))
            raise HTTPException(
                status_code=400,
                detail=f"Não foi possível abrir o arquivo Excel. Verifique se o arquivo não está corrompido: {str(e)}"
            )

        sheet_target = None
        for cand in ["LIQUIDADOS", "TITULOS LIQUIDADOS", "RESUMO", "DADOS"]:
            for name in wb.sheetnames:
                if name.strip().upper() == cand:
                    sheet_target = name
                    break
            if sheet_target:
                break

        if not sheet_target:
            sheet_target = wb.sheetnames[0]

        sheet = wb[sheet_target]
        rows_iter = sheet.iter_rows(values_only=True)

        try:
            header_row = next(rows_iter)
        except StopIteration:
            raise HTTPException(status_code=400, detail="A planilha está vazia.")

        user_name = current_user.name if current_user and current_user.name else "Sistema"
        user_id = current_user.iduser if current_user else None

        nova_importacao = Importacao(
            nomeArquivo=filename,
            extensaoArquivo=ext,
            tipo="TITULOS LIQUIDADOS",
            idUserInc=user_id,
            createdAt=datetime.now()
        )
        self.db.add(nova_importacao)
        self.db.flush()

        id_importacao = nova_importacao.idImportacoes
        data_agora = datetime.now()

        # Carrega chaves existentes para validação anti-duplicidade em memória (ultra-rápido via set)
        chaves_existentes = set(
            self.db.execute(text("""
                SELECT CONCAT_WS('|',
                    COALESCE(TRIM(estabelecimento), ''),
                    COALESCE(TRIM(especie_documento), ''),
                    COALESCE(TRIM(serie_documento), ''),
                    COALESCE(TRIM(titulo), ''),
                    COALESCE(TRIM(parcela), ''),
                    COALESCE(TRIM(cliente), ''),
                    COALESCE(liquidacao, ''),
                    COALESCE(ROUND(val_movimento, 2), '')
                )
                FROM previsao_titulos_liquidados
            """)).scalars().all()
        )

        registros_batch: List[Dict[str, Any]] = []
        total_registros = 0
        total_ignorados_duplicados = 0
        total_valor_somado = Decimal("0.00")
        BATCH_SIZE = 5000

        try:
            for row in rows_iter:
                if not row or all(v is None for v in row):
                    continue

                def col(idx: int) -> Any:
                    return row[idx] if idx < len(row) else None

                estab = self._parse_str(col(0), 20) or ""
                especie = self._parse_str(col(1), 20) or ""
                serie = self._parse_str(col(2), 20) or ""
                tit = self._parse_str(col(3), 50) or ""
                parc = self._parse_str(col(4), 20) or ""
                cli = self._parse_str(col(5), 50) or ""
                dt_liq = self._parse_data(col(29))
                val_mov = self._parse_decimal(col(22))
                val_liq = self._parse_decimal(col(26))
                val_orig = self._parse_decimal(col(37))

                # Monta chave de unicidade da movimentação
                dt_liq_str = dt_liq.strftime("%Y-%m-%d") if dt_liq else ""
                vlr_chave = f"{val_mov:.2f}" if val_mov is not None else ""
                chave = f"{estab.strip()}|{especie.strip()}|{serie.strip()}|{tit.strip()}|{parc.strip()}|{cli.strip()}|{dt_liq_str}|{vlr_chave}"

                if chave in chaves_existentes:
                    total_ignorados_duplicados += 1
                    continue

                chaves_existentes.add(chave)

                if val_mov:
                    total_valor_somado += val_mov
                elif val_liq:
                    total_valor_somado += val_liq
                elif val_orig:
                    total_valor_somado += val_orig

                reg = {
                    "estabelecimento": estab or None,
                    "especie_documento": especie or None,
                    "serie_documento": serie or None,
                    "titulo": tit or None,
                    "parcela": parc or None,
                    "cliente": cli or None,
                    "nome_cliente": self._parse_str(col(6), 255),
                    "portador": self._parse_str(col(7), 50),
                    "matriz": self._parse_str(col(8), 100),
                    "representante": self._parse_str(col(9), 50),
                    "nome_representante": self._parse_str(col(10), 255),
                    "carteira": self._parse_str(col(11), 50),
                    "data_vencimento": self._parse_data(col(12)),
                    "data_credito": self._parse_data(col(13)),
                    "data_emissao": self._parse_data(col(14)),
                    "trans_abrev": self._parse_str(col(15), 50),
                    "unid_negocio": self._parse_str(col(16), 50),
                    "ad": self._parse_str(col(17), 50),
                    "acumula_atraso": self._parse_str(col(18), 20),
                    "nome_abreviado": self._parse_str(col(19), 100),
                    "descricao_especie": self._parse_str(col(20), 100),
                    "referencia": self._parse_str(col(21), 100),
                    "val_movimento": val_mov,
                    "val_antecipado": self._parse_decimal(col(23)),
                    "descto_abatim": self._parse_decimal(col(24)),
                    "juros": self._parse_decimal(col(25)),
                    "valor_liquido": val_liq,
                    "valor_pendente": self._parse_decimal(col(27)),
                    "retencoes": self._parse_decimal(col(28)),
                    "liquidacao": dt_liq,
                    "vl_cheque": self._parse_decimal(col(30)),
                    "grupo_cliente": self._parse_str(col(31), 50),
                    "numero_plaqueta": self._parse_str(col(32), 50),
                    "ult_aprop_desp_fin": self._parse_str(col(33), 100),
                    "data_transacao": self._parse_data(col(34)),
                    "cliente_matriz": self._parse_str(col(36), 50),
                    "valor_original": val_orig,
                    "processo_exportacao": self._parse_str(col(38), 50),
                    "soma_valor_original": self._parse_str(col(39), 20),
                    "pedido_venda": self._parse_str(col(40), 50),
                    "idImportacoes": id_importacao,
                    "data_criacao": data_agora,
                    "usuario_inclusao": user_name
                }
                registros_batch.append(reg)
                total_registros += 1

                if len(registros_batch) >= BATCH_SIZE:
                    self.db.bulk_insert_mappings(PrevisaoTitulosLiquidados, registros_batch)
                    registros_batch.clear()

            if registros_batch:
                self.db.bulk_insert_mappings(PrevisaoTitulosLiquidados, registros_batch)
                registros_batch.clear()

            if total_registros == 0:
                self.db.rollback()
                if total_ignorados_duplicados > 0:
                    return {
                        "sucesso": True,
                        "mensagem": f"Nenhum novo registro a acrescentar. Todos os {total_ignorados_duplicados} títulos da planilha já constam no banco de dados.",
                        "idImportacoes": id_importacao,
                        "nomeArquivo": filename,
                        "totalRegistros": 0,
                        "totalIgnorados": total_ignorados_duplicados,
                        "totalValor": 0.0
                    }
                else:
                    raise HTTPException(status_code=400, detail="Nenhum registro válido foi encontrado na planilha de Títulos Liquidados.")

            self.db.commit()
            self.db.refresh(nova_importacao)

            # Recalcula e persiste a tabela consolidada de scores por cliente
            try:
                self.recalcular_scores_clientes(id_importacao=id_importacao)
            except Exception as e_score:
                logger.exception("Aviso: erro ao recalcular scores das matrizes: %s", str(e_score))

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.exception("Erro ao persistir registros de PrevisaoTitulosLiquidados: %s", str(e))
            raise HTTPException(status_code=500, detail=f"Erro ao salvar registros no banco de dados: {str(e)}")

        msg = f"Planilha de Títulos Liquidados importada com sucesso: {total_registros} novos registros inseridos"
        if total_ignorados_duplicados > 0:
            msg += f" ({total_ignorados_duplicados} já existentes foram ignorados)"
        msg += " e scores recalculados."

        return {
            "sucesso": True,
            "mensagem": msg,
            "idImportacoes": id_importacao,
            "nomeArquivo": filename,
            "totalRegistros": total_registros,
            "totalIgnorados": total_ignorados_duplicados,
            "totalValor": float(total_valor_somado)
        }

    def recalcular_scores_clientes(self, id_importacao: Optional[int] = None) -> int:
        """
        Calcula e persiste o score ponderado de 100% consolidado por MATRIZ
        com base no histórico de todos os títulos em 'previsao_titulos_liquidados'.
        
        Composição do Score (Total: 100%):
          1. Últimos 5 títulos da Matriz (Peso: 50%): Proporcional à pontualidade recente
          2. Recorrência / Histórico da Matriz (Peso: 40%): 40 pontos para Matriz com histórico (0 para nova)
          3. Média Geral Histórica da Matriz (Peso: 10%):
             - BOM   (>= 80% pontualidade): 10 pontos
             - MÉDIO (50% a 79% pontualidade): 5 pontos
             - RUIM  (< 50% pontualidade): 0 pontos
        """
        rows = self.db.execute(text("""
            SELECT 
                COALESCE(c.idMatriz, CAST(ptl.cliente AS SIGNED)) as id_matriz,
                COALESCE(m.codigo, ptl.cliente) as cod_matriz,
                COALESCE(m.nome, ptl.nome_cliente, 'Matriz') as nome_matriz,
                ptl.cliente, 
                ptl.nome_cliente,
                ptl.titulo, 
                ptl.parcela, 
                ptl.data_vencimento, 
                ptl.liquidacao, 
                ptl.data_credito, 
                ptl.val_movimento, 
                ptl.valor_liquido
            FROM previsao_titulos_liquidados ptl
            LEFT JOIN clientes c ON c.codigo = CAST(ptl.cliente AS SIGNED)
            LEFT JOIN matrizcliente m ON m.idmatrizCliente = c.idMatriz
            WHERE ptl.cliente IS NOT NULL AND TRIM(ptl.cliente) != ''
            ORDER BY COALESCE(c.idMatriz, CAST(ptl.cliente AS SIGNED)), COALESCE(ptl.liquidacao, ptl.data_credito, ptl.data_vencimento) DESC
        """)).fetchall()

        from collections import defaultdict
        por_matriz = defaultdict(list)
        matriz_info = {}

        for r in rows:
            m_id = int(r.id_matriz) if r.id_matriz is not None else 0
            if m_id not in matriz_info:
                matriz_info[m_id] = {
                    "codigoMatriz": str(r.cod_matriz or r.cliente or ""),
                    "nomeMatriz": str(r.nome_matriz or r.nome_cliente or "Matriz")
                }
            por_matriz[m_id].append(r)

        scores_batch = []
        for m_id, titulos in por_matriz.items():
            info = matriz_info[m_id]
            cod_matriz = info["codigoMatriz"]
            nome_matriz = info["nomeMatriz"]
            total_hist = len(titulos)

            # 1. Recorrência / Histórico (40 pts)
            pontos_rec = 40.0 if total_hist > 0 else 0.0

            # 2. Últimos 5 títulos da Matriz (50 pts)
            ultimos_5 = titulos[:5]
            u5_total = len(ultimos_5)
            u5_em_dia = 0
            for t in ultimos_5:
                dt_v = t.data_vencimento
                dt_p = t.liquidacao or t.data_credito
                if dt_v and dt_p:
                    if (dt_p - dt_v).days <= 0:
                        u5_em_dia += 1
                else:
                    u5_em_dia += 1

            pontos_u5 = round((u5_em_dia / u5_total) * 50.0, 2) if u5_total > 0 else 0.0

            # 3. Média geral histórica da Matriz (10 pts)
            total_em_dia = 0
            total_atraso = 0
            soma_dias_atraso = 0
            valor_total = 0.0
            for t in titulos:
                dt_v = t.data_vencimento
                dt_p = t.liquidacao or t.data_credito
                vlr = float(t.valor_liquido or t.val_movimento or 0.0)
                valor_total += vlr
                if dt_v and dt_p:
                    dias = (dt_p - dt_v).days
                    if dias > 0:
                        total_atraso += 1
                        soma_dias_atraso += dias
                    else:
                        total_em_dia += 1
                else:
                    total_em_dia += 1

            taxa_pontualidade = (total_em_dia / total_hist) * 100.0 if total_hist > 0 else 100.0
            if taxa_pontualidade >= 80.0:
                pontos_media = 10.0
                classif = "BOM"
            elif taxa_pontualidade >= 50.0:
                pontos_media = 5.0
                classif = "MEDIO"
            else:
                pontos_media = 0.0
                classif = "RUIM"

            score_final = min(100.0, max(0.0, round(pontos_u5 + pontos_rec + pontos_media, 2)))
            media_dias = round(soma_dias_atraso / total_atraso, 1) if total_atraso > 0 else 0.0

            scores_batch.append({
                "id_matriz": m_id,
                "codigo_matriz": cod_matriz,
                "nome_matriz": nome_matriz,
                "cliente": cod_matriz,
                "nome_cliente": nome_matriz,
                "score_final": score_final,
                "pontos_ultimos_5": pontos_u5,
                "pontos_recorrencia": pontos_rec,
                "pontos_media_geral": pontos_media,
                "classificacao_media": classif,
                "total_titulos_historico": total_hist,
                "titulos_em_dia": total_em_dia,
                "titulos_em_atraso": total_atraso,
                "media_dias_atraso": media_dias,
                "valor_total_liquidado": round(valor_total, 2),
                "ultimos_5_em_dia": u5_em_dia,
                "ultimos_5_total": u5_total,
                "idImportacoes": id_importacao
            })

        if scores_batch:
            self.db.execute(text("DELETE FROM previsao_cliente_score"))
            self.db.bulk_insert_mappings(PrevisaoClienteScore, scores_batch)
            self.db.commit()

        return len(scores_batch)

    def get_visao_geral(self, data_ref: Optional[date] = None) -> Dict[str, Any]:
        """
        Retorna os dados consolidados do painel Visão Geral de Previsão de Caixa.
        Primeira parte: Contas a Pagar (APB) classificadas em Provisão, Banco do Brasil e Itaú.
        Segunda parte: Contas a Receber (ACR) agrupadas por Matriz em Carteira e Boleto.
        Sempre traz a posição da data atual (ou mais recente disponível se o dia ainda não tiver registros).
        """
        hoje = date.today()
        if not data_ref:
            tem_hoje = self.db.query(VwPrevisaoApb.id).filter(VwPrevisaoApb.data == hoje).first()
            data_consulta = hoje if tem_hoje else (self.db.query(func.max(VwPrevisaoApb.data)).scalar() or hoje)
        else:
            data_consulta = data_ref

        titulos_apb = (
            self.db.query(
                VwPrevisaoApb,
                Cliente.codigo.label("cliente_codigo"),
                Cliente.nome.label("cliente_nome"),
                MatrizCliente.idmatrizCliente.label("id_matriz"),
                MatrizCliente.codigo.label("codigo_matriz"),
                MatrizCliente.nome.label("nome_matriz")
            )
            .outerjoin(Cliente, Cliente.codigo == cast(VwPrevisaoApb.numero_fornecedor, Integer))
            .outerjoin(MatrizCliente, MatrizCliente.idmatrizCliente == Cliente.idMatriz)
            .filter(VwPrevisaoApb.data == data_consulta)
            .order_by(VwPrevisaoApb.valor.desc())
            .all()
        )

        contas_bb = []
        contas_itau = []
        contas_provisao = []

        total_provisao = 0.0
        total_bb = 0.0
        total_itau = 0.0

        grupos_matriz: Dict[tuple, Dict[str, Any]] = {}

        for row in titulos_apb:
            t, c_cod, c_nome, m_id, m_cod, m_nome = row
            vlr = float(t.valor or 0.0)
            fav = (t.nome_emitente or t.nome_abrev or "Não informado").strip()
            cat = (t.cod_tp_fluxo or t.esp or "").strip()
            desc = (t.trans or t.modulo or "Despesa").strip()
            doc = f"{t.n_titulo or ''}/{t.parcela or ''}".strip('/')
            dt_venc = t.data.strftime("%d/%m/%Y") if t.data else ""

            id_matriz = m_id
            cod_matriz = m_cod
            nome_matriz = m_nome or fav
            if not cod_matriz:
                cod_matriz = t.nome_abrev or fav

            cli_cod = c_cod or (int(t.numero_fornecedor) if (t.numero_fornecedor and t.numero_fornecedor.isdigit()) else None)
            cli_nome = c_nome or fav

            item_dto = {
                "id": t.id,
                "banco": t.banco_destino or "ITAU",
                "favorecido": fav,
                "categoria": cat,
                "descricao": desc,
                "valor": vlr,
                "dataVencimento": dt_venc,
                "tipo": t.tipo_conta or "REAL",
                "status": "PROGRAMADO",
                "numeroDocumento": doc,
                "idMatriz": id_matriz,
                "codigoMatriz": cod_matriz,
                "nomeMatriz": nome_matriz,
                "clienteCodigo": cli_cod,
                "clienteNome": cli_nome
            }

            if t.banco_destino == 'PROVISAO' or t.tipo_conta == 'PROVISAO':
                contas_provisao.append(item_dto)
                total_provisao += vlr
            elif t.banco_destino == 'BANCO_DO_BRASIL':
                contas_bb.append(item_dto)
                total_bb += vlr
            else:
                contas_itau.append(item_dto)
                total_itau += vlr

            chave_matriz = (id_matriz, cod_matriz, nome_matriz, t.banco_destino or "ITAU", t.tipo_conta or "REAL")
            if chave_matriz not in grupos_matriz:
                grupos_matriz[chave_matriz] = {
                    "idMatriz": id_matriz,
                    "codigoMatriz": cod_matriz,
                    "nomeMatriz": nome_matriz,
                    "banco": t.banco_destino or "ITAU",
                    "tipo": t.tipo_conta or "REAL",
                    "valorTotal": 0.0,
                    "qtdTitulos": 0,
                    "titulos": []
                }
            grupos_matriz[chave_matriz]["valorTotal"] = round(grupos_matriz[chave_matriz]["valorTotal"] + vlr, 2)
            grupos_matriz[chave_matriz]["qtdTitulos"] += 1
            grupos_matriz[chave_matriz]["titulos"].append({
                "id": t.id,
                "numeroDocumento": doc,
                "valor": vlr,
                "clienteCodigo": cli_cod,
                "clienteNome": cli_nome,
                "dataVencimento": dt_venc,
                "banco": t.banco_destino or "ITAU",
                "categoria": cat,
                "descricao": desc
            })

        matrizes_agrupadas = sorted(grupos_matriz.values(), key=lambda x: x["valorTotal"], reverse=True)

        total_pagar_real = total_bb + total_itau
        qtd_pagar_real = len(contas_bb) + len(contas_itau)
        qtd_provisoes = len(contas_provisao)

        # Contas a Receber a partir da view vw_previsao_acr agrupadas por Matriz
        contas_receber: List[Dict[str, Any]] = []
        grupos_receber_matriz: Dict[tuple, Dict[str, Any]] = {}
        total_receber_carteira = 0.0
        total_receber_boleto = 0.0
        receber_menor_igual_80 = 0.0
        receber_maior_80 = 0.0
        receber_ponderado = 0.0

        try:
            titulos_acr = self.db.execute(text("""
                SELECT 
                    acr.id, 
                    acr.esp, 
                    acr.ser, 
                    acr.titulo, 
                    acr.parcela, 
                    acr.modalidade, 
                    acr.cliente as cliente_codigo, 
                    acr.nome_cliente, 
                    acr.vencto, 
                    acr.saldo,
                    c.idMatriz as id_matriz,
                    m.codigo as codigo_matriz,
                    m.nome as nome_matriz
                FROM vw_previsao_acr acr
                LEFT JOIN clientes c ON c.codigo = CAST(acr.cliente AS SIGNED)
                LEFT JOIN matrizcliente m ON m.idmatrizCliente = c.idMatriz
                ORDER BY acr.saldo DESC
            """)).fetchall()

            # Lista única de id_matriz presentes nos títulos a receber
            ids_matrizes = list(set([
                int(r.id_matriz) for r in titulos_acr 
                if r.id_matriz is not None
            ]))

            historico_map: Dict[int, Dict[str, Any]] = {}

            if ids_matrizes:
                # 1. Carrega os scores consolidados da tabela previsao_cliente_score por id_matriz
                score_rows = (
                    self.db.query(PrevisaoClienteScore)
                    .filter(PrevisaoClienteScore.id_matriz.in_(ids_matrizes))
                    .all()
                )
                score_map = {s.id_matriz: s for s in score_rows}

                # 2. Carrega até 5 títulos recentes de cada matriz para o modal de histórico
                format_ids = ", ".join(str(i) for i in ids_matrizes)
                liq_rows = self.db.execute(text(f"""
                    SELECT 
                        c.idMatriz as id_matriz,
                        ptl.cliente, 
                        ptl.titulo, 
                        ptl.parcela, 
                        ptl.data_vencimento, 
                        ptl.liquidacao, 
                        ptl.data_credito, 
                        ptl.val_movimento, 
                        ptl.valor_liquido
                    FROM previsao_titulos_liquidados ptl
                    JOIN clientes c ON c.codigo = CAST(ptl.cliente AS SIGNED)
                    WHERE c.idMatriz IN ({format_ids})
                    ORDER BY c.idMatriz, COALESCE(ptl.liquidacao, ptl.data_credito, ptl.data_vencimento) DESC
                """)).fetchall()

                from collections import defaultdict
                lancamentos_map = defaultdict(list)
                for lr in liq_rows:
                    m_key = int(lr.id_matriz)
                    if len(lancamentos_map[m_key]) < 5:
                        dt_v = lr.data_vencimento
                        dt_p = lr.liquidacao or lr.data_credito
                        vlr = float(lr.valor_liquido or lr.val_movimento or 0.0)
                        dias = (dt_p - dt_v).days if dt_p and dt_v else 0
                        is_atrasado = dias > 0
                        lancamentos_map[m_key].append({
                            "titulo": f"NF {lr.titulo}/{lr.parcela}".strip('/'),
                            "valor": round(vlr, 2),
                            "dataVencimento": dt_v.strftime("%d/%m/%Y") if dt_v else "",
                            "dataPagamento": dt_p.strftime("%d/%m/%Y") if dt_p else "",
                            "diasAtraso": max(0, dias),
                            "status": "ATRASADO" if is_atrasado else "EM_DIA"
                        })

                # Monta historico_map usando a tabela previsao_cliente_score por matriz
                for m_id in ids_matrizes:
                    s = score_map.get(m_id)
                    if s:
                        score_val = float(s.score_final)
                        total_h = s.total_titulos_historico
                        taxa_p = round((s.titulos_em_dia / total_h) * 100) if total_h > 0 else 85
                        if score_val >= 90:
                            classif = f"Excelente ({score_val:.0f}%)"
                        elif score_val >= 80:
                            classif = f"Bom ({score_val:.0f}%)"
                        elif score_val >= 70:
                            classif = f"Regular ({score_val:.0f}%)"
                        else:
                            classif = f"Atenção ({score_val:.0f}%)"

                        historico_map[m_id] = {
                            "idMatriz": m_id,
                            "codigoMatriz": s.codigo_matriz or "",
                            "nomeMatriz": s.nome_matriz or "",
                            "score": round(score_val),
                            "classificacao": classif,
                            "isNovo": False,
                            "titulosEmDia": s.titulos_em_dia,
                            "titulosEmAtraso": s.titulos_em_atraso,
                            "percentualPontualidade": taxa_p,
                            "mediaDiasAtraso": float(s.media_dias_atraso),
                            "valorTotalPago": float(s.valor_total_liquidado),
                            "lancamentos": lancamentos_map.get(m_id, [])
                        }
                    else:
                        # Matriz Nova (Sem Histórico): score 0% para projeção conservadora de fluxo de caixa
                        historico_map[m_id] = {
                            "idMatriz": m_id,
                            "codigoMatriz": "",
                            "nomeMatriz": "",
                            "score": 0,
                            "classificacao": "Sem Histórico (0%)",
                            "isNovo": True,
                            "titulosEmDia": 0,
                            "titulosEmAtraso": 0,
                            "percentualPontualidade": 0,
                            "mediaDiasAtraso": 0.0,
                            "valorTotalPago": 0.0,
                            "lancamentos": []
                        }

            for r in titulos_acr:
                m_id = int(r.id_matriz) if r.id_matriz is not None else (int(r.cliente_codigo) if (r.cliente_codigo and str(r.cliente_codigo).isdigit()) else 0)
                cod_m = (r.codigo_matriz or str(r.cliente_codigo or "")).strip()
                nome_m = (r.nome_matriz or r.nome_cliente or "Cliente").strip()
                mod = (r.modalidade or "BOLETO").strip().upper()
                vlr = float(r.saldo or 0.0)
                doc = f"{r.titulo or ''}/{r.parcela or ''}".strip('/')
                dt_v = r.vencto.strftime("%d/%m/%Y") if r.vencto else ""

                hist = historico_map.get(m_id, {
                    "idMatriz": m_id,
                    "codigoMatriz": cod_m,
                    "nomeMatriz": nome_m,
                    "score": 0,
                    "classificacao": "Sem Histórico (0%)",
                    "isNovo": True,
                    "titulosEmDia": 0,
                    "titulosEmAtraso": 0,
                    "percentualPontualidade": 0,
                    "mediaDiasAtraso": 0.0,
                    "valorTotalPago": 0.0,
                    "lancamentos": []
                })
                hist["idMatriz"] = m_id
                hist["codigoMatriz"] = cod_m
                hist["nomeMatriz"] = nome_m
                v_score = hist.get("score", 0)

                # Objeto individual do título para manter retrocompatibilidade
                item = {
                    "id": str(r.id),
                    "modalidade": mod,
                    "clienteCodigo": str(r.cliente_codigo or ""),
                    "clienteNome": (r.nome_cliente or "").strip(),
                    "idMatriz": m_id,
                    "codigoMatriz": cod_m,
                    "nomeMatriz": nome_m,
                    "documento": doc,
                    "valor": round(vlr, 2),
                    "dataVencimento": dt_v,
                    "score": v_score,
                    "isNovo": hist.get("isNovo", False),
                    "historico": hist
                }
                contas_receber.append(item)

                # Agrupamento por Matriz e Modalidade (Carteira ou Boleto)
                chave_m = (m_id, cod_m, nome_m, mod)
                if chave_m not in grupos_receber_matriz:
                    grupos_receber_matriz[chave_m] = {
                        "idMatriz": m_id,
                        "codigoMatriz": cod_m,
                        "nomeMatriz": nome_m,
                        "modalidade": mod,
                        "valorTotal": 0.0,
                        "qtdTitulos": 0,
                        "score": v_score,
                        "classificacao": hist.get("classificacao", ""),
                        "isNovo": hist.get("isNovo", False),
                        "titulosEmDia": hist.get("titulosEmDia", 0),
                        "titulosEmAtraso": hist.get("titulosEmAtraso", 0),
                        "percentualPontualidade": hist.get("percentualPontualidade", 0),
                        "mediaDiasAtraso": hist.get("mediaDiasAtraso", 0.0),
                        "valorTotalPago": hist.get("valorTotalPago", 0.0),
                        "titulos": [],
                        "lancamentos": hist.get("lancamentos", [])
                    }

                grupos_receber_matriz[chave_m]["valorTotal"] = round(grupos_receber_matriz[chave_m]["valorTotal"] + vlr, 2)
                grupos_receber_matriz[chave_m]["qtdTitulos"] += 1
                grupos_receber_matriz[chave_m]["titulos"].append({
                    "id": str(r.id),
                    "numeroDocumento": doc,
                    "valor": round(vlr, 2),
                    "clienteCodigo": str(r.cliente_codigo or ""),
                    "clienteNome": (r.nome_cliente or "").strip(),
                    "dataVencimento": dt_v,
                    "modalidade": mod
                })

                if mod == "CARTEIRA":
                    total_receber_carteira += vlr
                else:
                    total_receber_boleto += vlr

                if v_score <= 80:
                    receber_menor_igual_80 += vlr
                else:
                    receber_maior_80 += vlr

                receber_ponderado += vlr * (v_score / 100.0)

        except Exception as e:
            logger.exception("Erro ao carregar contas a receber de vw_previsao_acr: %s", str(e))

        matrizes_receber_agrupadas = sorted(grupos_receber_matriz.values(), key=lambda x: x["valorTotal"], reverse=True)
        matrizes_carteira = [m for m in matrizes_receber_agrupadas if m["modalidade"] == "CARTEIRA"]
        matrizes_boleto = [m for m in matrizes_receber_agrupadas if m["modalidade"] == "BOLETO"]

        total_receber = total_receber_carteira + total_receber_boleto
        qtd_receber = len(contas_receber)

        saldo_previsibilidade = receber_ponderado - total_pagar_real
        saldo_real_nominal = total_receber - total_pagar_real

        return {
            "data_referencia": data_consulta.strftime("%Y-%m-%d"),
            "data_formatada": data_consulta.strftime("%d/%m/%Y"),
            "is_hoje": data_consulta == hoje,
            "total_provisao": round(total_provisao, 2),
            "qtd_provisoes": qtd_provisoes,
            "total_pagar": round(total_pagar_real, 2),
            "qtd_pagar_real": qtd_pagar_real,
            "total_bb": round(total_bb, 2),
            "total_itau": round(total_itau, 2),
            "contas_bb": contas_bb,
            "contas_itau": contas_itau,
            "contas_provisao": contas_provisao,
            "matrizes_agrupadas": matrizes_agrupadas,
            "matrizes_receber": matrizes_receber_agrupadas,
            "matrizes_carteira": matrizes_carteira,
            "matrizes_boleto": matrizes_boleto,
            "total_receber": round(total_receber, 2),
            "qtd_receber": qtd_receber,
            "total_receber_carteira": round(total_receber_carteira, 2),
            "total_receber_boleto": round(total_receber_boleto, 2),
            "receber_menor_igual_80": round(receber_menor_igual_80, 2),
            "receber_maior_80": round(receber_maior_80, 2),
            "saldo_previsibilidade": round(saldo_previsibilidade, 2),
            "saldo_real_nominal": round(saldo_real_nominal, 2),
            "valor_investido_resgatavel": 0.0,
            "contas_receber": contas_receber
        }

