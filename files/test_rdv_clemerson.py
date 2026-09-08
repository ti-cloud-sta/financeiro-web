import pypdf
import sys

def test_rdv_parser():
    reader = pypdf.PdfReader('c:/Users/joeder-blanca/Documents/projetos-joe/git/colab/financeiro-web/files/RDV Clemerson De Almeida Espindola - Vitória.pdf')
    full_text = ""
    for page in reader.pages:
        full_text += (page.extract_text() or "") + "\n"
        
    print("----- FULL TEXT -----")
    print(full_text[:3000])  # Just printing the first 3000 chars to see the structure
    print("---------------------")

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    test_rdv_parser()
