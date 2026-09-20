-- Script para adicionar rastreamento de fase e status no Histórico de Pendências
-- Execute este script no seu banco de dados MySQL

ALTER TABLE historicopendencia ADD COLUMN fase VARCHAR(50) DEFAULT NULL;
ALTER TABLE historicopendencia ADD COLUMN status VARCHAR(50) DEFAULT NULL;
