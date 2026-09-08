import calendar
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from app.models.movimentacao import Movimentacao
from app.models.colaborador import Colaborador
from app.models.unidade import Unidade
from app.models.categoria import Categoria
from app.models.empresa import Empresa
from app.models.centro_custo import CentroCusto, CentroEstado
from app.models.importacao import Importacao

class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def obter_dados(
        self,
        data_inicio: str = None,
        data_fim: str = None,
        id_empresa: int = None,
        id_colaborador: int = None,
        id_categoria: int = None,
        tipo_importacao: str = None
    ) -> Dict[str, Any]:
        # Formata datas base
        if data_inicio:
            dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        else:
            # 6 meses atrás por padrão
            dt_inicio = datetime.now() - timedelta(days=180)
            dt_inicio = dt_inicio.replace(hour=0, minute=0, second=0, microsecond=0)

        if data_fim:
            dt_fim = datetime.strptime(data_fim, "%Y-%m-%d")
        else:
            dt_fim = datetime.now()

        # Garante incluir o dia inteiro de data_fim
        dt_fim_inclusive = dt_fim + timedelta(days=1)

        # Filtros utilitários
        def apply_filters(q):
            if tipo_importacao:
                tipos = [t.strip() for t in tipo_importacao.split(",")]
                q = q.join(Importacao, Movimentacao.idImportacoes == Importacao.idImportacoes).filter(Importacao.tipo.in_(tipos))
            q = q.filter(Movimentacao.createdAt >= dt_inicio)
            q = q.filter(Movimentacao.createdAt < dt_fim_inclusive)
            if id_empresa:
                q = q.filter(Movimentacao.idEmpresa == id_empresa)
            if id_colaborador:
                q = q.filter(Movimentacao.idColaborador == id_colaborador)
            if id_categoria:
                q = q.filter(Movimentacao.idCategoria == id_categoria)
            return q

        # --- CARD 1: Total e quantidade de despesas ---
        q_cards = self.db.query(
            func.sum(Movimentacao.valor).label("total"),
            func.count(Movimentacao.idMovimentacoes).label("qtd")
        )
        q_cards = apply_filters(q_cards)
        res_cards = q_cards.first()

        total_despesas = float(res_cards.total or 0)
        qtd_despesas = int(res_cards.qtd or 0)

        # --- CARD 2: Total no mês e variação vs mês anterior ---
        # Definimos o "mês atual" como o mês da última despesa encontrada na query filtrada, ou o mês de dt_fim
        q_last = self.db.query(Movimentacao.createdAt).order_by(Movimentacao.createdAt.desc())
        q_last = apply_filters(q_last)
        last_item = q_last.first()

        if last_item:
            ref_date = last_item[0]
        else:
            ref_date = dt_fim

        # Mês de referência (atual)
        start_month_ref = ref_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month_ref = (start_month_ref + timedelta(days=32)).replace(day=1)

        # Mês anterior
        start_month_prev = (start_month_ref - timedelta(days=15)).replace(day=1)
        next_month_prev = start_month_ref

        # Calcula somas para o mês de referência e mês anterior (aplicando os mesmos filtros)
        def query_month_sum(start, end):
            q = self.db.query(func.sum(Movimentacao.valor))
            q = q.filter(Movimentacao.createdAt >= start, Movimentacao.createdAt < end)
            if id_empresa:
                q = q.filter(Movimentacao.idEmpresa == id_empresa)
            if id_colaborador:
                q = q.filter(Movimentacao.idColaborador == id_colaborador)
            if id_categoria:
                q = q.filter(Movimentacao.idCategoria == id_categoria)
            return float(q.scalar() or 0)

        total_mes_ref = query_month_sum(start_month_ref, next_month_ref)
        total_mes_prev = query_month_sum(start_month_prev, next_month_prev)

        if total_mes_prev > 0:
            percentual_mes = round(((total_mes_ref - total_mes_prev) / total_mes_prev) * 100, 1)
        else:
            percentual_mes = 0.0

        # --- CARD 3: Ticket Médio e variação vs período anterior ---
        ticket_medio = total_despesas / qtd_despesas if qtd_despesas > 0 else 0.0

        # Período anterior com mesma duração
        delta_days = (dt_fim_inclusive - dt_inicio).days
        dt_inicio_prev = dt_inicio - timedelta(days=delta_days)
        dt_fim_prev_inclusive = dt_inicio

        # Queries do período anterior
        q_cards_prev = self.db.query(
            func.sum(Movimentacao.valor).label("total"),
            func.count(Movimentacao.idMovimentacoes).label("qtd")
        )
        q_cards_prev = q_cards_prev.filter(Movimentacao.createdAt >= dt_inicio_prev, Movimentacao.createdAt < dt_fim_prev_inclusive)
        if id_empresa:
            q_cards_prev = q_cards_prev.filter(Movimentacao.idEmpresa == id_empresa)
        if id_colaborador:
            q_cards_prev = q_cards_prev.filter(Movimentacao.idColaborador == id_colaborador)
        if id_categoria:
            q_cards_prev = q_cards_prev.filter(Movimentacao.idCategoria == id_categoria)

        res_cards_prev = q_cards_prev.first()
        total_prev = float(res_cards_prev.total or 0)
        qtd_prev = int(res_cards_prev.qtd or 0)
        ticket_prev = total_prev / qtd_prev if qtd_prev > 0 else 0.0

        if ticket_prev > 0:
            ticket_medio_percentual = round(((ticket_medio - ticket_prev) / ticket_prev) * 100, 1)
        else:
            ticket_medio_percentual = 0.0

        # --- CARD 4: Maior Despesa ---
        q_max = self.db.query(
            Movimentacao.valor,
            Categoria.nome.label("categoria_nome"),
            CentroEstado.estado.label("estado")
        ).join(Categoria, Movimentacao.idCategoria == Categoria.idCategorias)\
         .join(Colaborador, Movimentacao.idColaborador == Colaborador.idColaborador)\
         .outerjoin(CentroEstado, Colaborador.idCentroCusto == CentroEstado.idCentroCusto)
        q_max = apply_filters(q_max).order_by(Movimentacao.valor.desc())
        res_max = q_max.first()

        if res_max:
            maior_despesa = float(res_max[0])
            cat_name = res_max[1]
            unidade_desc = res_max[2] or "Unidade Não Identificada"
            state_name = clean_state_name(unidade_desc)
            maior_despesa_contexto = f"{cat_name} · {state_name}"
        else:
            maior_despesa = 0.0
            maior_despesa_contexto = "Nenhuma despesa"

        # --- GRÁFICO 1: Evolução Mensal (Área) ---
        q_evol = self.db.query(
            Movimentacao.createdAt,
            Categoria.nome,
            Movimentacao.valor
        ).join(Categoria, Movimentacao.idCategoria == Categoria.idCategorias)
        q_evol = apply_filters(q_evol).order_by(Movimentacao.createdAt.asc())
        res_evol = q_evol.all()

        MONTHS_PT = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}

        evol_dict = {}
        all_months_keys = set()

        for item in res_evol:
            date_val = item[0]
            cat_name = item[1]
            val = float(item[2])

            month_key = f"{date_val.year}-{date_val.month:02d}"
            all_months_keys.add(month_key)

            if cat_name not in evol_dict:
                evol_dict[cat_name] = {}
            if month_key not in evol_dict[cat_name]:
                evol_dict[cat_name][month_key] = 0.0
            evol_dict[cat_name][month_key] += val

        sorted_month_keys = sorted(list(all_months_keys))
        month_labels = []
        for mk in sorted_month_keys:
            y, m = map(int, mk.split('-'))
            short_m = MONTHS_PT[m]
            month_labels.append(f"{short_m}/{str(y)[2:]}")

        evol_series = []
        for cat_name, months_vals in evol_dict.items():
            cat_data = []
            for mk in sorted_month_keys:
                cat_data.append(round(months_vals.get(mk, 0.0), 2))
            evol_series.append({
                "name": cat_name,
                "data": cat_data
            })

        # --- GRÁFICO 2: Distribuição por Categoria (Donut Categorias) ---
        q_cat_dist = self.db.query(
            Categoria.nome,
            func.sum(Movimentacao.valor),
            func.count(Movimentacao.idMovimentacoes),
            Categoria.idCategorias
        ).join(Categoria, Movimentacao.idCategoria == Categoria.idCategorias)
        q_cat_dist = apply_filters(q_cat_dist).group_by(Categoria.nome, Categoria.idCategorias).all()
        donut_categorias = [
            {
                "name": r[0],
                "value": round(float(r[1]), 2),
                "qtd": int(r[2]),
                "id": r[3]
            } for r in q_cat_dist
        ]

        # --- GRÁFICO 3: Distribuição por Empresa (Donut Empresas) ---
        q_emp_dist = self.db.query(
            Empresa.nome,
            func.sum(Movimentacao.valor)
        ).join(Empresa, Movimentacao.idEmpresa == Empresa.idEmpresas)
        q_emp_dist = apply_filters(q_emp_dist).group_by(Empresa.nome).all()
        donut_empresas = [{"name": r[0], "value": round(float(r[1]), 2)} for r in q_emp_dist]

        # --- GRÁFICO 4: Distribuição por Estado (Mapa) ---
        q_map_dist = self.db.query(
            CentroEstado.estado,
            func.sum(Movimentacao.valor),
            func.count(Movimentacao.idMovimentacoes)
        ).join(Colaborador, Movimentacao.idColaborador == Colaborador.idColaborador)\
         .join(CentroEstado, Colaborador.idCentroCusto == CentroEstado.idCentroCusto)
        q_map_dist = apply_filters(q_map_dist).group_by(CentroEstado.estado).all()

        map_states_dict = {}
        for r in q_map_dist:
            unidade_desc = r[0]
            val = float(r[1])
            qtd = int(r[2])

            state_name = clean_state_name(unidade_desc)
            if state_name not in map_states_dict:
                map_states_dict[state_name] = {"value": 0.0, "qtd": 0}
            map_states_dict[state_name]["value"] += val
            map_states_dict[state_name]["qtd"] += qtd

        mapa_data = [
            {"name": state, "value": round(data["value"], 2), "qtd": data["qtd"]}
            for state, data in map_states_dict.items()
        ]

        # --- TABELA: Maiores Despesas ---
        q_table = self.db.query(
            Categoria.nome.label("descricao"),
            Colaborador.nome.label("pessoa"),
            Empresa.nome.label("empresa"),
            Categoria.nome.label("categoria"),
            Movimentacao.createdAt.label("data"),
            Movimentacao.valor.label("valor")
        ).join(Categoria, Movimentacao.idCategoria == Categoria.idCategorias)\
         .join(Colaborador, Movimentacao.idColaborador == Colaborador.idColaborador)\
         .join(Empresa, Movimentacao.idEmpresa == Empresa.idEmpresas)
        q_table = apply_filters(q_table).order_by(Movimentacao.valor.desc()).limit(5)
        res_table = q_table.all()

        tabela_maiores = []
        for r in res_table:
            tabela_maiores.append({
                "descricao": r[0],
                "pessoa": r[1],
                "empresa": r[2],
                "categoria": r[3],
                "data": r[4].strftime("%d/%m/%Y"),
                "valor": float(r[5])
            })

        # --- GRÁFICO 5: Maiores Gastos por Pessoa (Spenders) ---
        q_spenders = self.db.query(
            Colaborador.nome,
            func.sum(Movimentacao.valor)
        ).join(Colaborador, Movimentacao.idColaborador == Colaborador.idColaborador)
        q_spenders = apply_filters(q_spenders).group_by(Colaborador.nome).order_by(func.sum(Movimentacao.valor).desc()).limit(10).all()
        spenders = [{"name": r[0], "value": round(float(r[1]), 2)} for r in q_spenders]

        # --- CÁLCULO: Maior Crescimento de Categoria ---
        q_cat_dist_prev = self.db.query(
            Categoria.nome,
            func.sum(Movimentacao.valor)
        ).join(Categoria, Movimentacao.idCategoria == Categoria.idCategorias)
        q_cat_dist_prev = q_cat_dist_prev.filter(
            Movimentacao.createdAt >= dt_inicio_prev,
            Movimentacao.createdAt < dt_fim_prev_inclusive
        )
        if id_empresa:
            q_cat_dist_prev = q_cat_dist_prev.filter(Movimentacao.idEmpresa == id_empresa)
        if id_colaborador:
            q_cat_dist_prev = q_cat_dist_prev.filter(Movimentacao.idColaborador == id_colaborador)
        if id_categoria:
            q_cat_dist_prev = q_cat_dist_prev.filter(Movimentacao.idCategoria == id_categoria)
        q_cat_dist_prev = q_cat_dist_prev.group_by(Categoria.nome).all()

        prev_cat_dict = {r[0]: float(r[1]) for r in q_cat_dist_prev}

        maior_crescimento_nome = "N/A"
        maior_crescimento_pct = 0.0

        for r in q_cat_dist:
            cat_name = r[0]
            curr_val = float(r[1])
            prev_val = prev_cat_dict.get(cat_name, 0.0)
            if prev_val > 0:
                pct = round(((curr_val - prev_val) / prev_val) * 100, 1)
                if pct > maior_crescimento_pct:
                    maior_crescimento_pct = pct
                    maior_crescimento_nome = cat_name
            elif curr_val > 0:
                pct = 100.0
                if pct > maior_crescimento_pct:
                    maior_crescimento_pct = pct
                    maior_crescimento_nome = cat_name

        maior_crescimento = {
            "name": maior_crescimento_nome,
            "percentage": maior_crescimento_pct
        }

        return {
            "dashVisaoGeral": {
                "total": round(total_despesas, 2),
                "quantidadeDespesas": qtd_despesas,
                "totalMes": round(total_mes_ref, 2),
                "percentualMes": percentual_mes,
                "ticketMedio": round(ticket_medio, 2),
                "ticketMedioPercentual": ticket_medio_percentual,
                "maiorDespesa": round(maior_despesa, 2),
                "maiorDespesaContexto": maior_despesa_contexto
            },
            "evolucao": {
                "meses": month_labels,
                "series": evol_series
            },
            "donutCategorias": donut_categorias,
            "donutEmpresas": donut_empresas,
            "mapaData": mapa_data,
            "tabelaMaioresDespesas": tabela_maiores,
            "spenders": spenders,
            "maiorCrescimento": maior_crescimento
        }

    def obter_dados_analitico(
        self,
        data_inicio: str = None,
        data_fim: str = None,
        id_empresa: int = None,
        id_colaborador: int = None,
        id_categoria: int = None,
        tipo_importacao: str = None
    ) -> Dict[str, Any]:
        MONTHS_PT = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}

        # Formata datas base
        if data_inicio:
            dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        else:
            # 6 meses atrás por padrão
            dt_inicio = datetime.now() - timedelta(days=180)
            dt_inicio = dt_inicio.replace(hour=0, minute=0, second=0, microsecond=0)

        if data_fim:
            dt_fim = datetime.strptime(data_fim, "%Y-%m-%d")
        else:
            dt_fim = datetime.now()

        # Garante incluir o dia inteiro de data_fim
        dt_fim_inclusive = dt_fim + timedelta(days=1)

        # Filtros utilitários
        def apply_filters(q):
            if tipo_importacao:
                tipos = [t.strip() for t in tipo_importacao.split(",")]
                q = q.join(Importacao, Movimentacao.idImportacoes == Importacao.idImportacoes).filter(Importacao.tipo.in_(tipos))
            q = q.filter(Movimentacao.createdAt >= dt_inicio)
            q = q.filter(Movimentacao.createdAt < dt_fim_inclusive)
            if id_empresa:
                q = q.filter(Movimentacao.idEmpresa == id_empresa)
            if id_colaborador:
                q = q.filter(Movimentacao.idColaborador == id_colaborador)
            if id_categoria:
                q = q.filter(Movimentacao.idCategoria == id_categoria)
            return q

        # --- 1. KPI Total ---
        q_total = self.db.query(func.sum(Movimentacao.valor))
        q_total = apply_filters(q_total)
        total_despesas = float(q_total.scalar() or 0)

        # Buscar todos os dados base para agregações em memória
        # Essa abordagem é consistente com o resto do arquivo e evita problemas de dialeto SQL
        q_base = self.db.query(
            Movimentacao.idMovimentacoes,
            Movimentacao.createdAt,
            Movimentacao.valor,
            Categoria.nome.label('categoria_nome'),
            Categoria.idCategorias.label('categoria_id'),
            CentroCusto.codigo.label('centro_custo_codigo'),
            CentroCusto.nome.label('centro_custo_nome'),
            CentroEstado.estado.label('estado'),
            Colaborador.nome.label('colaborador_nome'),
            Colaborador.idColaborador.label('colaborador_id'),
            Colaborador.papel.label('papel'),
            Empresa.nome.label('empresa_nome')
        ).join(Categoria, Movimentacao.idCategoria == Categoria.idCategorias)\
         .join(Colaborador, Movimentacao.idColaborador == Colaborador.idColaborador)\
         .join(Empresa, Movimentacao.idEmpresa == Empresa.idEmpresas)\
         .join(CentroCusto, Colaborador.idCentroCusto == CentroCusto.idCentroCusto)\
         .outerjoin(CentroEstado, CentroCusto.idCentroCusto == CentroEstado.idCentroCusto)

        q_base = apply_filters(q_base).order_by(Movimentacao.createdAt.desc())
        all_movs = q_base.all()

        # Estruturas de dados para agregações
        meses_totais = {}
        categorias_totais = {}
        centro_custo_mensal = {}
        centro_custo_totais = {}
        estados_totais = {}
        butterfly_comercial = {}
        butterfly_marketing = {}
        colaboradores_totais = {}
        empresas_totais = {}
        colab_matrix_map = {}
        colab_cc_map = {}

        detalhes = []
        all_months_keys = set()

        # Preencher meses com 0 para todo o período
        cur_date = dt_inicio.replace(day=1) # normaliza para o dia 1
        while cur_date < dt_fim_inclusive:
            mk = f"{cur_date.year}-{cur_date.month:02d}"
            all_months_keys.add(mk)
            meses_totais[mk] = 0
            if cur_date.month == 12:
                cur_date = cur_date.replace(year=cur_date.year + 1, month=1)
            else:
                cur_date = cur_date.replace(month=cur_date.month + 1)

        seen_movs = set()
        detalhes_idx = 0

        for row in all_movs:
            mov_id = row.idMovimentacoes
            date_val = row.createdAt
            val = float(row.valor)
            cat_name = row.categoria_nome
            cat_id = row.categoria_id
            cc_nome = row.centro_custo_nome
            estado = row.estado or "-"
            colab_nome = row.colaborador_nome
            papel = (row.papel or "").strip().upper()

            # Só agrega e adiciona a detalhes se for a primeira vez que vemos essa movimentação
            if mov_id not in seen_movs:
                seen_movs.add(mov_id)

                # Detalhes (limitar a 200 itens únicos para não pesar o frontend)
                if detalhes_idx < 200:
                    detalhes.append({
                        "data": date_val.strftime("%d/%m/%Y"),
                        "categoria": cat_name,
                        "centroCustoNome": cc_nome,
                        "colaboradorNome": colab_nome,
                        "estado": estado,
                        "valor": val,
                        "empresa": row.empresa_nome
                    })
                    detalhes_idx += 1

                # Mês/Ano para Barras Verticais e Evolução
                month_key = f"{date_val.year}-{date_val.month:02d}"
                all_months_keys.add(month_key)

                meses_totais[month_key] = meses_totais.get(month_key, 0) + val

                # Categoria Barras e Donut
                if cat_name not in categorias_totais:
                    categorias_totais[cat_name] = {"id": cat_id, "valor": 0}
                categorias_totais[cat_name]["valor"] += val

                # Evolução por Centro de Custo e Total por Centro de Custo
                cc_display = cc_nome or "Sem Centro de Custo"
                centro_custo_totais[cc_display] = centro_custo_totais.get(cc_display, 0) + val

                if cc_display not in centro_custo_mensal:
                    centro_custo_mensal[cc_display] = {}
                centro_custo_mensal[cc_display][month_key] = centro_custo_mensal[cc_display].get(month_key, 0) + val

                # Mapa (somente na primeira região que a movimentação for vinculada, para manter consistência)
                estado_clean = clean_state_name(estado)
                if estado_clean not in estados_totais:
                    estados_totais[estado_clean] = {"value": 0.0, "qtd": 0}
                estados_totais[estado_clean]["value"] += val
                estados_totais[estado_clean]["qtd"] += 1

                # Butterfly (Comercial vs Marketing)
                if 'COMERCIAL' in papel:
                    butterfly_comercial[cat_name] = butterfly_comercial.get(cat_name, 0) + val
                elif 'MARKETING' in papel:
                    butterfly_marketing[cat_name] = butterfly_marketing.get(cat_name, 0) + val

                # Ranking Colaboradores e Matriz
                colaboradores_totais[colab_nome] = colaboradores_totais.get(colab_nome, 0) + val

                # Total por Empresa
                emp_nome = row.empresa_nome or "Sem Empresa"
                empresas_totais[emp_nome] = empresas_totais.get(emp_nome, 0) + val
                colab_cc_map[colab_nome] = row.centro_custo_codigo

                matrix_key = (colab_nome, row.empresa_nome)
                if matrix_key not in colab_matrix_map:
                    colab_matrix_map[matrix_key] = {}
                colab_matrix_map[matrix_key][cat_name] = colab_matrix_map[matrix_key].get(cat_name, 0) + val

        # --- Formatação dos Resultados ---

        sorted_month_keys = sorted(list(all_months_keys))
        month_labels = []
        for mk in sorted_month_keys:
            y, m = map(int, mk.split('-'))
            short_m = MONTHS_PT[m]
            month_labels.append(f"{short_m}/{str(y)[2:]}")

        barras_verticais = [round(meses_totais.get(mk, 0), 2) for mk in sorted_month_keys]

        # Categorias
        cat_sorted = sorted([{"name": k, "value": round(v["valor"], 2), "id": v["id"]} for k, v in categorias_totais.items()], key=lambda x: x["value"], reverse=True)

        # Top 5 Centros de Custo
        top_cc = sorted(centro_custo_totais.items(), key=lambda x: x[1], reverse=True)[:5]
        top_cc_names = [cc[0] for cc in top_cc]

        evol_cc_series = []
        for cc_name in top_cc_names:
            cat_data = []
            for mk in sorted_month_keys:
                cat_data.append(round(centro_custo_mensal[cc_name].get(mk, 0.0), 2))
            evol_cc_series.append({
                "name": cc_name,
                "data": cat_data
            })

        centro_custo_barras = [{"name": cc[0], "value": round(cc[1], 2)} for cc in top_cc]

        # Mapa
        mapa_data = [{"name": st, "value": round(data["value"], 2), "qtd": data["qtd"]} for st, data in estados_totais.items()]

        # Butterfly
        # Pegar todas as categorias presentes nas movimentações
        all_cats = list(categorias_totais.keys())
        butterfly = {
            "categorias": all_cats,
            "comercial": [round(butterfly_comercial.get(c, 0), 2) for c in all_cats],
            "marketing": [round(butterfly_marketing.get(c, 0), 2) for c in all_cats]
        }

        # Rankings
        total_geral = total_despesas or 1
        ranking_colab = sorted(colaboradores_totais.items(), key=lambda x: x[1], reverse=True)[:10]
        ranking_colaboradores = [{"posicao": i+1, "nome": k, "valor": round(v, 2), "pct": round((v/total_geral)*100, 1)} for i, (k,v) in enumerate(ranking_colab)]

        ranking_categorias = [{"posicao": i+1, "nome": c["name"], "valor": c["value"], "pct": round((c["value"]/total_geral)*100, 1)} for i, c in enumerate(cat_sorted[:10])]

        # Ranking por Empresa
        ranking_emp = sorted(empresas_totais.items(), key=lambda x: x[1], reverse=True)
        ranking_empresas = [{"posicao": i+1, "nome": k, "valor": round(v, 2), "pct": round((v/total_geral)*100, 1)} for i, (k,v) in enumerate(ranking_emp)]

        # Matrix Detalhes
        detalhes_categorias_colunas = sorted(list(categorias_totais.keys()))
        detalhes_totais_categoria = {k: round(v["valor"], 2) for k, v in categorias_totais.items()}

        matriz = []
        for (colab, emp), cat_vals in colab_matrix_map.items():
            row_total = sum(cat_vals.values())
            matriz.append({
                "colaboradorNome": colab,
                "empresaNome": emp,
                "centroCustoCodigo": colab_cc_map.get(colab, ""),
                "valoresPorCategoria": {k: round(v, 2) for k, v in cat_vals.items()},
                "total": round(row_total, 2)
            })
        matriz.sort(key=lambda x: (x["colaboradorNome"], x["empresaNome"]))

        return {
            "analiticoTotalDespesas": round(total_despesas, 2),
            "meses": month_labels,
            "barrasVerticais": barras_verticais,
            "categoriaBarras": cat_sorted,
            "evolucaoCentroCusto": {
                "meses": month_labels,
                "series": evol_cc_series
            },
            "centroCustoBarras": centro_custo_barras,
            "mapaData": mapa_data,
            "butterfly": butterfly,
            "rankingColaboradores": ranking_colaboradores,
            "rankingEmpresas": ranking_empresas,
            "rankingCategorias": ranking_categorias,
            "detalhesMatrizOriginal": matriz,
            "detalhesCategoriasColunas": detalhes_categorias_colunas,
            "detalhesTotaisPorCategoria": detalhes_totais_categoria,
            "detalhesTotalGeral": round(total_despesas, 2),
            "detalhes": detalhes
        }

def clean_state_name(desc: str) -> str:
    desc_clean = desc.strip().upper()
    if desc_clean in ["SP", "SÃO PAULO", "SAO PAULO"]:
        return "São Paulo"
    if desc_clean in ["RJ", "RIO DE JANEIRO"]:
        return "Rio de Janeiro"
    if desc_clean in ["MG", "MINAS GERAIS"]:
        return "Minas Gerais"
    if desc_clean in ["PR", "PARANÁ", "PARANA"]:
        return "Paraná"
    if desc_clean in ["RS", "RIO GRANDE DO SUL"]:
        return "Rio Grande do Sul"
    if desc_clean in ["SC", "SANTA CATARINA"]:
        return "Santa Catarina"
    if desc_clean in ["DF", "DISTRITO FEDERAL", "BRASÍLIA", "BRASILIA"]:
        return "Distrito Federal"
    if desc_clean in ["GO", "GOIÁS", "GOIAS"]:
        return "Goiás"
    if desc_clean in ["BA", "BAHIA"]:
        return "Bahia"
    if desc_clean in ["PE", "PERNAMBUCO"]:
        return "Pernambuco"
    if desc_clean in ["CE", "CEARÁ", "CEARA"]:
        return "Ceará"
    if desc_clean in ["ES", "ESPÍRITO SANTO", "ESPIRITO SANTO"]:
        return "Espírito Santo"
    return desc.title()
