import asyncio
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv('c:/Users/joeder-blanca/Documents/projetos-joe/git/colab/financeiro-web/backend/.env')

from app.services.despesas_viagens_parser_service import DespesasViagensParserService

async def main():
    service = DespesasViagensParserService()
    file_path = 'c:/Users/joeder-blanca/Documents/projetos-joe/git/colab/financeiro-web/files/doc25142520260831103919.pdf'
    
    with open(file_path, "rb") as f:
        file_content = f.read()

    file_name = "doc25142520260831103919.pdf"
    categorias = ["Combustiveis / Lubrificantes"]
    colaboradores = ["CLEMERSON DE ALMEIDA ESPINDOLA"]
    empresa_context = "Santa Maria"
    
    print("Iniciando analisar_arquivo...")
    try:
        resultado = await service.analisar_arquivo(
            file_content=file_content,
            file_name=file_name,
            categorias=categorias,
            colaboradores=colaboradores,
            empresa_context=empresa_context,
            db=None
        )
        print("Sucesso!")
        print(resultado)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
