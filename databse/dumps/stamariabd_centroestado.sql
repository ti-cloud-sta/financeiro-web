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
-- Table structure for table `centroestado`
--

DROP TABLE IF EXISTS `centroestado`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `centroestado` (
  `idCentroCusto` int NOT NULL,
  `estado` varchar(200) NOT NULL,
  KEY `centroEsta_idx` (`idCentroCusto`),
  CONSTRAINT `centroEsta` FOREIGN KEY (`idCentroCusto`) REFERENCES `centrocusto` (`idCentroCusto`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `centroestado`
--

LOCK TABLES `centroestado` WRITE;
/*!40000 ALTER TABLE `centroestado` DISABLE KEYS */;
INSERT INTO `centroestado` VALUES (214,'São Paulo'),(215,'São Paulo'),(216,'São Paulo'),(217,'São Paulo'),(218,'São Paulo'),(219,'São Paulo'),(263,'São Paulo'),(220,'São Paulo'),(221,'São Paulo'),(222,'São Paulo'),(223,'São Paulo'),(224,'São Paulo'),(225,'São Paulo'),(268,'São Paulo'),(226,'São Paulo'),(268,'Rio de Janeiro'),(226,'Rio de Janeiro'),(268,'Espírito Santo'),(226,'Espírito Santo'),(268,'Minas Gerais'),(226,'Minas Gerais'),(227,'São Paulo'),(228,'São Paulo'),(229,'São Paulo'),(230,'São Paulo'),(231,'São Paulo'),(232,'São Paulo'),(233,'São Paulo'),(234,'São Paulo'),(235,'São Paulo'),(236,'São Paulo'),(237,'São Paulo'),(238,'São Paulo'),(239,'São Paulo'),(240,'São Paulo'),(241,'São Paulo'),(242,'São Paulo'),(243,'São Paulo'),(244,'São Paulo'),(245,'São Paulo'),(246,'São Paulo'),(267,'Pará'),(247,'Pará'),(267,'Amapá'),(247,'Amapá'),(248,'São Paulo'),(249,'São Paulo'),(250,'São Paulo'),(262,'São Paulo'),(251,'São Paulo'),(262,'Rio de Janeiro'),(251,'Rio de Janeiro'),(262,'Espírito Santo'),(251,'Espírito Santo'),(262,'Minas Gerais'),(251,'Minas Gerais'),(252,'Mato Grosso'),(252,'Mato Grosso do Sul'),(252,'Goiás'),(252,'Distrito Federal'),(253,'Rio de Janeiro'),(253,'Espírito Santo'),(253,'Minas Gerais'),(254,'Pará'),(254,'Amapá'),(255,'Espírito Santo'),(256,'Espírito Santo'),(257,'Espírito Santo'),(258,'Espírito Santo'),(259,'Espírito Santo'),(260,'Espírito Santo'),(261,'Espírito Santo'),(264,'Exterior'),(265,'São Paulo'),(266,'Goiás'),(266,'Mato Grosso'),(266,'Mato Grosso do Sul'),(266,'Distrito Federal'),(270,'São Paulo'),(271,'São Paulo'),(272,'São Paulo'),(273,'São Paulo'),(276,'São Paulo'),(277,'São Paulo');
/*!40000 ALTER TABLE `centroestado` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-11 19:42:57
