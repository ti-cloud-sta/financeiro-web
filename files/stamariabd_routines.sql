-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: stamariabd
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
-- Temporary view structure for view `vw_nfpendencias_fase`
--

DROP TABLE IF EXISTS `vw_nfpendencias_fase`;
/*!50001 DROP VIEW IF EXISTS `vw_nfpendencias_fase`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `vw_nfpendencias_fase` AS SELECT 
 1 AS `idnfpendencias`,
 1 AS `titulo`,
 1 AS `dtVencimento`,
 1 AS `createdAt`,
 1 AS `idCliente`,
 1 AS `especie`,
 1 AS `carteira`,
 1 AS `idUnidade`,
 1 AS `serie`,
 1 AS `parccela`,
 1 AS `portador`,
 1 AS `dtEmissao`,
 1 AS `dtEntrega`,
 1 AS `valorOriginal`,
 1 AS `valorSaldo`,
 1 AS `fase`,
 1 AS `status`*/;
SET character_set_client = @saved_cs_client;

--
-- Final view structure for view `vw_nfpendencias_fase`
--

/*!50001 DROP VIEW IF EXISTS `vw_nfpendencias_fase`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `vw_nfpendencias_fase` AS select `p`.`idnfpendencias` AS `idnfpendencias`,`p`.`titulo` AS `titulo`,`p`.`dtVencimento` AS `dtVencimento`,`p`.`createdAt` AS `createdAt`,`p`.`idCliente` AS `idCliente`,`p`.`especie` AS `especie`,`p`.`carteira` AS `carteira`,`p`.`idUnidade` AS `idUnidade`,`p`.`serie` AS `serie`,`p`.`parccela` AS `parccela`,`p`.`portador` AS `portador`,`p`.`dtEmissao` AS `dtEmissao`,`p`.`dtEntrega` AS `dtEntrega`,`p`.`valorOriginal` AS `valorOriginal`,`p`.`valorSaldo` AS `valorSaldo`,(case when (ifnull(`p`.`encerrado`,'N') = 'S') then 'FINALIZADO' when ((`p`.`especie` = 'DP') and (`p`.`carteira` = 'DEV')) then 'LOGISTICA' when ((`p`.`especie` = 'DP') and (`p`.`tipoPedido` = 'PV') and (`p`.`dtEntrega` is null)) then 'LOGISTICA' when ((`p`.`especie` = 'DP') and (`p`.`tipoPedido` = 'ER') and (`p`.`carteira` = 'CAR') and (`p`.`dtEntrega` is not null) and (ifnull(`p`.`valorSaldo`,0) < ifnull(`p`.`valorOriginal`,0))) then 'FISCAL' else 'PENDENCIAS' end) AS `fase`,(case when (ifnull(`p`.`encerrado`,'N') = 'S') then 'Ok' when ((`p`.`especie` = 'DP') and (`p`.`carteira` = 'DEV')) then 'DEVOLUCAO' when ((`p`.`especie` = 'DP') and (`p`.`tipoPedido` = 'PV') and (`p`.`dtEntrega` is null)) then 'SEM DATA DE ENTREGA' else 'PENDENTE' end) AS `status` from `nfpendencias` `p` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-13 21:11:56
