import re
import pypdf
import sys

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

def test_parse():
    reader = pypdf.PdfReader('c:/Users/joeder-blanca/Documents/projetos-joe/git/colab/financeiro-web/files/onfly2.pdf')
    full_text = ""
    for page in reader.pages:
        full_text += (page.extract_text() or "") + "\n"
        
    fatura_match = re.search(r'Fatura\s+(\d+)', full_text)
    codigo_rdv = f"Fatura {fatura_match.group(1)}" if fatura_match else None
    
    # Remove footer
    full_text_cleaned = re.sub(r'ONFLY TECNOLOGIA LTDA.*?Data de vencimento:\s*\d{2}/\d{2}/\d{4}', '', full_text, flags=re.DOTALL)
    
    # regex for entry
    pattern = r'(Hotel|Aéreo|Carro|Ônibus|Transfer|Hospedagem|Voo|Seguro)\s+([A-Z0-9]{5,8})\s+(\d{2}/\d{2}/\d{4})(.*?)(R\$\s*[\d\.,]+)'
    matches = re.finditer(pattern, full_text_cleaned, flags=re.DOTALL)
    
    for m in matches:
        modal = m.group(1)
        protocolo = m.group(2)
        data_compra = m.group(3)
        middle_text = m.group(4)
        valor_str = m.group(5)
        
        print(f"Modal: {modal}, Prot: {protocolo}, Valor: {valor_str}")
        
        # In middle_text, the traveler (Viajante) is right before the CC.
        # The structure is Date1 Date2 Comprador Viajante CC
        # Example: 11/08/2026 12/08/2026 JANILSON \n SANTOS \n JANILSON \n SANTOS \n 14119 - \n MERCHANDISING \n CO
        # Note that Comprador and Viajante can have spaces and newlines.
        # Let's find the dates: \d{2}/\d{2}/\d{4}\s+\d{2}/\d{2}/\d{4}
        dates_match = re.search(r'(\d{2}/\d{2}/\d{4})\s*(\d{2}/\d{2}/\d{4})(.*)', middle_text, flags=re.DOTALL)
        if dates_match:
            rest = dates_match.group(3).strip()
            # The CC usually starts with digits and a dash: \d+ - 
            # Let's find the CC part
            cc_match = re.search(r'(\d+\s*-.*)', rest, flags=re.DOTALL)
            if cc_match:
                names_part = rest[:cc_match.start()].strip()
                cc_part = cc_match.group(1).strip()
                # names_part contains Comprador and Viajante. Since they are often the same or just two names,
                # we can try to split them. If they are exactly duplicated, Viajante is the second half.
                # Actually, in PyPDF, newlines might separate words. Let's remove newlines from names_part.
                names_clean = re.sub(r'\s+', ' ', names_part)
                viajante = extract_viajante(names_clean)
                print(f"  Names part: {names_clean} -> Viajante: {viajante}")
            else:
                print("  CC not found in:", rest)
        else:
            print("  Dates not found in:", middle_text)
            
if __name__ == '__main__':
    test_parse()
