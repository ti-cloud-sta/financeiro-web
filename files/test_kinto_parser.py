import pypdf
import re

def test_kinto_parser():
    reader = pypdf.PdfReader('c:/Users/joeder-blanca/Documents/projetos-joe/git/colab/financeiro-web/files/Kinto.pdf')
    full_text = ""
    for page in reader.pages:
        full_text += (page.extract_text() or "") + "\n"
        
    fatura_match = re.search(r'(\d+)http://www\.kinto', full_text, flags=re.IGNORECASE)
    fatura = f"FATURA {fatura_match.group(1)}" if fatura_match else "Não Identificada"
    print(f"Fatura: {fatura}")
    
    usuario = "Rubens P. V. A. Netto"
    print(f"Usuario: {usuario}")
    
    saldo_match = re.search(r'([\d\.,]+)VALOR TOTAL', full_text, flags=re.IGNORECASE)
    saldo = saldo_match.group(1).strip() if saldo_match else "0"
    print(f"Saldo: {saldo}")

if __name__ == '__main__':
    test_kinto_parser()
