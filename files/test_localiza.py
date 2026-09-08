import pypdf
import re

def test_localiza():
    reader = pypdf.PdfReader('c:/Users/joeder-blanca/Documents/projetos-joe/git/colab/financeiro-web/files/LOCALIZA FLEET.pdf')
    full_text = ""
    for page in reader.pages:
        full_text += (page.extract_text() or "") + "\n"
        
    fatura_match = re.search(r'Fatura[:\s]*[A-Z]*[- ]?(\d+)', full_text)
    fatura = fatura_match.group(1) if fatura_match else "Não Identificada"
    print(f"Fatura: {fatura}")
    
    # We can search for blocks starting with 'Condutor:' and ending with 'Total'
    pattern = r'Condutor:\s*(.*?)\s*Início Cobrança:.*?Total\s+([\d\.,]+)'
    matches = re.finditer(pattern, full_text, flags=re.DOTALL)
    
    for m in matches:
        condutor = m.group(1).replace('\n', ' ').strip()
        valor = m.group(2).strip()
        print(f"Condutor: {condutor} | Valor: {valor}")

if __name__ == '__main__':
    test_localiza()
