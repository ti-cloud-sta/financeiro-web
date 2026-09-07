import pypdf
import re

def test_kinto():
    reader = pypdf.PdfReader('c:/Users/joeder-blanca/Documents/projetos-joe/git/colab/financeiro-web/files/Kinto.pdf')
    full_text = ""
    for page in reader.pages:
        full_text += (page.extract_text() or "") + "\n"
        
    print("----- FULL TEXT -----")
    print(full_text)
    print("---------------------")

if __name__ == '__main__':
    test_kinto()
