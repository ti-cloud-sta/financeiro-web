"""
Script de Carga da Tabela matrizcliente
Fonte de Dados: files/matriz_emitente.xlsx

Mapeamento:
- codigo = nome-matriz (código identificador único da matriz)
- nome   = nome-emit (razão social da matriz)

Quando uma matriz possui múltiplas filiais na planilha (ex.: ATACADAO com 568 lojas),
o script prioriza o registro onde nome-matriz == nome-abrev (loja matriz principal).

Uso:
  python backend/scripts/carga_matriz_cliente.py          -> Apenas gera o arquivo SQL files/carga_matrizcliente.sql
  python backend/scripts/carga_matriz_cliente.py --exec   -> Gera o SQL e executa a carga diretamente no banco de dados configurado no .env
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

EXCEL_PATH = REPO_ROOT / "files" / "matriz_emitente.xlsx"
OUTPUT_SQL_PATH = REPO_ROOT / "files" / "carga_matrizcliente.sql"


def escape_sql_string(val: str) -> str:
    if val is None:
        return "NULL"
    # Escapa aspas simples e barras invertidas para SQL padrão MySQL
    escaped = str(val).replace("\\", "\\\\").replace("'", "''")
    return f"'{escaped}'"


def preparar_dados():
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {EXCEL_PATH}")

    print(f"Lendo planilha: {EXCEL_PATH} ...")
    df = pd.read_excel(EXCEL_PATH)

    print(f"Total de linhas brutas: {len(df):,}")

    # Tratamento inicial
    df["cod-emitente"] = pd.to_numeric(df["cod-emitente"], errors="coerce").fillna(0).astype(int)
    df["nome-matriz"] = df["nome-matriz"].astype(str).str.strip()
    df["nome-abrev"] = df["nome-abrev"].astype(str).str.strip()
    df["nome-emit"] = df["nome-emit"].fillna("").astype(str).str.strip()

    # Pontuação para desempate
    df["is_exact_matriz"] = (df["nome-matriz"].str.upper() == df["nome-abrev"].str.upper()).astype(int)
    df["has_name"] = (df["nome-emit"] != "").astype(int)

    # Ordenação: prioriza registro onde matriz == abrev, depois que tem nome, depois menor código emitente
    df_sorted = df.sort_values(
        by=["nome-matriz", "is_exact_matriz", "has_name", "cod-emitente"],
        ascending=[True, False, False, True]
    )

    # Deduplicação por nome-matriz
    dedup = df_sorted.drop_duplicates(subset=["nome-matriz"], keep="first").copy()

    # Fallback se nome-emit estiver vazio
    dedup["final_nome"] = dedup["nome-emit"]
    mask_empty = dedup["final_nome"] == ""
    dedup.loc[mask_empty, "final_nome"] = dedup.loc[mask_empty, "nome-abrev"]

    # Truncamento de segurança para limites de schema (codigo: 200, nome: 100)
    dedup["codigo"] = dedup["nome-matriz"].str.slice(0, 200)
    dedup["nome"] = dedup["final_nome"].str.slice(0, 100)

    print(f"Total de matrizes únicas selecionadas: {len(dedup):,}")
    return dedup[["codigo", "nome"]]


def gerar_arquivo_sql(df_matrizes: pd.DataFrame):
    print(f"Gerando arquivo SQL: {OUTPUT_SQL_PATH} ...")

    linhas_sql = [
        "-- =====================================================================",
        "-- CARGA DA TABELA matrizcliente",
        "-- Fonte: files/matriz_emitente.xlsx",
        "-- Mapeamento: codigo = nome-matriz, nome = nome-emit",
        f"-- Total de matrizes unicas: {len(df_matrizes):,}",
        "-- =====================================================================",
        "USE stamariabd;",
        "SET SQL_SAFE_UPDATES = 0;",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "",
        "-- 1. Garante que a coluna codigo aceita VARCHAR(200)",
        "ALTER TABLE matrizcliente MODIFY COLUMN codigo VARCHAR(200) NULL DEFAULT NULL;",
        "",
        "-- 2. Limpa registros anteriores e reseta auto_increment",
        "TRUNCATE TABLE matrizcliente;",
        "SET FOREIGN_KEY_CHECKS = 1;",
        "",
        "-- 3. Insercao em lotes de 1.000 registros"
    ]

    batch_size = 1000
    total = len(df_matrizes)

    for i in range(0, total, batch_size):
        batch = df_matrizes.iloc[i : i + batch_size]
        values_list = []
        for _, row in batch.iterrows():
            c_esc = escape_sql_string(row["codigo"])
            n_esc = escape_sql_string(row["nome"])
            values_list.append(f"  ({c_esc}, {n_esc})")

        sql_insert = f"INSERT INTO matrizcliente (codigo, nome) VALUES\n" + ",\n".join(values_list) + ";"
        linhas_sql.append(sql_insert)
        linhas_sql.append("")

    linhas_sql.extend([
        "SET SQL_SAFE_UPDATES = 1;",
        "",
        "-- Conferencia",
        "SELECT COUNT(*) AS total_matrizes_carregadas FROM matrizcliente;",
        "SELECT * FROM matrizcliente LIMIT 10;"
    ])

    with open(OUTPUT_SQL_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas_sql))

    print(f"Arquivo SQL gerado com sucesso! Tamanho: {os.path.getsize(OUTPUT_SQL_PATH) / 1024:.1f} KB")


def executar_no_banco(df_matrizes: pd.DataFrame):
    print("Conectando ao banco de dados via SQLAlchemy...")
    from app.core.database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        print("Truncando tabela matrizcliente...")
        db.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        db.execute(text("TRUNCATE TABLE matrizcliente"))
        db.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        db.commit()

        print("Inserindo registros em lote...")
        registros = df_matrizes.to_dict(orient="records")

        # Inserção em lotes de 2000
        batch_size = 2000
        total = len(registros)
        for i in range(0, total, batch_size):
            chunk = registros[i : i + batch_size]
            db.execute(
                text("INSERT INTO matrizcliente (codigo, nome) VALUES (:codigo, :nome)"),
                chunk
            )
            print(f"  Inseridos {min(i + batch_size, total):,} de {total:,}...")

        db.commit()

        total_banco = db.execute(text("SELECT COUNT(*) FROM matrizcliente")).scalar()
        print(f"Sucesso! Total de registros em matrizcliente: {total_banco:,}")

        sample = db.execute(text("SELECT * FROM matrizcliente LIMIT 5")).fetchall()
        print("\nAmostra gravada:")
        for r in sample:
            print(" ", r)

    except Exception as e:
        db.rollback()
        print(f"Erro ao executar no banco: {e}")
        raise
    finally:
        db.close()


def main():
    exec_db = "--exec" in sys.argv or "--db" in sys.argv

    df_matrizes = preparar_dados()
    gerar_arquivo_sql(df_matrizes)

    if exec_db:
        executar_no_banco(df_matrizes)
    else:
        print("\nPara executar a carga diretamente no banco pelo Python:")
        print("  backend\\venv\\Scripts\\python.exe backend/scripts/carga_matriz_cliente.py --exec")
        print("\nOu execute o script SQL gerado no MySQL Workbench/DBeaver:")
        print(f"  {OUTPUT_SQL_PATH}")


if __name__ == "__main__":
    main()
