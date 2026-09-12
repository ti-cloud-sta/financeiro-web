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
) ENGINE=InnoDB AUTO_INCREMENT=251 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `importacoes`
--

LOCK TABLES `importacoes` WRITE;
/*!40000 ALTER TABLE `importacoes` DISABLE KEYS */;
INSERT INTO `importacoes` VALUES (218,'texto1 (46)_conciliado.xlsx','xlsx',NULL,'2026-09-11 08:30:47',NULL,'Prorrogação - Atacadão',13),(219,'RELAÇÃO FUNCIONÁRIOS ATIVOS - AGOSTO 2026.xlsx','xlsx',NULL,'2026-09-11 08:37:31',NULL,'COLABORADORES',NULL),(220,'RELAÇÃO FUNCIONÁRIOS ATIVOS - AGOSTO 2026.xlsx','xlsx',NULL,'2026-09-11 08:41:28',NULL,'COLABORADORES',NULL),(222,'seguro vida 104..pdf','pdf',23,'2026-09-11 08:47:14',NULL,'SEGURO',3),(223,'seguro vida 106..pdf','pdf',23,'2026-09-11 08:48:20',NULL,'SEGURO',3),(224,'Seguro Saude..pdf','pdf',22,'2026-09-11 08:51:17',NULL,'SEGURO',3),(225,'Sorriso..pdf','pdf',21,'2026-09-11 08:52:05',NULL,'PLANO_SAUDE',3),(226,'ANALITICO TAXA DE FATURAMENTO  (104) (1).pdf','pdf',25,'2026-09-11 08:52:35',NULL,'PLANO_SAUDE',3),(227,'ANALITICO TAXA DE FATURAMENTO  (106) (1).pdf','pdf',25,'2026-09-11 08:58:25',NULL,'PLANO_SAUDE',3),(228,'CO- PARTICIPAÇÃO (104) (1).pdf','pdf',25,'2026-09-11 08:58:39',NULL,'PLANO_SAUDE',3),(230,'Odonto 101..pdf','pdf',28,'2026-09-11 09:04:27',NULL,'PLANO_SAUDE',3),(231,'Odonto 104..pdf','pdf',28,'2026-09-11 09:05:37',NULL,'PLANO_SAUDE',3),(232,'Odonto 106..pdf','pdf',28,'2026-09-11 09:09:53',NULL,'PLANO_SAUDE',3),(233,'seguro vida 101..pdf','pdf',23,'2026-09-11 09:21:13',NULL,'SEGURO',3),(234,'demonstrativo-fatura-mensal_39888202673139898 (1).csv','csv',29,'2026-09-11 09:25:44',NULL,'PLANO_SAUDE',3),(236,'demonstrativo-fatura-mensal_39936202673139938 (1).csv','csv',29,'2026-09-11 09:27:38',NULL,'PLANO_SAUDE',3),(237,'demonstrativo-fatura-mensal_42157202673142159 (1).csv','csv',29,'2026-09-11 09:27:56',NULL,'PLANO_SAUDE',3),(238,'demonstrativo-fatura-mensal_39925202673139928 (1).csv','csv',29,'2026-09-11 09:30:55',NULL,'PLANO_SAUDE',3),(239,'CO- PARTICIPAÇÃO (106) (1).pdf','pdf',25,'2026-09-11 09:43:11',NULL,'PLANO_SAUDE',3),(240,'RELATÓRIO FUNCIONÁRIOS ATIVOS- SETEMBRO.xlsx','xlsx',NULL,'2026-09-11 09:59:47',NULL,'COLABORADORES',NULL),(241,'Pagamento Sendas 11.09.2026_extraido.xlsx','xlsx',NULL,'2026-09-11 11:27:52',NULL,'Composição - Sendas',3),(242,'demonstrativo-fatura-mensal_5754820269257550.csv','csv',29,'2026-09-11 14:02:45',NULL,'PLANO_SAUDE',3),(243,'demonstrativo-fatura-mensal_5738220269257390.csv','csv',29,'2026-09-11 14:05:13',NULL,'PLANO_SAUDE',3),(244,'demonstrativo-fatura-mensal_5751420269257516.csv','csv',29,'2026-09-11 14:05:59',NULL,'PLANO_SAUDE',3),(245,'demonstrativo-fatura-mensal_5744920269257453.csv','csv',29,'2026-09-11 14:09:17',NULL,'PLANO_SAUDE',3),(246,'Odonto 101.09.pdf','pdf',28,'2026-09-11 14:15:22',NULL,'PLANO_SAUDE',3),(247,'Odonto 104.09.pdf','pdf',28,'2026-09-11 14:17:28',NULL,'PLANO_SAUDE',3),(248,'Odonto 106.09.pdf','pdf',28,'2026-09-11 14:23:05',NULL,'PLANO_SAUDE',3),(249,'Sorriso.09.pdf','pdf',21,'2026-09-11 14:25:26',NULL,'PLANO_SAUDE',3),(250,'Odonto 106.09.pdf','pdf',23,'2026-09-11 19:02:49',NULL,'SEGURO',3);
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

-- Dump completed on 2026-09-11 19:44:01
