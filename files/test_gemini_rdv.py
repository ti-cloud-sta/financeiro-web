import asyncio
from google import genai
from google.genai import types
import os
import io

async def main():
    # Carregar API key do .env
    from dotenv import load_dotenv
    load_dotenv('c:/Users/joeder-blanca/Documents/projetos-joe/git/colab/financeiro-web/backend/.env')
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    file_path = 'c:/Users/joeder-blanca/Documents/projetos-joe/git/colab/financeiro-web/files/RDV Clemerson De Almeida Espindola - Vitória.pdf'
    
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # Upload using File API for GenAI
    print("Uploading file to Gemini...")
    uploaded_file = await client.aio.files.upload(
        file=file_path,
        config=types.UploadFileConfig(mime_type="application/pdf")
    )
    print(f"File uploaded. Name: {uploaded_file.name}")
    
    prompt = """
    Analise a imagem deste Relatório de Despesas de Viagem e extraia as despesas listadas na tabela "Descrição" / "Vr.Total".
    Para cada despesa que tiver um valor preenchido na coluna Vr.Total (ignorar linhas zeradas), extraia:
    
    - colaborador: O nome do colaborador que aparece na linha abaixo de Cabeçalho (ex: CLEMERSON DE ALMEIDA ESPINDOLA).
    - motivo (codigo_rdv): O texto que está no campo 'Motivo' (ex: COMBUSTÍVEL - VIAGENS ATÉ FRANCA...).
    - categoria: A descrição da despesa na tabela (ex: Combustiveis / Lubrificantes).
    - valor: O valor na coluna Vr.Total (como número float, ex: 250.0).

    Retorne APENAS um JSON com o array "despesas".
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
    
    print("Chamando Gemini...")
    response = await client.aio.models.generate_content(
        model='gemini-2.5-flash',
        contents=[uploaded_file, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1
        )
    )
    
    print(response.text)

if __name__ == '__main__':
    asyncio.run(main())
