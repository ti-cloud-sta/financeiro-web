-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: localhost    Database: stamariabd
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `importacoes`
--

DROP TABLE IF EXISTS `importacoes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `importacoes` (
  `idImportacoes` int NOT NULL AUTO_INCREMENT,
  `nomeArquivo` varchar(200) NOT NULL,
  `extensaoArquivo` varchar(10) NOT NULL,
  `idEmpresa` int DEFAULT NULL,
  `createdAt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updatedAte` datetime DEFAULT NULL,
  `tipo` varchar(45) NOT NULL,
  `idUserInc` int DEFAULT NULL,
  PRIMARY KEY (`idImportacoes`),
  KEY `importEmpresa_idx` (`idEmpresa`),
  KEY `importUser_idx` (`idUserInc`),
  CONSTRAINT `importEmpresa` FOREIGN KEY (`idEmpresa`) REFERENCES `empresas` (`idEmpresas`),
  CONSTRAINT `importUser` FOREIGN KEY (`idUserInc`) REFERENCES `users` (`iduser`)
) ENGINE=InnoDB AUTO_INCREMENT=361 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `importacoes`
--

LOCK TABLES `importacoes` WRITE;
/*!40000 ALTER TABLE `importacoes` DISABLE KEYS */;
INSERT INTO `importacoes` VALUES (218,'texto1 (46)_conciliado.xlsx','xlsx',NULL,'2026-09-11 08:30:47',NULL,'Prorrogação - Atacadão',13),(219,'RELAÇÃO FUNCIONÁRIOS ATIVOS - AGOSTO 2026.xlsx','xlsx',NULL,'2026-09-11 08:37:31',NULL,'COLABORADORES',NULL),(220,'RELAÇÃO FUNCIONÁRIOS ATIVOS - AGOSTO 2026.xlsx','xlsx',NULL,'2026-09-11 08:41:28',NULL,'COLABORADORES',NULL),(222,'seguro vida 104..pdf','pdf',23,'2026-09-11 08:47:14',NULL,'SEGURO',3),(223,'seguro vida 106..pdf','pdf',23,'2026-09-11 08:48:20',NULL,'SEGURO',3),(224,'Seguro Saude..pdf','pdf',22,'2026-09-11 08:51:17',NULL,'SEGURO',3),(225,'Sorriso..pdf','pdf',21,'2026-09-11 08:52:05',NULL,'PLANO_SAUDE',3),(226,'ANALITICO TAXA DE FATURAMENTO  (104) (1).pdf','pdf',25,'2026-09-11 08:52:35',NULL,'PLANO_SAUDE',3),(227,'ANALITICO TAXA DE FATURAMENTO  (106) (1).pdf','pdf',25,'2026-09-11 08:58:25',NULL,'PLANO_SAUDE',3),(228,'CO- PARTICIPAÇÃO (104) (1).pdf','pdf',25,'2026-09-11 08:58:39',NULL,'PLANO_SAUDE',3),(230,'Odonto 101..pdf','pdf',28,'2026-09-11 09:04:27',NULL,'PLANO_SAUDE',3),(231,'Odonto 104..pdf','pdf',28,'2026-09-11 09:05:37',NULL,'PLANO_SAUDE',3),(232,'Odonto 106..pdf','pdf',28,'2026-09-11 09:09:53',NULL,'PLANO_SAUDE',3),(233,'seguro vida 101..pdf','pdf',23,'2026-09-11 09:21:13',NULL,'SEGURO',3),(234,'demonstrativo-fatura-mensal_39888202673139898 (1).csv','csv',29,'2026-09-11 09:25:44',NULL,'PLANO_SAUDE',3),(236,'demonstrativo-fatura-mensal_39936202673139938 (1).csv','csv',29,'2026-09-11 09:27:38',NULL,'PLANO_SAUDE',3),(237,'demonstrativo-fatura-mensal_42157202673142159 (1).csv','csv',29,'2026-09-11 09:27:56',NULL,'PLANO_SAUDE',3),(238,'demonstrativo-fatura-mensal_39925202673139928 (1).csv','csv',29,'2026-09-11 09:30:55',NULL,'PLANO_SAUDE',3),(239,'CO- PARTICIPAÇÃO (106) (1).pdf','pdf',25,'2026-09-11 09:43:11',NULL,'PLANO_SAUDE',3),(240,'RELATÓRIO FUNCIONÁRIOS ATIVOS- SETEMBRO.xlsx','xlsx',NULL,'2026-09-11 09:59:47',NULL,'COLABORADORES',NULL),(241,'Pagamento Sendas 11.09.2026_extraido.xlsx','xlsx',NULL,'2026-09-11 11:27:52',NULL,'Composição - Sendas',3),(252,'RELATÓRIO FUNCIONÁRIOS ATIVOS- SETEMBRO.xlsx','xlsx',NULL,'2026-09-11 21:41:17',NULL,'COLABORADORES',NULL),(253,'RELATÓRIO FUNCIONÁRIOS ATIVOS- SETEMBRO.xlsx','xlsx',NULL,'2026-09-11 21:44:03',NULL,'COLABORADORES',NULL),(262,'Liberação 20260909 (4) (1).xlsx','xlsx',NULL,'2026-09-12 23:16:50',NULL,'Conciliação Bancária',3),(263,'Liberação 20260911.xlsx','xlsx',NULL,'2026-09-13 09:53:21',NULL,'Conciliação Bancária',3),(264,'planilha_conciliada_Liberação 20260911.xlsx','xlsx',NULL,'2026-09-13 10:00:30',NULL,'Conciliação Bancária',3),(265,'Liberação 20260911.xlsx','xlsx',NULL,'2026-09-13 10:04:49',NULL,'Conciliação Bancária',3),(266,'Liberação 20260910.xlsx','xlsx',NULL,'2026-09-13 10:12:28',NULL,'Conciliação Bancária',3),(267,'Liberação 20260910.xlsx','xlsx',NULL,'2026-09-13 10:13:20',NULL,'Conciliação Bancária',3),(268,'Liberação 20260910.xlsx','xlsx',NULL,'2026-09-13 10:15:58',NULL,'Conciliação Bancária',3),(269,'Liberação 20260910.xlsx','xlsx',NULL,'2026-09-13 10:19:14',NULL,'Conciliação Bancária',3),(270,'Liberação 20260910.xlsx','xlsx',NULL,'2026-09-13 10:20:57',NULL,'Conciliação Bancária',3),(271,'Liberação 20260910.xlsx','xlsx',NULL,'2026-09-13 10:22:49',NULL,'Conciliação Bancária',3),(272,'Liberação 20260910.xlsx','xlsx',NULL,'2026-09-13 10:29:06',NULL,'Conciliação Bancária',3),(273,'Liberação 20260910.xlsx','xlsx',NULL,'2026-09-13 10:32:35',NULL,'Conciliação Bancária',3),(274,'Liberação 20260910.xlsx','xlsx',NULL,'2026-09-13 10:36:17',NULL,'Conciliação Bancária',3),(294,'Liberação 20260914.xlsx','xlsx',NULL,'2026-09-14 13:34:16',NULL,'Conciliação Bancária',3),(295,'texto1 (13)_conciliado.xlsx','xlsx',NULL,'2026-09-14 13:35:33',NULL,'Prorrogação - Atacadão',3),(296,'Sorriso.09.pdf','pdf',21,'2026-09-14 13:45:04',NULL,'PLANO_SAUDE',3),(297,'Odonto 101.09.pdf','pdf',28,'2026-09-14 13:53:21',NULL,'PLANO_SAUDE',3),(298,'Odonto 104.09.pdf','pdf',28,'2026-09-14 13:53:56',NULL,'PLANO_SAUDE',3),(299,'Odonto 106.09.pdf','pdf',28,'2026-09-14 14:04:11',NULL,'PLANO_SAUDE',3),(300,'Seguro de vida 101.09.pdf','pdf',23,'2026-09-14 14:16:40',NULL,'SEGURO',3),(301,'Seguro de vida 104.09.pdf','pdf',23,'2026-09-14 14:17:25',NULL,'SEGURO',3),(302,'Seguro de vida 106.09.pdf','pdf',23,'2026-09-14 14:19:19',NULL,'SEGURO',3),(303,'CO- PARTICIPAÇÃO (106) (2).pdf','pdf',25,'2026-09-14 14:24:00',NULL,'PLANO_SAUDE',3),(304,'ANALITICO TAXA DE FATURAMENTO  (106) (2).pdf','pdf',25,'2026-09-14 14:28:39',NULL,'PLANO_SAUDE',3),(305,'ANALITICO TAXA DE FATURAMENTO  (104) (2).pdf','pdf',25,'2026-09-14 14:29:11',NULL,'PLANO_SAUDE',3),(306,'demonstrativo-fatura-mensal_5738220269257390.csv','csv',29,'2026-09-14 14:31:47',NULL,'PLANO_SAUDE',3),(307,'demonstrativo-fatura-mensal_5744920269257453.csv','csv',29,'2026-09-14 14:32:33',NULL,'PLANO_SAUDE',3),(308,'demonstrativo-fatura-mensal_5751420269257516.csv','csv',29,'2026-09-14 14:33:04',NULL,'PLANO_SAUDE',3),(309,'demonstrativo-fatura-mensal_5754820269257550.csv','csv',29,'2026-09-14 14:33:21',NULL,'PLANO_SAUDE',3),(311,'pagamentos_CEMA (10)_extraido.xlsx','xlsx',NULL,'2026-09-15 08:56:09',NULL,'Prorrogação - Cema',13),(312,'sendas _conciliado.xlsx','xlsx',NULL,'2026-09-15 09:09:33',NULL,'Prorrogação - Sendas',13),(313,'raia_conciliado.xlsx','xlsx',NULL,'2026-09-15 09:50:09',NULL,'Prorrogação - Droga Raia',13),(314,'mart minas_conciliado.xlsx','xlsx',NULL,'2026-09-15 09:56:24',NULL,'Prorrogação - Mart Minas',13),(315,'bahamas_conciliado.xlsx','xlsx',NULL,'2026-09-15 10:17:32',NULL,'Prorrogação - Mart Minas',13),(316,'nordestao_conciliado.xlsx','xlsx',NULL,'2026-09-15 10:19:10',NULL,'Prorrogação - Mart Minas',13),(317,'savegnago_conciliado.xlsx','xlsx',NULL,'2026-09-15 10:21:12',NULL,'Prorrogação - Savegnago',13),(318,'Liberação 20260915.xlsx','xlsx',NULL,'2026-09-15 11:46:36',NULL,'Conciliação Bancária',3),(320,'ADIÇÃO_extraido.xlsx','xlsx',NULL,'2026-09-16 11:53:15',NULL,'Composição - Adição',3),(321,'Seguro Saude.09.pdf','pdf',22,'2026-09-16 14:20:28',NULL,'SEGURO',3),(322,'pagamento armazem mateus _extraido.xlsx','xlsx',NULL,'2026-09-16 14:33:33',NULL,'Composição - Mateus',3),(323,'Ze Ferino Pagamento_extraido.xlsx','xlsx',NULL,'2026-09-16 16:38:12',NULL,'Composição - Zeferino',3),(324,'Ze Ferino Pagamento_extraido.xlsx','xlsx',NULL,'2026-09-16 16:41:11',NULL,'Composição - Zeferino',3),(325,'Prorrogação Ze Ferino_conciliado.xlsx','xlsx',NULL,'2026-09-16 16:54:13',NULL,'Prorrogação - Zeferino',3),(326,'Prorrogação Ze Ferino_conciliado.xlsx','xlsx',NULL,'2026-09-16 16:56:43',NULL,'Prorrogação - Zeferino',3),(327,'pagamentos_CEMA_extraido.xlsx','xlsx',NULL,'2026-09-16 17:07:10',NULL,'Composição - Cema',3),(328,'pagamentos_CEMA_extraido.xlsx','xlsx',NULL,'2026-09-16 17:17:59',NULL,'Composição - Cema',3),(335,'pagamento cema_extraido.xlsx','xlsx',NULL,'2026-09-17 08:00:50',NULL,'Composição - Cema',13),(336,'ZEFERERINO_extraido.xlsx','xlsx',NULL,'2026-09-17 08:05:22',NULL,'Composição - Zeferino',13),(337,'texto1 (50)_conciliado.xlsx','xlsx',NULL,'2026-09-17 08:14:33',NULL,'Prorrogação - Atacadão',13),(340,'amazon pro _conciliado.xlsx','xlsx',NULL,'2026-09-17 08:31:59',NULL,'Prorrogação - Amazon',13),(342,'PRO ZEFERINO_conciliado.xlsx','xlsx',NULL,'2026-09-17 08:51:14',NULL,'Prorrogação - Zeferino',13),(343,'prorro cema_extraido.xlsx','xlsx',NULL,'2026-09-17 09:19:38',NULL,'Prorrogação - Cema',13),(344,'Liberação 20260917.xlsx','xlsx',NULL,'2026-09-17 10:38:17',NULL,'Conciliação Bancária',3),(347,'Kinto (2).pdf','pdf',2,'2026-09-17 00:00:00',NULL,'IA_DESPESAS',3),(348,'05.09.2026_CAIO MARCELO (1).pdf','pdf',3,'2026-09-17 00:00:00',NULL,'IA_DESPESAS',3),(349,'10.09.26_Jose Eduardo Carvalho Junior (1).pdf','pdf',1,'2026-09-17 00:00:00',NULL,'IA_DESPESAS',3),(353,'Fatura99041.pdf','pdf',4,'2026-09-17 00:00:00',NULL,'IA_DESPESAS',3),(354,'texto1 (52)_conciliado.xlsx','xlsx',NULL,'2026-09-18 08:03:38',NULL,'Prorrogação - Atacadão',13),(360,'ACR- 18.09.2026.xlsx','xlsx',NULL,'2026-09-20 13:38:09',NULL,'PENDENCIAS',3);
/*!40000 ALTER TABLE `importacoes` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-20 22:57:04
