import time
import os
import io
import json
import asyncio
import tempfile
from typing import List, Dict, Any, Tuple, Optional
import pypdf
import pandas as pd
import re
from google import genai
from google.genai import types

from app.schemas.despesas_viagens import EstruturaExtracaoIADespesas

class DespesasViagensParserService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
            self.model_name = "gemini-3.1-pro-preview"
        else:
            self.client = None
            self.model_name = ""

    async def analisar_arquivo(self, file_content: bytes, file_name: str, categorias: List[str], colaboradores: List[str], empresa_context: str, db=None) -> Dict[str, Any]:
        t0_total = time.time()
        
        metrics = {
            "upload_pdf_ms": 0.0,
            "file_ready_ms": 0.0,
            "gemini_generation_ms": 0.0,
            "structured_output_ms": 0.0,
            "post_processing_ms": 0.0,
            "total_ms": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "method": "none",
            "usou_fallback_ia": False
        }

        # 1. Tentar parsear via Python puro primeiro (determinístico)
        despesas_list = []
        parsed_via_python = False
        
        try:
            if file_name.lower().endswith('.pdf'):
                # Verifica se é Onfly
                reader = pypdf.PdfReader(io.BytesIO(file_content))
                first_page = reader.pages[0].extract_text() or ""
                if "kinto" in first_page.lower():
                    parsed_data = self._parse_kinto_pdf(file_content, db)
                    if parsed_data:
                        despesas_list = parsed_data
                        parsed_via_python = True
                
                if not parsed_via_python and first_page.strip() == "" and "rdv" in file_name.lower():
                    parsed_data = await self._parse_santamaria_rdv_via_ia(file_content, file_name, db)
                    if parsed_data:
                        despesas_list = parsed_data
                        parsed_via_python = True

                if not parsed_via_python and ("danfe" in first_page.lower() or "nfe" in file_name.lower()):
                    parsed_data = await self._parse_danfe_rosemary_via_ia(file_content, file_name, db)
                    if parsed_data:
                        despesas_list = parsed_data
                        parsed_via_python = True

                if not parsed_via_python and "localiza rent" in first_page.lower():
                    parsed_data = self._parse_localiza_rent_pdf(file_content, db)
                    if parsed_data:
                        despesas_list = parsed_data
                        parsed_via_python = True
                
                if not parsed_via_python and ("localiza fleet" in first_page.lower() or "fatura de aluguel" in first_page.lower()):
                    parsed_data = self._parse_localiza_pdf(file_content, db)
                    if parsed_data:
                        despesas_list = parsed_data
                        parsed_via_python = True
                
                if not parsed_via_python and "tastur" in file_name.lower():
                    parsed_data = await self._parse_tastur_fatura_via_ia(file_content, file_name, db)
                    if parsed_data:
                        despesas_list = parsed_data
                        parsed_via_python = True
                
                if not parsed_via_python and "maiorca" in first_page.lower():
                    parsed_data = await self._parse_maiorca_fatura_via_ia(file_content, file_name, db)
                    if parsed_data:
                        despesas_list = parsed_data
                        parsed_via_python = True
                
                if not parsed_via_python and "sem parar" in first_page.lower():
                    parsed_data = await self._parse_semparar_fatura_via_ia(file_content, file_name, db)
                    if parsed_data:
                        despesas_list = parsed_data
                        parsed_via_python = True
                
                if not parsed_via_python and "fatura-pj-cartao" in file_name.lower():
                    parsed_data = await self._parse_fatura_cartao_eduardo_via_ia(file_content, file_name, db)
                    if parsed_data:
                        despesas_list = parsed_data
                        parsed_via_python = True
                
                if not parsed_via_python and ("fatura" in file_name.lower() or "fatura" in first_page.lower()):
                    parsed_data = self._parse_onfly_fatura_pdf(file_content, db)
                    if parsed_data:
                        despesas_list = parsed_data
                        parsed_via_python = True
                
                if not parsed_via_python and ("Onfly" in file_name or "onfly" in first_page.lower() or "rdv -" in first_page.lower()):
                    parsed_data = self._parse_onfly_pdf(file_content, db)
                    if parsed_data:
                        despesas_list = parsed_data
                        parsed_via_python = True
        except Exception as e:
            print(f"[DESPESAS PARSER] Erro no parser python: {e}")
        
        # 2. Fallback para IA se o Python falhar ou não encontrar nada
        file_to_delete = None
        if not parsed_via_python or not despesas_list:
            print("[DESPESAS PARSER] Acionando extração via IA (Fallback ou formato desconhecido)")
            metrics["usou_fallback_ia"] = True
            metrics["method"] = "gemini_fallback"
            
            ia_result = await self._analisar_via_ia(file_content, file_name, categorias, colaboradores, empresa_context, metrics, db)
            despesas_list = ia_result.get("despesas", [])
            file_to_delete = ia_result.get("file_name_to_delete")

        metrics["post_processing_ms"] = round((time.time() - t0_total) * 1000, 2)
        metrics["total_ms"] = round((time.time() - t0_total) * 1000, 2)

        return {
            "despesas": despesas_list,
            "metrics": metrics,
            "file_name_to_delete": file_to_delete
        }

    async def _analisar_via_ia(self, file_content: bytes, file_name: str, categorias: List[str], colaboradores: List[str], empresa_context: str, metrics: Dict[str, Any], db=None) -> Dict[str, Any]:
        if not self.client:
            raise Exception("API Key do Gemini não configurada.")
            
        file_size = len(file_content)
        uploaded_file = None
        temp_path = None
        is_inline = file_size < 15 * 1024 * 1024
        
        try:
            if is_inline:
                t0_prep = time.time()
                mime_type = "application/pdf" if file_name.lower().endswith(".pdf") else "text/plain"
                content_part = types.Part.from_bytes(data=file_content, mime_type=mime_type)
                metrics["upload_pdf_ms"] = round((time.time() - t0_prep) * 1000, 2)
                contents = [content_part]
            else:
                t0_prep = time.time()
                ext = ".pdf" if file_name.lower().endswith(".pdf") else ""
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
                    temp_file.write(file_content)
                    temp_path = temp_file.name
                
                mime_type = "application/pdf" if ext == ".pdf" else "text/plain"
                uploaded_file = await self.client.aio.files.upload(
                    file=temp_path,
                    config=types.UploadFileConfig(mime_type=mime_type)
                )
                metrics["upload_pdf_ms"] = round((time.time() - t0_prep) * 1000, 2)
                
                t0_ready = time.time()
                sleep_time = 0.2
                while uploaded_file.state and uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(sleep_time)
                    uploaded_file = await self.client.aio.files.get(name=uploaded_file.name)
                    sleep_time = min(sleep_time * 1.5, 1.0)
                    
                if uploaded_file.state and uploaded_file.state.name == "FAILED":
                    raise Exception("Falha ao processar arquivo na Files API do Gemini.")
                metrics["file_ready_ms"] = round((time.time() - t0_ready) * 1000, 2)
                contents = [uploaded_file]
                
            prompt = f"""
            Você é um assistente especializado em auditoria de faturas de viagens corporativas e despesas de cartão corporativo.
            Sua tarefa é analisar o relatório de despesas fornecido (anexo) para a empresa "{empresa_context}" e estruturar cada transação.

            Regras de Extração e Classificação:
            1. Identifique as despesas individuais. Cada despesa deve ter um Colaborador responsável, uma Empresa relacionada (que deve ser "{empresa_context}"), um Valor e a Data da despesa (se houver, formato YYYY-MM-DD).
            2. Mapeie o Colaborador responsável de cada despesa exclusivamente a partir da lista de colaboradores válidos do sistema fornecida abaixo:
            {json.dumps(colaboradores, ensure_ascii=False)}
            Se o nome no documento estiver ligeiramente diferente (abreviado ou com sobrenomes ocultos), faça a correspondência com o colaborador real correspondente da lista. Se não encontrar nenhuma correspondência plausível, use "Não Identificado" ou o nome mais próximo possível da lista.
            
            3. Classifique a categoria de cada despesa no menor nível possível, escolhendo exclusivamente uma destas categorias disponíveis no sistema:
            {json.dumps(categorias, ensure_ascii=False)}
            Se nenhuma categoria se encaixar perfeitamente, classifique na categoria mais genérica aplicável (como "Outros" ou "Viagens").
            
            Retorne o resultado de forma estruturada estritamente conforme o schema estruturado EstruturaExtracaoIADespesas.
            """
            
            contents.append(prompt)
            
            t0_gen = time.time()
            response = None
            for attempt in range(3):
                try:
                    response = await self.client.aio.models.generate_content(
                        model=self.model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1
                        )
                    )
                    break
                except Exception as e:
                    error_str = str(e)
                    if "429 RESOURCE_EXHAUSTED" in error_str and "Quota exceeded" in error_str:
                        await asyncio.sleep(5.0)
                        continue
                    if any(msg in error_str for msg in ["503", "UNAVAILABLE", "500", "504", "deadline"]):
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    raise e
            
            metrics["gemini_generation_ms"] = round((time.time() - t0_gen) * 1000, 2)
            
            t0_struct = time.time()
            despesas_list = []
            if response and response.parsed:
                despesas_list = [d.model_dump() for d in response.parsed.despesas]
            else:
                raw_text = response.text.strip() if response else ""
                if raw_text:
                    if raw_text.startswith("```json"):
                        raw_text = raw_text[7:]
                    if raw_text.startswith("```"):
                        raw_text = raw_text[3:]
                    if raw_text.endswith("```"):
                        raw_text = raw_text[:-3]
                    raw_text = raw_text.strip()
                    data = json.loads(raw_text)
                    
                    if isinstance(data, list):
                        raw_list = data
                    else:
                        raw_list = data.get("despesas", [])
                        
                    despesas_list = []
                    for item in raw_list:
                        if isinstance(item, dict):
                            normalized_item = {k.lower(): v for k, v in item.items()}
                            despesas_list.append(normalized_item)
            metrics["structured_output_ms"] = round((time.time() - t0_struct) * 1000, 2)
            
            if response and response.usage_metadata:
                metrics["input_tokens"] = response.usage_metadata.prompt_token_count or 0
                metrics["output_tokens"] = response.usage_metadata.candidates_token_count or 0
                metrics["total_tokens"] = response.usage_metadata.total_token_count or 0
            
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            
            
            # Realiza o de-para (enriquecimento com banco de dados) se o DB estiver disponível
            if db:
                from app.repositories.colaborador_repository import ColaboradorRepository
                from app.repositories.colaborador_alias_repository import ColaboradorAliasRepository
                from app.models.categoria import Categoria
                from app.models.categoria_alias import CategoriaAlias

                colab_repo = ColaboradorRepository(db)
                alias_repo = ColaboradorAliasRepository(db)

                for item in despesas_list:
                    # Mapear Categoria
                    cat_name = item.get("categoria", "")
                    cat_id = None
                    categoria_encontrada = False

                    if cat_name:
                        cat = db.query(Categoria).filter(Categoria.nome == cat_name).first()
                        if not cat:
                            alias = db.query(CategoriaAlias).filter(CategoriaAlias.alias == cat_name).first()
                            if alias:
                                cat = db.query(Categoria).filter(Categoria.idCategorias == alias.idCategoria).first()
                        if cat:
                            cat_id = cat.idCategorias
                            item["categoria"] = cat.nome
                            categoria_encontrada = True

                    item["idCategoria"] = cat_id
                    item["categoria_encontrada"] = categoria_encontrada

                    # Mapear Colaborador
                    viajante_nome = item.get("colaborador", "Não Identificado")
                    colaborador_id = None
                    pessoa_encontrada = False

                    if viajante_nome != "Não Identificado":
                        colab = colab_repo.get_by_nome_normalizado(viajante_nome)
                        if not colab:
                            colab_alias = alias_repo.get_by_nome_divergente(viajante_nome)
                            if colab_alias:
                                colab = colab_repo.get_by_id(colab_alias.idColaborador)
                        if colab:
                            colaborador_id = colab.idColaborador
                            item["colaborador"] = colab.nome
                            pessoa_encontrada = True

                    item["idColaborador"] = colaborador_id
                    item["pessoa_encontrada"] = pessoa_encontrada

            return {
                "despesas": despesas_list,
                "file_name_to_delete": uploaded_file.name if uploaded_file else None
            }
            
        except Exception as e:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    def deletar_arquivo(self, file_name: str):
        if not self.client:
            return
        try:
            self.client.files.delete(name=file_name)
            print(f"[Gemini] Arquivo temporário {file_name} deletado com sucesso.")
        except Exception as e:
            print(f"[Gemini] Erro ao deletar arquivo {file_name}: {e}")

    def _parse_onfly_pdf(self, file_content: bytes, db) -> List[Dict]:
        from app.repositories.colaborador_repository import ColaboradorRepository
        from app.models.categoria import Categoria
        from app.models.categoria_alias import CategoriaAlias

        reader = pypdf.PdfReader(io.BytesIO(file_content))
        full_text = ""
        for page in reader.pages:
            full_text += (page.extract_text() or "") + "\n"

        # Extrair CPF e Nome
        cpf_match = re.search(r'CPF:\s*([\d\.\-]+)', full_text)
        cpf_norm = ""
        if cpf_match:
            from app.repositories.colaborador_repository import ColaboradorRepository
            cpf_norm = ColaboradorRepository._normaliza_cpf(cpf_match.group(1))

        nome_match = re.search(r'Colaborador:\s*([^\n]+)', full_text)
        colaborador_nome = nome_match.group(1).strip() if nome_match else "Não Identificado"

        rdv_match = re.search(r'(RDV\s*-\s*#\d+)', full_text)
        codigo_rdv = rdv_match.group(1).strip() if rdv_match else None

        # Resolução de Colaborador via BD
        colaborador_id = None
        pessoa_encontrada = False
        if db and cpf_norm:
            colab_repo = ColaboradorRepository(db)
            colab = colab_repo.get_by_documento(cpf_norm)
            if colab:
                colaborador_id = colab.idColaborador
                colaborador_nome = colab.nome
                pessoa_encontrada = True

        # Resumo de custos
        despesas = []
        resumo_match = re.search(r'Categorias de despesa\s*(.*?)(?=Total despesas|Total custo da viagem)', full_text, re.DOTALL)
        if resumo_match:
            linhas = resumo_match.group(1).strip().split('\n')
            for linha in linhas:
                linha = linha.strip()
                if not linha: continue
                # Match linha: "Combustível R$ 320,09" ou similar
                match_val = re.search(r'(.*?)\s+R\$\s*([\d\.,]+)', linha)
                if match_val:
                    cat_name = match_val.group(1).strip()
                    val_str = match_val.group(2).replace('.', '').replace(',', '.')
                    
                    cat_id = None
                    categoria_encontrada = False
                    if db:
                        # 1. Exact match
                        cat = db.query(Categoria).filter(Categoria.nome == cat_name).first()
                        if not cat:
                            # 2. Alias match
                            alias = db.query(CategoriaAlias).filter(CategoriaAlias.alias == cat_name).first()
                            if alias:
                                cat = db.query(Categoria).filter(Categoria.idCategorias == alias.idCategoria).first()
                        
                        if cat:
                            cat_id = cat.idCategorias
                            cat_name = cat.nome
                            categoria_encontrada = True

                    despesas.append({
                        "colaborador": colaborador_nome,
                        "idColaborador": colaborador_id,
                        "cpf": cpf_norm,
                        "pessoa_encontrada": pessoa_encontrada,
                        "categoria": cat_name,
                        "idCategoria": cat_id,
                        "categoria_encontrada": categoria_encontrada,
                        "valor": float(val_str),
                        "codigo_rdv": codigo_rdv
                    })
        return despesas

    def _parse_onfly_fatura_pdf(self, file_content: bytes, db) -> List[Dict]:
        from app.repositories.colaborador_repository import ColaboradorRepository
        from app.repositories.colaborador_alias_repository import ColaboradorAliasRepository
        from app.models.categoria import Categoria
        from app.models.categoria_alias import CategoriaAlias

        reader = pypdf.PdfReader(io.BytesIO(file_content))
        full_text = ""
        for page in reader.pages:
            full_text += (page.extract_text() or "") + "\n"

        fatura_match = re.search(r'Fatura\s+(\d+)', full_text)
        codigo_rdv = f"Fatura {fatura_match.group(1)}" if fatura_match else None
        
        full_text_cleaned = re.sub(r'ONFLY TECNOLOGIA LTDA.*?Data de vencimento:\s*\d{2}/\d{2}/\d{4}', '', full_text, flags=re.DOTALL)

        pattern = r'(Hotel|Aéreo|Carro|Ônibus|Transfer|Hospedagem|Voo|Seguro)\s+([A-Z0-9]{5,8})\s+(\d{2}/\d{2}/\d{4})(.*?)(R\$\s*[\d\.,]+)'
        matches = re.finditer(pattern, full_text_cleaned, flags=re.DOTALL)

        def extract_viajante(names_str):
            names_str = names_str.strip()
            words = [w for w in names_str.split() if w]
            if len(words) % 2 == 0:
                half = len(words) // 2
                if words[:half] == words[half:]:
                    return " ".join(words[:half])
            for i in range(len(names_str) // 2 - 2, len(names_str) // 2 + 3):
                if i > 0 and names_str[:i].strip() == names_str[i:].strip():
                    return names_str[:i].strip()
            return names_str

        despesas = []
        colab_repo = ColaboradorRepository(db) if db else None
        alias_repo = ColaboradorAliasRepository(db) if db else None

        for m in matches:
            modal = m.group(1).strip()
            middle_text = m.group(4)
            valor_str = m.group(5).replace('R$', '').replace('.', '').replace(',', '.').strip()
            
            dates_match = re.search(r'(\d{2}/\d{2}/\d{4})\s*(\d{2}/\d{2}/\d{4})(.*)', middle_text, flags=re.DOTALL)
            viajante_nome = "Não Identificado"
            if dates_match:
                rest = dates_match.group(3).strip()
                cc_match = re.search(r'(\d+\s*-.*)', rest, flags=re.DOTALL)
                if cc_match:
                    names_part = rest[:cc_match.start()].strip()
                    names_clean = re.sub(r'\s+', ' ', names_part)
                    viajante_nome = extract_viajante(names_clean)

            colaborador_id = None
            pessoa_encontrada = False
            
            if db and viajante_nome != "Não Identificado":
                colab = colab_repo.get_by_nome_normalizado(viajante_nome)
                if not colab:
                    colab_alias = alias_repo.get_by_nome_divergente(viajante_nome)
                    if colab_alias:
                        colab = colab_repo.get_by_id(colab_alias.idColaborador)
                
                if colab:
                    colaborador_id = colab.idColaborador
                    viajante_nome = colab.nome
                    pessoa_encontrada = True

            cat_name = modal
            cat_id = None
            categoria_encontrada = False
            if db:
                cat = db.query(Categoria).filter(Categoria.nome == cat_name).first()
                if not cat:
                    alias = db.query(CategoriaAlias).filter(CategoriaAlias.alias == cat_name).first()
                    if alias:
                        cat = db.query(Categoria).filter(Categoria.idCategorias == alias.idCategoria).first()
                
                if cat:
                    cat_id = cat.idCategorias
                    cat_name = cat.nome
                    categoria_encontrada = True

            despesas.append({
                "colaborador": viajante_nome,
                "idColaborador": colaborador_id,
                "cpf": "",
                "pessoa_encontrada": pessoa_encontrada,
                "categoria": cat_name,
                "idCategoria": cat_id,
                "categoria_encontrada": categoria_encontrada,
                "valor": float(valor_str),
                "codigo_rdv": codigo_rdv
            })

        return despesas

    def _parse_localiza_pdf(self, file_content: bytes, db) -> List[Dict]:
        from app.repositories.colaborador_repository import ColaboradorRepository
        from app.repositories.colaborador_alias_repository import ColaboradorAliasRepository
        from app.models.categoria import Categoria
        from app.models.categoria_alias import CategoriaAlias

        reader = pypdf.PdfReader(io.BytesIO(file_content))
        full_text = ""
        for page in reader.pages:
            full_text += (page.extract_text() or "") + "\n"

        fatura_match = re.search(r'Fatura[:\s]*[A-Z]*[- ]?(\d+)', full_text)
        codigo_rdv = fatura_match.group(1) if fatura_match else None
        
        pattern = r'Condutor:\s*(.*?)\s*Início Cobrança:.*?Total\s+([\d\.,]+)'
        matches = re.finditer(pattern, full_text, flags=re.DOTALL)

        despesas = []
        colab_repo = ColaboradorRepository(db) if db else None
        alias_repo = ColaboradorAliasRepository(db) if db else None

        cat_name = "Locação de Veiculo"
        cat_id = None
        categoria_encontrada = False

        if db:
            cat = db.query(Categoria).filter(Categoria.nome == cat_name).first()
            if not cat:
                alias = db.query(CategoriaAlias).filter(CategoriaAlias.alias == cat_name).first()
                if alias:
                    cat = db.query(Categoria).filter(Categoria.idCategorias == alias.idCategoria).first()
            
            if cat:
                cat_id = cat.idCategorias
                cat_name = cat.nome
                categoria_encontrada = True

        for m in matches:
            condutor = m.group(1).replace('\n', ' ').strip()
            valor_str = m.group(2).replace('.', '').replace(',', '.').strip()
            
            viajante_nome = condutor
            colaborador_id = None
            pessoa_encontrada = False
            
            if db and viajante_nome:
                colab = colab_repo.get_by_nome_normalizado(viajante_nome)
                if not colab:
                    colab_alias = alias_repo.get_by_nome_divergente(viajante_nome)
                    if colab_alias:
                        colab = colab_repo.get_by_id(colab_alias.idColaborador)
                
                if colab:
                    colaborador_id = colab.idColaborador
                    viajante_nome = colab.nome
                    pessoa_encontrada = True

            despesas.append({
                "colaborador": viajante_nome,
                "idColaborador": colaborador_id,
                "cpf": "",
                "pessoa_encontrada": pessoa_encontrada,
                "categoria": cat_name,
                "idCategoria": cat_id,
                "categoria_encontrada": categoria_encontrada,
                "valor": float(valor_str),
                "codigo_rdv": codigo_rdv
            })

        return despesas

    def _parse_localiza_rent_pdf(self, file_content: bytes, db) -> List[Dict]:
        from app.repositories.colaborador_repository import ColaboradorRepository
        from app.repositories.colaborador_alias_repository import ColaboradorAliasRepository
        from app.models.categoria import Categoria
        from app.models.categoria_alias import CategoriaAlias

        reader = pypdf.PdfReader(io.BytesIO(file_content))
        full_text = ""
        for page in reader.pages:
            full_text += (page.extract_text() or "") + "\n"

        fatura_match = re.search(r'Fatura\s+(\d+)', full_text, flags=re.IGNORECASE)
        codigo_rdv = f"FATURA {fatura_match.group(1)}" if fatura_match else None
        
        usuario_match = re.search(r'Usuário:\s*\d*\s*(.*?)\n', full_text, flags=re.IGNORECASE)
        viajante_nome = usuario_match.group(1).strip() if usuario_match else "Não Identificado"
        
        saldo_match = re.search(r'SALDO DEVIDO\s+([\d\.,]+)', full_text, flags=re.IGNORECASE)
        valor_str = saldo_match.group(1).replace('.', '').replace(',', '.').strip() if saldo_match else "0"

        despesas = []
        colab_repo = ColaboradorRepository(db) if db else None
        alias_repo = ColaboradorAliasRepository(db) if db else None

        cat_name = "Locação de Veiculo"
        cat_id = None
        categoria_encontrada = False

        if db:
            cat = db.query(Categoria).filter(Categoria.nome == cat_name).first()
            if not cat:
                alias = db.query(CategoriaAlias).filter(CategoriaAlias.alias == cat_name).first()
                if alias:
                    cat = db.query(Categoria).filter(Categoria.idCategorias == alias.idCategoria).first()
            
            if cat:
                cat_id = cat.idCategorias
                cat_name = cat.nome
                categoria_encontrada = True

        colaborador_id = None
        pessoa_encontrada = False
        
        if db and viajante_nome != "Não Identificado":
            colab = colab_repo.get_by_nome_normalizado(viajante_nome)
            if not colab:
                colab_alias = alias_repo.get_by_nome_divergente(viajante_nome)
                if colab_alias:
                    colab = colab_repo.get_by_id(colab_alias.idColaborador)
            
            if colab:
                colaborador_id = colab.idColaborador
                viajante_nome = colab.nome
                pessoa_encontrada = True

        if float(valor_str) > 0 or viajante_nome != "Não Identificado":
            despesas.append({
                "colaborador": viajante_nome,
                "idColaborador": colaborador_id,
                "cpf": "",
                "pessoa_encontrada": pessoa_encontrada,
                "categoria": cat_name,
                "idCategoria": cat_id,
                "categoria_encontrada": categoria_encontrada,
                "valor": float(valor_str),
                "codigo_rdv": codigo_rdv
            })

        return despesas

    def _parse_kinto_pdf(self, file_content: bytes, db) -> List[Dict]:
        from app.repositories.colaborador_repository import ColaboradorRepository
        from app.repositories.colaborador_alias_repository import ColaboradorAliasRepository
        from app.models.categoria import Categoria
        from app.models.categoria_alias import CategoriaAlias

        reader = pypdf.PdfReader(io.BytesIO(file_content))
        full_text = ""
        for page in reader.pages:
            full_text += (page.extract_text() or "") + "\n"

        fatura_match = re.search(r'(\d+)http://www\.kinto', full_text, flags=re.IGNORECASE)
        codigo_rdv = f"FATURA {fatura_match.group(1)}" if fatura_match else None
        
        viajante_nome = "Rubens P. V. A. Netto"
        
        saldo_match = re.search(r'([\d\.,]+)VALOR TOTAL', full_text, flags=re.IGNORECASE)
        valor_str = saldo_match.group(1).replace('.', '').replace(',', '.').strip() if saldo_match else "0"

        despesas = []
        colab_repo = ColaboradorRepository(db) if db else None
        alias_repo = ColaboradorAliasRepository(db) if db else None

        cat_name = "Locação de Veiculo"
        cat_id = None
        categoria_encontrada = False

        if db:
            cat = db.query(Categoria).filter(Categoria.nome == cat_name).first()
            if not cat:
                alias = db.query(CategoriaAlias).filter(CategoriaAlias.alias == cat_name).first()
                if alias:
                    cat = db.query(Categoria).filter(Categoria.idCategorias == alias.idCategoria).first()
            
            if cat:
                cat_id = cat.idCategorias
                cat_name = cat.nome
                categoria_encontrada = True

        colaborador_id = None
        pessoa_encontrada = False
        
        if db and viajante_nome != "Não Identificado":
            colab = colab_repo.get_by_nome_normalizado(viajante_nome)
            if not colab:
                colab_alias = alias_repo.get_by_nome_divergente(viajante_nome)
                if colab_alias:
                    colab = colab_repo.get_by_id(colab_alias.idColaborador)
            
            if colab:
                colaborador_id = colab.idColaborador
                viajante_nome = colab.nome
                pessoa_encontrada = True

        if float(valor_str) > 0:
            despesas.append({
                "colaborador": viajante_nome,
                "idColaborador": colaborador_id,
                "cpf": "",
                "pessoa_encontrada": pessoa_encontrada,
                "categoria": cat_name,
                "idCategoria": cat_id,
                "categoria_encontrada": categoria_encontrada,
                "valor": float(valor_str),
                "codigo_rdv": codigo_rdv
            })

        return despesas

    async def _parse_santamaria_rdv_via_ia(self, file_content: bytes, file_name: str, db) -> List[Dict]:
        from google.genai import types
        import json
        import tempfile
        import asyncio
        from app.repositories.colaborador_repository import ColaboradorRepository
        from app.repositories.colaborador_alias_repository import ColaboradorAliasRepository
        from app.models.categoria import Categoria
        from app.models.categoria_alias import CategoriaAlias

        if not self.client:
            return []
            
        file_size = len(file_content)
        uploaded_file = None
        is_inline = file_size < 15 * 1024 * 1024
        contents = []
        
        try:
            if is_inline:
                content_part = types.Part.from_bytes(data=file_content, mime_type="application/pdf")
                contents = [content_part]
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                    temp_file.write(file_content)
                    temp_path = temp_file.name
                
                uploaded_file = await self.client.aio.files.upload(
                    file=temp_path,
                    config=types.UploadFileConfig(mime_type="application/pdf")
                )
                
                sleep_time = 0.2
                while uploaded_file.state and uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(sleep_time)
                    uploaded_file = await self.client.aio.files.get(name=uploaded_file.name)
                    sleep_time = min(sleep_time * 1.5, 1.0)
                    
                contents = [uploaded_file]
                
            prompt = """
Analise a imagem deste Relatório de Despesas de Viagem e extraia as despesas listadas na tabela "Descrição" / "Vr.Total".
Para cada despesa que tiver um valor preenchido na coluna Vr.Total (ignorar linhas zeradas ou vazias), extraia:

- colaborador: O nome do colaborador que aparece na linha abaixo de Cabeçalho (ex: CLEMERSON DE ALMEIDA ESPINDOLA).
- motivo (codigo_rdv): O texto que está no campo 'Motivo' (ex: COMBUSTÍVEL - VIAGENS ATÉ FRANCA PARA...).
- categoria: A descrição da despesa na tabela (ex: Combustiveis / Lubrificantes).
- valor: O valor na coluna Vr.Total (como número float, sem cifrão).

Retorne APENAS um JSON válido contendo o array "despesas" com os campos extraídos.
Formato:
{
  "despesas": [
    {
      "colaborador": "...",
      "codigo_rdv": "...",
      "categoria": "...",
      "valor": 123.45
    }
  ]
}
"""
            contents.append(prompt)
            
            try:
                response = await self.client.aio.models.generate_content(
                    model='gemini-3.1-pro-preview',
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
                
                try:
                    result_dict = json.loads(response.text)
                    despesas_raw = result_dict.get("despesas", [])
                except Exception as e:
                    print(f"[DESPESAS PARSER] Erro ao processar JSON do Gemini: {e}")
                    print(f"[DESPESAS PARSER] Resposta bruta: {response.text}")
                    despesas_raw = []
            except Exception as e:
                print(f"[DESPESAS PARSER] Erro na chamada da API Gemini: {e}")
                if hasattr(e, 'response') and e.response:
                    print(f"[DESPESAS PARSER] Detalhes do Erro API: {e.response}")
                elif hasattr(e, 'message'):
                    print(f"[DESPESAS PARSER] Mensagem de Erro: {e.message}")
                despesas_raw = []
                
        finally:
            if uploaded_file:
                try:
                    await self.client.aio.files.delete(name=uploaded_file.name)
                except:
                    pass

        despesas = []
        colab_repo = ColaboradorRepository(db) if db else None
        alias_repo = ColaboradorAliasRepository(db) if db else None

        for item in despesas_raw:
            cat_name = item.get("categoria", "")
            cat_id = None
            categoria_encontrada = False

            if db and cat_name:
                cat = db.query(Categoria).filter(Categoria.nome == cat_name).first()
                if not cat:
                    alias = db.query(CategoriaAlias).filter(CategoriaAlias.alias == cat_name).first()
                    if alias:
                        cat = db.query(Categoria).filter(Categoria.idCategorias == alias.idCategoria).first()
                
                if cat:
                    cat_id = cat.idCategorias
                    cat_name = cat.nome
                    categoria_encontrada = True

            viajante_nome = item.get("colaborador", "Não Identificado")
            colaborador_id = None
            pessoa_encontrada = False
            
            if db and viajante_nome != "Não Identificado":
                colab = colab_repo.get_by_nome_normalizado(viajante_nome)
                if not colab:
                    colab_alias = alias_repo.get_by_nome_divergente(viajante_nome)
                    if colab_alias:
                        colab = colab_repo.get_by_id(colab_alias.idColaborador)
                
                if colab:
                    colaborador_id = colab.idColaborador
                    viajante_nome = colab.nome
                    pessoa_encontrada = True

            valor = item.get("valor", 0.0)
            if float(valor) > 0:
                despesas.append({
                    "colaborador": viajante_nome,
                    "idColaborador": colaborador_id,
                    "cpf": "",
                    "pessoa_encontrada": pessoa_encontrada,
                    "categoria": cat_name,
                    "idCategoria": cat_id,
                    "categoria_encontrada": categoria_encontrada,
                    "valor": float(valor),
                    "codigo_rdv": item.get("codigo_rdv", "")
                })

        return despesas

    async def _parse_danfe_rosemary_via_ia(self, file_content: bytes, file_name: str, db) -> List[Dict]:
        from google.genai import types
        import json
        import tempfile
        import asyncio
        from app.repositories.colaborador_repository import ColaboradorRepository
        from app.repositories.colaborador_alias_repository import ColaboradorAliasRepository
        from app.models.categoria import Categoria
        from app.models.categoria_alias import CategoriaAlias

        if not self.client:
            return []
            
        file_size = len(file_content)
        uploaded_file = None
        is_inline = file_size < 15 * 1024 * 1024
        contents = []
        
        try:
            if is_inline:
                content_part = types.Part.from_bytes(data=file_content, mime_type="application/pdf")
                contents = [content_part]
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                    temp_file.write(file_content)
                    temp_path = temp_file.name
                
                uploaded_file = await self.client.aio.files.upload(
                    file=temp_path,
                    config=types.UploadFileConfig(mime_type="application/pdf")
                )
                
                sleep_time = 0.2
                while uploaded_file.state and uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(sleep_time)
                    uploaded_file = await self.client.aio.files.get(name=uploaded_file.name)
                    sleep_time = min(sleep_time * 1.5, 1.0)
                    
                contents = [uploaded_file]
                
            prompt = """
Analise a imagem desta DANFE/NFe (fatura de restaurante).
Extraia as seguintes informações:

- codigo_rdv: O número da DANFE ou Fatura que aparece no documento (ex: 663).
- valor: O valor total da nota, localizado na coluna "Valor Total" ou no final do documento (como número float, sem cifrão).

Nota:
- categoria: será sempre "Refeição"
- colaborador: será sempre "Não Identificado" (pois não aparece no documento).

Retorne APENAS um JSON válido contendo o array "despesas" com os campos extraídos.
Formato:
{
  "despesas": [
    {
      "colaborador": "Não Identificado",
      "codigo_rdv": "...",
      "categoria": "Refeição",
      "valor": 123.45
    }
  ]
}
"""
            contents.append(prompt)
            
            try:
                response = await self.client.aio.models.generate_content(
                    model='gemini-3.1-pro-preview',
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
                
                try:
                    result_dict = json.loads(response.text)
                    despesas_raw = result_dict.get("despesas", [])
                except Exception as e:
                    print(f"[DESPESAS PARSER] Erro ao processar JSON do Gemini (DANFE): {e}")
                    despesas_raw = []
            except Exception as e:
                print(f"[DESPESAS PARSER] Erro na chamada da API Gemini (DANFE): {e}")
                despesas_raw = []
                
        finally:
            if uploaded_file:
                try:
                    await self.client.aio.files.delete(name=uploaded_file.name)
                except:
                    pass

        despesas = []
        colab_repo = ColaboradorRepository(db) if db else None
        alias_repo = ColaboradorAliasRepository(db) if db else None

        for item in despesas_raw:
            cat_name = item.get("categoria", "Refeição")
            cat_id = None
            categoria_encontrada = False

            if db and cat_name:
                cat = db.query(Categoria).filter(Categoria.nome == cat_name).first()
                if not cat:
                    alias = db.query(CategoriaAlias).filter(CategoriaAlias.alias == cat_name).first()
                    if alias:
                        cat = db.query(Categoria).filter(Categoria.idCategorias == alias.idCategoria).first()
                
                if cat:
                    cat_id = cat.idCategorias
                    cat_name = cat.nome
                    categoria_encontrada = True

            viajante_nome = item.get("colaborador", "Não Identificado")
            colaborador_id = None
            pessoa_encontrada = False
            
            if db and viajante_nome != "Não Identificado":
                colab = colab_repo.get_by_nome_normalizado(viajante_nome)
                if not colab:
                    colab_alias = alias_repo.get_by_nome_divergente(viajante_nome)
                    if colab_alias:
                        colab = colab_repo.get_by_id(colab_alias.idColaborador)
                
                if colab:
                    colaborador_id = colab.idColaborador
                    viajante_nome = colab.nome
                    pessoa_encontrada = True

            valor_str = str(item.get("valor", "0"))
            try:
                val = float(valor_str)
            except:
                val = 0.0

            if val > 0:
                despesas.append({
                    "colaborador": viajante_nome,
                    "idColaborador": colaborador_id,
                    "cpf": "",
                    "pessoa_encontrada": pessoa_encontrada,
                    "categoria": cat_name,
                    "idCategoria": cat_id,
                    "categoria_encontrada": categoria_encontrada,
                    "valor": val,
                    "codigo_rdv": item.get("codigo_rdv", "")
                })

        return despesas

    async def _parse_fatura_cartao_eduardo_via_ia(self, file_content: bytes, file_name: str, db) -> List[Dict]:
        from google.genai import types
        import json
        import tempfile
        import asyncio
        from app.repositories.colaborador_repository import ColaboradorRepository
        from app.repositories.colaborador_alias_repository import ColaboradorAliasRepository
        from app.models.categoria import Categoria
        from app.models.categoria_alias import CategoriaAlias

        if not self.client:
            return []
            
        file_size = len(file_content)
        uploaded_file = None
        is_inline = file_size < 15 * 1024 * 1024
        contents = []
        
        try:
            if is_inline:
                content_part = types.Part.from_bytes(data=file_content, mime_type="application/pdf")
                contents = [content_part]
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                    temp_file.write(file_content)
                    temp_path = temp_file.name
                
                uploaded_file = await self.client.aio.files.upload(
                    file=temp_path,
                    config=types.UploadFileConfig(mime_type="application/pdf")
                )
                
                sleep_time = 0.2
                while uploaded_file.state and uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(sleep_time)
                    uploaded_file = await self.client.aio.files.get(name=uploaded_file.name)
                    sleep_time = min(sleep_time * 1.5, 1.0)
                    
                contents = [uploaded_file]
                
            prompt = """
Analise esta fatura de cartão corporativo.
Extraia as despesas listadas na tabela "Demonstrativo de Transações" (ou similar) que possuem valores na coluna "R$".
Para cada transação (despesa), extraia:

- codigo_rdv: A identificação da fatura (ex: "FATURA MENSAL" ou o número da fatura/cartão). Pode ser o mesmo para todas as despesas deste documento.
- categoria: A descrição da transação (nome do estabelecimento ou categoria indicada na tabela).
- valor: O valor da transação listado na coluna "R$" (como número float, sem cifrão).

Nota:
- colaborador: será sempre "Eduardo Milanez Silva".

Retorne APENAS um JSON válido contendo o array "despesas" com os campos extraídos.
Formato:
{
  "despesas": [
    {
      "colaborador": "Eduardo Milanez Silva",
      "codigo_rdv": "...",
      "categoria": "...",
      "valor": 123.45
    }
  ]
}
"""
            contents.append(prompt)
            
            try:
                response = await self.client.aio.models.generate_content(
                    model='gemini-3.1-pro-preview',
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
                
                try:
                    result_dict = json.loads(response.text)
                    despesas_raw = result_dict.get("despesas", [])
                except Exception as e:
                    print(f"[DESPESAS PARSER] Erro ao processar JSON do Gemini (Fatura Cartao): {e}")
                    despesas_raw = []
            except Exception as e:
                print(f"[DESPESAS PARSER] Erro na chamada da API Gemini (Fatura Cartao): {e}")
                despesas_raw = []
                
        finally:
            if uploaded_file:
                try:
                    await self.client.aio.files.delete(name=uploaded_file.name)
                except:
                    pass

        despesas = []
        colab_repo = ColaboradorRepository(db) if db else None
        alias_repo = ColaboradorAliasRepository(db) if db else None

        for item in despesas_raw:
            cat_name = item.get("categoria", "")
            cat_id = None
            categoria_encontrada = False

            if db and cat_name:
                cat = db.query(Categoria).filter(Categoria.nome == cat_name).first()
                if not cat:
                    alias = db.query(CategoriaAlias).filter(CategoriaAlias.alias == cat_name).first()
                    if alias:
                        cat = db.query(Categoria).filter(Categoria.idCategorias == alias.idCategoria).first()
                
                if cat:
                    cat_id = cat.idCategorias
                    cat_name = cat.nome
                    categoria_encontrada = True

            viajante_nome = item.get("colaborador", "Eduardo Milanez Silva")
            colaborador_id = None
            pessoa_encontrada = False
            
            if db and viajante_nome != "Não Identificado":
                colab = colab_repo.get_by_nome_normalizado(viajante_nome)
                if not colab:
                    colab_alias = alias_repo.get_by_nome_divergente(viajante_nome)
                    if colab_alias:
                        colab = colab_repo.get_by_id(colab_alias.idColaborador)
                
                if colab:
                    colaborador_id = colab.idColaborador
                    viajante_nome = colab.nome
                    pessoa_encontrada = True

            valor_str = str(item.get("valor", "0"))
            try:
                val = float(valor_str)
            except:
                val = 0.0

            if val > 0:
                despesas.append({
                    "colaborador": viajante_nome,
                    "idColaborador": colaborador_id,
                    "cpf": "",
                    "pessoa_encontrada": pessoa_encontrada,
                    "categoria": cat_name,
                    "idCategoria": cat_id,
                    "categoria_encontrada": categoria_encontrada,
                    "valor": val,
                    "codigo_rdv": item.get("codigo_rdv", "")
                })

        return despesas

    async def _parse_tastur_fatura_via_ia(self, file_content: bytes, file_name: str, db) -> List[Dict]:
        from google.genai import types
        import json
        import tempfile
        import asyncio
        from app.repositories.colaborador_repository import ColaboradorRepository
        from app.repositories.colaborador_alias_repository import ColaboradorAliasRepository
        from app.models.categoria import Categoria
        from app.models.categoria_alias import CategoriaAlias

        if not self.client:
            return []
            
        file_size = len(file_content)
        uploaded_file = None
        is_inline = file_size < 15 * 1024 * 1024
        contents = []
        
        try:
            if is_inline:
                content_part = types.Part.from_bytes(data=file_content, mime_type="application/pdf")
                contents = [content_part]
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                    temp_file.write(file_content)
                    temp_path = temp_file.name
                
                uploaded_file = await self.client.aio.files.upload(
                    file=temp_path,
                    config=types.UploadFileConfig(mime_type="application/pdf")
                )
                
                sleep_time = 0.2
                while uploaded_file.state and uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(sleep_time)
                    uploaded_file = await self.client.aio.files.get(name=uploaded_file.name)
                    sleep_time = min(sleep_time * 1.5, 1.0)
                    
                contents = [uploaded_file]
                
            prompt = """
Analise esta fatura da Agência de Viagens (ex: Tastur).
Extraia as despesas listadas.
Para cada despesa, extraia:

- codigo_rdv: A identificação da fatura (ex: "FAT-98300" ou o número da fatura). Pode ser o mesmo para todas as despesas deste documento.
- colaborador: O nome do passageiro / colaborador, que está localizado na linha abaixo do "Fornecedor". Se não encontrar, use "Não Identificado".
- categoria: A categoria da despesa. Analise o Fornecedor e o Serviço prestado. Por exemplo: se o Fornecedor for "Movida" ou "Localiza", a categoria deve ser "Locação de Veiculo"; se for uma companhia aérea (ex: Azul, Gol, Latam), use "Passagem Aérea"; se for hospedagem, use "Hospedagem".
- valor: O valor da despesa listado na coluna "Total" (como número float, sem cifrão).

Retorne APENAS um JSON válido contendo o array "despesas" com os campos extraídos.
Formato:
{
  "despesas": [
    {
      "colaborador": "...",
      "codigo_rdv": "...",
      "categoria": "...",
      "valor": 123.45
    }
  ]
}
"""
            contents.append(prompt)
            
            try:
                response = await self.client.aio.models.generate_content(
                    model='gemini-3.1-pro-preview',
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
                
                try:
                    result_dict = json.loads(response.text)
                    despesas_raw = result_dict.get("despesas", [])
                except Exception as e:
                    print(f"[DESPESAS PARSER] Erro ao processar JSON do Gemini (Tastur): {e}")
                    despesas_raw = []
            except Exception as e:
                print(f"[DESPESAS PARSER] Erro na chamada da API Gemini (Tastur): {e}")
                despesas_raw = []
                
        finally:
            if uploaded_file:
                try:
                    await self.client.aio.files.delete(name=uploaded_file.name)
                except:
                    pass

        despesas = []
        colab_repo = ColaboradorRepository(db) if db else None
        alias_repo = ColaboradorAliasRepository(db) if db else None

        for item in despesas_raw:
            cat_name = item.get("categoria", "")
            cat_id = None
            categoria_encontrada = False

            if db and cat_name:
                cat = db.query(Categoria).filter(Categoria.nome == cat_name).first()
                if not cat:
                    alias = db.query(CategoriaAlias).filter(CategoriaAlias.alias == cat_name).first()
                    if alias:
                        cat = db.query(Categoria).filter(Categoria.idCategorias == alias.idCategoria).first()
                
                if cat:
                    cat_id = cat.idCategorias
                    cat_name = cat.nome
                    categoria_encontrada = True

            viajante_nome = item.get("colaborador", "Não Identificado")
            colaborador_id = None
            pessoa_encontrada = False
            
            if db and viajante_nome != "Não Identificado":
                colab = colab_repo.get_by_nome_normalizado(viajante_nome)
                if not colab:
                    colab_alias = alias_repo.get_by_nome_divergente(viajante_nome)
                    if colab_alias:
                        colab = colab_repo.get_by_id(colab_alias.idColaborador)
                
                if colab:
                    colaborador_id = colab.idColaborador
                    viajante_nome = colab.nome
                    pessoa_encontrada = True

            valor_str = str(item.get("valor", "0"))
            try:
                val = float(valor_str)
            except:
                val = 0.0

            if val > 0:
                despesas.append({
                    "colaborador": viajante_nome,
                    "idColaborador": colaborador_id,
                    "cpf": "",
                    "pessoa_encontrada": pessoa_encontrada,
                    "categoria": cat_name,
                    "idCategoria": cat_id,
                    "categoria_encontrada": categoria_encontrada,
                    "valor": val,
                    "codigo_rdv": item.get("codigo_rdv", "")
                })

        return despesas

    async def _parse_maiorca_fatura_via_ia(self, file_content: bytes, file_name: str, db) -> List[Dict]:
        from google.genai import types
        import json
        import tempfile
        import asyncio
        from app.repositories.colaborador_repository import ColaboradorRepository
        from app.repositories.colaborador_alias_repository import ColaboradorAliasRepository
        from app.models.categoria import Categoria
        from app.models.categoria_alias import CategoriaAlias

        if not self.client:
            return []
            
        file_size = len(file_content)
        uploaded_file = None
        is_inline = file_size < 15 * 1024 * 1024
        contents = []
        
        try:
            if is_inline:
                content_part = types.Part.from_bytes(data=file_content, mime_type="application/pdf")
                contents = [content_part]
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                    temp_file.write(file_content)
                    temp_path = temp_file.name
                
                uploaded_file = await self.client.aio.files.upload(
                    file=temp_path,
                    config=types.UploadFileConfig(mime_type="application/pdf")
                )
                
                sleep_time = 0.2
                while uploaded_file.state and uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(sleep_time)
                    uploaded_file = await self.client.aio.files.get(name=uploaded_file.name)
                    sleep_time = min(sleep_time * 1.5, 1.0)
                    
                contents = [uploaded_file]
                
            prompt = """
Analise esta fatura/nota fiscal (ex: Maiorca ou similar).
Extraia as despesas listadas.
Para cada despesa, extraia:

- codigo_rdv: A identificação da fatura (ex: "MAIORCA" ou o número da fatura). Pode ser o mesmo para todas as despesas deste documento.
- colaborador: O nome do cliente / colaborador, que está localizado na linha "Cliente". Se não encontrar, use "Não Identificado".
- categoria: A categoria da despesa. Será sempre "Locação de veiculo".
- valor: O valor da despesa listado na coluna "Valor total" (como número float, sem cifrão).

Retorne APENAS um JSON válido contendo o array "despesas" com os campos extraídos.
Formato:
{
  "despesas": [
    {
      "colaborador": "...",
      "codigo_rdv": "...",
      "categoria": "Locação de veiculo",
      "valor": 123.45
    }
  ]
}
"""
            contents.append(prompt)
            
            try:
                response = await self.client.aio.models.generate_content(
                    model='gemini-3.1-pro-preview',
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
                
                try:
                    result_dict = json.loads(response.text)
                    despesas_raw = result_dict.get("despesas", [])
                except Exception as e:
                    print(f"[DESPESAS PARSER] Erro ao processar JSON do Gemini (Maiorca): {e}")
                    despesas_raw = []
            except Exception as e:
                print(f"[DESPESAS PARSER] Erro na chamada da API Gemini (Maiorca): {e}")
                despesas_raw = []
                
        finally:
            if uploaded_file:
                try:
                    await self.client.aio.files.delete(name=uploaded_file.name)
                except:
                    pass

        despesas = []
        colab_repo = ColaboradorRepository(db) if db else None
        alias_repo = ColaboradorAliasRepository(db) if db else None

        for item in despesas_raw:
            cat_name = item.get("categoria", "Locação de veiculo")
            cat_id = None
            categoria_encontrada = False

            if db and cat_name:
                cat = db.query(Categoria).filter(Categoria.nome == cat_name).first()
                if not cat:
                    alias = db.query(CategoriaAlias).filter(CategoriaAlias.alias == cat_name).first()
                    if alias:
                        cat = db.query(Categoria).filter(Categoria.idCategorias == alias.idCategoria).first()
                
                if cat:
                    cat_id = cat.idCategorias
                    cat_name = cat.nome
                    categoria_encontrada = True

            viajante_nome = item.get("colaborador", "Não Identificado")
            colaborador_id = None
            pessoa_encontrada = False
            
            if db and viajante_nome != "Não Identificado":
                colab = colab_repo.get_by_nome_normalizado(viajante_nome)
                if not colab:
                    colab_alias = alias_repo.get_by_nome_divergente(viajante_nome)
                    if colab_alias:
                        colab = colab_repo.get_by_id(colab_alias.idColaborador)
                
                if colab:
                    colaborador_id = colab.idColaborador
                    viajante_nome = colab.nome
                    pessoa_encontrada = True

            valor_str = str(item.get("valor", "0"))
            try:
                val = float(valor_str)
            except:
                val = 0.0

            if val > 0:
                despesas.append({
                    "colaborador": viajante_nome,
                    "idColaborador": colaborador_id,
                    "cpf": "",
                    "pessoa_encontrada": pessoa_encontrada,
                    "categoria": cat_name,
                    "idCategoria": cat_id,
                    "categoria_encontrada": categoria_encontrada,
                    "valor": val,
                    "codigo_rdv": item.get("codigo_rdv", "")
                })

        return despesas

    async def _parse_semparar_fatura_via_ia(self, file_content: bytes, file_name: str, db) -> List[Dict]:
        from google.genai import types
        import json
        import tempfile
        import asyncio
        from app.repositories.colaborador_repository import ColaboradorRepository
        from app.repositories.colaborador_alias_repository import ColaboradorAliasRepository
        from app.models.categoria import Categoria
        from app.models.categoria_alias import CategoriaAlias

        if not self.client:
            return []
            
        file_size = len(file_content)
        uploaded_file = None
        is_inline = file_size < 15 * 1024 * 1024
        contents = []
        
        try:
            if is_inline:
                content_part = types.Part.from_bytes(data=file_content, mime_type="application/pdf")
                contents = [content_part]
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                    temp_file.write(file_content)
                    temp_path = temp_file.name
                
                uploaded_file = await self.client.aio.files.upload(
                    file=temp_path,
                    config=types.UploadFileConfig(mime_type="application/pdf")
                )
                
                sleep_time = 0.2
                while uploaded_file.state and uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(sleep_time)
                    uploaded_file = await self.client.aio.files.get(name=uploaded_file.name)
                    sleep_time = min(sleep_time * 1.5, 1.0)
                    
                contents = [uploaded_file]
                
            prompt = """
Analise esta fatura de pedágio (ex: SEM PARAR).
Extraia as despesas listadas na tabela "Resumo da sua fatura" ou similar.
Agrupe os valores por placa/colaborador, prestando muita atenção na seguinte regra de mapeamento.

Para cada grupo de placa ou arrecadação, extraia:

- codigo_rdv: A identificação da fatura (ex: "SEM PARAR" ou o número da fatura). Será o mesmo para todas as despesas deste documento.
- categoria: Será sempre "Pedágio/Estacionamento".
- colaborador: Mapeie a placa do veículo (ou tipo de arrecadação) para o nome do colaborador seguindo RIGOROSAMENTE a regra abaixo:
    - Se a placa for FFl0C24 (ou FFL0C24), o colaborador é "Rubens P. V. A. Netto".
    - Se a placa for GHX5160, o colaborador é "MARIA INES".
    - Se a placa for DBI1283, DNE9302 ou GGU1D25, o colaborador é "FROTA PROPRIA CARROS".
    - IMPORTANTE: Para quaisquer "outras arrecadações" (ex: mensalidades, taxas de adesão, etc.) que apareçam na linha debaixo de "Adesão" ou separados das placas, agrupe e some os valores, associando ao colaborador "FROTA PROPRIA CARROS".
- valor: O valor total correspondente a essa placa ou agrupamento de arrecadação (como número float, sem cifrão).

Nota: Se mais de uma placa pertencer a "FROTA PROPRIA CARROS" (ex: DBI1283 e DNE9302 e arrecadações extras), some os valores delas em uma única despesa final para esse colaborador, ou retorne separadamente (serão somados depois se necessário). Apenas certifique-se de retornar os valores corretamente associados ao colaborador mapeado.

Retorne APENAS um JSON válido contendo o array "despesas" com os campos extraídos.
Formato:
{
  "despesas": [
    {
      "colaborador": "...",
      "codigo_rdv": "...",
      "categoria": "Pedágio/Estacionamento",
      "valor": 123.45
    }
  ]
}
"""
            contents.append(prompt)
            
            try:
                response = await self.client.aio.models.generate_content(
                    model='gemini-3.1-pro-preview',
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
                
                try:
                    result_dict = json.loads(response.text)
                    despesas_raw = result_dict.get("despesas", [])
                except Exception as e:
                    print(f"[DESPESAS PARSER] Erro ao processar JSON do Gemini (Sem Parar): {e}")
                    despesas_raw = []
            except Exception as e:
                print(f"[DESPESAS PARSER] Erro na chamada da API Gemini (Sem Parar): {e}")
                despesas_raw = []
                
        finally:
            if uploaded_file:
                try:
                    await self.client.aio.files.delete(name=uploaded_file.name)
                except:
                    pass

        despesas = []
        colab_repo = ColaboradorRepository(db) if db else None
        alias_repo = ColaboradorAliasRepository(db) if db else None

        # Vamos agrupar despesas pelo nome do colaborador caso a IA retorne várias linhas para "FROTA PROPRIA CARROS"
        agrupamento = {}

        for item in despesas_raw:
            viajante_nome = item.get("colaborador", "Não Identificado")
            valor_str = str(item.get("valor", "0"))
            try:
                val = float(valor_str)
            except:
                val = 0.0

            if val > 0:
                codigo_rdv = item.get("codigo_rdv", "SEM PARAR")
                if viajante_nome not in agrupamento:
                    agrupamento[viajante_nome] = {
                        "valor": val,
                        "codigo_rdv": codigo_rdv
                    }
                else:
                    agrupamento[viajante_nome]["valor"] += val

        for viajante_nome, data in agrupamento.items():
            cat_name = "Pedágio/Estacionamento"
            cat_id = None
            categoria_encontrada = False

            if db:
                cat = db.query(Categoria).filter(Categoria.nome == cat_name).first()
                if not cat:
                    alias = db.query(CategoriaAlias).filter(CategoriaAlias.alias == cat_name).first()
                    if alias:
                        cat = db.query(Categoria).filter(Categoria.idCategorias == alias.idCategoria).first()
                
                if cat:
                    cat_id = cat.idCategorias
                    cat_name = cat.nome
                    categoria_encontrada = True

            colaborador_id = None
            pessoa_encontrada = False
            
            if db and viajante_nome != "Não Identificado":
                colab = colab_repo.get_by_nome_normalizado(viajante_nome)
                if not colab:
                    colab_alias = alias_repo.get_by_nome_divergente(viajante_nome)
                    if colab_alias:
                        colab = colab_repo.get_by_id(colab_alias.idColaborador)
                
                if colab:
                    colaborador_id = colab.idColaborador
                    viajante_nome = colab.nome
                    pessoa_encontrada = True

            despesas.append({
                "colaborador": viajante_nome,
                "idColaborador": colaborador_id,
                "cpf": "",
                "pessoa_encontrada": pessoa_encontrada,
                "categoria": cat_name,
                "idCategoria": cat_id,
                "categoria_encontrada": categoria_encontrada,
                "valor": round(data["valor"], 2),
                "codigo_rdv": data["codigo_rdv"]
            })

        return despesas
