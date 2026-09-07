import pypdf
import sys

def main():
    reader = pypdf.PdfReader('c:/Users/joeder-blanca/Documents/projetos-joe/git/colab/financeiro-web/files/onfly2.pdf')
    text = ""
    for page in reader.pages:
        text += (page.extract_text() or "") + "\n"
    
    with open('c:/Users/joeder-blanca/Documents/projetos-joe/git/colab/financeiro-web/files/onfly2_out.txt', 'w', encoding='utf-8') as f:
        f.write(text)

if __name__ == '__main__':
    main()
