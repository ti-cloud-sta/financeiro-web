from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from fastapi import UploadFile
from datetime import datetime
import pandas as pd
import io
from app.models.movimentacao import Movimentacao
from app.models.importacao import Importacao
from app.models.colaborador import Colaborador
from app.models.colaborador_unidade import ColaboradorUnidade
from app.models.empresa import Empresa
from app.models.unidade import Unidade
from app.models.centro_custo import CentroCusto
from app.schemas.plano_saude import RelatorioGeralResponse, RelatorioGeralRow, ConciliacaoResponse, ConciliacaoRow

class PlanoSaudeService:
    def __init__(self, db: Session):
        self.db = db

    def obter_relatorio_geral(self, mes: int, ano: int, search: str = None, id_empresa: int = None, page: int = 1, size: int = 10) -> RelatorioGeralResponse:
        # Soma por colaborador/empresa isolada da junção de Unidade: um colaborador pode
        # ter mais de uma Unidade (relação N:N via ColaboradorUnidade), e juntar Unidade
        # direto nesta soma duplicaria/multiplicaria o valor da Movimentacao para quem
        # tem mais de uma unidade.
        sub = self.db.query(
            Movimentacao.idColaborador.label("id_colaborador"),
            Movimentacao.idEmpresa.label("id_empresa"),
            func.sum(Movimentacao.valor).label("total")
        ).join(
            Importacao, Importacao.idImportacoes == Movimentacao.idImportacoes
        ).filter(
            Importacao.tipo.in_(["PLANO_SAUDE", "SEGURO"]),
            extract('year', Movimentacao.createdAt) == ano,
            extract('month', Movimentacao.createdAt) == mes
        )
        if id_empresa:
            sub = sub.filter(Movimentacao.idEmpresa == id_empresa)
        sub = sub.group_by(Movimentacao.idColaborador, Movimentacao.idEmpresa).subquery()

        # A partir da soma já correta acima, junta Colaborador/Empresa/CentroCusto e, só
        # para exibição/filtro, as Unidades agregadas com GROUP_CONCAT (func.max no total
        # porque ele já é um valor único por colaborador — não deve ser somado de novo).
        query = self.db.query(
            func.group_concat(func.distinct(Unidade.codigo)).label("unidade_codigo"),
            Empresa.nome.label("empresa_nome"),
            Colaborador.nome.label("colaborador_nome"),
            CentroCusto.codigo.label("centro_custo_codigo"),
            func.max(sub.c.total).label("total")
        ).select_from(sub).join(
            Colaborador, Colaborador.idColaborador == sub.c.id_colaborador
        ).join(
            Empresa, Empresa.idEmpresas == sub.c.id_empresa
        ).outerjoin(
            ColaboradorUnidade, ColaboradorUnidade.idColaborador == Colaborador.idColaborador
        ).outerjoin(
            Unidade, Unidade.idUnidade == ColaboradorUnidade.idUnidade
        ).join(
            CentroCusto, CentroCusto.idCentroCusto == Colaborador.idCentroCusto
        )

        if search:
            search_str = f"%{search}%"
            query = query.filter(
                (Colaborador.nome.ilike(search_str)) |
                (Empresa.nome.ilike(search_str)) |
                (Unidade.descricao.ilike(search_str))
            )

        query = query.group_by(
            Colaborador.idColaborador,
            Empresa.nome,
            CentroCusto.codigo,
            Colaborador.nome
        ).order_by(Empresa.nome, Colaborador.nome)

        # Volume tratável em memória (limitado ao nº de colaboradores/empresa filtrados),
        # então paginamos e somamos o total geral em Python a partir do mesmo resultado —
        # evita manter duas queries quase idênticas divergindo com o tempo.
        todos = query.all()
        total_items = len(todos)

        offset = (page - 1) * size
        results = todos[offset:offset + size]

        items = []
        comp_str = f"{mes:02d}/{ano}"
        for r in results:
            items.append(RelatorioGeralRow(
                competencia=comp_str,
                unidade=r.unidade_codigo,
                empresa=r.empresa_nome,
                nome=r.colaborador_nome,
                centro_custo=str(r.centro_custo_codigo) if r.centro_custo_codigo is not None else None,
                total=r.total or 0.0
            ))

        total_valor_scalar = sum(float(r.total or 0.0) for r in todos)

        return RelatorioGeralResponse(
            items=items,
            total=total_items,
            total_valor=total_valor_scalar,
            page=page,
            size=size
        )

    def exportar_relatorio_geral(self, mes: int, ano: int, search: str = None, id_empresa: int = None):
        import pandas as pd
        import io
        from fastapi.responses import StreamingResponse

        # Get all data without pagination
        res = self.obter_relatorio_geral(mes, ano, search, id_empresa, page=1, size=999999)
        
        data = []
        for r in res.items:
            data.append({
                "Competência": r.competencia,
                "Unidade": r.unidade or "N/D",
                "Empresa": r.empresa,
                "Nome": r.nome,
                "Centro de Custo": r.centro_custo or "N/D",
                "Total (R$)": r.total
            })
            
        df = pd.DataFrame(data)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Relatório Geral')
            worksheet = writer.sheets['Relatório Geral']
            
            # Basic formatting: auto-adjust columns
            for idx, col in enumerate(df.columns):
                series = df[col]
                max_len = max((
                    series.astype(str).map(len).max(),
                    len(str(col))
                )) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_len, 50)
                
        output.seek(0)
        
        filename = f"relatorio_geral_planosaude_{mes:02d}_{ano}.xlsx"
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )

    # Empresas cujo template da coluna O inclui o nome da empresa no "PAGTO DOC"
    _CONTABILIDADE_EMPRESAS_COM_NOME = {29, 23, 22}
    # Empresas cujo template da coluna O deixa o "PAGTO DOC" em branco
    _CONTABILIDADE_EMPRESAS_SEM_NOME = {30, 28, 21, 25}
    # Conta contábil (coluna U): idEmpresas 23 usa uma conta especial, as demais usam a padrão
    _CONTABILIDADE_CONTA_ESPECIAL = {23: "31201003"}
    _CONTABILIDADE_CONTA_PADRAO = "31201005"

    @staticmethod
    def _fmt_valor_contabilidade(valor: float) -> str:
        """Formata em padrão BR (vírgula decimal, ponto de milhar), preservando o sinal."""
        sinal = "-" if valor < 0 else ""
        s = f"{abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{sinal}{s}"

    def _montar_linhas_contabilidade(self, mes: int, ano: int, search: str = None, id_empresa: int = None):
        """Monta as linhas do relatório de Contabilidade (uma por Empresa + Centro de
        Custo + Unidade), já com os 23 valores lógicos das colunas A-W calculados —
        consumido tanto pela exportação em CSV quanto na de largura fixa (.txt)."""
        import calendar

        query = self.db.query(
            Empresa.idEmpresas.label("id_empresa"),
            Empresa.nome.label("empresa_nome"),
            Empresa.tipo.label("empresa_tipo"),
            CentroCusto.codigo.label("cc_codigo"),
            Unidade.codigo.label("unidade_codigo"),
            func.sum(Movimentacao.valor).label("total")
        ).join(
            Importacao, Importacao.idImportacoes == Movimentacao.idImportacoes
        ).join(
            Colaborador, Colaborador.idColaborador == Movimentacao.idColaborador
        ).join(
            Empresa, Empresa.idEmpresas == Movimentacao.idEmpresa
        ).join(
            CentroCusto, CentroCusto.idCentroCusto == Colaborador.idCentroCusto
        ).join(
            ColaboradorUnidade, ColaboradorUnidade.idColaborador == Colaborador.idColaborador
        ).join(
            Unidade, Unidade.idUnidade == ColaboradorUnidade.idUnidade
        ).filter(
            Importacao.tipo.in_(["PLANO_SAUDE", "SEGURO"]),
            extract('year', Movimentacao.createdAt) == ano,
            extract('month', Movimentacao.createdAt) == mes
        )

        if search:
            search_str = f"%{search}%"
            query = query.filter(
                (Colaborador.nome.ilike(search_str)) |
                (Empresa.nome.ilike(search_str)) |
                (Unidade.descricao.ilike(search_str))
            )
        if id_empresa:
            query = query.filter(Movimentacao.idEmpresa == id_empresa)

        query = query.group_by(
            Empresa.idEmpresas, Empresa.nome, Empresa.tipo,
            CentroCusto.codigo, Unidade.codigo
        ).order_by(Empresa.nome, CentroCusto.codigo, Unidade.codigo)

        resultados = query.all()

        ultimo_dia = calendar.monthrange(ano, mes)[1]
        data_str = f"{ultimo_dia:02d}/{mes:02d}/{ano}"
        plano_mes_str = f"PLANO MÊS {mes:02d}/{ano}"

        linhas = []
        for i, r in enumerate(resultados, start=1):
            valor_original = float(r.total or 0.0)
            valor_abs = abs(valor_original)
            tipo_cr_db = "CR" if valor_original >= 0 else "DB"

            nome_empresa = r.empresa_nome or ""
            tipo_empresa = r.empresa_tipo or ""

            pagto_doc_nome = "" if r.id_empresa in self._CONTABILIDADE_EMPRESAS_SEM_NOME else nome_empresa
            # O TOTAL dentro da coluna O usa o valor ORIGINAL (com sinal) e sem separador
            # de milhar, arredondado a 2 casas mas sem zero à direita (ex.: "213,6",
            # "-14,55") — formato diferente do da própria coluna E.
            total_o = round(valor_original, 2)
            total_o_str = str(total_o).replace(".", ",")
            col_o = (
                f"|PAGTO DOC - {pagto_doc_nome}|{tipo_empresa} - {nome_empresa}"
                f"|C CUSTO - {r.cc_codigo}|TOTAL: {total_o_str}|"
            )

            conta = self._CONTABILIDADE_CONTA_ESPECIAL.get(r.id_empresa, self._CONTABILIDADE_CONTA_PADRAO)

            linhas.append({
                "A": "REAL",
                "B": 2 * i - 1,
                "C": 1,
                "D": "FGL",
                "E": self._fmt_valor_contabilidade(valor_abs),
                "F": "GERAL",
                "G": data_str,
                "H": 1,
                "I": tipo_cr_db,
                "J": "",
                "K": r.unidade_codigo,
                "L": plano_mes_str,
                "M": 1,
                "N": 31550109,
                "O": col_o,
                "P": "",
                "Q": "NAO",
                "R": "GERAL",
                "S": r.cc_codigo,
                "T": 19000,
                "U": conta,
                "V": 2 * i,
                "W": r.cc_codigo,
            })
        return linhas

    def gerar_relatorio_contabilidade(self, mes: int, ano: int, search: str = None, id_empresa: int = None):
        import csv
        import io as _io
        from fastapi.responses import StreamingResponse

        linhas = self._montar_linhas_contabilidade(mes, ano, search, id_empresa)

        output = _io.StringIO()
        writer = csv.writer(output, delimiter=';')
        colunas = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
                   "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W"]
        for linha in linhas:
            writer.writerow([linha[c] for c in colunas])

        csv_bytes = output.getvalue().encode('utf-8-sig')
        filename = f"contabilidade_planosaude_{mes:02d}_{ano}.csv"
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
        return StreamingResponse(
            _io.BytesIO(csv_bytes),
            media_type="text/csv",
            headers=headers
        )

    # Layout de largura fixa (colunas A-W), validado byte-a-byte contra um arquivo real
    # de referência (SAUDE JUL26_importar.txt): (largura, alinhamento 'L'/'R').
    _CONTABILIDADE_TXT_LAYOUT = [
        ("A", 8, "L"), ("B", 5, "R"), ("C", 10, "R"), ("D", 3, "L"), ("E", 16, "R"),
        ("F", 8, "L"), ("G", 14, "L"), ("H", 1, "R"), ("I", 2, "L"), ("J", 8, "L"),
        ("K", 3, "R"), ("L", 40, "L"), ("M", 3, "L"), ("N", 20, "L"), ("O", 152, "L"),
        ("Q", 3, "L"), ("R", 5, "L"), ("S", 8, "R"), ("T", 5, "L"), ("U", 8, "L"),
        ("V", 17, "R"), ("W", 5, "R"),
    ]

    def gerar_relatorio_contabilidade_txt(self, mes: int, ano: int, search: str = None, id_empresa: int = None):
        import io as _io
        from fastapi.responses import StreamingResponse

        linhas = self._montar_linhas_contabilidade(mes, ano, search, id_empresa)

        registros = []
        for linha in linhas:
            partes = []
            for nome_col, largura, alinhamento in self._CONTABILIDADE_TXT_LAYOUT:
                valor = str(linha[nome_col])
                campo = valor.rjust(largura) if alinhamento == "R" else valor.ljust(largura)
                partes.append(campo[:largura])
            registros.append("".join(partes))

        texto = "\r\n".join(registros) + "\r\n" if registros else ""
        txt_bytes = texto.encode('latin-1', errors='replace')
        filename = f"contabilidade_planosaude_{mes:02d}_{ano}.txt"
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
        return StreamingResponse(
            _io.BytesIO(txt_bytes),
            media_type="text/plain",
            headers=headers
        )

    def conciliar_planilha(self, file: UploadFile) -> ConciliacaoResponse:
        # Ler a planilha
        contents = file.file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # Encontrar competência (Data Trans)
        data_trans_col = df.get('Data Trans')
        if data_trans_col is None or data_trans_col.empty:
            raise ValueError("Coluna 'Data Trans' não encontrada na planilha.")
            
        val = data_trans_col.dropna().iloc[0]
        if isinstance(val, datetime):
            # Já vem como data/Timestamp (pandas detectou a coluna como data).
            # pd.Timestamp é subclasse de datetime, então cobre os dois.
            primeira_data = pd.to_datetime(val)
        else:
            try:
                # Número serial do Excel (dias desde 1899-12-30) — cobre int, float,
                # numpy.int64/float64 (o que o pandas normalmente entrega aqui).
                primeira_data = pd.to_datetime(float(val), origin='1899-12-30', unit='D')
            except (TypeError, ValueError):
                # Sobrou string em outro formato (ex.: "05/08/2026")
                primeira_data = pd.to_datetime(val)
            
        mes = primeira_data.month
        ano = primeira_data.year
        competencia_str = f"{mes:02d}/{ano}"

        # Agrupar por Estab e somar Débito. Obter também o Nome Abrev se disponível.
        # "Estab" pode vir como int ou str.
        if 'Estab' not in df.columns or 'Débito' not in df.columns:
            raise ValueError("Colunas 'Estab' ou 'Débito' não encontradas na planilha.")
            
        df['Estab_str'] = df['Estab'].astype(str).str.strip().str.lstrip('0') # Normalize
        
        # Agrupa e calcula por Estab e Nome Abrev
        agg_dict = {'Débito': 'sum'}
        group_cols = ['Estab_str']
        if 'Nome Abrev' in df.columns:
            df['Nome_Abrev_str'] = df['Nome Abrev'].astype(str).str.strip().str.upper()
            group_cols.append('Nome_Abrev_str')
            
        planilha_grouped = df.groupby(group_cols).agg(agg_dict).reset_index()

        # Query the database
        db_query = self.db.query(
            Unidade.codigo.label("unidade_codigo"),
            Empresa.nomeAbrev.label("empresa_abrev"),
            func.sum(Movimentacao.valor).label("total_sistema")
        ).join(
            Importacao, Importacao.idImportacoes == Movimentacao.idImportacoes
        ).join(
            Colaborador, Colaborador.idColaborador == Movimentacao.idColaborador
        ).join(
            ColaboradorUnidade, ColaboradorUnidade.idColaborador == Colaborador.idColaborador
        ).join(
            Unidade, Unidade.idUnidade == ColaboradorUnidade.idUnidade
        ).join(
            Empresa, Empresa.idEmpresas == Movimentacao.idEmpresa
        ).filter(
            Importacao.tipo.in_(["PLANO_SAUDE", "SEGURO"]),
            extract('year', Movimentacao.createdAt) == ano,
            extract('month', Movimentacao.createdAt) == mes
        ).group_by(
            Unidade.codigo,
            Empresa.nomeAbrev
        ).all()

        # Convert to dictionary for easy matching: key is (estab, empresa_abrev)
        db_totais = {}
        for r in db_query:
            cod_str = str(r.unidade_codigo).strip().lstrip('0')
            emp_abrev = str(r.empresa_abrev).strip().upper() if r.empresa_abrev else "N/D"
            db_totais[(cod_str, emp_abrev)] = float(r.total_sistema or 0.0)

        # Merge results
        linhas = []
        processados = set()
        divergencias_count = 0

        # Iterar sobre o que veio da planilha
        for _, row in planilha_grouped.iterrows():
            estab = str(row['Estab_str'])
            total_plan = float(row['Débito'])
            abrev = str(row['Nome_Abrev_str']) if 'Nome_Abrev_str' in row else "N/D"
            
            # Key for matching
            match_key = (estab, abrev)
            
            total_sis = db_totais.get(match_key, 0.0)
            diff = abs(total_plan - total_sis)
            
            if match_key not in db_totais:
                status = "NAO_ENCONTRADO_SISTEMA"
                divergencias_count += 1
            elif diff > 0.01:
                status = "DIVERGENTE"
                divergencias_count += 1
            else:
                status = "OK"
                
            linhas.append(ConciliacaoRow(
                unidade_codigo=estab,
                unidade_descricao="",
                empresa_abrev=abrev,
                total_planilha=total_plan,
                total_sistema=total_sis,
                diferenca=total_plan - total_sis,
                status=status
            ))
            processados.add(match_key)
            
        # Verificar chaves que tem no sistema mas não na planilha
        for match_key, total_sis in db_totais.items():
            if match_key not in processados:
                linhas.append(ConciliacaoRow(
                    unidade_codigo=match_key[0],
                    unidade_descricao="",
                    empresa_abrev=match_key[1],
                    total_planilha=0.0,
                    total_sistema=total_sis,
                    diferenca=0.0 - total_sis,
                    status="NAO_ENCONTRADO_PLANILHA"
                ))
                divergencias_count += 1

        linhas.sort(key=lambda x: (x.unidade_codigo, x.empresa_abrev))

        return ConciliacaoResponse(
            competencia=competencia_str,
            linhas=linhas,
            total_divergencias=divergencias_count,
            total_processado=len(linhas)
        )
