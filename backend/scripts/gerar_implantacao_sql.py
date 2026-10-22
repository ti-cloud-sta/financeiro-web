"""
Gerador do Script Único de Implantação em Produção: files/implantacao.sql
Unifica DDL, Views, Carga de Matrizes e Atualização/Carga de Clientes com idMatriz.
"""

import sys
import os
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

EXCEL_PATH = REPO_ROOT / "files" / "cod-emitente,nome-matriz,nome-abrev,nome-emit.xlsx"
OUTPUT_SQL_PATH = REPO_ROOT / "files" / "implantacao.sql"


def escape_sql(val) -> str:
    if val is None or pd.isna(val):
        return "NULL"
    s = str(val).replace("\\", "\\\\").replace("'", "''")
    return f"'{s}'"


def gerar_implantacao():
    print(f"Lendo planilha: {EXCEL_PATH} ...")
    df = pd.read_excel(EXCEL_PATH)
    
    df["cod-emitente"] = pd.to_numeric(df["cod-emitente"], errors="coerce").fillna(0).astype(int)
    df["nome-matriz"] = df["nome-matriz"].astype(str).str.strip()
    df["nome-abrev"] = df["nome-abrev"].fillna("").astype(str).str.strip()
    df["nome-emit"] = df["nome-emit"].fillna("").astype(str).str.strip()

    # 1. Preparar matrizes únicas
    df["is_exact"] = (df["nome-matriz"].str.upper() == df["nome-abrev"].str.upper()).astype(int)
    df["has_name"] = (df["nome-emit"] != "").astype(int)
    df_sorted = df.sort_values(by=["nome-matriz", "is_exact", "has_name", "cod-emitente"], ascending=[True, False, False, True])
    dedup_matrizes = df_sorted.drop_duplicates(subset=["nome-matriz"], keep="first").copy()
    
    dedup_matrizes["final_nome"] = dedup_matrizes["nome-emit"]
    mask = dedup_matrizes["final_nome"] == ""
    dedup_matrizes.loc[mask, "final_nome"] = dedup_matrizes.loc[mask, "nome-abrev"]
    dedup_matrizes["codigo"] = dedup_matrizes["nome-matriz"].str.slice(0, 200)
    dedup_matrizes["nome"] = dedup_matrizes["final_nome"].str.slice(0, 100)

    # Mapa em memória de nome-matriz -> índice sequencial (idmatrizCliente simula auto_increment começando em 1)
    matriz_id_map = {row["codigo"]: idx + 1 for idx, (_, row) in enumerate(dedup_matrizes.iterrows())}

    print(f"Total de matrizes únicas: {len(dedup_matrizes):,}")

    # 2. Preparar clientes únicos
    df_clientes = df.drop_duplicates(subset=["cod-emitente"], keep="first").copy()
    df_clientes["final_nome"] = df_clientes["nome-emit"]
    mask_c = df_clientes["final_nome"] == ""
    df_clientes.loc[mask_c, "final_nome"] = df_clientes.loc[mask_c, "nome-abrev"]
    df_clientes["nome"] = df_clientes["final_nome"].str.slice(0, 100)
    df_clientes["nome_abrev"] = df_clientes["nome-abrev"].str.slice(0, 100)
    df_clientes["idMatriz"] = df_clientes["nome-matriz"].map(matriz_id_map)

    print(f"Total de clientes/emitentes na planilha: {len(df_clientes):,}")

    linhas = [
        "-- =====================================================================",
        "-- SCRIPT UNICO DE IMPLANTACAO - PREVISAO DE CAIXA E MATRIZES CLIENTES",
        "-- ERP SANTAMARIA",
        "-- Data: 2026-10-22",
        "--",
        "-- Este script contem TUDO o que e necessario para rodar em producao:",
        "--   1. DDL e Ajustes de Integridade (drop seguro de FK e alter de colunas)",
        "--   2. Criacao das 3 tabelas de previsao (apb, acr, titulos_liquidados)",
        "--   3. Criacao da VIEW vw_previsao_apb (regras de classificacao)",
        "--   4. Carga da tabela matrizcliente (28.323 registros)",
        "--   5. Atualizacao e Insercao dos Clientes com vinculo idMatriz",
        "--   6. Criacao de indices e foreign keys de performance",
        "--   7. Verificacao de integridade e totais",
        "-- =====================================================================",
        "SET SQL_SAFE_UPDATES = 0;",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "",
        "-- =====================================================================",
        "-- PASSO 1: AJUSTES ESTRUTURAIS EM TABELAS EXISTENTES",
        "-- =====================================================================",
        "",
        "-- 1.1 Desvincula a FK antiga entre nfpendencias e matrizcliente se existir",
        "SET @remove_fk_nf = IF(",
        "  (SELECT COUNT(*) FROM information_schema.table_constraints",
        "   WHERE table_schema = DATABASE() AND table_name = 'nfpendencias' AND constraint_name = 'nfClienteMatriz') > 0,",
        "  'ALTER TABLE `nfpendencias` DROP FOREIGN KEY `nfClienteMatriz`;',",
        "  'SELECT ''FK nfClienteMatriz ja nao existe em nfpendencias'' AS aviso;'",
        ");",
        "PREPARE stmt_fk_nf FROM @remove_fk_nf;",
        "EXECUTE stmt_fk_nf;",
        "DEALLOCATE PREPARE stmt_fk_nf;",
        "",
        "-- 1.2 Ajusta coluna codigo em matrizcliente para VARCHAR(200)",
        "ALTER TABLE `matrizcliente` MODIFY COLUMN `codigo` VARCHAR(200) NULL DEFAULT NULL;",
        "",
        "-- 1.3 Garante que a coluna idMatriz existe na tabela clientes",
        "SET @cria_coluna_matriz = IF(",
        "  (SELECT COUNT(*) FROM information_schema.columns",
        "   WHERE table_schema = DATABASE() AND table_name = 'clientes' AND column_name = 'idMatriz') = 0,",
        "  'ALTER TABLE `clientes` ADD COLUMN `idMatriz` INT NULL DEFAULT NULL AFTER `nome_abrev`;',",
        "  'SELECT ''coluna idMatriz ja existe em clientes'' AS aviso;'",
        ");",
        "PREPARE stmt_matriz FROM @cria_coluna_matriz;",
        "EXECUTE stmt_matriz;",
        "DEALLOCATE PREPARE stmt_matriz;",
        "",
        "-- 1.4 Garante indice de performance por codigo na tabela clientes",
        "SET @cria_idx_cod = IF(",
        "  (SELECT COUNT(*) FROM information_schema.statistics",
        "   WHERE table_schema = DATABASE() AND table_name = 'clientes' AND index_name = 'idx_clientes_codigo') = 0,",
        "  'ALTER TABLE `clientes` ADD INDEX `idx_clientes_codigo` (`codigo`);',",
        "  'SELECT ''indice idx_clientes_codigo ja existe'' AS aviso;'",
        ");",
        "PREPARE stmt_idx_cod FROM @cria_idx_cod;",
        "EXECUTE stmt_idx_cod;",
        "DEALLOCATE PREPARE stmt_idx_cod;",
        "",
        "-- =====================================================================",
        "-- PASSO 2: CRIACAO DAS TABELAS DO MODULO PREVISAO DE CAIXA",
        "-- =====================================================================",
        "",
        "CREATE TABLE IF NOT EXISTS `previsao_apb` (",
        "  `id` INT NOT NULL AUTO_INCREMENT,",
        "  `arquivo` VARCHAR(50) NULL COMMENT 'Identificador de lote/arquivo de origem',",
        "  `data` DATE NULL COMMENT 'Data do lancamento/fluxo',",
        "  `cod_tp_fluxo` VARCHAR(20) NULL COMMENT 'Codigo do tipo de fluxo (ex: 01.01.01)',",
        "  `ent_sai` VARCHAR(10) NULL COMMENT 'Indicador de Entrada ou Saida (ENT / SAI)',",
        "  `prev_real` VARCHAR(10) NULL COMMENT 'Previsao ou Real (PR / RE)',",
        "  `modulo` VARCHAR(20) NULL COMMENT 'Modulo de origem (APB / ACR)',",
        "  `vlr_cam_2` DECIMAL(15,2) NULL COMMENT 'Valor do campo 2',",
        "  `trans` VARCHAR(100) NULL COMMENT 'Tipo de transacao (ex: Implantacao, Liquidacao)',",
        "  `emp` VARCHAR(10) NULL COMMENT 'Codigo da empresa',",
        "  `estab` VARCHAR(10) NULL COMMENT 'Codigo do estabelecimento/filial',",
        "  `esp` VARCHAR(10) NULL COMMENT 'Especie do documento (DP, AN, etc)',",
        "  `serie` VARCHAR(20) NULL COMMENT 'Serie do documento',",
        "  `n_titulo` VARCHAR(50) NULL COMMENT 'Numero do titulo / documento',",
        "  `parcela` VARCHAR(10) NULL COMMENT 'Parcela do titulo',",
        "  `numero_fornecedor` VARCHAR(30) NULL COMMENT 'Codigo/numero do fornecedor ou cliente',",
        "  `nome_abrev` VARCHAR(100) NULL COMMENT 'Nome abreviado do favorecido/fornecedor',",
        "  `valor_fluxo` DECIMAL(15,2) NULL COMMENT 'Valor absoluto do fluxo financeiro',",
        "  `valor` DECIMAL(15,2) NULL COMMENT 'Valor liquido/nominal',",
        "  `nome_emitente` VARCHAR(255) NULL COMMENT 'Razao social / Nome completo do emitente',",
        "  `idImportacoes` INT NULL COMMENT 'FK para a tabela importacoes',",
        "  `data_criacao` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,",
        "  `usuario_inclusao` VARCHAR(100) NULL,",
        "  PRIMARY KEY (`id`),",
        "  INDEX `idx_previsao_apb_importacoes` (`idImportacoes`),",
        "  INDEX `idx_previsao_apb_data` (`data`),",
        "  INDEX `idx_previsao_apb_titulo` (`n_titulo`),",
        "  INDEX `idx_previsao_apb_fornecedor` (`numero_fornecedor`),",
        "  INDEX `idx_previsao_apb_modulo` (`modulo`),",
        "  INDEX `idx_previsao_apb_prev_real` (`prev_real`),",
        "  CONSTRAINT `fk_previsao_apb_importacoes`",
        "    FOREIGN KEY (`idImportacoes`) REFERENCES `importacoes` (`idImportacoes`)",
        "    ON DELETE CASCADE ON UPDATE CASCADE",
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
        "",
        "CREATE TABLE IF NOT EXISTS `previsao_acr` (",
        "  `id` INT NOT NULL AUTO_INCREMENT,",
        "  `est` VARCHAR(20) NULL,",
        "  `esp` VARCHAR(20) NULL,",
        "  `ser` VARCHAR(20) NULL,",
        "  `titulo` VARCHAR(50) NULL,",
        "  `parcela` VARCHAR(20) NULL,",
        "  `un_neg` VARCHAR(50) NULL,",
        "  `nr_pedcli` VARCHAR(50) NULL,",
        "  `tipo_pedido` VARCHAR(20) NULL,",
        "  `cliente` VARCHAR(50) NULL,",
        "  `nome_abrev` VARCHAR(100) NULL,",
        "  `nome_cliente` VARCHAR(255) NULL,",
        "  `grp_cliente` VARCHAR(50) NULL,",
        "  `cliente_matriz` VARCHAR(50) NULL,",
        "  `port` VARCHAR(50) NULL,",
        "  `cart` VARCHAR(50) NULL,",
        "  `repres` VARCHAR(50) NULL,",
        "  `emissao` DATE NULL,",
        "  `dt_entrega` DATE NULL,",
        "  `vencto` DATE NULL,",
        "  `dt_agdnto` DATE NULL,",
        "  `liquidac` DATE NULL,",
        "  `refer` VARCHAR(100) NULL,",
        "  `tit_banco` VARCHAR(50) NULL,",
        "  `moeda` VARCHAR(20) NULL,",
        "  `val_original` DECIMAL(15,2) NULL,",
        "  `saldo` DECIMAL(15,2) NULL,",
        "  `saldo_apresentacao` DECIMAL(15,2) NULL,",
        "  `cond_pagto` VARCHAR(50) NULL,",
        "  `vl_descto` DECIMAL(15,2) NULL,",
        "  `vl_abat` DECIMAL(15,2) NULL,",
        "  `dias` INT NULL,",
        "  `pedido_venda` VARCHAR(50) NULL,",
        "  `data_indic` DATE NULL,",
        "  `cond_cobr` VARCHAR(50) NULL,",
        "  `cidade` VARCHAR(100) NULL,",
        "  `telefone` VARCHAR(50) NULL,",
        "  `cidade_cobranca_cliente` VARCHAR(100) NULL,",
        "  `id_federal` VARCHAR(50) NULL,",
        "  `unid_federac` VARCHAR(10) NULL,",
        "  `idImportacoes` INT NULL,",
        "  `data_criacao` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,",
        "  `usuario_inclusao` VARCHAR(100) NULL,",
        "  PRIMARY KEY (`id`),",
        "  INDEX `idx_previsao_acr_importacao` (`idImportacoes`),",
        "  INDEX `idx_previsao_acr_titulo` (`titulo`),",
        "  INDEX `idx_previsao_acr_cliente` (`cliente`),",
        "  INDEX `idx_previsao_acr_vencto` (`vencto`),",
        "  INDEX `idx_previsao_acr_cart` (`cart`),",
        "  CONSTRAINT `fk_previsao_acr_importacoes`",
        "    FOREIGN KEY (`idImportacoes`) REFERENCES `importacoes` (`idImportacoes`)",
        "    ON DELETE CASCADE ON UPDATE CASCADE",
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
        "",
        "CREATE TABLE IF NOT EXISTS `previsao_titulos_liquidados` (",
        "  `id` INT NOT NULL AUTO_INCREMENT,",
        "  `estabelecimento` VARCHAR(20) NULL,",
        "  `especie_documento` VARCHAR(20) NULL,",
        "  `serie_documento` VARCHAR(20) NULL,",
        "  `titulo` VARCHAR(50) NULL,",
        "  `parcela` VARCHAR(20) NULL,",
        "  `cliente` VARCHAR(50) NULL,",
        "  `nome_cliente` VARCHAR(255) NULL,",
        "  `portador` VARCHAR(50) NULL,",
        "  `matriz` VARCHAR(100) NULL,",
        "  `representante` VARCHAR(50) NULL,",
        "  `nome_representante` VARCHAR(255) NULL,",
        "  `carteira` VARCHAR(50) NULL,",
        "  `data_vencimento` DATE NULL,",
        "  `data_credito` DATE NULL,",
        "  `data_emissao` DATE NULL,",
        "  `trans_abrev` VARCHAR(50) NULL,",
        "  `unid_negocio` VARCHAR(50) NULL,",
        "  `ad` VARCHAR(50) NULL,",
        "  `acumula_atraso` VARCHAR(20) NULL,",
        "  `nome_abreviado` VARCHAR(100) NULL,",
        "  `descricao_especie` VARCHAR(100) NULL,",
        "  `referencia` VARCHAR(100) NULL,",
        "  `val_movimento` DECIMAL(15,2) NULL,",
        "  `val_antecipado` DECIMAL(15,2) NULL,",
        "  `descto_abatim` DECIMAL(15,2) NULL,",
        "  `juros` DECIMAL(15,2) NULL,",
        "  `valor_liquido` DECIMAL(15,2) NULL,",
        "  `valor_pendente` DECIMAL(15,2) NULL,",
        "  `retencoes` DECIMAL(15,2) NULL,",
        "  `liquidacao` DATE NULL,",
        "  `vl_cheque` DECIMAL(15,2) NULL,",
        "  `grupo_cliente` VARCHAR(50) NULL,",
        "  `numero_plaqueta` VARCHAR(50) NULL,",
        "  `ult_aprop_desp_fin` VARCHAR(100) NULL,",
        "  `data_transacao` DATE NULL,",
        "  `cliente_matriz` VARCHAR(50) NULL,",
        "  `valor_original` DECIMAL(15,2) NULL,",
        "  `processo_exportacao` VARCHAR(50) NULL,",
        "  `soma_valor_original` VARCHAR(20) NULL,",
        "  `pedido_venda` VARCHAR(50) NULL,",
        "  `idImportacoes` INT NULL,",
        "  `data_criacao` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,",
        "  `usuario_inclusao` VARCHAR(100) NULL,",
        "  PRIMARY KEY (`id`),",
        "  INDEX `idx_prev_liq_importacao` (`idImportacoes`),",
        "  INDEX `idx_prev_liq_titulo` (`titulo`),",
        "  INDEX `idx_prev_liq_cliente` (`cliente`),",
        "  INDEX `idx_prev_liq_vencimento` (`data_vencimento`),",
        "  INDEX `idx_prev_liq_liquidacao` (`liquidacao`),",
        "  CONSTRAINT `fk_prev_liq_importacoes`",
        "    FOREIGN KEY (`idImportacoes`) REFERENCES `importacoes` (`idImportacoes`)",
        "    ON DELETE CASCADE ON UPDATE CASCADE",
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
        "",
        "-- =====================================================================",
        "-- PASSO 3: VIEW DE REGRAS DE NEGOCIO (vw_previsao_apb)",
        "-- =====================================================================",
        "CREATE OR REPLACE VIEW `vw_previsao_apb` AS",
        "SELECT",
        "  `a`.`id` AS `id`,",
        "  `a`.`idImportacoes` AS `idImportacoes`,",
        "  `a`.`arquivo` AS `arquivo`,",
        "  `a`.`data` AS `data`,",
        "  `a`.`cod_tp_fluxo` AS `cod_tp_fluxo`,",
        "  `a`.`ent_sai` AS `ent_sai`,",
        "  `a`.`prev_real` AS `prev_real`,",
        "  `a`.`modulo` AS `modulo`,",
        "  `a`.`vlr_cam_2` AS `vlr_cam_2`,",
        "  `a`.`trans` AS `trans`,",
        "  `a`.`emp` AS `emp`,",
        "  `a`.`estab` AS `estab`,",
        "  `a`.`esp` AS `esp`,",
        "  `a`.`serie` AS `serie`,",
        "  `a`.`n_titulo` AS `n_titulo`,",
        "  `a`.`parcela` AS `parcela`,",
        "  `a`.`numero_fornecedor` AS `numero_fornecedor`,",
        "  `a`.`nome_abrev` AS `nome_abrev`,",
        "  `a`.`valor_fluxo` AS `valor_fluxo`,",
        "  `a`.`valor` AS `valor`,",
        "  `a`.`nome_emitente` AS `nome_emitente`,",
        "  `a`.`data_criacao` AS `data_criacao`,",
        "  `a`.`usuario_inclusao` AS `usuario_inclusao`,",
        "  (CASE",
        "    WHEN UPPER(TRIM(`a`.`esp`)) = 'PR' AND TRIM(`a`.`cod_tp_fluxo`) = '04.01.01' THEN 'PROVISAO'",
        "    ELSE 'REAL'",
        "  END) AS `tipo_conta`,",
        "  (CASE",
        "    WHEN UPPER(TRIM(`a`.`esp`)) = 'PR' AND TRIM(`a`.`cod_tp_fluxo`) = '04.01.01' THEN 'PROVISAO'",
        "    WHEN UPPER(TRIM(`a`.`nome_abrev`)) IN ('13O SALARIO', '13º SALARIO', '13° SALARIO', 'FOLHA PAGTO', 'RESCIAO', 'RESCISAO', 'FERIAS') THEN 'BANCO_DO_BRASIL'",
        "    ELSE 'ITAU'",
        "  END) AS `banco_destino`",
        "FROM `previsao_apb` `a`;",
        "",
        "-- =====================================================================",
        "-- PASSO 4: CARGA DA TABELA matrizcliente (28.323 REGISTROS UNICOS)",
        "-- =====================================================================",
        "TRUNCATE TABLE `matrizcliente`;",
        "ALTER TABLE `matrizcliente` AUTO_INCREMENT = 1;",
        ""
    ]

    # Inserção das matrizes em lotes de 1.000
    batch_size = 1000
    for i in range(0, len(dedup_matrizes), batch_size):
        chunk = dedup_matrizes.iloc[i : i + batch_size]
        vals = []
        for _, r in chunk.iterrows():
            c_esc = escape_sql(r["codigo"])
            n_esc = escape_sql(r["nome"])
            vals.append(f"  ({c_esc}, {n_esc})")
        sql = "INSERT INTO `matrizcliente` (`codigo`, `nome`) VALUES\n" + ",\n".join(vals) + ";"
        linhas.append(sql)
        linhas.append("")

    linhas.extend([
        "-- =====================================================================",
        "-- PASSO 5: ATUALIZACAO E CARGA DA TABELA clientes VIA TABELA TEMPORARIA",
        "-- (Compatibilidade universal com qualquer versao de MySQL e alta velocidade)",
        "-- =====================================================================",
        "CREATE TEMPORARY TABLE `staging_clientes_matriz` (",
        "  `codigo` INT NOT NULL,",
        "  `nome` VARCHAR(100) NULL,",
        "  `nome_abrev` VARCHAR(100) NULL,",
        "  `idMatriz` INT NULL,",
        "  PRIMARY KEY (`codigo`)",
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;",
        ""
    ])

    # Insere dados dos clientes na staging em lotes de 1.000
    for i in range(0, len(df_clientes), batch_size):
        chunk = df_clientes.iloc[i : i + batch_size]
        vals_c = []
        for _, r in chunk.iterrows():
            c_cod = int(r["cod-emitente"])
            c_nom = escape_sql(r["nome"])
            c_abr = escape_sql(r["nome_abrev"])
            c_mid = int(r["idMatriz"]) if pd.notna(r["idMatriz"]) else "NULL"
            vals_c.append(f"  ({c_cod}, {c_nom}, {c_abr}, {c_mid})")
        sql_staging = "INSERT INTO `staging_clientes_matriz` (`codigo`, `nome`, `nome_abrev`, `idMatriz`) VALUES\n" + ",\n".join(vals_c) + ";"
        linhas.append(sql_staging)
        linhas.append("")

    # Executa o UPDATE e o INSERT a partir da staging
    linhas.extend([
        "-- 5.1 Atualiza idMatriz dos clientes que ja existem no cadastro",
        "UPDATE `clientes` `c`",
        "JOIN `staging_clientes_matriz` `s` ON `s`.`codigo` = `c`.`codigo`",
        "SET `c`.`idMatriz` = `s`.`idMatriz`;",
        "",
        "-- 5.2 Insere os novos emitentes da planilha que ainda nao existiam na tabela clientes",
        "INSERT INTO `clientes` (`codigo`, `nome`, `nome_abrev`, `idMatriz`)",
        "SELECT `s`.`codigo`, `s`.`nome`, `s`.`nome_abrev`, `s`.`idMatriz`",
        "FROM `staging_clientes_matriz` `s`",
        "LEFT JOIN `clientes` `c` ON `c`.`codigo` = `s`.`codigo`",
        "WHERE `c`.`codigo` IS NULL;",
        "",
        "-- 5.3 Limpeza da tabela temporaria",
        "DROP TEMPORARY TABLE IF EXISTS `staging_clientes_matriz`;",
        "",
        "-- =====================================================================",
        "-- PASSO 6: GARANTIA DE FOREIGN KEY ENTRE clientes E matrizcliente",
        "-- =====================================================================",
        "SET @cria_fk_cli = IF(",
        "  (SELECT COUNT(*) FROM information_schema.table_constraints",
        "   WHERE table_schema = DATABASE() AND table_name = 'clientes' AND constraint_name = 'clienteMatriz') = 0,",
        "  'ALTER TABLE `clientes` ADD CONSTRAINT `clienteMatriz` FOREIGN KEY (`idMatriz`) REFERENCES `matrizcliente` (`idmatrizCliente`) ON DELETE SET NULL ON UPDATE CASCADE;',",
        "  'SELECT ''FK clienteMatriz ja existe em clientes'' AS aviso;'",
        ");",
        "PREPARE stmt_fk_cli FROM @cria_fk_cli;",
        "EXECUTE stmt_fk_cli;",
        "DEALLOCATE PREPARE stmt_fk_cli;",
        "",
        "SET FOREIGN_KEY_CHECKS = 1;",
        "SET SQL_SAFE_UPDATES = 1;",
        "",
        "-- =====================================================================",
        "-- PASSO 7: CONFERENCIA FINAL DE SUCESSO",
        "-- =====================================================================",
        "SELECT 'Tabela matrizcliente' AS item, COUNT(*) AS total, '28.323' AS esperado FROM `matrizcliente`",
        "UNION ALL",
        "SELECT 'Clientes com Matriz', COUNT(*), '>= 37.894' FROM `clientes` WHERE `idMatriz` IS NOT NULL",
        "UNION ALL",
        "SELECT 'Tabela previsao_apb', COUNT(*), '0 (aguardando importacao)' FROM `previsao_apb`",
        "UNION ALL",
        "SELECT 'Tabela previsao_acr', COUNT(*), '0 (aguardando importacao)' FROM `previsao_acr`",
        "UNION ALL",
        "SELECT 'Tabela previsao_titulos_liquidados', COUNT(*), '0 (aguardando importacao)' FROM `previsao_titulos_liquidados`;",
        "",
        "SELECT 'IMPLANTACAO CONCLUIDA COM SUCESSO!' AS status;"
    ])

    print(f"Escrevendo arquivo SQL: {OUTPUT_SQL_PATH} ...")
    with open(OUTPUT_SQL_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    tamanho_mb = os.path.getsize(OUTPUT_SQL_PATH) / (1024 * 1024)
    print(f"Arquivo gerado com sucesso! Tamanho: {tamanho_mb:.2f} MB")


if __name__ == "__main__":
    gerar_implantacao()

