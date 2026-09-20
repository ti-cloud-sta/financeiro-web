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
-- Table structure for table `nfpendencias_mensagens`
--

DROP TABLE IF EXISTS `nfpendencias_mensagens`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nfpendencias_mensagens` (
  `idmensagem` int NOT NULL AUTO_INCREMENT,
  `idNfPendencias` int NOT NULL,
  `mensagem_id` varchar(200) DEFAULT NULL,
  `thread_id` varchar(100) DEFAULT NULL,
  `de` varchar(255) NOT NULL,
  `para` varchar(500) NOT NULL,
  `copia` varchar(500) DEFAULT NULL,
  `assunto` varchar(255) NOT NULL,
  `conteudo` longtext NOT NULL,
  `anexos` json DEFAULT NULL,
  `dataEnvio` datetime DEFAULT CURRENT_TIMESTAMP,
  `idUserCreated` int DEFAULT NULL,
  `minha_mensagem` char(1) DEFAULT 'S',
  PRIMARY KEY (`idmensagem`),
  KEY `idNfPendencias` (`idNfPendencias`),
  CONSTRAINT `nfpendencias_mensagens_ibfk_1` FOREIGN KEY (`idNfPendencias`) REFERENCES `nfpendencias` (`idnfpendencias`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `nfpendencias_mensagens`
--

LOCK TABLES `nfpendencias_mensagens` WRITE;
/*!40000 ALTER TABLE `nfpendencias_mensagens` DISABLE KEYS */;
INSERT INTO `nfpendencias_mensagens` VALUES (1,7812,'1a0b5ae3374bfc7c','1a0b5ae3374bfc7c','tania.canedo@stamaria.ind.br','joebblanca@gmail.com',NULL,'Cobrança - Título 0288540 - ANGELO RICARDO RIBEIRO DA SI…','Teste<br><br><img src=\"https://stamaria.cloud/assets/images/assinatura.png\" alt=\"Assinatura\" style=\"max-width: 100%; height: auto;\">','[{\"nome\": \"Banco do Brasil.pdf\", \"tamanho\": 0}]','2026-09-18 15:01:27',3,'S');
/*!40000 ALTER TABLE `nfpendencias_mensagens` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-19 12:18:06
