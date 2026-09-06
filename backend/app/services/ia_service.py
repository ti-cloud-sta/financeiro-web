import os
import json
import tempfile
import time
import asyncio
import re
import pypdf
from google import genai
from google.genai import types
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class DespesaExtraida(BaseModel):
    empresa: str
    colaborador: str
    categoria: str
    valor: float

class EstruturaExtracaoIA(BaseModel):
    despesas: List[DespesaExtraida]

class TransacaoBanco(BaseModel):
    data: str
    descricao: str
    valor: float
    documento: Optional[str] = None
    situacao: Optional[str] = None

class EstruturaExtracaoBanco(BaseModel):
    transacoes: List[TransacaoBanco]

class DependentExtraido(BaseModel):
    nome: str
    valor: float

class TitularExtraido(BaseModel):
    nome_pdf: str
    nome_db: str
    valor_titular: float
    dependentes: List[DependentExtraido]
    valor_total: float
    centro_custo: Optional[str] = "N/D"
    documento: Optional[str] = None

class EstruturaExtracaoPlanoSaude(BaseModel):
    titulares: List[TitularExtraido]

SCHEMA_PLANO_SAUDE = {
    "type": "OBJECT",
    "properties": {
        "titulares": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "nome_pdf": {"type": "STRING"},
                    "nome_db": {"type": "STRING"},
                    "valor_titular": {"type": "NUMBER"},
                    "dependentes": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "nome": {"type": "STRING"},
                                "valor": {"type": "NUMBER"}
                            },
                            "required": ["nome", "valor"]
                        }
                    },
                    "valor_total": {"type": "NUMBER"},
                    "centro_custo": {"type": "STRING", "nullable": True},
                    "unidade": {"type": "STRING", "nullable": True},
                    "documento": {"type": "STRING", "nullable": True}
                },
                "required": ["nome_pdf", "nome_db", "valor_titular", "dependentes", "valor_total"]
            }
        }
    },
    "required": ["titulares"]
}

class DependentExtraidoUnimed(BaseModel):
    nome: str
    tipo: str
    valor: float

class TitularExtraidoUnimed(BaseModel):
    nome_pdf: str
    nome_db: str
    matricula: str
    valor_titular: float
    dependentes: List[DependentExtraidoUnimed]
    valor_total: float
    centro_custo: Optional[str] = "N/D"
    unidade: Optional[str] = "N/D"
    documento: Optional[str] = None

class EstruturaExtracaoUnimedOdonto(BaseModel):
    titulares: List[TitularExtraidoUnimed]

class IAService:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        self.model_name = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
        
        # Testar se a API Key está presente
        if api_key:
            try:
                # Usando o novo SDK google-genai
                self.client = genai.Client(api_key=api_key)
            except Exception as e:
                print(f"[ERROR] Falha ao inicializar GenAI Client: {e}")
                self.client = None
        else:
            print("[WARN] GEMINI_API_KEY não encontrada nas variáveis de ambiente.")
            self.client = None

    @staticmethod
    def _parse_brl(valor_str: str) -> float:
        """Converte '1.234,56' ou '35.00' (ou negativos com sufixo '-') em float."""
        s = valor_str.strip()
        negativo = s.endswith('-')
        if negativo:
            s = s[:-1].strip()
        if ',' in s:
            s = s.replace('.', '').replace(',', '.')
        valor = float(s)
        return -valor if negativo else valor

    @staticmethod
    def _normaliza_cpf(digitos: str) -> Optional[str]:
        """Normaliza um CPF extraído do PDF para 11 dígitos.

        Alguns sistemas de origem guardam o CPF como número (não como texto), o que
        derruba os zeros à esquerda (ex.: 3365098550 em vez de 03365098550, ou até
        365098550 quando são 2 zeros perdidos). Não dá pra saber de antemão quantos
        zeros faltam, então aceitamos de 8 a 11 dígitos e completamos à esquerda até
        11 — CPF sempre tem 11 dígitos.
        """
        if not digitos:
            return None
        digitos = re.sub(r'\D', '', digitos)
        if 8 <= len(digitos) <= 11:
            return digitos.zfill(11)
        return None

    @staticmethod
    def _add_titular(titulares_dict, key, name, valor, documento=None):
        if key in titulares_dict:
            titulares_dict[key]["valor_titular"] = round(titulares_dict[key]["valor_titular"] + valor, 2)
            titulares_dict[key]["valor_total"] = round(titulares_dict[key]["valor_total"] + valor, 2)
        else:
            titulares_dict[key] = {
                "nome_pdf": name, "nome_db": name,
                "valor_titular": valor, "dependentes": [],
                "valor_total": valor, "centro_custo": "N/D",
                "documento": documento
            }

    def _fmt_unimed_single_line(self, lines):
        """FORMATO A: Unimed - numero de beneficiario X.XXXXXXX.XXXXXXXX-X, tudo em uma linha."""
        benef_pattern = re.compile(r'(\d\.\d{7}\.\d{8}-\d)')
        benef_count = sum(1 for l in lines if len(l) < 400 and benef_pattern.search(l))
        if benef_count < 5:
            return None

        tp_pattern = re.compile(r'\s([TDA])\s')
        val_pattern = re.compile(r'(\d+,\d{2}-?)')
        name_re = re.compile(r'^([A-Z\u00C0-\u00FF][A-Z\u00C0-\u00FF\s\.\,\-\'\?\&]+?)(?=\d)')
        cpf_fmt_re = re.compile(r'\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b')
        cpf_raw_re = re.compile(r'(?<!\d)(\d{8,11})(?!\d)')

        titulares_dict = {}
        dependentes_list = []
        current_titular_key = None

        for line in lines:
            if len(line) > 400:
                continue
            bm = benef_pattern.search(line)
            if not bm:
                continue
            matricula = bm.group(1)

            tm = tp_pattern.search(line)
            if not tm:
                continue
            tp = tm.group(1)

            nm = name_re.match(line)
            if not nm:
                continue
            name = nm.group(1).strip()
            if len(name) < 3:
                continue

            vals = val_pattern.findall(line)
            if not vals:
                continue
            valor = self._parse_brl(vals[0])

            # CPF do benefici\u00E1rio (com ou sem formata\u00E7\u00E3o), quando presente na linha.
            documento = None
            cpf_fmt_match = cpf_fmt_re.search(line)
            if cpf_fmt_match:
                documento = self._normaliza_cpf(cpf_fmt_match.group(1))
            else:
                linha_sem_matricula = benef_pattern.sub('', line)
                cpf_raw_match = cpf_raw_re.search(linha_sem_matricula)
                if cpf_raw_match:
                    documento = self._normaliza_cpf(cpf_raw_match.group(1))

            if tp == 'T':
                key = f"{name.upper()}::{matricula}"
                current_titular_key = key
                self._add_titular(titulares_dict, key, name, valor, documento=documento)
            else:
                if current_titular_key:
                    dependentes_list.append({"nome": name, "valor": valor, "_parent": current_titular_key})

        return titulares_dict, dependentes_list, "unimed"

    def _fmt_matricula_suffix(self, lines):
        """FORMATO E: Unimed 'ANALITICO DE TAXA' - cada beneficiario em uma linha iniciada por
        <prefixo com pontos>-<sufixo>, onde sufixo '00' e sempre o titular e os demais sao
        dependentes da mesma familia (mesmo prefixo)."""
        row_pattern = re.compile(r'^(\d+(?:\.\d+)+)-(\d{1,3})\s+(.{1,600})$')
        row_count = sum(1 for l in lines if row_pattern.match(l))
        if row_count < 5:
            return None

        name_pattern = re.compile(r'^(.{1,120}?)\s+[A-Z]\s+(?:MENSALIDADE|TAXA)')
        val_pattern = re.compile(r'(-?\d+,\d{2})')

        familias = {}
        ordem_prefixos = []
        ordem_sufixos = {}

        for line in lines:
            m = row_pattern.match(line)
            if not m:
                continue
            prefixo, sufixo, resto = m.group(1), m.group(2), m.group(3)

            nm = name_pattern.match(resto)
            if not nm:
                continue
            nome = re.sub(r'\s+', ' ', nm.group(1)).strip(' -')
            if len(nome) < 3:
                continue

            vals = val_pattern.findall(resto)
            if not vals:
                continue
            valor = self._parse_brl(vals[-1])

            if prefixo not in familias:
                familias[prefixo] = {}
                ordem_prefixos.append(prefixo)
                ordem_sufixos[prefixo] = []
            if sufixo not in familias[prefixo]:
                familias[prefixo][sufixo] = {"nome": nome, "valor": 0.0}
                ordem_sufixos[prefixo].append(sufixo)
            familias[prefixo][sufixo]["valor"] = round(familias[prefixo][sufixo]["valor"] + valor, 2)

        titulares_dict = {}
        dependentes_list = []

        for prefixo in ordem_prefixos:
            membros = familias[prefixo]
            sufixos = ordem_sufixos[prefixo]
            titular_sufixo = "00" if "00" in membros else sufixos[0]

            titular_info = membros[titular_sufixo]
            key = f"{titular_info['nome'].upper()}::{prefixo}"
            self._add_titular(titulares_dict, key, titular_info['nome'], titular_info['valor'])

            for sufixo in sufixos:
                if sufixo == titular_sufixo:
                    continue
                dep_info = membros[sufixo]
                dependentes_list.append({"nome": dep_info['nome'], "valor": dep_info['valor'], "_parent": key})

        return titulares_dict, dependentes_list, "unimed_matricula_sufixo"

    def _fmt_seguro_vida(self, lines):
        """FORMATO B: Seguro de Vida - marcadores de movimento ALT/INC/EXC colados a digitos
        (ex: 'N ALT156248298'), seguidos de valor, nome e tipo T/D na mesma linha."""
        mov_pattern = re.compile(r'\b(?:ALT|INC|EXC)\s{0,2}\d')
        candidate_lines = [l for l in lines if len(l) < 400 and mov_pattern.search(l)]
        if len(candidate_lines) < 5:
            return None

        seg_pattern = re.compile(r'(\d+,\d{2})(\d+)([A-Z][^\d]{2,80}?)\s+(T|D)(?=\s|$)\s*(\d{0,15})')

        titulares_dict = {}
        dependentes_list = []
        current_titular_key = None

        for line in candidate_lines:
            m = seg_pattern.search(line)
            if not m:
                continue

            valor = self._parse_brl(m.group(1))
            name = m.group(3).strip()
            tp = m.group(4)
            matricula = m.group(5) or ""
            # Neste layout, quando o campo após T/D tem 10 ou 11 dígitos, é o CPF do
            # beneficiário (o campo "Matrícula" do cabeçalho geralmente vem vazio).
            documento = self._normaliza_cpf(matricula) if 8 <= len(matricula) <= 11 else None

            if len(name) < 3:
                continue

            if tp == 'T':
                key = f"{name.upper()}::{matricula}" if matricula else name.upper()
                current_titular_key = key
                self._add_titular(titulares_dict, key, name, valor, documento=documento)
            elif tp == 'D' and current_titular_key:
                dependentes_list.append({"nome": name, "valor": valor, "_parent": current_titular_key})

        return titulares_dict, dependentes_list, "seguro_vida"

    def _fmt_rubrica_multiline(self, page_texts):
        """FORMATO A2: Demonstrativo Analitico de Faturamento Unimed (Saude/Odonto) cujo texto
        quebra o registro de cada beneficiario em varias linhas (nome, plano e rubrica em
        linhas separadas). Normaliza cada pagina para uma unica string e localiza cada rubrica
        conhecida (Mensalidade/Premio Titular|Dependente|Agregado, Cobranca/Devolucao Retroativa)."""
        rubrica_re = re.compile(
            r'\b([TDA])\s+\d{1,3}\s+(?:[A-Za-z\u00C0-\u00FF()]+\s+)?\d{2}/\d{2}/\d{4}(?:\s+\d{2}/\d{2}/\d{4})?\s+'
            r'(?:Premio|Mensalidade|Cobran\u00e7a|Devolu\u00e7\u00e3o)\s+'
            r'(?:Titular|Dependente|Agregado|Inclus[\u00e3a]o\s+Retroativa|Exclus[\u00e3a]o\s+Retroativa)\s*'
            r'(?:Pre\u00e7o\s*M\u00e9dio)?\s+(-?[\d.]+,\d{2})'
        )
        cpf_name_re = re.compile(r'([A-Z\u00C0-\u00FF][A-Z\u00C0-\u00FF\s]{2,60}?)\s+(?:\d{1,6}\s+)?(\d{8,11})\b')

        normalized_pages = [re.sub(r'\s+', ' ', pt) for pt in page_texts]
        total_matches = sum(len(rubrica_re.findall(p)) for p in normalized_pages)
        if total_matches < 5:
            return None

        titulares_dict = {}
        dependentes_list = []
        current_titular_key = None

        for page in normalized_pages:
            for m in rubrica_re.finditer(page):
                window = page[max(0, m.start() - 200):m.start()]
                name_matches = list(cpf_name_re.finditer(window))
                if not name_matches:
                    continue
                name = re.sub(r'\s+', ' ', name_matches[-1].group(1)).strip()
                documento = self._normaliza_cpf(name_matches[-1].group(2))
                if len(name) < 3:
                    continue

                tp = m.group(1)
                valor = self._parse_brl(m.group(2))

                if tp in ('T', 'A') or current_titular_key is None:
                    key = name.upper()
                    current_titular_key = key
                    self._add_titular(titulares_dict, key, name, valor, documento=documento)
                else:
                    dependentes_list.append({"nome": name, "valor": valor, "_parent": current_titular_key})

        return titulares_dict, dependentes_list, "unimed_demonstrativo_multilinha"

    def _fmt_responsavel(self, lines):
        """FORMATO G: Demonstrativo com blocos 'Responsavel: <cod> <nome>' e linhas
        'Valor Benef........: <valor>' por beneficiario (ex.: operadoras regionais/ANS)."""
        resp_count = sum(1 for l in lines if l.startswith('Respons\u00e1vel:'))
        valor_benef_count = sum(1 for l in lines if 'Valor Benef' in l)
        if resp_count < 1 or valor_benef_count < 2:
            return None

        resp_re = re.compile(r'^Respons\u00e1vel:\s*(\d+)')
        codigo_nome_re = re.compile(r'^(\d{4,8})\s+([A-Z\u00C0-\u00FF].+)$')
        valor_benef_re = re.compile(r'Valor Benef[\.\s]*:\s*([\d\.,]+)')

        titulares_dict = {}
        dependentes_list = []

        # Primeiro, agrupa todos os benefici\u00e1rios de cada bloco "Respons\u00e1vel:" \u2014 a ordem das
        # linhas dentro do bloco n\u00e3o \u00e9 confi\u00e1vel (o titular \u00e0s vezes aparece DEPOIS de um
        # dependente), ent\u00e3o s\u00f3 decidimos quem \u00e9 o titular depois de ler o bloco inteiro.
        blocos = []
        responsavel_codigo = None
        bloco_atual = []
        n = len(lines)
        i = 0
        while i < n:
            line = lines[i]
            rm = resp_re.match(line)
            if rm:
                if bloco_atual:
                    blocos.append((responsavel_codigo, bloco_atual))
                responsavel_codigo = rm.group(1)
                bloco_atual = []
                i += 1
                continue

            cm = codigo_nome_re.match(line)
            if cm:
                codigo, nome = cm.group(1), re.sub(r'\s+', ' ', cm.group(2)).strip()
                valor = None
                for j in range(i + 1, min(i + 6, n)):
                    if lines[j].startswith('Respons\u00e1vel:') or codigo_nome_re.match(lines[j]):
                        break
                    vm = valor_benef_re.search(lines[j])
                    if vm:
                        valor = self._parse_brl(vm.group(1))
                        break
                if valor is not None and len(nome) >= 3:
                    bloco_atual.append({"codigo": codigo, "nome": nome, "valor": valor})
            i += 1
        if bloco_atual:
            blocos.append((responsavel_codigo, bloco_atual))

        for cod_responsavel, membros in blocos:
            if not membros:
                continue
            idx_titular = next(
                (idx for idx, m in enumerate(membros) if m["codigo"] == cod_responsavel), 0
            )
            titular_info = membros[idx_titular]
            titular_key = f"{titular_info['nome'].upper()}::{titular_info['codigo']}"
            self._add_titular(titulares_dict, titular_key, titular_info['nome'], titular_info['valor'])

            for idx, membro in enumerate(membros):
                if idx == idx_titular:
                    continue
                dependentes_list.append({"nome": membro['nome'], "valor": membro['valor'], "_parent": titular_key})

        if not titulares_dict:
            return None
        return titulares_dict, dependentes_list, "demonstrativo_responsavel"

    def _fmt_sorriso_fragmented(self, lines):
        """FORMATO F: Tabelas extraidas pelo pypdf com uma celula por linha (ex.: Sorriso
        Odontologico), onde o tipo T/D aparece isolado em sua propria linha."""
        tipo_idx = [i for i, l in enumerate(lines) if l in ('T', 'D')]
        if len(tipo_idx) < 5:
            return None

        stopwords_name = {'PLANO', 'SUBTOTAL:', 'TOTAL:', 'BENEFICI\u00c1RIO', 'CARTEIRINHA'}
        decimal_re = re.compile(r'^-?\d+\.\d{2}$')
        boundary_re = re.compile(r'^(PLANO|SUBTOTAL:|TOTAL:)$', re.IGNORECASE)
        cpf_re = re.compile(r'^\d{8,11}$')

        n = len(lines)
        titulares_dict = {}
        dependentes_list = []
        current_titular_key = None

        for idx in tipo_idx:
            tp = lines[idx]

            nome_parts = []
            j = idx - 1
            while j >= 0:
                cand = lines[j]
                if cand.upper() in stopwords_name or boundary_re.match(cand):
                    break
                if re.search(r'\d', cand):
                    break
                if not re.match(r'^[A-Z\u00C0-\u00FF][A-Z\u00C0-\u00FF\s\.\-]*$', cand):
                    break
                nome_parts.insert(0, cand)
                j -= 1
                if len(nome_parts) >= 6:
                    break
            if not nome_parts:
                continue
            nome = re.sub(r'\s+', ' ', ' '.join(nome_parts)).strip()
            if len(nome) < 3:
                continue

            valor = None
            documento = None
            for k in range(idx + 1, min(idx + 25, n)):
                if boundary_re.match(lines[k]):
                    break
                if documento is None and cpf_re.match(lines[k]):
                    documento = self._normaliza_cpf(lines[k])
                if decimal_re.match(lines[k]):
                    valor = self._parse_brl(lines[k])
            if valor is None:
                continue

            if tp == 'T':
                key = nome.upper()
                current_titular_key = key
                self._add_titular(titulares_dict, key, nome, valor, documento=documento)
            elif current_titular_key:
                dependentes_list.append({"nome": nome, "valor": valor, "_parent": current_titular_key})

        if not titulares_dict:
            return None
        return titulares_dict, dependentes_list, "sorriso_fragmentado"

    def _fmt_coparticipacao(self, lines):
        """FORMATO H: Relatorio de utilizacao/co-participacao (Analitico de Servico), sem
        mensalidade fixa por beneficiario. Cada familia e somada usando o bloco
        'TOT AL TITULAR : <valor>' / 'TOTAL TITULAR ... <valor>' ja impresso no PDF."""
        header_re = re.compile(r'^([A-Z\u00C0-\u00FF][A-Z\u00C0-\u00FF\s]{2,80}?)\s*-\s*\d[\d\.]*\d\s+Matr[i\u00ed]cula')
        total_titular_re = re.compile(r'TOT\s*AL\s+TITULAR|TOTAL\s+TITULAR', re.IGNORECASE)
        val_re = re.compile(r'(\d[\d\.]*,\d{2})')

        header_count = sum(1 for l in lines if header_re.match(l))
        total_count = sum(1 for l in lines if total_titular_re.search(l))
        if header_count < 1 or total_count < 1:
            return None

        titulares_dict = {}
        current_nome = None

        for line in lines:
            hm = header_re.match(line)
            if hm:
                current_nome = re.sub(r'\s+', ' ', hm.group(1)).strip()
                continue

            if total_titular_re.search(line) and current_nome:
                vals = val_re.findall(line)
                if vals:
                    valor = self._parse_brl(vals[-1])
                    key = current_nome.upper()
                    if key in titulares_dict:
                        titulares_dict[key]["valor_titular"] = round(valor, 2)
                        titulares_dict[key]["valor_total"] = round(valor, 2)
                    else:
                        titulares_dict[key] = {
                            "nome_pdf": current_nome, "nome_db": current_nome,
                            "valor_titular": valor, "dependentes": [],
                            "valor_total": valor, "centro_custo": "N/D"
                        }
                current_nome = None

        if not titulares_dict:
            return None
        return titulares_dict, [], "coparticipacao"

    def _fmt_generic(self, lines):
        """FORMATO C: Generico (marcadores T/D com valores tabulares) - usado apenas quando
        nenhum formato especifico e reconhecido."""
        skip_words = ['SUBTOTAL', 'TOTAL GERAL', 'P\u00c1GINA', 'COMPET\u00caNCIA', 'ESTIPULANTE',
                     'DESCRI\u00c7\u00c3O', 'RELA\u00c7\u00c3O', 'NOME TITULAR', 'VR. MENS']

        gen_p1 = re.compile(r'([A-Z][A-Z\u00C0-\u00FF\s\.\,\-\'\?\&]{3,80}?)\s+.{0,120}?(\d+,\d{2}).{0,60}?\s(T|D)\b')
        gen_p2 = re.compile(r'(\d+,\d{2}).{0,120}?([A-Z][A-Z\u00C0-\u00FF\s\.\,\-\'\?\&]{3,80}?)\s+(T|D)\b')

        titulares_dict = {}
        dependentes_list = []
        current_titular_key = None

        for line in lines:
            if len(line) > 350:
                continue
            if any(sw in line.upper() for sw in skip_words):
                continue
            name, valor, tp = None, None, None
            m1 = gen_p1.search(line)
            if m1:
                name, valor, tp = m1.group(1).strip(), self._parse_brl(m1.group(2)), m1.group(3)
            else:
                m2 = gen_p2.search(line)
                if m2:
                    valor, name, tp = self._parse_brl(m2.group(1)), m2.group(2).strip(), m2.group(3)

            if not name or not tp or len(name) < 3:
                continue
            name_key = name.upper()

            if tp == 'T':
                current_titular_key = name_key
                self._add_titular(titulares_dict, name_key, name, valor)
            elif tp == 'D' and current_titular_key:
                dependentes_list.append({"nome": name, "valor": valor, "_parent": current_titular_key})

        return titulares_dict, dependentes_list, "generic"

    def _detectar_total_esperado(self, full_text: str) -> Optional[float]:
        """Tenta localizar um total geral já impresso no próprio documento (ex: 'Total Geral',
        'TOT AL EMPRESA...', 'TOTAL DA FATURA'), para reconciliar com a soma calculada pelo
        parser determinístico. Usado como gatilho do fallback via IA — não lançamos exceção
        se nada for encontrado, apenas deixamos de reconciliar."""
        anchors = [
            r'TOT\s*AL\s+EMPRESA',
            r'TOTAL\s+GERAL',
            r'TOTAL\s+DA\s+F\s*ATURA',
            r'VALOR\s+TOTAL\s*:',
            r'^Total[\.\s]*:',
        ]
        lines = full_text.split('\n')
        val_re = re.compile(r'(\d[\d\.]*,\d{2})')
        for anchor in anchors:
            anchor_re = re.compile(anchor, re.IGNORECASE)
            candidatos = []
            for line in lines:
                if anchor_re.search(line):
                    vals = val_re.findall(line)
                    if vals:
                        candidatos.append(vals[-1])
            if candidatos:
                try:
                    return self._parse_brl(candidatos[-1])
                except ValueError:
                    continue
        return None

    async def _extrair_beneficiarios_via_ia_fallback(self, file_content: bytes, file_name: str) -> Optional[list]:
        """Fallback via Gemini, usado apenas quando o parser determinístico não reconcilia com
        o total impresso no próprio documento (ex.: PDFs cuja extração de texto embaralha
        colunas). Envia o PDF original (não o texto já corrompido pelo pypdf) para o modelo,
        preservando a estrutura visual da tabela."""
        if not self.client:
            return None
        try:
            content_part = types.Part.from_bytes(data=file_content, mime_type="application/pdf")
            prompt = """
            Você é um especialista em auditoria de demonstrativos de plano de saúde, odontológico e seguro de vida corporativos.
            Analise o PDF anexado e extraia TODOS os titulares e seus dependentes, com os valores de mensalidade/prêmio de cada um.

            Regras:
            1. Identifique cada titular (funcionário/beneficiário principal) e seus dependentes vinculados (cônjuge, filhos, agregados).
            2. Preencha "nome_pdf" e "nome_db" com o nome exatamente como consta no documento.
            3. "valor_titular" é o valor de mensalidade/prêmio do titular. "dependentes" é a lista de dependentes com nome e valor individual de cada um.
            4. "valor_total" é a soma do valor do titular com todos os seus dependentes (o total do grupo familiar).
            5. Ignore linhas de cabeçalho, rodapé, resumo ou totalizadores — extraia apenas beneficiários individuais.
            6. Se houver movimentações de exclusão, devolução ou estorno (valores negativos) atribuídas a um beneficiário específico, some-as ao valor daquele beneficiário.
            7. A soma de todos os "valor_total" deve bater com o total geral da fatura impresso no documento (ex.: "TOTAL DA FATURA", "VALOR LÍQUIDO DA FATURA" ou "TOTAL EMPRESA").
            8. Alguns documentos são relatórios de utilização/co-participação (analítico de serviço), onde cada beneficiário aparece com várias linhas de atendimentos/procedimentos individuais em vez de uma única mensalidade fixa. Nesses casos:
               a. Cada bloco de atendimentos é encerrado por uma linha "TOTAL DEPENDENTE" — isso é o subtotal daquele ÚNICO beneficiário (seja ele o titular ou um dependente), não a soma de todos os dependentes da família.
               b. Ao final de cada grupo familiar existe uma linha "TOTAL TITULAR" que já é a soma de TODOS os beneficiários daquele grupo (titular + todos os dependentes). Use esse valor diretamente como "valor_total" do grupo — NÃO some novamente os subtotais individuais, para evitar contagem duplicada.
               c. Preencha "valor_titular" com o subtotal ("TOTAL DEPENDENTE") do próprio titular (o primeiro beneficiário listado no grupo) e cada dependente com o seu respectivo subtotal individual.
            9. Se houver um CPF (11 dígitos) associado ao titular no documento, preencha "documento" com ele (apenas números, sem pontuação). Caso contrário, deixe nulo.

            Retorne estritamente conforme o schema estruturado EstruturaExtracaoPlanoSaude.
            """

            max_retries = 3
            response = None
            for attempt in range(max_retries):
                try:
                    response = await self.client.aio.models.generate_content(
                        model=self.model_name,
                        contents=[content_part, prompt],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=SCHEMA_PLANO_SAUDE
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

            if not response:
                return None

            titulares_list = []
            if response.parsed:
                if isinstance(response.parsed, dict):
                    titulares_list = response.parsed.get("titulares", [])
                else:
                    titulares_list = [t.model_dump() for t in response.parsed.titulares]
            else:
                raw_text = response.text.strip() if response.text else ""
                if raw_text:
                    if raw_text.startswith("```json"):
                        raw_text = raw_text[7:]
                    if raw_text.startswith("```"):
                        raw_text = raw_text[3:]
                    if raw_text.endswith("```"):
                        raw_text = raw_text[:-3]
                    data = json.loads(raw_text.strip())
                    titulares_list = data.get("titulares", [])

            for t in titulares_list:
                t.setdefault("centro_custo", "N/D")

            return titulares_list if titulares_list else None
        except Exception as e:
            print(f"[PARSER UNIVERSAL] Fallback IA falhou: {e}", flush=True)
            return None

    async def extrair_beneficiarios_pdf_universal(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """
        Parser universal deterministico para PDFs de planos de saude, odontologicos e seguros.
        Extrai titulares e dependentes com valores usando regex puro - sem IA.

        Tenta, em cascata, os formatos conhecidos (do mais especifico ao mais generico) e usa
        o primeiro que produzir resultados.
        """
        import io

        t0 = time.time()

        pdf_file = io.BytesIO(file_content)
        reader = pypdf.PdfReader(pdf_file)
        page_texts = [page.extract_text() or "" for page in reader.pages]
        full_text = "\n".join(page_texts)

        lines = [l.strip() for l in full_text.split('\n') if l.strip()]
        total_pages = len(reader.pages)

        titulares_dict = {}
        dependentes_list = []
        method_used = "none"

        formatos = [
            lambda: self._fmt_unimed_single_line(lines),
            lambda: self._fmt_matricula_suffix(lines),
            lambda: self._fmt_seguro_vida(lines),
            lambda: self._fmt_rubrica_multiline(page_texts),
            lambda: self._fmt_coparticipacao(lines),
            lambda: self._fmt_responsavel(lines),
            lambda: self._fmt_sorriso_fragmented(lines),
            lambda: self._fmt_generic(lines),
        ]

        for tentar_formato in formatos:
            resultado = tentar_formato()
            if resultado is None:
                continue
            candidato_titulares, candidato_dependentes, nome_metodo = resultado
            if candidato_titulares:
                titulares_dict, dependentes_list, method_used = candidato_titulares, candidato_dependentes, nome_metodo
                break

        # Formatos cujo layout nunca traz coluna de CPF (Unimed "Analítico de Taxa de
        # Faturamento" e "Analítico de Serviço"/Co-participação) — para esses, e só
        # para esses, a identificação do beneficiário precisa cair para o nome, já
        # que não existe outra informação de identidade no documento.
        FORMATOS_SEM_CPF = {"unimed_matricula_sufixo", "coparticipacao"}
        permite_fallback_nome = method_used in FORMATOS_SEM_CPF

        for dep in dependentes_list:
            parent_key = dep.pop("_parent", None)
            if parent_key and parent_key in titulares_dict:
                titulares_dict[parent_key]["dependentes"].append({"nome": dep["nome"], "valor": dep["valor"]})
                titulares_dict[parent_key]["valor_total"] = round(
                    titulares_dict[parent_key]["valor_total"] + dep["valor"], 2)

        titulares_list = list(titulares_dict.values())
        titulares_list.sort(key=lambda t: (t.get("nome_pdf") or "").lower())

        # Reconciliação: se nenhum beneficiário foi extraído (ex.: PDF escaneado/sem texto,
        # ou layout desconhecido) OU o total calculado não bater com o total impresso no
        # próprio documento, tenta um fallback via IA (envia o PDF original, não o texto
        # eventualmente corrompido pelo pypdf) antes de desistir do resultado determinístico.
        tentou_fallback_ia = False
        usou_fallback_ia = False
        soma_calculada = round(sum(t.get("valor_total", 0.0) for t in titulares_list), 2)
        total_esperado = self._detectar_total_esperado(full_text)

        motivo_fallback = None
        if not titulares_list:
            motivo_fallback = "nenhum beneficiário extraído"
        elif total_esperado is not None and abs(soma_calculada - total_esperado) > max(1.0, total_esperado * 0.01):
            motivo_fallback = f"calculado={soma_calculada} vs impresso={total_esperado}"

        if motivo_fallback:
            tentou_fallback_ia = True
            print(f"[PARSER UNIVERSAL] Acionando fallback via IA ({motivo_fallback})", flush=True)
            titulares_ia = await self._extrair_beneficiarios_via_ia_fallback(file_content, file_name)
            if titulares_ia:
                titulares_list = titulares_ia
                titulares_list.sort(key=lambda t: (t.get("nome_pdf") or "").lower())
                method_used = f"{method_used}+ia_fallback"
                usou_fallback_ia = True

        n_dependentes = sum(len(t.get("dependentes", [])) for t in titulares_list)

        elapsed = round((time.time() - t0) * 1000, 2)
        print(f"[PARSER UNIVERSAL] Metodo: {method_used} | {len(titulares_list)} titulares | "
              f"{n_dependentes} deps | {total_pages} pags | {elapsed}ms", flush=True)

        metrics = {
            "total_ms": elapsed, "method": method_used,
            "permite_fallback_nome": permite_fallback_nome,
            "pages": total_pages, "total_chars": len(full_text),
            "titulares_found": len(titulares_list), "dependentes_found": n_dependentes,
            "total_esperado": total_esperado, "usou_fallback_ia": usou_fallback_ia,
            "tentou_fallback_ia": tentou_fallback_ia, "gemini_configurado": self.client is not None,
            "upload_pdf_ms": 0.0, "file_ready_ms": 0.0,
            "gemini_generation_ms": 0.0, "structured_output_ms": 0.0,
            "post_processing_ms": elapsed,
            "input_tokens": 0, "output_tokens": 0, "total_tokens": 0
        }

        return {"titulares": titulares_list, "metrics": metrics, "file_name_to_delete": None}

    # ------------------------------------------------------------------
    # Planilha (CSV/Excel) de demonstrativo de fatura — colunas fixas por posição
    # ------------------------------------------------------------------
    def extrair_beneficiarios_planilha(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """Extrai titulares/dependentes de um demonstrativo em CSV ou Excel.

        Layout com posição de coluna fixa (letras do Excel, 0-indexado):
        B (1) = Cod Titular — agrupa dependentes ao titular
        C (2) = Tit/Dep — 'T' ou 'D'
        J (9) = Valor da mensalidade daquela linha
        P (15) = CPF do titular do grupo (mesmo valor em todas as linhas T/D da família)
        """
        import io
        import pandas as pd

        t0 = time.time()

        COL_COD_TITULAR = 1
        COL_TIT_DEP = 2
        COL_VALOR = 9
        COL_CPF = 15
        MIN_COLS = COL_CPF + 1

        buf = io.BytesIO(file_content)
        is_excel = file_name.lower().endswith((".xlsx", ".xls"))
        if is_excel:
            df = pd.read_excel(buf, dtype=str, header=0)
        else:
            try:
                df = pd.read_csv(buf, sep=';', dtype=str, encoding='utf-8-sig', engine='python')
            except UnicodeDecodeError:
                buf.seek(0)
                df = pd.read_csv(buf, sep=';', dtype=str, encoding='latin1', engine='python')
        df = df.fillna('')

        headers_lower = [str(h).strip().lower() for h in df.columns]

        def _find_col(*termos):
            for i, h in enumerate(headers_lower):
                if all(t in h for t in termos):
                    return i
            return None

        col_nome_benef = _find_col('nome', 'benefici')
        col_nome_tit = _find_col('nome', 'titular')

        titulares = {}
        for row in df.itertuples(index=False, name=None):
            if len(row) < MIN_COLS:
                continue

            cod_titular = str(row[COL_COD_TITULAR]).strip()
            tipo = str(row[COL_TIT_DEP]).strip().upper()
            if not cod_titular or tipo not in ('T', 'D'):
                continue

            valor_str = str(row[COL_VALOR]).strip()
            if not valor_str:
                continue
            try:
                valor = self._parse_brl(valor_str)
            except ValueError:
                continue

            documento = self._normaliza_cpf(str(row[COL_CPF]))
            nome_benef = str(row[col_nome_benef]).strip() if col_nome_benef is not None else ''
            nome_tit = str(row[col_nome_tit]).strip() if col_nome_tit is not None else ''
            nome_grupo = nome_tit or nome_benef

            if cod_titular not in titulares:
                titulares[cod_titular] = {
                    "nome_pdf": nome_grupo, "nome_db": nome_grupo,
                    "valor_titular": 0.0, "dependentes": [],
                    "valor_total": 0.0, "centro_custo": "N/D",
                    "documento": documento,
                }
            grupo = titulares[cod_titular]
            if documento and not grupo.get("documento"):
                grupo["documento"] = documento

            if tipo == 'T':
                grupo["valor_titular"] = round(grupo["valor_titular"] + valor, 2)
                grupo["valor_total"] = round(grupo["valor_total"] + valor, 2)
                if nome_grupo:
                    grupo["nome_pdf"] = nome_grupo
                    grupo["nome_db"] = nome_grupo
            else:
                grupo["dependentes"].append({"nome": nome_benef, "valor": valor})
                grupo["valor_total"] = round(grupo["valor_total"] + valor, 2)

        titulares_list = list(titulares.values())
        titulares_list.sort(key=lambda t: (t.get("nome_pdf") or "").lower())
        n_dependentes = sum(len(t.get("dependentes", [])) for t in titulares_list)

        elapsed = round((time.time() - t0) * 1000, 2)
        print(f"[PARSER PLANILHA] {len(titulares_list)} titulares | {n_dependentes} deps | "
              f"{len(df)} linhas | {elapsed}ms", flush=True)

        metrics = {
            "total_ms": elapsed, "method": "planilha_csv_excel",
            "permite_fallback_nome": False,
            "pages": 1, "total_chars": len(df),
            "titulares_found": len(titulares_list), "dependentes_found": n_dependentes,
            "total_esperado": None, "usou_fallback_ia": False,
            "tentou_fallback_ia": False, "gemini_configurado": self.client is not None,
            "upload_pdf_ms": 0.0, "file_ready_ms": 0.0,
            "gemini_generation_ms": 0.0, "structured_output_ms": 0.0,
            "post_processing_ms": elapsed,
            "input_tokens": 0, "output_tokens": 0, "total_tokens": 0
        }

        return {"titulares": titulares_list, "metrics": metrics, "file_name_to_delete": None}

    async def analisar_fatura_despesas(self, file_content: bytes, file_name: str, categorias: List[str]) -> Dict[str, Any]:
        if not self.client:
            raise Exception("API Key do Gemini não configurada.")
            
        metrics = {
            "upload_pdf_ms": 0.0,
            "file_ready_ms": 0.0,
            "gemini_generation_ms": 0.0,
            "structured_output_ms": 0.0,
            "post_processing_ms": 0.0,
            "total_ms": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }
        
        t0_total = time.time()
        file_size = len(file_content)
        uploaded_file = None
        temp_path = None
        
        is_inline = file_size < 15 * 1024 * 1024
        
        try:
            if is_inline:
                t0_prep = time.time()
                mime_type = "application/pdf" if file_name.lower().endswith(".pdf") else "text/plain"
                content_part = types.Part.from_bytes(
                    data=file_content,
                    mime_type=mime_type
                )
                metrics["upload_pdf_ms"] = round((time.time() - t0_prep) * 1000, 2)
                metrics["file_ready_ms"] = 0.0
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
            Sua tarefa é analisar o relatório de despesas fornecido (anexo) e estruturar cada transação.

            Regras de Extração e Classificação:
            1. Identifique as despesas individuais. Cada despesa deve ter um Colaborador responsável, uma Empresa relacionada e um Valor.
            2. Classifique a categoria de cada despesa no menor nível possível, escolhendo exclusivamente uma destas categorias disponíveis no sistema:
            {json.dumps(categorias, ensure_ascii=False)}
            Se nenhuma categoria se encaixar perfeitamente, classifique na categoria mais genérica aplicável (como "Outros" ou "Viagens").
            
            Retorne o resultado de forma estruturada estritamente conforme o schema estruturado EstruturaExtracaoIA.
            """
            
            contents.append(prompt)
            
            max_retries = 3
            response = None
            
            t0_gen = time.time()
            for attempt in range(max_retries):
                try:
                    response = await self.client.aio.models.generate_content(
                        model=self.model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=EstruturaExtracaoIA,
                            thinking_config=types.ThinkingConfig(thinking_level="low")
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
                    despesas_list = data.get("despesas", [])
            metrics["structured_output_ms"] = round((time.time() - t0_struct) * 1000, 2)
            
            if response and response.usage_metadata:
                metrics["input_tokens"] = response.usage_metadata.prompt_token_count or 0
                metrics["output_tokens"] = response.usage_metadata.candidates_token_count or 0
                metrics["total_tokens"] = response.usage_metadata.total_token_count or 0
            
            t0_post = time.time()
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            metrics["post_processing_ms"] = round((time.time() - t0_post) * 1000, 2)
            
            metrics["total_ms"] = round((time.time() - t0_total) * 1000, 2)
            
            return {
                "despesas": despesas_list,
                "metrics": metrics,
                "file_name_to_delete": uploaded_file.name if uploaded_file else None
            }
            
        except Exception as e:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    async def analisar_extrato(self, file_content: bytes, file_name: str, categorias: List[str], colaboradores: List[str], empresa_context: str) -> Dict[str, Any]:
        if not self.client:
            raise Exception("API Key do Gemini não configurada.")
            
        metrics = {
            "upload_pdf_ms": 0.0,
            "file_ready_ms": 0.0,
            "gemini_generation_ms": 0.0,
            "structured_output_ms": 0.0,
            "post_processing_ms": 0.0,
            "total_ms": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }
        
        t0_total = time.time()
        file_size = len(file_content)
        uploaded_file = None
        temp_path = None
        
        is_inline = file_size < 15 * 1024 * 1024
        
        try:
            if is_inline:
                t0_prep = time.time()
                mime_type = "application/pdf" if file_name.lower().endswith(".pdf") else "text/plain"
                content_part = types.Part.from_bytes(
                    data=file_content,
                    mime_type=mime_type
                )
                metrics["upload_pdf_ms"] = round((time.time() - t0_prep) * 1000, 2)
                metrics["file_ready_ms"] = 0.0
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
            1. Identifique as despesas individuais. Cada despesa deve ter um Colaborador responsável, uma Empresa relacionada (que deve ser "{empresa_context}") e um Valor.
            2. Mapeie o Colaborador responsável de cada despesa exclusivamente a partir da lista de colaboradores válidos do sistema fornecida abaixo:
            {json.dumps(colaboradores, ensure_ascii=False)}
            Se o nome no documento estiver ligeiramente diferente (abreviado ou com sobrenomes ocultos), faça a correspondência com o colaborador real correspondente da lista. Se não encontrar nenhuma correspondência plausível, use "Não Identificado" ou o nome mais próximo possível da lista.
            
            3. Classifique a categoria de cada despesa no menor nível possível, escolhendo exclusivamente uma destas categorias disponíveis no sistema:
            {json.dumps(categorias, ensure_ascii=False)}
            Se nenhuma categoria se encaixar perfeitamente, classifique na categoria mais genérica aplicável (como "Outros" ou "Viagens").
            
            Retorne o resultado de forma estruturada estritamente conforme o schema estruturado EstruturaExtracaoIA.
            """
            
            contents.append(prompt)
            
            max_retries = 3
            response = None
            
            t0_gen = time.time()
            for attempt in range(max_retries):
                try:
                    response = await self.client.aio.models.generate_content(
                        model=self.model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=EstruturaExtracaoIA,
                            thinking_config=types.ThinkingConfig(thinking_level="low")
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
                    despesas_list = data.get("despesas", [])
            metrics["structured_output_ms"] = round((time.time() - t0_struct) * 1000, 2)
            
            if response and response.usage_metadata:
                metrics["input_tokens"] = response.usage_metadata.prompt_token_count or 0
                metrics["output_tokens"] = response.usage_metadata.candidates_token_count or 0
                metrics["total_tokens"] = response.usage_metadata.total_token_count or 0
            
            t0_post = time.time()
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            metrics["post_processing_ms"] = round((time.time() - t0_post) * 1000, 2)
            
            metrics["total_ms"] = round((time.time() - t0_total) * 1000, 2)
            
            return {
                "despesas": despesas_list,
                "metrics": metrics,
                "file_name_to_delete": uploaded_file.name if uploaded_file else None
            }
            
        except Exception as e:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    async def analisar_extrato_bancario(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        if not self.client:
            raise Exception("API Key do Gemini não configurada.")
            
        metrics = {
            "upload_pdf_ms": 0.0,
            "file_ready_ms": 0.0,
            "gemini_generation_ms": 0.0,
            "structured_output_ms": 0.0,
            "post_processing_ms": 0.0,
            "total_ms": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }
        
        t0_total = time.time()
        file_size = len(file_content)
        uploaded_file = None
        temp_path = None
        
        is_inline = file_size < 15 * 1024 * 1024
        
        try:
            if is_inline:
                t0_prep = time.time()
                mime_type = "application/pdf" if file_name.lower().endswith(".pdf") else "text/plain"
                content_part = types.Part.from_bytes(
                    data=file_content,
                    mime_type=mime_type
                )
                metrics["upload_pdf_ms"] = round((time.time() - t0_prep) * 1000, 2)
                metrics["file_ready_ms"] = 0.0
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
                
            prompt = """
            Você é um assistente especializado em conciliação bancária de ERPs de alta performance.
            Sua tarefa é analisar o extrato bancário anexado (PDF ou texto) e estruturar cada transação.

            Regras de Extração e Estruturação:
            1. Identifique as transações individuais. Cada transação deve ter uma data, uma descrição e um valor.
            2. Se houver coluna de documento, situação ou número de controle, extraia-a no campo correspondente "documento".
            
            Retorne o resultado de forma estruturada estritamente conforme o schema estruturado EstruturaExtracaoBanco.
            """
            
            contents.append(prompt)
            
            max_retries = 3
            response = None
            
            t0_gen = time.time()
            for attempt in range(max_retries):
                try:
                    response = await self.client.aio.models.generate_content(
                        model=self.model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=EstruturaExtracaoBanco,
                            thinking_config=types.ThinkingConfig(thinking_level="low")
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
            transacoes_list = []
            if response and response.parsed:
                transacoes_list = [t.model_dump() for t in response.parsed.transacoes]
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
                    transacoes_list = data.get("transacoes", [])
            metrics["structured_output_ms"] = round((time.time() - t0_struct) * 1000, 2)
            
            if response and response.usage_metadata:
                metrics["input_tokens"] = response.usage_metadata.prompt_token_count or 0
                metrics["output_tokens"] = response.usage_metadata.candidates_token_count or 0
                metrics["total_tokens"] = response.usage_metadata.total_token_count or 0
            
            t0_post = time.time()
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            metrics["post_processing_ms"] = round((time.time() - t0_post) * 1000, 2)
            
            metrics["total_ms"] = round((time.time() - t0_total) * 1000, 2)
            
            return {
                "transacoes": transacoes_list,
                "metrics": metrics,
                "file_name_to_delete": uploaded_file.name if uploaded_file else None
            }
            
        except Exception as e:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    async def analisar_plano_saude_unimed_odonto(self, file_content: bytes, file_name: str, colaboradores: List[str]) -> Dict[str, Any]:
        print(">>> EXECUÇÃO EXTRAÇÃO PYTHON - UNIMED ODONTO <<<", flush=True)
        metrics = {
            "upload_pdf_ms": 0.0,
            "file_ready_ms": 0.0,
            "gemini_generation_ms": 0.0,
            "structured_output_ms": 0.0,
            "post_processing_ms": 0.0,
            "total_ms": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }
        
        t0_total = time.time()
        
        try:
            # 1. Extrair texto usando pypdf em memória
            t0_prep = time.time()
            import io
            import difflib
            import re
            
            pdf_file = io.BytesIO(file_content)
            reader = pypdf.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            metrics["upload_pdf_ms"] = round((time.time() - t0_prep) * 1000, 2)
            
            # 2. Parsear as linhas deterministicamente
            lines = text.split('\n')
            
            titulares = {}
            dependentes = []
            
            beneficiary_pattern = re.compile(r'(\d\.\d{7}\.\d{8}-\d)')
            tp_pattern = re.compile(r'\s([TDA])\s')
            val_pattern = re.compile(r'(\d+,\d{2}-?)')
            
            # Log das primeiras linhas com matrícula para debug de CPF
            _debug_count = 0
            for line in lines:
                line = line.strip()
                benef_match = beneficiary_pattern.search(line)
                if not benef_match:
                    continue
                if _debug_count < 5:
                    print(f"[DEBUG UNIMED LINE] {repr(line)}")
                    _debug_count += 1
                    
                num_benef = benef_match.group(1)
                prefix = num_benef[:-4]
                
                tp_match = tp_pattern.search(line)
                if not tp_match:
                    continue
                tp = tp_match.group(1)
                
                name_match = re.match(r'^([A-Z\u00C0-\u00FF\s\.\,\-\'\?]+?)\s*(?=\d)', line)
                if not name_match:
                    continue
                name = name_match.group(1).strip()
                
                # Busca CPF em qualquer posição da linha (com ou sem formatação)
                documento = None
                # Tenta primeiro CPF formatado: 000.000.000-00
                cpf_fmt_match = re.search(r'\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b', line)
                if cpf_fmt_match:
                    documento = self._normaliza_cpf(cpf_fmt_match.group(1))
                else:
                    # Tenta CPF como 8 a 11 dígitos consecutivos (não parte de matrícula
                    # longa) — pode vir com 1 a 3 zeros à esquerda faltando. A matrícula
                    # tem formato X.XXXXXXX.XXXXXXXX-X — excluímos ela.
                    linha_sem_matricula = beneficiary_pattern.sub('', line)
                    cpf_raw_match = re.search(r'(?<!\d)(\d{8,11})(?!\d)', linha_sem_matricula)
                    if cpf_raw_match:
                        documento = self._normaliza_cpf(cpf_raw_match.group(1))
                
                val_matches = val_pattern.findall(line)
                if not val_matches:
                    continue
                    
                val_str = val_matches[0]
                if val_str.endswith('-'):
                    valor = -float(val_str[:-1].replace(',', '.'))
                else:
                    valor = float(val_str.replace(',', '.'))
                    
                if tp == 'T':
                    if prefix in titulares:
                        titulares[prefix]["valor_titular"] = round(titulares[prefix]["valor_titular"] + valor, 2)
                        titulares[prefix]["valor_total"] = round(titulares[prefix]["valor_total"] + valor, 2)
                        # If a later line has the CPF, update it
                        if documento and not titulares[prefix].get("documento"):
                            titulares[prefix]["documento"] = documento
                    else:
                        # Match name to database colaboradores using diff
                        nome_db = name
                        closest = difflib.get_close_matches(name, colaboradores, n=1, cutoff=0.85)
                        if closest:
                            nome_db = closest[0]
                            
                        titulares[prefix] = {
                            "nome_pdf": name,
                            "nome_db": nome_db,
                            "matricula": prefix,
                            "valor_titular": valor,
                            "dependentes": [],
                            "valor_total": valor,
                            "centro_custo": "N/D",
                            "unidade": "N/D",
                            "documento": documento
                        }
                else:
                    dependentes.append({
                        "nome": name,
                        "tipo": tp,
                        "valor": valor,
                        "parent_prefix": prefix
                    })
                    
            # Associar dependentes
            for dep in dependentes:
                parent_prefix = dep["parent_prefix"]
                if parent_prefix in titulares:
                    titulares[parent_prefix]["dependentes"].append({
                        "nome": dep["nome"],
                        "tipo": dep["tipo"],
                        "valor": dep["valor"]
                    })
                    titulares[parent_prefix]["valor_total"] = round(titulares[parent_prefix]["valor_total"] + dep["valor"], 2)
            
            titulares_list = list(titulares.values())
            
            metrics["gemini_generation_ms"] = 0.0
            metrics["structured_output_ms"] = 0.0
            metrics["post_processing_ms"] = round((time.time() - t0_total) * 1000, 2)
            metrics["total_ms"] = round((time.time() - t0_total) * 1000, 2)
            
            return {
                "titulares": titulares_list,
                "metrics": metrics,
                "file_name_to_delete": None
            }
            
        except Exception as e:
            raise e

    async def analisar_plano_saude_sorriso(self, file_content: bytes, file_name: str, colaboradores: List[str]) -> Dict[str, Any]:
        if not self.client:
            raise Exception("API Key do Gemini não configurada.")
            
        metrics = {
            "upload_pdf_ms": 0.0,
            "file_ready_ms": 0.0,
            "gemini_generation_ms": 0.0,
            "structured_output_ms": 0.0,
            "post_processing_ms": 0.0,
            "total_ms": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }
        
        t0_total = time.time()
        
        try:
            # 1. Extrair texto usando pypdf em memória
            t0_prep = time.time()
            import io
            pdf_file = io.BytesIO(file_content)
            reader = pypdf.PdfReader(pdf_file)
            text = ""
            for idx, page in enumerate(reader.pages):
                text += f"--- PAGE {idx+1} ---\n" + page.extract_text() + "\n"
            metrics["upload_pdf_ms"] = round((time.time() - t0_prep) * 1000, 2)

            total_paginas = len(reader.pages)

            prompt = f"""
            Você é um assistente especializado em auditoria de planos de saúde e odontológicos.
            Sua tarefa é analisar o texto extraído do relatório de beneficiários do plano SORRISO CONVÊNIO ODONTOLÓGICO abaixo e extrair os titulares e dependentes com seus respectivos valores (mensalidade).

            Texto Extraído do PDF:
            {text}

            Regras de Extração e Estruturação:
            1. O arquivo possui {total_paginas} páginas (PÁGINA 1 a PÁGINA {total_paginas}). Você deve ler e processar todo o texto fornecido, de todas as páginas. NÃO pare a extração na primeira página; percorra todas as páginas para extrair todos os titulares e dependentes efetivamente presentes no texto — não assuma um total fixo de antemão.
            2. Identifique todos os titulares (TIPO = T) em todas as páginas do PDF.
            3. Identifique todos os dependentes (TIPO = D) vinculados a cada titular. No PDF, os dependentes são listados logo após o respectivo titular e antes da linha de SUBTOTAL do grupo familiar correspondente.
            4. Extraia o nome literal do titular e do dependente exatamente como consta no PDF. Preencha os campos "nome_pdf" e "nome_db" com esse exato mesmo valor literal extraído, sem tentar corrigir ou deduzir nomes.
            5. Extraia o valor unitário da mensalidade (coluna "VR. MENS.") para o titular (valor_titular) e para cada dependente (valor).
            6. Calcule a soma de mensalidade do titular e de todos os dependentes do seu grupo familiar e preencha em "valor_total".
            7. Extraia o CPF do titular (coluna "CPF", 11 dígitos) e preencha no campo "documento", apenas os números, sem pontuação. Se não houver CPF legível para aquele titular, deixe "documento" nulo.

            Retorne o resultado de todos os titulares de todas as páginas estritamente conforme o schema estruturado EstruturaExtracaoPlanoSaude.
            """
            
            max_retries = 3
            response = None
            
            t0_gen = time.time()
            for attempt in range(max_retries):
                try:
                    response = await self.client.aio.models.generate_content(
                        model=self.model_name,
                        contents=[prompt],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=SCHEMA_PLANO_SAUDE
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
            titulares_list = []
            if response and response.parsed:
                if isinstance(response.parsed, dict):
                    titulares_list = response.parsed.get("titulares", [])
                else:
                    titulares_list = [t.model_dump() for t in response.parsed.titulares]
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
                    titulares_list = data.get("titulares", [])
            metrics["structured_output_ms"] = round((time.time() - t0_struct) * 1000, 2)
            
            if response and response.usage_metadata:
                metrics["input_tokens"] = response.usage_metadata.prompt_token_count or 0
                metrics["output_tokens"] = response.usage_metadata.candidates_token_count or 0
                metrics["total_tokens"] = response.usage_metadata.total_token_count or 0
            
            t0_post = time.time()
            metrics["post_processing_ms"] = round((time.time() - t0_post) * 1000, 2)
            
            metrics["total_ms"] = round((time.time() - t0_total) * 1000, 2)
            
            return {
                "titulares": titulares_list,
                "metrics": metrics,
                "file_name_to_delete": None
            }
            
        except Exception as e:
            raise e
