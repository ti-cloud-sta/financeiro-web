import pypdf
import re

def test_localiza_rent():
    reader = pypdf.PdfReader('c:/Users/joeder-blanca/Documents/projetos-joe/git/colab/financeiro-web/files/LOcaliza REnt.pdf')
    full_text = ""
    for page in reader.pages:
        full_text += (page.extract_text() or "") + "\n"
        
    fatura_match = re.search(r'Fatura\s+(\d+)', full_text, flags=re.IGNORECASE)
    fatura = f"FATURA {fatura_match.group(1)}" if fatura_match else "Não Identificada"
    print(f"Fatura: {fatura}")
    
    usuario_match = re.search(r'Usuário:\s*\d*\s*(.*?)\n', full_text, flags=re.IGNORECASE)
    usuario = usuario_match.group(1).strip() if usuario_match else "Não Identificado"
    print(f"Usuario: {usuario}")
    
    saldo_match = re.search(r'SALDO DEVIDO\s+([\d\.,]+)', full_text, flags=re.IGNORECASE)
    saldo = saldo_match.group(1).strip() if saldo_match else "0"
    print(f"Saldo: {saldo}")

if __name__ == '__main__':
    test_localiza_rent()
