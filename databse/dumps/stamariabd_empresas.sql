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
-- Table structure for table `empresas`
--

DROP TABLE IF EXISTS `empresas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `empresas` (
  `idEmpresas` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(80) NOT NULL,
  `descricao` varchar(200) DEFAULT NULL,
  `createdAt` datetime DEFAULT CURRENT_TIMESTAMP,
  `updatedAte` datetime DEFAULT NULL,
  `nomeAbrev` varchar(100) DEFAULT NULL,
  `tipo` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`idEmpresas`)
) ENGINE=InnoDB AUTO_INCREMENT=32 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `empresas`
--

LOCK TABLES `empresas` WRITE;
/*!40000 ALTER TABLE `empresas` DISABLE KEYS */;
INSERT INTO `empresas` VALUES (1,'OnFly','Empresa de registro de empresas variadas.','2026-08-13 23:05:06','2026-08-25 23:11:02',NULL,NULL),(2,'Kinto','Empresa de aluguel de carros.','2026-08-13 23:05:33',NULL,NULL,NULL),(3,'RDV - SANTA MARIA','Gastos em geral de despesa de viagem','2026-08-14 21:08:36',NULL,NULL,NULL),(4,'TASTUR','Empresa de alguel de carros e viagens','2026-08-14 21:15:15',NULL,NULL,NULL),(5,'Localiza','Empresa de aluguel de carros.','2026-08-18 17:03:32','2026-08-18 17:03:48',NULL,NULL),(6,'Maiorca','Empresa de aluguel de carros.','2026-08-19 13:34:39','2026-08-19 13:34:47',NULL,NULL),(7,'Cartão Corporativo Banco do Brasil','Gastos em geral de despesa de viagem','2026-08-19 13:41:50','2026-08-19 13:47:04',NULL,'INVISIVEL'),(8,'Cartão Corporativo Banco Santander','Gastos em geral de despesa de viagem','2026-08-19 13:46:54','2026-09-07 14:34:44',NULL,NULL),(21,'SORRISO ODONTO','Plano odontológico Sorisso','2026-08-23 15:08:42',NULL,'UNIDENT','PLANO DE SAUDE'),(22,'SEGURO SAÚDE','Seguro saúde','2026-08-23 15:45:19','2026-08-23 15:45:47','SEGUROS UNIM','PLANO DE SAUDE'),(23,'SEGURO DE VIDA EM GRUPO','Seguro de vida da unidade 101','2026-08-23 15:45:36','2026-08-23 15:45:51','UNIMED SEG.','PLANO DE SAUDE'),(25,'UNIMED CAPIXABA','FATURA DE PLANO DE SAUDE','2026-08-30 14:47:27',NULL,'UNIMED NORT','PLANO DE SAUDE'),(28,'UNIMED ODONTO','Plano odontológico','2026-08-30 17:49:02',NULL,'UNIMED ODONT','PLANO DE SAUDE'),(29,'UNIMED ITUVERAVA','FATURA DE PLANO DE SAUDE','2026-08-30 18:23:45',NULL,'UNIMED ITUV','PLANO DE SAUDE'),(30,'SEGURO UNIMED','Seguro de vida da unidade 104 e 106','2026-08-30 18:23:45',NULL,'UNIMED SEG.','PLANO DE SAUDE'),(31,'SEM PARAR','','2026-09-07 13:02:13',NULL,NULL,'');
/*!40000 ALTER TABLE `empresas` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-11 19:43:42
