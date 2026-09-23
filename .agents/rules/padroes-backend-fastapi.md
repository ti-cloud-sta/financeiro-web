# Padrões de Backend FastAPI

Diretrizes e boas práticas para desenvolvimento da API FastAPI em Python.

---

## 1. Arquitetura em Camadas
O backend segue separação estrita de responsabilidades:
- **`routers/`**: Declaração de rotas HTTP, injeção de dependências (`Depends(get_db)`), validação de entrada/saída via schemas Pydantic e chamada dos serviços correspondentes.
- **`services/`**: Concentração de todas as regras de negócio, transformações de dados, cruzamento de registros, orquestração de processamentos e validações complexas.
- **`repositories/`**: Consultas diretas ao banco de dados via SQLAlchemy, abstraindo operações de CRUD e persistência.
- **`models/`**: Entidades ORM do SQLAlchemy representando as tabelas do banco de dados MySQL.
- **`schemas/`**: Modelos Pydantic para validação, serialização e documentação automática OpenAPI.

---

## 2. Processamento Tabular e Streaming
- **Uso de Pandas**: Para importação e leitura de arquivos tabulares pesados (como planilhas Excel e CSVs), utilize a biblioteca `pandas` com tipos estritos e tratamento de nulos.
- **Streaming de Respostas Longas (NDJSON)**:
  - Nunca execute operações demoradas (como cruzamento de centenas de registros, validação de notas ou importações complexas) de forma síncrona bloqueante que deixe o frontend sem feedback.
  - Utilize o `StreamingResponse` do FastAPI com media type `application/x-ndjson`:
    ```python
    from fastapi.responses import StreamingResponse
    import json

    async def chunk_generator():
        for i, item in enumerate(itens):
            # processa item...
            yield json.dumps({"progresso": i + 1, "total": total, "detalhe": item.nome}) + "\n"

    return StreamingResponse(chunk_generator(), media_type="application/x-ndjson")
    ```

---

## 3. Validação e Sanitização com Pydantic
- **Nomes em Maiúsculas (Uppercase)**: Todos os cadastros de nomes de colaboradores devem obrigatoriamente ser validados para caixa alta no schema Pydantic através de `@field_validator`:
  ```python
  @field_validator('nome', mode='before')
  def force_uppercase(cls, v: str) -> str:
      return v.strip().upper() if isinstance(v, str) else v
  ```
- Garanta tipagens claras com `Optional`, `List` e anotações Pydantic v2.

---

## 4. Tratamento de Erros e Exceções
- Sempre utilize `HTTPException` com status code adequado (`400`, `404`, `422`, `500`) e passe uma mensagem clara e autoexplicativa no parâmetro `detail`.
- O frontend consome diretamente o `err.error?.detail` para alertar o usuário com precisão sobre o que falhou.
