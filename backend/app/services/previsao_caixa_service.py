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

        registros_batch: List[Dict[str, Any]] = []
        total_registros = 0
        total_valor_somado = Decimal("0.00")
        BATCH_SIZE = 5000

        try:
            for row in rows_iter:
                if not row or all(v is None for v in row):
                    continue

                def col(idx: int) -> Any:
                    return row[idx] if idx < len(row) else None

                val_mov = self._parse_decimal(col(22))
                val_liq = self._parse_decimal(col(26))
                val_orig = self._parse_decimal(col(37))

                if val_mov:
                    total_valor_somado += val_mov
                elif val_liq:
                    total_valor_somado += val_liq
                elif val_orig:
                    total_valor_somado += val_orig

                reg = {
                    "estabelecimento": self._parse_str(col(0), 20),
                    "especie_documento": self._parse_str(col(1), 20),
                    "serie_documento": self._parse_str(col(2), 20),
                    "titulo": self._parse_str(col(3), 50),
                    "parcela": self._parse_str(col(4), 20),
                    "cliente": self._parse_str(col(5), 50),
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
                    "liquidacao": self._parse_data(col(29)),
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
                raise HTTPException(status_code=400, detail="Nenhum registro válido foi encontrado na planilha de Títulos Liquidados.")

            self.db.commit()
            self.db.refresh(nova_importacao)

        except Exception as e:
            self.db.rollback()
            logger.exception("Erro ao persistir registros de PrevisaoTitulosLiquidados: %s", str(e))
            raise HTTPException(status_code=500, detail=f"Erro ao salvar registros no banco de dados: {str(e)}")

        return {
            "sucesso": True,
            "mensagem": f"Planilha de Títulos Liquidados importada com sucesso ({total_registros} registros inseridos).",
            "idImportacoes": id_importacao,
            "nomeArquivo": filename,
            "totalRegistros": total_registros,
            "totalValor": float(total_valor_somado)
        }

    def get_visao_geral(self, data_ref: Optional[date] = None) -> Dict[str, Any]:
        """
        Retorna os dados consolidados do painel Visão Geral de Previsão de Caixa.
        Primeira parte: Contas a Pagar (APB) classificadas em Provisão, Banco do Brasil e Itaú.
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

        # Contas a Receber a partir da view vw_previsao_acr
        contas_receber: List[Dict[str, Any]] = []
        total_receber_carteira = 0.0
        total_receber_boleto = 0.0
        receber_menor_igual_80 = 0.0
        receber_maior_80 = 0.0
        receber_ponderado = 0.0

        try:
            titulos_acr = self.db.execute(text("""
                SELECT 
                    id, esp, ser, titulo, parcela, modalidade, cliente, nome_cliente, vencto, saldo
                FROM vw_previsao_acr
                ORDER BY saldo DESC
            """)).fetchall()

            codigos_clientes = list(set([str(r.cliente).strip() for r in titulos_acr if r.cliente]))
            historico_map: Dict[str, Dict[str, Any]] = {}

            if codigos_clientes:
                format_cli = "', '".join(codigos_clientes)
                liq_rows = self.db.execute(text(f"""
                    SELECT 
                        cliente, 
                        titulo, 
                        parcela, 
                        data_vencimento, 
                        liquidacao, 
                        data_credito, 
                        val_movimento, 
                        valor_liquido
                    FROM previsao_titulos_liquidados
                    WHERE cliente IN ('{format_cli}')
                    ORDER BY liquidacao DESC
                """)).fetchall()

                from collections import defaultdict
                por_cli = defaultdict(list)
                for lr in liq_rows:
                    por_cli[str(lr.cliente).strip()].append(lr)

                for c_cod, l_list in por_cli.items():
                    em_dia = 0
                    atraso = 0
                    soma_dias_atraso = 0
                    valor_total_pago = 0.0
                    lancamentos = []

                    for row in l_list:
                        dt_v = row.data_vencimento
                        dt_p = row.liquidacao or row.data_credito
                        vlr = float(row.valor_liquido or row.val_movimento or 0.0)
                        valor_total_pago += vlr

                        dias = (dt_p - dt_v).days if dt_p and dt_v else 0
                        is_atrasado = dias > 0
                        if is_atrasado:
                            atraso += 1
                            soma_dias_atraso += dias
                        else:
                            em_dia += 1

                        if len(lancamentos) < 5:
                            lancamentos.append({
                                "titulo": f"NF {row.titulo}/{row.parcela}".strip('/'),
                                "valor": round(vlr, 2),
                                "dataVencimento": dt_v.strftime("%d/%m/%Y") if dt_v else "",
                                "dataPagamento": dt_p.strftime("%d/%m/%Y") if dt_p else "",
                                "diasAtraso": max(0, dias),
                                "status": "ATRASADO" if is_atrasado else "EM_DIA"
                            })

                    total_t = em_dia + atraso
                    score = round((em_dia / total_t) * 100) if total_t > 0 else 85
                    media_dias = round(soma_dias_atraso / atraso, 1) if atraso > 0 else 0.0

                    if score >= 90:
                        classif = "Excelente (Altíssima Previsibilidade)"
                    elif score >= 80:
                        classif = "Bom (Alta Previsibilidade)"
                    elif score >= 70:
                        classif = "Regular (Previsibilidade Média)"
                    else:
                        classif = "Atenção (Baixa Previsibilidade)"

                    historico_map[c_cod] = {
                        "score": score,
                        "classificacao": classif,
                        "titulosEmDia": em_dia,
                        "titulosEmAtraso": atraso,
                        "percentualPontualidade": score,
                        "mediaDiasAtraso": media_dias,
                        "valorTotalPago": round(valor_total_pago, 2),
                        "lancamentos": lancamentos
                    }

            for r in titulos_acr:
                c_cod = str(r.cliente).strip() if r.cliente else ""
                c_nome = (r.nome_cliente or 'Cliente').strip()
                hist = historico_map.get(c_cod, {
                    "clienteCodigo": c_cod,
                    "clienteNome": c_nome,
                    "score": 85,
                    "classificacao": "Bom (Padrão)",
                    "titulosEmDia": 0,
                    "titulosEmAtraso": 0,
                    "percentualPontualidade": 85,
                    "mediaDiasAtraso": 0,
                    "valorTotalPago": 0.0,
                    "lancamentos": []
                })
                hist["clienteCodigo"] = c_cod
                hist["clienteNome"] = c_nome

                v_val = float(r.saldo or 0.0)
                v_score = hist.get("score", 85)

                item = {
                    "id": str(r.id),
                    "modalidade": r.modalidade or "BOLETO",
                    "clienteCodigo": c_cod,
                    "clienteNome": c_nome,
                    "documento": f"{r.titulo}/{r.parcela}".strip('/'),
                    "valor": round(v_val, 2),
                    "dataVencimento": r.vencto.strftime("%d/%m/%Y") if r.vencto else "",
                    "score": v_score,
                    "historico": hist
                }
                contas_receber.append(item)

                if item["modalidade"] == "CARTEIRA":
                    total_receber_carteira += v_val
                else:
                    total_receber_boleto += v_val

                if v_score <= 80:
                    receber_menor_igual_80 += v_val
                else:
                    receber_maior_80 += v_val

                receber_ponderado += v_val * (v_score / 100.0)

        except Exception as e:
            logger.exception("Erro ao carregar contas a receber de vw_previsao_acr: %s", str(e))

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

