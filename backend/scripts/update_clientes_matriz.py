"""
Script de Atualização da Coluna clientes.idMatriz
Fonte de Dados: files/cod-emitente,nome-matriz,nome-abrev,nome-emit.xlsx

Mapeamento:
1. Planilha: cod-emitente -> nome-matriz
2. Tabela matrizcliente: codigo (nome-matriz) -> idmatrizCliente
3. Tabela clientes: update c.idMatriz = idmatrizCliente WHERE c.codigo = cod-emitente

Uso:
  python backend/scripts/update_clientes_matriz.py          -> Gera o arquivo SQL files/update_clientes_idmatriz.sql
  python backend/scripts/update_clientes_matriz.py --exec   -> Gera o SQL e executa o UPDATE no banco configurado no .env
"""

import sys
import os
from pathlib import Path
import pandas as pd

# Garante path para importar app se necessário
BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

EXCEL_PATH = REPO_ROOT / "files" / "cod-emitente,nome-matriz,nome-abrev,nome-emit.xlsx"
OUTPUT_SQL_PATH = REPO_ROOT / "files" / "update_clientes_idmatriz.sql"


def carregar_dados():
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {EXCEL_PATH}")

    print(f"Lendo planilha: {EXCEL_PATH} ...")
    df = pd.read_excel(EXCEL_PATH)
    print(f"Total de linhas na planilha: {len(df):,}")

    df["cod-emitente"] = pd.to_numeric(df["cod-emitente"], errors="coerce").fillna(0).astype(int)
    df["nome-matriz"] = df["nome-matriz"].astype(str).str.strip()

    # Mapeamento único cod-emitente -> nome-matriz
    df_unique = df.drop_duplicates(subset=["cod-emitente"], keep="first")
    return df_unique[["cod-emitente", "nome-matriz"]]


def obter_mapa_matrizes(db):
    from sqlalchemy import text
    res = db.execute(text("SELECT idmatrizCliente, codigo FROM matrizcliente")).fetchall()
    return {row[1]: row[0] for row in res}


def obter_clientes_banco(db):
    from sqlalchemy import text
    res = db.execute(text("SELECT idclientes, codigo, nome_abrev FROM clientes")).fetchall()
    return res


def gerar_arquivo_sql(updates: list[tuple[int, int]]):
    print(f"Gerando arquivo SQL: {OUTPUT_SQL_PATH} ...")

    linhas_sql = [
        "-- =====================================================================",
        "-- ATUALIZACAO DA COLUNA idMatriz NA TABELA clientes",
        "-- Fonte: files/cod-emitente,nome-matriz,nome-abrev,nome-emit.xlsx",
        "-- Cruzamento: clientes.codigo = cod-emitente -> nome-matriz -> matrizcliente.idmatrizCliente",
        f"-- Total de clientes a atualizar: {len(updates):,}",
        "-- =====================================================================",
        "USE stamariabd;",
        "SET SQL_SAFE_UPDATES = 0;",
        ""
    ]

    # Quebra em lotes de 1.000 para compatibilidade e performance
    batch_size = 1000
    for i in range(0, len(updates), batch_size):
        chunk = updates[i : i + batch_size]
        rows_str = ",\n".join(f"  ROW({cod}, {mid})" for cod, mid in chunk)

        batch_sql = f"""UPDATE clientes c
JOIN (VALUES
{rows_str}
) AS t (codigo, idMatriz) ON t.codigo = c.codigo
SET c.idMatriz = t.idMatriz;
"""
        linhas_sql.append(batch_sql)

    linhas_sql.extend([
        "SET SQL_SAFE_UPDATES = 1;",
        "",
        "-- Conferencia",
        "SELECT COUNT(*) AS total_clientes, ",
        "       SUM(idMatriz IS NOT NULL) AS com_matriz, ",
        "       SUM(idMatriz IS NULL) AS sem_matriz ",
        "FROM clientes;",
        "",
        "SELECT c.idclientes, c.codigo, c.nome_abrev, c.idMatriz, m.codigo AS cod_matriz, m.nome AS nome_matriz",
        "FROM clientes c",
        "LEFT JOIN matrizcliente m ON m.idmatrizCliente = c.idMatriz",
        "LIMIT 10;"
    ])

    with open(OUTPUT_SQL_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas_sql))

    print(f"Arquivo SQL gerado com sucesso! Tamanho: {os.path.getsize(OUTPUT_SQL_PATH) / 1024:.1f} KB")


def executar_update_banco(updates: list[tuple[int, int]], db):
    from sqlalchemy import text
    print("Executando UPDATE em lote diretamente no banco de dados...")

    batch_size = 1000
    total = len(updates)
    for i in range(0, total, batch_size):
        chunk = updates[i : i + batch_size]
        # Inserção temporária / update via bulk mapping
        db.execute(
            text("""
                UPDATE clientes 
                SET idMatriz = :idMatriz 
                WHERE codigo = :codigo
            """),
            [{"codigo": cod, "idMatriz": mid} for cod, mid in chunk]
        )
        print(f"  Atualizados {min(i + batch_size, total):,} de {total:,} clientes...")

    db.commit()

    total_com_matriz = db.execute(text("SELECT COUNT(*) FROM clientes WHERE idMatriz IS NOT NULL")).scalar()
    total_geral = db.execute(text("SELECT COUNT(*) FROM clientes")).scalar()
    print(f"\nSucesso! Clientes com idMatriz preenchido: {total_com_matriz:,} de {total_geral:,}")

    sample = db.execute(text("""
        SELECT c.idclientes, c.codigo, c.nome_abrev, c.idMatriz, m.codigo AS cod_matriz, m.nome AS nome_matriz
        FROM clientes c
        JOIN matrizcliente m ON m.idmatrizCliente = c.idMatriz
        LIMIT 5
    """)).fetchall()

    print("\nAmostra de conferência após o UPDATE:")
    for r in sample:
        print(f"  Cliente {r[1]} ({r[2]}) -> idMatriz: {r[3]} | Matriz: {r[4]} - {r[5]}")


def main():
    exec_db = "--exec" in sys.argv or "--db" in sys.argv

    df_excel = carregar_dados()
    emit_to_matriz = dict(zip(df_excel["cod-emitente"], df_excel["nome-matriz"]))

    from app.core.database import SessionLocal
    db = SessionLocal()

    try:
        matriz_map = obter_mapa_matrizes(db)
        print(f"Total de matrizes cadastradas em matrizcliente: {len(matriz_map):,}")

        clientes_banco = obter_clientes_banco(db)
        print(f"Total de clientes no banco: {len(clientes_banco):,}")

        updates = []
        nao_encontrados_excel = []
        matriz_nao_encontrada = []

        for cid, ccod, cabrev in clientes_banco:
            if ccod not in emit_to_matriz:
                nao_encontrados_excel.append((cid, ccod, cabrev))
                continue

            nmatriz = emit_to_matriz[ccod]
            if nmatriz not in matriz_map:
                matriz_nao_encontrada.append((cid, ccod, cabrev, nmatriz))
                continue

            mid = matriz_map[nmatriz]
            updates.append((ccod, mid))

        print(f"\nResumo do cruzamento:")
        print(f"  Clientes prontos para atualização: {len(updates):,}")
        print(f"  Clientes ausentes na planilha: {len(nao_encontrados_excel)}")
        if nao_encontrados_excel:
            for n in nao_encontrados_excel:
                print(f"    - ID: {n[0]}, Código: {n[1]}, Nome Abrev: {n[2]}")
        print(f"  Matrizes não encontradas na tabela: {len(matriz_nao_encontrada)}")

        gerar_arquivo_sql(updates)

        if exec_db:
            executar_update_banco(updates, db)
        else:
            print("\nPara executar o UPDATE diretamente no banco pelo Python:")
            print("  backend\\venv\\Scripts\\python.exe backend/scripts/update_clientes_matriz.py --exec")
            print("\nOu execute o script SQL gerado no MySQL Workbench/DBeaver:")
            print(f"  {OUTPUT_SQL_PATH}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
