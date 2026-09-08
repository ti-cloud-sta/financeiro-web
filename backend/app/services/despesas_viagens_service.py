from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
from app.models.movimentacao import Movimentacao
from app.models.importacao import Importacao
from app.repositories.categoria_repository import CategoriaRepository
from app.repositories.colaborador_repository import ColaboradorRepository
from app.repositories.empresa_repository import EmpresaRepository
from app.repositories.colaborador_alias_repository import ColaboradorAliasRepository
from app.schemas.despesas_viagens import SalvarDespesaViagemPayload


class DespesasViagensService:
    def __init__(self, db: Session):
        self.db = db
        self.cat_repo = CategoriaRepository(db)
        self.colab_repo = ColaboradorRepository(db)
        self.emp_repo = EmpresaRepository(db)
        self.alias_repo = ColaboradorAliasRepository(db)

    def salvar_importacao(self, payload: SalvarDespesaViagemPayload):
        # Resolve a data de competência do form (criará as movimentações com essa data)
        data_competencia_obj = None
        if payload.dataCompetencia:
            try:
                data_competencia_obj = datetime.strptime(payload.dataCompetencia, "%Y-%m-%d")
            except ValueError:
                pass

        nova_importacao = None

        # -----------------------------------------------------------------------
        # Lançamento via IMPORTAÇÃO (IA): cria um registro de importação primeiro
        # -----------------------------------------------------------------------
        if not payload.isManualEntry:
            extensao = payload.nomeArquivo.split('.')[-1] if '.' in payload.nomeArquivo else ''

            id_empresa_importacao = None
            if payload.despesas:
                emp = self.emp_repo.get_by_nome(payload.despesas[0].empresa)
                if emp:
                    id_empresa_importacao = emp.idEmpresas

            nova_importacao = Importacao(
                nomeArquivo=payload.nomeArquivo,
                extensaoArquivo=extensao,
                idEmpresa=id_empresa_importacao,
                tipo="IA_DESPESAS",
                idUserInc=payload.idUserInc,
                createdAt=data_competencia_obj or datetime.now()
            )
            self.db.add(nova_importacao)
            self.db.flush()

        # -----------------------------------------------------------------------
        # Para lançamento manual: usa a empresa selecionada no payload
        # -----------------------------------------------------------------------
        empresa_manual = None
        if payload.isManualEntry and payload.idEmpresaManual:
            empresa_manual = self.emp_repo.get_by_id(payload.idEmpresaManual)
            if not empresa_manual:
                raise HTTPException(status_code=400, detail="Empresa selecionada não encontrada.")

        # -----------------------------------------------------------------------
        # Grava as movimentações
        # -----------------------------------------------------------------------
        for d in payload.despesas:
            cat = self.cat_repo.get_by_nome(d.categoria)
            if not cat:
                raise HTTPException(status_code=400, detail=f"Categoria não encontrada: {d.categoria}")

            if payload.isManualEntry:
                emp = empresa_manual
            else:
                emp = self.emp_repo.get_by_nome(d.empresa)
            if not emp:
                raise HTTPException(status_code=400, detail=f"Empresa não encontrada: {d.empresa}")

            # nome_original = nome divergente como estava no documento (ex: "JOSE DA SILVA")
            # nome_corrigido = nome que o usuário escolheu no select (ex: "José da Silva")
            nome_original = (d.colaborador_original or d.colaborador).strip()
            nome_corrigido = d.colaborador.strip()
            colab = None

            # 1) Verifica se já existe um alias mapeado para o nome original divergente
            alias = self.alias_repo.get_by_nome_divergente(nome_original)
            if alias:
                colab = self.colab_repo.get_by_id(alias.idColaborador)

            # 2) Se não achou via alias, tenta pelo nome corrigido (o que o usuário selecionou)
            if not colab:
                colab = self.colab_repo.get_by_nome_normalizado(nome_corrigido)

            if not colab:
                raise HTTPException(
                    status_code=400,
                    detail=f"Colaborador não encontrado e não mapeado: {d.colaborador}"
                )

            # 3) Se o nome original diverge do nome cadastrado, registra/atualiza o alias
            #    para que próximas importações com esse mesmo nome sejam resolvidas automaticamente
            if nome_original.lower() != colab.nome.lower():
                self.alias_repo.create_or_update(colab.idColaborador, nome_original)

            # Prioridade da data: campo data individual da despesa > dataCompetencia do form
            data_mov = data_competencia_obj
            if d.data:
                try:
                    data_mov = datetime.strptime(d.data, "%Y-%m-%d")
                except ValueError:
                    pass

            nova_mov = Movimentacao(
                idCategoria=cat.idCategorias,
                idColaborador=colab.idColaborador,
                idEmpresa=emp.idEmpresas,
                idImportacoes=nova_importacao.idImportacoes if nova_importacao else None,
                nroDocumento=d.nroDocumento or None,
                valor=d.valor,
                createdAt=data_mov or datetime.now()
            )
            self.db.add(nova_mov)

        self.db.commit()

        return {
            "sucesso": True,
            "idImportacoes": nova_importacao.idImportacoes if nova_importacao else None,
            "totalMovimentacoes": len(payload.despesas)
        }

    def obter_visao_geral(self, filtros: dict):
        from sqlalchemy import func, extract, case
        from datetime import datetime, timedelta
        from app.models.movimentacao import Movimentacao
        from app.models.importacao import Importacao
        from app.models.colaborador import Colaborador
        from app.models.empresa import Empresa
        from app.models.categoria import Categoria

        db = self.db

        # ---- Parse filtros ----
        data_inicio = filtros.get("data_inicio")
        data_fim = filtros.get("data_fim")
        id_empresa = filtros.get("id_empresa")
        id_colaborador = filtros.get("id_colaborador")
        id_categoria = filtros.get("id_categoria")

        def parse_date(d):
            if not d:
                return None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                try:
                    return datetime.strptime(d, fmt)
                except ValueError:
                    pass
            return None

        dt_inicio = parse_date(data_inicio)
        dt_fim = parse_date(data_fim)

        # ---- Base query ----
        def base_q():
            q = db.query(Movimentacao)
            if dt_inicio:
                q = q.filter(Movimentacao.createdAt >= dt_inicio)
            if dt_fim:
                # inclui o dia todo
                q = q.filter(Movimentacao.createdAt <= dt_fim.replace(hour=23, minute=59, second=59))
            if id_empresa:
                q = q.filter(Movimentacao.idEmpresa == id_empresa)
            if id_colaborador:
                q = q.filter(Movimentacao.idColaborador == id_colaborador)
            if id_categoria:
                q = q.filter(Movimentacao.idCategoria == id_categoria)
            # Apenas importações do tipo IA_DESPESAS ou lançamentos manuais (sem importacao)
            q = q.outerjoin(Importacao, Movimentacao.idImportacoes == Importacao.idImportacoes)
            q = q.filter(
                (Movimentacao.idImportacoes == None) |
                (Importacao.tipo == "IA_DESPESAS")
            )
            return q

        # ---- KPI: Total e Quantidade ----
        agg = base_q().with_entities(
            func.coalesce(func.sum(Movimentacao.valor), 0).label("total"),
            func.count(Movimentacao.idMovimentacoes).label("qtd")
        ).one()
        total = float(agg.total)
        qtd = int(agg.qtd)

        # ---- KPI: Ticket Médio ----
        ticket_medio = round(total / qtd, 2) if qtd > 0 else 0.0

        # ---- KPI: Total do Mês atual ----
        agora = datetime.now()
        inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Mes anterior (ultimo dia do mes anterior)
        inicio_mes_ant = (inicio_mes - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0)
        fim_mes_ant = inicio_mes - timedelta(seconds=1)

        def soma_mes(inicio, fim):
            q = db.query(func.coalesce(func.sum(Movimentacao.valor), 0))
            q = q.outerjoin(Importacao, Movimentacao.idImportacoes == Importacao.idImportacoes)
            q = q.filter(
                (Movimentacao.idImportacoes == None) |
                (Importacao.tipo == "IA_DESPESAS")
            )
            q = q.filter(Movimentacao.createdAt >= inicio, Movimentacao.createdAt <= fim)
            if id_empresa:
                q = q.filter(Movimentacao.idEmpresa == id_empresa)
            if id_colaborador:
                q = q.filter(Movimentacao.idColaborador == id_colaborador)
            if id_categoria:
                q = q.filter(Movimentacao.idCategoria == id_categoria)
            return float(q.scalar() or 0)

        total_mes = soma_mes(inicio_mes, agora)
        total_mes_ant = soma_mes(inicio_mes_ant, fim_mes_ant)
        if total_mes_ant > 0:
            pct_mes = round(((total_mes - total_mes_ant) / total_mes_ant) * 100, 1)
        elif total_mes > 0:
            pct_mes = 100.0
        else:
            pct_mes = 0.0

        # ---- KPI: Maior Despesa ----
        maior = base_q().with_entities(
            Movimentacao.valor,
            Movimentacao.idColaborador,
            Movimentacao.idCategoria
        ).order_by(Movimentacao.valor.desc()).first()

        maior_valor = 0.0
        maior_contexto = "Sem registros"
        if maior:
            maior_valor = float(maior.valor)
            colab = db.query(Colaborador).filter(Colaborador.idColaborador == maior.idColaborador).first()
            cat = db.query(Categoria).filter(Categoria.idCategorias == maior.idCategoria).first()
            nome_colab = colab.nome if colab else "?"
            nome_cat = cat.nome if cat else "?"
            maior_contexto = f"{nome_colab} · {nome_cat}"

        # ---- Tabela Maiores Despesas (top 10) ----
        top_rows = (
            base_q()
            .join(Colaborador, Movimentacao.idColaborador == Colaborador.idColaborador)
            .join(Empresa, Movimentacao.idEmpresa == Empresa.idEmpresas)
            .join(Categoria, Movimentacao.idCategoria == Categoria.idCategorias)
            .with_entities(
                Movimentacao.nroDocumento,
                Colaborador.nome.label("colaborador"),
                Empresa.nome.label("empresa"),
                Categoria.nome.label("categoria"),
                Movimentacao.createdAt,
                Movimentacao.valor
            )
            .order_by(Movimentacao.valor.desc())
            .limit(10)
            .all()
        )
        tabela_maiores = [
            {
                "descricao": r.nroDocumento or "—",
                "pessoa": r.colaborador,
                "empresa": r.empresa,
                "categoria": r.categoria,
                "data": r.createdAt.strftime("%d/%m/%Y") if r.createdAt else "—",
                "valor": float(r.valor)
            }
            for r in top_rows
        ]

        # ---- Donut Categorias ----
        cat_agg = (
            base_q()
            .join(Categoria, Movimentacao.idCategoria == Categoria.idCategorias)
            .with_entities(
                Categoria.idCategorias.label("id"),
                Categoria.nome.label("nome"),
                func.sum(Movimentacao.valor).label("total"),
                func.count(Movimentacao.idMovimentacoes).label("qtd")
            )
            .group_by(Categoria.idCategorias, Categoria.nome)
            .order_by(func.sum(Movimentacao.valor).desc())
            .limit(8)
            .all()
        )
        donut_categorias = [{"id": r.id, "name": r.nome, "value": round(float(r.total), 2), "qtd": r.qtd} for r in cat_agg]

        # ---- Donut Empresas ----
        emp_agg = (
            base_q()
            .join(Empresa, Movimentacao.idEmpresa == Empresa.idEmpresas)
            .with_entities(
                Empresa.nome.label("nome"),
                func.sum(Movimentacao.valor).label("total")
            )
            .group_by(Empresa.nome)
            .order_by(func.sum(Movimentacao.valor).desc())
            .all()
        )
        donut_empresas = [{"name": r.nome, "value": round(float(r.total), 2)} for r in emp_agg]

        # ---- Evolução Mensal por Categoria ----
        # 1. Determina a janela de meses (mesmo os sem dados)
        min_max = base_q().with_entities(func.min(Movimentacao.createdAt), func.max(Movimentacao.createdAt)).one()
        min_dt = dt_inicio or min_max[0]
        max_dt = dt_fim or min_max[1]
        
        all_months = []
        if min_dt and max_dt:
            curr = min_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = max_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            while curr <= end:
                all_months.append((curr.year, curr.month))
                month = curr.month % 12 + 1
                year = curr.year + (1 if curr.month == 12 else 0)
                curr = curr.replace(year=year, month=month)
                
        meses_labels = [f"{m:02d}/{a}" for a, m in all_months]

        # 2. Top 5 categorias por total
        top_cats = [r.nome for r in cat_agg[:5]]

        # 3. Pega os dados brutos de evolucao da query para as top categorias (para evitar N queries no loop)
        evolucao_raw = (
            base_q()
            .join(Categoria, Movimentacao.idCategoria == Categoria.idCategorias)
            .filter(Categoria.nome.in_(top_cats) if top_cats else False)
            .with_entities(
                Categoria.nome.label("cat_nome"),
                func.year(Movimentacao.createdAt).label("ano"),
                func.month(Movimentacao.createdAt).label("mes"),
                func.sum(Movimentacao.valor).label("total")
            )
            .group_by(Categoria.nome, func.year(Movimentacao.createdAt), func.month(Movimentacao.createdAt))
            .all()
        )
        
        # Mapa: dict[cat_nome][ano][mes] = total
        evolucao_dict = {}
        for r in evolucao_raw:
            if r.cat_nome not in evolucao_dict:
                evolucao_dict[r.cat_nome] = {}
            if r.ano not in evolucao_dict[r.cat_nome]:
                evolucao_dict[r.cat_nome][r.ano] = {}
            evolucao_dict[r.cat_nome][r.ano][r.mes] = float(r.total)

        series = []
        for cat_nome in top_cats:
            data_points = []
            for ano, mes in all_months:
                val = evolucao_dict.get(cat_nome, {}).get(ano, {}).get(mes, 0.0)
                data_points.append(round(val, 2))
            series.append({"name": cat_nome, "data": data_points})

        # ---- Mapa: Despesas por Estado ----
        from app.models.centro_custo import CentroEstado
        
        mapa_agg = (
            base_q()
            .join(Colaborador, Movimentacao.idColaborador == Colaborador.idColaborador)
            .join(CentroEstado, Colaborador.idCentroCusto == CentroEstado.idCentroCusto)
            .with_entities(
                CentroEstado.estado.label("estado"),
                func.sum(Movimentacao.valor).label("total"),
                func.count(Movimentacao.idMovimentacoes).label("qtd")
            )
            .group_by(CentroEstado.estado)
            .all()
        )
        
        # Mapeamento do nome completo do estado caso esteja em sigla (Ex: 'SP' -> 'São Paulo')
        # O echarts brazil map precisa do nome exato e case-sensitive do estado.
        sigla_para_nome = {
            "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
            "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
            "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
            "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
            "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
            "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
            "SE": "Sergipe", "TO": "Tocantins"
        }
        
        # Permite resolver tanto se vier "SP" quanto se vier "SÃO PAULO" do banco
        upper_to_correct = {v.upper(): v for v in sigla_para_nome.values()}
        upper_to_correct.update(sigla_para_nome)
        
        mapa_data = []
        for r in mapa_agg:
            estado_original = (r.estado or "").strip().upper()
            nome_estado = upper_to_correct.get(estado_original, estado_original)
            mapa_data.append({
                "name": nome_estado,
                "value": round(float(r.total), 2),
                "qtd": int(r.qtd)
            })
        # ---- Spenders (Maiores Gastos por Pessoa) ----
        spenders_agg = (
            base_q()
            .join(Colaborador, Movimentacao.idColaborador == Colaborador.idColaborador)
            .with_entities(
                Colaborador.nome.label("nome"),
                func.sum(Movimentacao.valor).label("total")
            )
            .group_by(Colaborador.nome)
            .order_by(func.sum(Movimentacao.valor).desc())
            .limit(10)
            .all()
        )
        spenders = [{"name": r.nome, "value": round(float(r.total), 2)} for r in spenders_agg]

        return {
            "dashVisaoGeral": {
                "total": round(total, 2),
                "quantidadeDespesas": qtd,
                "totalMes": round(total_mes, 2),
                "percentualMes": pct_mes,
                "ticketMedio": round(ticket_medio, 2),
                "ticketMedioPercentual": 0.0,
                "maiorDespesa": round(maior_valor, 2),
                "maiorDespesaContexto": maior_contexto
            },
            "tabelaMaioresDespesas": tabela_maiores,
            "donutCategorias": donut_categorias,
            "donutEmpresas": donut_empresas,
            "mapaData": mapa_data,
            "spenders": spenders,
            "evolucao": {
                "meses": meses_labels,
                "series": series
            }
        }

    def obter_visao_comercial(self, filtros):
        from sqlalchemy import func
        from datetime import datetime
        from app.models.movimentacao import Movimentacao
        from app.models.importacao import Importacao
        from app.models.colaborador import Colaborador
        from app.models.centro_custo import CentroCusto
        from app.models.categoria import Categoria

        data_inicio_str = filtros.get("data_inicio")
        data_fim_str = filtros.get("data_fim")
        id_empresa = filtros.get("id_empresa")
        id_colaborador = filtros.get("id_colaborador")
        id_categoria = filtros.get("id_categoria")

        # Base query for all Despesas de Viagens
        def base_q():
            q = self.db.query(Movimentacao)
            q = q.outerjoin(Importacao, Movimentacao.idImportacoes == Importacao.idImportacoes)
            q = q.filter(
                (Movimentacao.idImportacoes == None) |
                (Importacao.tipo == "IA_DESPESAS")
            )
            if data_inicio_str:
                di = datetime.strptime(data_inicio_str, "%Y-%m-%d")
                q = q.filter(Movimentacao.createdAt >= di)
            if data_fim_str:
                df = datetime.strptime(data_fim_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                q = q.filter(Movimentacao.createdAt <= df)
            if id_empresa:
                q = q.filter(Movimentacao.idEmpresa == id_empresa)
            if id_colaborador:
                q = q.filter(Movimentacao.idColaborador == id_colaborador)
            if id_categoria:
                q = q.filter(Movimentacao.idCategoria == id_categoria)
            
            # Filtro Comercial/Marketing
            q = q.join(Colaborador, Movimentacao.idColaborador == Colaborador.idColaborador)
            q = q.filter(
                Colaborador.papel.ilike("%COMERCIAL%") |
                Colaborador.papel.ilike("%MARKETING%")
            )
            return q

        total = base_q().with_entities(func.coalesce(func.sum(Movimentacao.valor), 0)).scalar()
        total = float(total or 0)

        movs = base_q().with_entities(
            Movimentacao.valor,
            Movimentacao.createdAt,
            Categoria.nome.label("categoria_nome"),
            Colaborador.nome.label("colab_nome"),
            Colaborador.papel.label("colab_papel"),
            CentroCusto.nome.label("cc_nome"),
            CentroCusto.codigo.label("cc_codigo")
        ).outerjoin(Categoria, Movimentacao.idCategoria == Categoria.idCategorias) \
         .outerjoin(CentroCusto, Colaborador.idCentroCusto == CentroCusto.codigo).all()

        meses_set = set()
        barras_vert_dict = {}
        cc_evolucao = {}
        cat_barras_dict = {}
        butterfly_cats = set()
        comercial_dict = {}
        marketing_dict = {}
        cc_barras_dict = {}
        ranking_colab_dict = {}
        ranking_cat_dict = {}
        matriz_colabs = {}

        for r in movs:
            val = float(r.valor or 0)
            dt = r.createdAt
            if not dt: continue
            mes_key = f"{dt.year}-{dt.month:02d}"
            
            cat = r.categoria_nome or "Sem Categoria"
            colab = r.colab_nome or "Desconhecido"
            cc = f"{r.cc_codigo} - {r.cc_nome}"
            colab_papel = (r.colab_papel or "").upper()

            meses_set.add(mes_key)
            barras_vert_dict[mes_key] = barras_vert_dict.get(mes_key, 0) + val
            
            if cc not in cc_evolucao: cc_evolucao[cc] = {}
            cc_evolucao[cc][mes_key] = cc_evolucao[cc].get(mes_key, 0) + val
            
            cat_barras_dict[cat] = cat_barras_dict.get(cat, 0) + val
            cc_barras_dict[cc] = cc_barras_dict.get(cc, 0) + val
            
            ranking_colab_dict[colab] = ranking_colab_dict.get(colab, 0) + val
            ranking_cat_dict[cat] = ranking_cat_dict.get(cat, 0) + val
            
            butterfly_cats.add(cat)
            if "MARKETING" in colab_papel:
                marketing_dict[cat] = marketing_dict.get(cat, 0) + val
            else:
                comercial_dict[cat] = comercial_dict.get(cat, 0) + val

            if colab not in matriz_colabs:
                matriz_colabs[colab] = {"total": 0, "valores": {}}
            matriz_colabs[colab]["total"] += val
            matriz_colabs[colab]["valores"][cat] = matriz_colabs[colab]["valores"].get(cat, 0) + val

        sorted_mes_keys = sorted(list(meses_set))
        meses_labels = [f"{k.split('-')[1]}/{k.split('-')[0]}" for k in sorted_mes_keys]
        barras_verticais = [round(barras_vert_dict.get(k, 0), 2) for k in sorted_mes_keys]

        evolucao_cc_series = []
        for cc_name, mes_dict in cc_evolucao.items():
            data_pts = [round(mes_dict.get(k, 0), 2) for k in sorted_mes_keys]
            evolucao_cc_series.append({"name": cc_name, "data": data_pts})

        cat_barras_list = [{"name": k, "value": round(v, 2)} for k, v in cat_barras_dict.items()]
        cat_barras_list.sort(key=lambda x: x["value"], reverse=True)

        cc_barras_list = [{"name": k, "value": round(v, 2)} for k, v in cc_barras_dict.items()]
        cc_barras_list.sort(key=lambda x: x["value"], reverse=True)

        def build_rank(d, total_geral):
            lst = [{"nome": k, "valor": round(v, 2)} for k, v in d.items()]
            lst.sort(key=lambda x: x["valor"], reverse=True)
            lst = lst[:10]
            res = []
            for i, item in enumerate(lst):
                pct = (item["valor"] / total_geral * 100) if total_geral > 0 else 0
                res.append({
                    "posicao": i + 1,
                    "nome": item["nome"],
                    "valor": item["valor"],
                    "pct": round(pct, 1)
                })
            return res
        
        ranking_colaboradores = build_rank(ranking_colab_dict, total)
        ranking_categorias = build_rank(ranking_cat_dict, total)

        bf_cats = sorted(list(butterfly_cats))
        bf_comercial = [round(comercial_dict.get(c, 0), 2) for c in bf_cats]
        bf_marketing = [round(marketing_dict.get(c, 0), 2) for c in bf_cats]
        butterfly = {
            "categorias": bf_cats,
            "comercial": bf_comercial,
            "marketing": bf_marketing
        }

        det_colabs = []
        for colab, info in matriz_colabs.items():
            info["colaborador"] = colab
            info["total"] = round(info["total"], 2)
            for c in info["valores"]:
                info["valores"][c] = round(info["valores"][c], 2)
            det_colabs.append(info)
        det_colabs.sort(key=lambda x: x["total"], reverse=True)

        from app.models.centro_custo import CentroEstado
        mapa_agg = (
            base_q().with_entities(
                CentroEstado.estado.label("estado"),
                func.sum(Movimentacao.valor).label("total")
            )
            .outerjoin(CentroEstado, Colaborador.idCentroCusto == CentroEstado.idCentroCusto)
            .group_by(CentroEstado.estado).all()
        )
        
        sigla_para_nome = {
            "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
            "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
            "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
            "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
            "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
            "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
            "SE": "Sergipe", "TO": "Tocantins"
        }
        upper_to_correct = {v.upper(): v for v in sigla_para_nome.values()}
        upper_to_correct.update(sigla_para_nome)
        
        mapa_data = []
        for r in mapa_agg:
            estado_original = (r.estado or "").strip().upper()
            if not estado_original: continue
            nome_estado = upper_to_correct.get(estado_original, estado_original)
            mapa_data.append({"name": nome_estado, "value": round(float(r.total or 0), 2)})

        return {
            "analiticoTotalDespesas": round(total, 2),
            "meses": meses_labels,
            "barrasVerticais": barras_verticais,
            "categoriaBarras": cat_barras_list,
            "butterfly": butterfly,
            "evolucaoCentroCusto": {
                "meses": meses_labels,
                "series": evolucao_cc_series
            },
            "centroCustoBarras": cc_barras_list,
            "mapaData": mapa_data,
            "rankingColaboradores": ranking_colaboradores,
            "rankingCategorias": ranking_categorias,
            "detalhesMatrizOriginal": det_colabs,
            "detalhesCategoriasColunas": bf_cats,
            "detalhesTotaisPorCategoria": cat_barras_dict,
            "detalhesTotalGeral": round(total, 2),
            "detalhes": det_colabs
        }

    def obter_relatorio(self, filtros: dict) -> dict:
        from sqlalchemy import func
        from app.models.movimentacao import Movimentacao
        from app.models.categoria import Categoria
        from app.models.colaborador import Colaborador
        from app.models.centro_custo import CentroCusto
        from app.models.empresa import Empresa
        from app.models.user import User
        from app.models.importacao import Importacao
        
        q = self.db.query(
            Movimentacao.valor,
            Categoria.nome.label("categoria_nome"),
            Colaborador.nome.label("colab_nome"),
            Empresa.nome.label("empresa_nome"),
            CentroCusto.nome.label("cc_nome"),
            CentroCusto.codigo.label("cc_codigo")
        ).outerjoin(Importacao, Movimentacao.idImportacoes == Importacao.idImportacoes) \
         .outerjoin(Categoria, Movimentacao.idCategoria == Categoria.idCategorias) \
         .outerjoin(Colaborador, Movimentacao.idColaborador == Colaborador.idColaborador) \
         .outerjoin(CentroCusto, Colaborador.idCentroCusto == CentroCusto.idCentroCusto) \
         .outerjoin(Empresa, Movimentacao.idEmpresa == Empresa.idEmpresas) \
         .filter((Movimentacao.idImportacoes == None) | (Importacao.tipo == 'IA_DESPESAS'))

        if filtros.get("data_inicio"):
            q = q.filter(Movimentacao.createdAt >= f"{filtros['data_inicio']} 00:00:00")
        if filtros.get("data_fim"):
            q = q.filter(Movimentacao.createdAt <= f"{filtros['data_fim']} 23:59:59")
        if filtros.get("id_empresa"):
            q = q.filter(Movimentacao.idEmpresa == filtros["id_empresa"])
        if filtros.get("id_colaborador"):
            q = q.filter(Movimentacao.idColaborador == filtros["id_colaborador"])
        if filtros.get("id_centro_custo"):
            q = q.filter(CentroCusto.nome == filtros["id_centro_custo"])

        movs = q.all()

        matriz_colabs = {}
        categorias_set = set()
        totais_cat = {}
        total_geral = 0.0

        for r in movs:
            val = float(r.valor or 0)
            total_geral += val
            cat = r.categoria_nome or "Sem Categoria"
            colab = r.colab_nome or "Desconhecido"
            empresa = r.empresa_nome or ""
            cc_nome = r.cc_nome or ""
            cc_codigo = r.cc_codigo or ""
            
            categorias_set.add(cat)
            totais_cat[cat] = totais_cat.get(cat, 0) + val
            
            if colab not in matriz_colabs:
                matriz_colabs[colab] = {
                    "colaboradorNome": colab,
                    "empresaNome": empresa,
                    "centroCustoNome": cc_nome,
                    "centroCustoCodigo": cc_codigo,
                    "valoresPorCategoria": {},
                    "total": 0
                }
            matriz_colabs[colab]["valoresPorCategoria"][cat] = matriz_colabs[colab]["valoresPorCategoria"].get(cat, 0) + val
            matriz_colabs[colab]["total"] += val

        det_colabs = list(matriz_colabs.values())
        det_colabs.sort(key=lambda x: x["total"], reverse=True)
        cat_list = sorted(list(categorias_set))

        return {
            "detalhesMatrizOriginal": det_colabs,
            "detalhesCategoriasColunas": cat_list,
            "detalhesTotaisPorCategoria": totais_cat,
            "detalhesTotalGeral": round(total_geral, 2)
        }
