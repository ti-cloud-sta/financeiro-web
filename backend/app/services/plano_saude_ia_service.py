import io
import re
from datetime import datetime

import pandas as pd
from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.models.colaborador import Colaborador
from app.models.empresa import Empresa
from app.models.importacao import Importacao
from app.models.movimentacao import Movimentacao
from app.repositories.categoria_repository import CategoriaRepository
from app.repositories.colaborador_alias_repository import ColaboradorAliasRepository
from app.repositories.colaborador_repository import ColaboradorRepository
from app.repositories.empresa_repository import EmpresaRepository
from app.schemas.categoria import CategoriaCreate
from app.schemas.plano_saude import (
    ConfirmarImportacaoSorrisoPayload,
    ConfirmarImportacaoUnimedPayload,
    ExportarSorrisoExcelPayload,
    ExportarUnimedExcelPayload,
)
from app.services.ia_service import IAService


class PlanoSaudeIAService:
    """Extração (IA/regex), confirmação e exportação das faturas de Plano de Saúde
    (Sorriso, Unimed Odonto e a rota universal por regex). Extraído de
    `app/routers/importacoes.py` para seguir o padrão Router -> Service -> Repository
    do resto do projeto."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _normaliza_cpf(documento) -> str:
        """Normaliza um CPF para 11 dígitos, completando com zero(s) à esquerda quando
        vier mais curto (o sistema de origem do PDF às vezes guarda o CPF como número,
        o que derruba de 1 a 3 zeros à esquerda — não dá pra saber quantos de antemão)."""
        digitos = re.sub(r'\D', '', str(documento or ''))
        if 8 <= len(digitos) <= 11:
            digitos = digitos.zfill(11)
        return digitos

    # ------------------------------------------------------------------
    # Resolução de colaborador (compartilhada entre Sorriso e a rota universal)
    # ------------------------------------------------------------------
    def _resolver_colaborador(self, colab_repo, alias_repo, nomes_colaboradores, documento, nome_pdf, permite_fallback_nome=False):
        """Resolve o Colaborador de um beneficiário extraído de um PDF de plano de saúde.

        A identificação é feita EXCLUSIVAMENTE pelo CPF ('documento') sempre que o
        documento traz esse campo — nunca por aproximação/comparação de nome, já que
        o nome do beneficiário no PDF frequentemente diverge do cadastro (abreviações,
        "DA"/"DE" omitidos, acentuação, etc.) e usar nome como critério de identidade
        nesses casos gera vínculos incorretos.

        Quando o PDF traz CPF → busca o Colaborador somente por ele.
        Quando o PDF NÃO traz CPF:
        - primeiro tenta um vínculo já ensinado manualmente antes para aquele texto
          exato (alias) — não é aproximação, é recall de uma decisão humana anterior;
        - se `permite_fallback_nome` for True (layout do fornecedor estruturalmente
          nunca tem CPF, ex.: Analítico de Taxa/Serviço da Unimed), tenta ainda uma
          comparação EXATA de nome com o cadastro (maiúsculas, sem acento, sem espaço
          duplicado — nunca por similaridade/aproximação);
        - caso contrário, fica sem vínculo automático e precisa ser associado
          manualmente na tela de conferência.
        """
        if documento:
            doc_normalizado = self._normaliza_cpf(documento)
            if len(doc_normalizado) == 11:
                colab = colab_repo.get_by_documento(doc_normalizado)
                if colab:
                    return colab, colab.nome
            # CPF fornecido mas não encontrado no banco → não inventa vínculo por nome
            return None, nome_pdf

        alias_record = alias_repo.get_by_nome_divergente(nome_pdf)
        if alias_record and alias_record.colaborador:
            return alias_record.colaborador, alias_record.colaborador.nome

        if permite_fallback_nome:
            colab = colab_repo.get_by_nome_normalizado(nome_pdf)
            if colab:
                return colab, colab.nome

        return None, nome_pdf

    @staticmethod
    def _montar_validacoes(titulares_extraidos):
        nomes_titulares = [t["nome_pdf"].strip().upper() for t in titulares_extraidos]
        titulares_unicos = set(nomes_titulares)

        nomes_dependentes = []
        for t in titulares_extraidos:
            for d in t.get("dependentes", []):
                nomes_dependentes.append(d["nome"].strip().upper())

        intersection = titulares_unicos.intersection(set(nomes_dependentes))

        soma_individual = 0.0
        soma_grupo = 0.0
        for t in titulares_extraidos:
            val_tit = t["valor_titular"]
            val_deps = sum(d["valor"] for d in t.get("dependentes", []))
            soma_individual += val_tit + val_deps
            soma_grupo += t["valor_total"]

        validacoes = {
            "apenas_titulares_na_tabela": True,
            "sem_titulares_duplicados": len(nomes_titulares) == len(titulares_unicos),
            "sem_dependentes_como_titulares": len(intersection) == 0,
            "soma_individual_bate_com_total_geral": round(soma_individual, 2) == round(soma_grupo, 2),
            "titulares_count": len(titulares_extraidos),
            "dependentes_count": len(nomes_dependentes),
            "total_count": len(titulares_extraidos) + len(nomes_dependentes),
        }

        validacoes_sucesso = all([
            validacoes["sem_titulares_duplicados"],
            validacoes["sem_dependentes_como_titulares"],
            validacoes["soma_individual_bate_com_total_geral"],
        ])

        return validacoes, validacoes_sucesso, round(soma_grupo, 2)

    def _resolver_empresa_e_categoria(self, id_empresa):
        emp_repo = EmpresaRepository(self.db)
        cat_repo = CategoriaRepository(self.db)

        emp = None
        if id_empresa is not None:
            emp = emp_repo.get_by_id(id_empresa)

        if not emp:
            emp = emp_repo.get_by_nome("RDV - SANTA MARIA")
        if not emp:
            empresas_todas = self.db.query(Empresa).all()
            if empresas_todas:
                emp = empresas_todas[0]
            else:
                raise HTTPException(status_code=400, detail="Empresa RDV - SANTA MARIA não encontrada.")

        is_seguro = "seguro" in emp.nome.lower()

        if is_seguro:
            cat = cat_repo.get_by_id(9)
            if not cat:
                cat = cat_repo.get_by_nome("Seguro/Saúde")
            if not cat:
                cat = cat_repo.get_by_nome("Seguro/Saude")
            if not cat:
                try:
                    novo_cat = CategoriaCreate(nome="Seguro/Saúde", descricao="Despesas com seguros e saúde")
                    cat = cat_repo.create(novo_cat)
                except Exception:
                    cat = None
            if not cat:
                class MockCat:
                    idCategorias = 9
                cat = MockCat()
        else:
            cat = cat_repo.get_by_nome("Plano de Saúde")
            if not cat:
                cat = cat_repo.get_by_nome("Plano de Saude")
            if not cat:
                try:
                    novo_cat = CategoriaCreate(nome="Plano de Saúde", descricao="Despesas com planos de saúde e odontológicos")
                    cat = cat_repo.create(novo_cat)
                except Exception:
                    cat = cat_repo.get_by_id(8)
                    if not cat:
                        raise HTTPException(status_code=400, detail="Categoria Plano de Saúde não encontrada e fallback falhou.")

        return emp, cat, is_seguro

    # ------------------------------------------------------------------
    # Rota universal (regex, sem IA)
    # ------------------------------------------------------------------
    async def analisar_universal(self, file: UploadFile) -> dict:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Arquivo inválido")

        content = await file.read()

        colab_repo = ColaboradorRepository(self.db)
        colabs_db, _ = colab_repo.get_all(limit=5000)
        nomes_colaboradores = [c.nome for c in colabs_db]

        ia = IAService()
        eh_planilha = file.filename.lower().endswith(('.csv', '.xlsx', '.xls'))
        if eh_planilha:
            res = ia.extrair_beneficiarios_planilha(
                file_content=content,
                file_name=file.filename,
            )
        else:
            res = await ia.extrair_beneficiarios_pdf_universal(
                file_content=content,
                file_name=file.filename,
            )

        titulares_extraidos = res.get("titulares", [])
        metrics = res.get("metrics", {})

        if not titulares_extraidos:
            sem_texto = metrics.get('total_chars', 0) < 20
            tentou_ia = metrics.get('tentou_fallback_ia', False)
            gemini_ok = metrics.get('gemini_configurado', False)
            detalhe = f"Não foi possível extrair beneficiários do arquivo '{file.filename}'. "
            if sem_texto:
                detalhe += "O PDF parece ser uma imagem escaneada, sem texto selecionável. "
            if tentou_ia and gemini_ok:
                detalhe += "O fallback via IA também foi acionado, mas não retornou resultados. "
            elif tentou_ia and not gemini_ok:
                detalhe += (
                    "O fallback via IA foi necessário, mas a GEMINI_API_KEY não está configurada no servidor. "
                )
            detalhe += "Verifique se o PDF contém uma lista de beneficiários legível."
            raise HTTPException(status_code=422, detail=detalhe)

        alias_repo = ColaboradorAliasRepository(self.db)
        permite_fallback_nome = metrics.get("permite_fallback_nome", False)

        for t in titulares_extraidos:
            nome_pdf = t.get("nome_pdf", "")
            documento = t.get("documento")

            colab, nome_db = self._resolver_colaborador(
                colab_repo, alias_repo, nomes_colaboradores, documento, nome_pdf,
                permite_fallback_nome=permite_fallback_nome
            )
            t["nome_db"] = nome_db
            t["id_db"] = colab.idColaborador if colab else None

            if colab and colab.centro_custo:
                t["centro_custo"] = str(colab.centro_custo.codigo)
            else:
                t["centro_custo"] = "N/D"

        validacoes, validacoes_sucesso, total_geral = self._montar_validacoes(titulares_extraidos)

        return {
            "sucesso": True,
            "dados": titulares_extraidos,
            "validacoes": validacoes,
            "validacoes_sucesso": validacoes_sucesso,
            "total_geral": total_geral,
            "metrics": metrics,
        }

    # ------------------------------------------------------------------
    # Sorriso (via IA/Gemini)
    # ------------------------------------------------------------------
    async def analisar_sorriso(self, file: UploadFile) -> dict:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Arquivo inválido")

        content = await file.read()

        colab_repo = ColaboradorRepository(self.db)
        colabs_db, _ = colab_repo.get_all(limit=5000)
        nomes_colaboradores = [c.nome for c in colabs_db]

        ia = IAService()
        res_ia = await ia.analisar_plano_saude_sorriso(
            file_content=content,
            file_name=file.filename,
            colaboradores=nomes_colaboradores,
        )

        titulares_extraidos = res_ia.get("titulares", [])

        alias_repo = ColaboradorAliasRepository(self.db)

        # Injetar o Centro de Custo correspondente do banco para cada titular.
        # Matching prioriza o CPF extraído pela IA, com fallback para alias + nome aproximado.
        for t in titulares_extraidos:
            nome_pdf = t.get("nome_pdf", "")
            documento = t.get("documento")

            colab, nome_db = self._resolver_colaborador(
                colab_repo, alias_repo, nomes_colaboradores, documento, nome_pdf
            )
            t["nome_db"] = nome_db
            t["id_db"] = colab.idColaborador if colab else None

            if colab and colab.centro_custo:
                t["centro_custo"] = str(colab.centro_custo.codigo)
            else:
                t["centro_custo"] = "N/D"

        validacoes, validacoes_sucesso, total_geral = self._montar_validacoes(titulares_extraidos)

        return {
            "sucesso": True,
            "dados": titulares_extraidos,
            "validacoes": validacoes,
            "validacoes_sucesso": validacoes_sucesso,
            "total_geral": total_geral,
        }

    def confirmar_sorriso(self, payload: ConfirmarImportacaoSorrisoPayload, current_user) -> dict:
        colab_repo = ColaboradorRepository(self.db)

        emp, cat, is_seguro = self._resolver_empresa_e_categoria(payload.idEmpresa)

        extensao = payload.nomeArquivo.split('.')[-1] if '.' in payload.nomeArquivo else 'pdf'
        tipo_importacao = "SEGURO" if is_seguro else "PLANO_SAUDE"

        nova_importacao = Importacao(
            nomeArquivo=payload.nomeArquivo,
            extensaoArquivo=extensao,
            idEmpresa=emp.idEmpresas,
            tipo=tipo_importacao,
            idUserInc=current_user.iduser,
        )
        self.db.add(nova_importacao)
        self.db.flush()  # Gerar idImportacoes

        movimentacoes_criadas = 0
        erros_colaboradores = []

        for t in payload.titulares:
            colab = None
            if t.id_db:
                # Vínculo feito manualmente pelo usuário na tela de conferência
                # (ex.: beneficiário sem CPF no PDF) — usa diretamente, sem reavaliar.
                colab = colab_repo.get_by_id(t.id_db)
            if not colab and t.documento:
                doc_normalizado = self._normaliza_cpf(t.documento)
                if len(doc_normalizado) == 11:
                    colab = colab_repo.get_by_documento(doc_normalizado)

            if not colab:
                erros_colaboradores.append(t.nome_pdf)
                continue

            # --- SALVAR O ALIAS / APRENDIZADO ---
            if t.nome_pdf and t.nome_pdf.strip().upper() != colab.nome.strip().upper():
                try:
                    alias_repo = ColaboradorAliasRepository(self.db)
                    alias_repo.create_or_update(colab.idColaborador, t.nome_pdf.strip())
                except Exception as ex:
                    print(f"[WARN] Falha ao salvar Alias de colaborador: {ex}")

            nova_mov = Movimentacao(
                idCategoria=cat.idCategorias,
                idColaborador=colab.idColaborador,
                idEmpresa=emp.idEmpresas,
                idImportacoes=nova_importacao.idImportacoes,
                idUnidade=payload.idUnidade,
                valor=t.valor_total,
            )

            if payload.dataCompetencia:
                try:
                    data_comp = datetime.strptime(payload.dataCompetencia, "%Y-%m-%d")
                    nova_mov.createdAt = data_comp
                except ValueError:
                    pass

            self.db.add(nova_mov)
            movimentacoes_criadas += 1

        if erros_colaboradores:
            print(f"[WARN] Colaboradores não encontrados: {erros_colaboradores}")

        self.db.commit()
        return {
            "sucesso": True,
            "idImportacoes": nova_importacao.idImportacoes,
            "movimentacoes_criadas": movimentacoes_criadas,
            "erros_colaboradores": erros_colaboradores,
        }

    @staticmethod
    def exportar_sorriso(payload: ExportarSorrisoExcelPayload) -> StreamingResponse:
        rows = []
        total_geral = 0.0
        for t in payload.titulares:
            rows.append({
                "Beneficiário (Titular)": t.nome_db or t.nome_pdf,
                "Centro de Custo": t.centro_custo or "N/D",
                "Valor Total": t.valor_total,
            })
            total_geral += t.valor_total

        rows.append({
            "Beneficiário (Titular)": "TOTAL GERAL",
            "Centro de Custo": "",
            "Valor Total": total_geral,
        })

        df = pd.DataFrame(rows)
        df["Valor Total"] = df["Valor Total"].apply(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Consolidação Sorriso')

        output.seek(0)

        headers_response = {
            'Content-Disposition': 'attachment; filename="planilha_consolidada_sorriso.xlsx"',
            'Access-Control-Expose-Headers': 'Content-Disposition',
        }

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers_response,
        )

    # ------------------------------------------------------------------
    # Unimed Odonto (regex + pypdf, sem IA)
    # ------------------------------------------------------------------
    async def analisar_unimed_odonto(self, file: UploadFile) -> dict:
        content = await file.read()

        colabs_db = self.db.query(Colaborador).all()
        nomes_colaboradores = [c.nome for c in colabs_db]

        ia = IAService()
        res_ia = await ia.analisar_plano_saude_unimed_odonto(
            file_content=content,
            file_name=file.filename,
            colaboradores=nomes_colaboradores,
        )

        titulares_extraidos = res_ia.get("titulares", [])

        colab_repo = ColaboradorRepository(self.db)
        alias_repo = ColaboradorAliasRepository(self.db)

        for t in titulares_extraidos:
            nome_pdf = t.get("nome_pdf", "")
            documento = t.get("documento")

            colab_base, nome_db = self._resolver_colaborador(
                colab_repo, alias_repo, nomes_colaboradores, documento, nome_pdf
            )
            t["nome_db"] = nome_db
            t["id_db"] = colab_base.idColaborador if colab_base else None

            colab = None
            if colab_base:
                colab = self.db.query(Colaborador).options(
                    joinedload(Colaborador.centro_custo),
                ).filter(Colaborador.idColaborador == colab_base.idColaborador).first()

            if colab and colab.centro_custo:
                t["centro_custo"] = str(colab.centro_custo.codigo)
            else:
                t["centro_custo"] = "N/D"

        validacoes, validacoes_sucesso, total_geral = self._montar_validacoes(titulares_extraidos)

        return {
            "sucesso": True,
            "dados": titulares_extraidos,
            "validacoes": validacoes,
            "validacoes_sucesso": validacoes_sucesso,
            "total_geral": total_geral,
        }

    def confirmar_unimed_odonto(self, payload: ConfirmarImportacaoUnimedPayload, current_user) -> dict:
        colab_repo = ColaboradorRepository(self.db)

        emp, cat, is_seguro = self._resolver_empresa_e_categoria(payload.idEmpresa)

        extensao = payload.nomeArquivo.split('.')[-1] if '.' in payload.nomeArquivo else 'pdf'
        tipo_importacao = "SEGURO" if is_seguro else "PLANO_SAUDE"

        nova_importacao = Importacao(
            nomeArquivo=payload.nomeArquivo,
            extensaoArquivo=extensao,
            idEmpresa=emp.idEmpresas,
            tipo=tipo_importacao,
            idUserInc=current_user.iduser,
        )
        self.db.add(nova_importacao)
        self.db.flush()

        movimentacoes_criadas = 0
        erros_colaboradores = []

        for t in payload.titulares:
            colab = None
            if t.id_db:
                # Vínculo feito manualmente pelo usuário na tela de conferência
                # (ex.: beneficiário sem CPF no PDF) — usa diretamente, sem reavaliar.
                colab = colab_repo.get_by_id(t.id_db)
            if not colab and t.documento:
                doc_normalizado = self._normaliza_cpf(t.documento)
                if len(doc_normalizado) == 11:
                    colab = colab_repo.get_by_documento(doc_normalizado)

            if not colab:
                erros_colaboradores.append(t.nome_db)
                continue

            nova_mov = Movimentacao(
                idCategoria=cat.idCategorias,
                idColaborador=colab.idColaborador,
                idEmpresa=emp.idEmpresas,
                idImportacoes=nova_importacao.idImportacoes,
                idUnidade=payload.idUnidade,
                valor=t.valor_total,
            )

            if payload.dataCompetencia:
                try:
                    data_comp = datetime.strptime(payload.dataCompetencia, "%Y-%m-%d")
                    nova_mov.createdAt = data_comp
                except ValueError:
                    pass

            self.db.add(nova_mov)
            movimentacoes_criadas += 1

        if erros_colaboradores:
            print(f"[WARN] Colaboradores não encontrados: {erros_colaboradores}")

        self.db.commit()
        return {
            "sucesso": True,
            "idImportacoes": nova_importacao.idImportacoes,
            "movimentacoes_criadas": movimentacoes_criadas,
            "erros_colaboradores": erros_colaboradores,
        }

    @staticmethod
    def exportar_unimed_odonto(payload: ExportarUnimedExcelPayload) -> StreamingResponse:
        rows = []
        total_geral = 0.0
        for t in payload.titulares:
            rows.append({
                "Beneficiário (Titular)": t.nome_db or t.nome_pdf,
                "Centro de Custo": t.centro_custo or "N/D",
                "Valor Total": t.valor_total,
            })
            total_geral += t.valor_total

        rows.append({
            "Beneficiário (Titular)": "TOTAL GERAL",
            "Centro de Custo": "",
            "Valor Total": total_geral,
        })

        df = pd.DataFrame(rows)
        df["Valor Total"] = df["Valor Total"].apply(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Consolidação Unimed')

        output.seek(0)

        headers_response = {
            'Content-Disposition': 'attachment; filename="planilha_consolidada_unimed_odonto.xlsx"',
            'Access-Control-Expose-Headers': 'Content-Disposition',
        }

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers_response,
        )
