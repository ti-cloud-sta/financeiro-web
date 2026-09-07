import pypdf

def main():
    reader = pypdf.PdfReader('c:/Users/joeder-blanca/Documents/projetos-joe/git/colab/financeiro-web/files/LOcaliza REnt.pdf')
    text = ""
    for page in reader.pages:
        text += (page.extract_text() or "") + "\n"
    
    with open('c:/Users/joeder-blanca/Documents/projetos-joe/git/colab/financeiro-web/files/localiza_rent_out.txt', 'w', encoding='utf-8') as f:
        f.write(text)

if __name__ == '__main__':
    main()
