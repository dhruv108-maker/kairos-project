-- MySQL dump 10.13  Distrib 9.0.1, for macos15.1 (arm64)
--
-- Host: sagiros-db.cyxoemmc2q2b.us-east-1.rds.amazonaws.com    Database: kairos
-- ------------------------------------------------------
-- Server version	8.4.11

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `academic_years`
--

DROP TABLE IF EXISTS `academic_years`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `academic_years` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `institution_id` bigint unsigned NOT NULL,
  `label` varchar(30) NOT NULL,
  `starts_on` date NOT NULL,
  `ends_on` date NOT NULL,
  `year_label` varchar(30) DEFAULT NULL,
  `start_date` date DEFAULT NULL,
  `end_date` date DEFAULT NULL,
  `is_current` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_academic_year_label` (`institution_id`,`label`),
  CONSTRAINT `fk_academic_year_institution` FOREIGN KEY (`institution_id`) REFERENCES `institutions` (`id`),
  CONSTRAINT `ck_academic_year_dates` CHECK ((`ends_on` >= `starts_on`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `academic_years`
--

LOCK TABLES `academic_years` WRITE;
/*!40000 ALTER TABLE `academic_years` DISABLE KEYS */;
/*!40000 ALTER TABLE `academic_years` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `account_roles`
--

DROP TABLE IF EXISTS `account_roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `account_roles` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `account_id` bigint unsigned NOT NULL,
  `role_id` bigint unsigned NOT NULL,
  `institution_id` bigint unsigned DEFAULT NULL,
  `school_id` bigint unsigned DEFAULT NULL,
  `department_id` bigint unsigned DEFAULT NULL,
  `cohort_id` bigint unsigned DEFAULT NULL,
  `granted_by_account_id` bigint unsigned DEFAULT NULL,
  `granted_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `revoked_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_account_roles_active` (`account_id`,`revoked_at`),
  KEY `ix_roles_scope` (`role_id`,`institution_id`,`school_id`,`department_id`,`cohort_id`),
  KEY `fk_account_roles_institution` (`institution_id`),
  KEY `fk_account_roles_school` (`school_id`),
  KEY `fk_account_roles_department` (`department_id`),
  KEY `fk_account_roles_cohort` (`cohort_id`),
  KEY `fk_account_roles_granted_by` (`granted_by_account_id`),
  CONSTRAINT `fk_account_roles_account` FOREIGN KEY (`account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_account_roles_cohort` FOREIGN KEY (`cohort_id`) REFERENCES `cohorts` (`id`),
  CONSTRAINT `fk_account_roles_department` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`),
  CONSTRAINT `fk_account_roles_granted_by` FOREIGN KEY (`granted_by_account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_account_roles_institution` FOREIGN KEY (`institution_id`) REFERENCES `institutions` (`id`),
  CONSTRAINT `fk_account_roles_role` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`),
  CONSTRAINT `fk_account_roles_school` FOREIGN KEY (`school_id`) REFERENCES `schools` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `account_roles`
--

LOCK TABLES `account_roles` WRITE;
/*!40000 ALTER TABLE `account_roles` DISABLE KEYS */;
INSERT INTO `account_roles` VALUES (1,2,7001,11,NULL,NULL,NULL,NULL,'2026-10-24 13:59:19',NULL),(4,73001,7005,11,NULL,NULL,NULL,NULL,'2026-10-25 10:05:58',NULL);
/*!40000 ALTER TABLE `account_roles` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `accounts`
--

DROP TABLE IF EXISTS `accounts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `email` varchar(254) NOT NULL,
  `password_hash` varchar(255) DEFAULT NULL,
  `display_name` varchar(200) NOT NULL,
  `account_status` varchar(20) NOT NULL DEFAULT 'pending',
  `email_verified_at` datetime DEFAULT NULL,
  `last_login_at` datetime DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deactivated_at` datetime DEFAULT NULL,
  `full_name` varchar(255) NOT NULL,
  `phone_number` varchar(32) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `is_verified` tinyint(1) NOT NULL DEFAULT '0',
  `token_version` int NOT NULL DEFAULT '0',
  `verification_token` varchar(128) DEFAULT NULL,
  `reset_token` varchar(128) DEFAULT NULL,
  `reset_token_expires_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_accounts_email` (`email`),
  CONSTRAINT `ck_accounts_status` CHECK ((`account_status` in (_utf8mb4'pending',_utf8mb4'active',_utf8mb4'locked',_utf8mb4'disabled')))
) ENGINE=InnoDB AUTO_INCREMENT=73002 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accounts`
--

LOCK TABLES `accounts` WRITE;
/*!40000 ALTER TABLE `accounts` DISABLE KEYS */;
INSERT INTO `accounts` VALUES (2,'23sc06007@gsfcuniversity.ac.in','$argon2id$v=19$m=65536,t=3,p=4$shHcN1z/+bu2xRWjHUuTXw$ynNJDCgzelDFcYapnvhSOtn8X0JvvjiUkofdThgG+fY','Dhruv Verma','active',NULL,'2026-10-25 08:34:25','2026-10-24 13:59:18','2026-10-25 08:36:48',NULL,'Dhruv Verma',NULL,1,1,3,'a7b5b6e459fae27c85e25e3a4572ae58e4a4da4dea3f0767fbe1d36a7c8e8341','6e18140fce8ba5e466b6276be7264bf469e15fdb720bcdb7d880bdc574381151','2026-10-24 14:49:05'),(73001,'vishal.harith@gsfcuniversity.ac.in','$argon2id$v=19$m=65536,t=3,p=4$CKz+Vx8MpDPM5DCT5/0gUw$W3nPYQy43v+jlZLR4mifsgZB8oPEIl+xemtLnA3WoTU','Vishal Hairth','active',NULL,'2026-10-25 10:53:21','2026-10-25 10:05:57','2026-10-25 10:53:21',NULL,'Vishal Hairth',NULL,1,1,0,'5fab4f9c1f28a7acc4ebe2c2f0ae2cec0e48f1b50276bd4eba3e902ff5f474fd',NULL,NULL);
/*!40000 ALTER TABLE `accounts` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `alembic_version`
--

DROP TABLE IF EXISTS `alembic_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alembic_version`
--

LOCK TABLES `alembic_version` WRITE;
/*!40000 ALTER TABLE `alembic_version` DISABLE KEYS */;
INSERT INTO `alembic_version` VALUES ('20261022_01');
/*!40000 ALTER TABLE `alembic_version` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `assessment_assignments`
--

DROP TABLE IF EXISTS `assessment_assignments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `assessment_assignments` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `campaign_id` bigint unsigned NOT NULL,
  `faculty_id` bigint unsigned NOT NULL,
  `assigned_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `assignment_status` varchar(20) NOT NULL DEFAULT 'assigned',
  `selection_key` varchar(200) DEFAULT NULL,
  `score` decimal(5,2) DEFAULT NULL,
  `feedback_comments` text,
  `submitted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_campaign_faculty` (`campaign_id`,`faculty_id`),
  KEY `ix_assignment_faculty_status` (`faculty_id`,`assignment_status`),
  CONSTRAINT `fk_assignment_campaign` FOREIGN KEY (`campaign_id`) REFERENCES `assessment_campaigns` (`id`),
  CONSTRAINT `fk_assignment_faculty` FOREIGN KEY (`faculty_id`) REFERENCES `faculty` (`id`),
  CONSTRAINT `ck_assignment_score_range` CHECK (((`score` is null) or ((`score` >= 0) and (`score` <= 100)))),
  CONSTRAINT `ck_assignment_status` CHECK ((`assignment_status` in (_utf8mb4'assigned',_utf8mb4'started',_utf8mb4'submitted',_utf8mb4'excused',_utf8mb4'cancelled')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `assessment_assignments`
--

LOCK TABLES `assessment_assignments` WRITE;
/*!40000 ALTER TABLE `assessment_assignments` DISABLE KEYS */;
/*!40000 ALTER TABLE `assessment_assignments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `assessment_attempts`
--

DROP TABLE IF EXISTS `assessment_attempts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `assessment_attempts` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `assignment_id` bigint unsigned NOT NULL,
  `attempt_number` int unsigned NOT NULL DEFAULT '1',
  `started_at` datetime DEFAULT NULL,
  `submitted_at` datetime DEFAULT NULL,
  `attempt_status` varchar(20) NOT NULL DEFAULT 'not_started',
  `score` decimal(8,4) DEFAULT NULL,
  `max_score` decimal(8,4) DEFAULT NULL,
  `evaluated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_assessment_attempt_number` (`assignment_id`,`attempt_number`),
  KEY `ix_assessment_attempt_status` (`attempt_status`,`submitted_at`),
  CONSTRAINT `fk_assessment_attempt_assignment` FOREIGN KEY (`assignment_id`) REFERENCES `assessment_assignments` (`id`),
  CONSTRAINT `ck_assessment_attempt_score` CHECK ((((`score` is null) or (`score` >= 0)) and ((`max_score` is null) or (`max_score` >= 0)) and ((`score` is null) or (`max_score` is null) or (`score` <= `max_score`)))),
  CONSTRAINT `ck_assessment_attempt_status` CHECK ((`attempt_status` in (_utf8mb4'not_started',_utf8mb4'in_progress',_utf8mb4'submitted',_utf8mb4'evaluated',_utf8mb4'voided'))),
  CONSTRAINT `ck_assessment_attempt_times` CHECK (((`submitted_at` is null) or (`started_at` is null) or (`submitted_at` >= `started_at`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `assessment_attempts`
--

LOCK TABLES `assessment_attempts` WRITE;
/*!40000 ALTER TABLE `assessment_attempts` DISABLE KEYS */;
/*!40000 ALTER TABLE `assessment_attempts` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `assessment_campaigns`
--

DROP TABLE IF EXISTS `assessment_campaigns`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `assessment_campaigns` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `assessment_version_id` bigint unsigned NOT NULL,
  `name` varchar(200) NOT NULL,
  `starts_at` datetime DEFAULT NULL,
  `ends_at` datetime DEFAULT NULL,
  `selection_strategy` varchar(30) NOT NULL DEFAULT 'manual',
  `status` varchar(20) NOT NULL DEFAULT 'draft',
  `created_by_account_id` bigint unsigned NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_campaign_status_dates` (`status`,`starts_at`,`ends_at`),
  KEY `fk_campaign_version` (`assessment_version_id`),
  KEY `fk_campaign_creator` (`created_by_account_id`),
  CONSTRAINT `fk_campaign_creator` FOREIGN KEY (`created_by_account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_campaign_version` FOREIGN KEY (`assessment_version_id`) REFERENCES `assessment_versions` (`id`),
  CONSTRAINT `ck_campaign_dates` CHECK (((`starts_at` is null) or (`ends_at` is null) or (`ends_at` >= `starts_at`))),
  CONSTRAINT `ck_campaign_status` CHECK ((`status` in (_utf8mb4'draft',_utf8mb4'scheduled',_utf8mb4'active',_utf8mb4'completed',_utf8mb4'cancelled'))),
  CONSTRAINT `ck_campaign_strategy` CHECK ((`selection_strategy` in (_utf8mb4'manual',_utf8mb4'random',_utf8mb4'all_eligible')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `assessment_campaigns`
--

LOCK TABLES `assessment_campaigns` WRITE;
/*!40000 ALTER TABLE `assessment_campaigns` DISABLE KEYS */;
/*!40000 ALTER TABLE `assessment_campaigns` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `assessment_responses`
--

DROP TABLE IF EXISTS `assessment_responses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `assessment_responses` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `attempt_id` bigint unsigned NOT NULL,
  `question_key` varchar(150) NOT NULL,
  `response` json DEFAULT NULL,
  `score` decimal(8,4) DEFAULT NULL,
  `feedback` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_assessment_response_question` (`attempt_id`,`question_key`),
  CONSTRAINT `fk_assessment_response_attempt` FOREIGN KEY (`attempt_id`) REFERENCES `assessment_attempts` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `assessment_responses`
--

LOCK TABLES `assessment_responses` WRITE;
/*!40000 ALTER TABLE `assessment_responses` DISABLE KEYS */;
/*!40000 ALTER TABLE `assessment_responses` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `assessment_versions`
--

DROP TABLE IF EXISTS `assessment_versions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `assessment_versions` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `assessment_id` bigint unsigned NOT NULL,
  `version_number` int unsigned NOT NULL,
  `definition` json NOT NULL,
  `published_at` datetime DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_assessment_version` (`assessment_id`,`version_number`),
  CONSTRAINT `fk_assessment_version_assessment` FOREIGN KEY (`assessment_id`) REFERENCES `assessments` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `assessment_versions`
--

LOCK TABLES `assessment_versions` WRITE;
/*!40000 ALTER TABLE `assessment_versions` DISABLE KEYS */;
/*!40000 ALTER TABLE `assessment_versions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `assessments`
--

DROP TABLE IF EXISTS `assessments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `assessments` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `institution_id` bigint unsigned NOT NULL,
  `code` varchar(80) NOT NULL,
  `title` varchar(200) NOT NULL,
  `assessment_type` varchar(40) NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'draft',
  `created_by_account_id` bigint unsigned NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_assessment_institution_code` (`institution_id`,`code`),
  KEY `fk_assessment_creator` (`created_by_account_id`),
  CONSTRAINT `fk_assessment_creator` FOREIGN KEY (`created_by_account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_assessment_institution` FOREIGN KEY (`institution_id`) REFERENCES `institutions` (`id`),
  CONSTRAINT `ck_assessment_status` CHECK ((`status` in (_utf8mb4'draft',_utf8mb4'published',_utf8mb4'closed',_utf8mb4'archived'))),
  CONSTRAINT `ck_assessment_type` CHECK ((`assessment_type` in (_utf8mb4'faculty_test',_utf8mb4'student_test',_utf8mb4'other')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `assessments`
--

LOCK TABLES `assessments` WRITE;
/*!40000 ALTER TABLE `assessments` DISABLE KEYS */;
/*!40000 ALTER TABLE `assessments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `audit_events`
--

DROP TABLE IF EXISTS `audit_events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_events` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `actor_account_id` bigint unsigned DEFAULT NULL,
  `action` varchar(100) NOT NULL,
  `entity_type` varchar(100) NOT NULL,
  `entity_id` varchar(100) NOT NULL,
  `request_id` varchar(100) DEFAULT NULL,
  `occurred_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `details` json DEFAULT NULL,
  `institution_id` varchar(36) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_audit_entity_time` (`entity_type`,`entity_id`,`occurred_at`),
  KEY `ix_audit_actor_time` (`actor_account_id`,`occurred_at`),
  KEY `ix_audit_request` (`request_id`),
  CONSTRAINT `fk_audit_actor` FOREIGN KEY (`actor_account_id`) REFERENCES `accounts` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `audit_events`
--

LOCK TABLES `audit_events` WRITE;
/*!40000 ALTER TABLE `audit_events` DISABLE KEYS */;
INSERT INTO `audit_events` VALUES (10,2,'storage.file_uploaded','storage_file','b19b35f4-991c-46e2-9c3a-5df4b85846c8',NULL,'2026-10-24 17:42:55','{\"mime_type\": \"application/pdf\", \"file_size_bytes\": 148490}',NULL);
/*!40000 ALTER TABLE `audit_events` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `audit_events_v2`
--

DROP TABLE IF EXISTS `audit_events_v2`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_events_v2` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `institution_id` bigint unsigned DEFAULT NULL,
  `actor_account_id` bigint unsigned DEFAULT NULL,
  `action_code` varchar(120) NOT NULL,
  `entity_type` varchar(100) NOT NULL,
  `entity_id` varchar(100) NOT NULL,
  `correlation_id` varchar(150) DEFAULT NULL,
  `before_snapshot` json DEFAULT NULL,
  `after_snapshot` json DEFAULT NULL,
  `ip_address` varbinary(16) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_audit_institution_time` (`institution_id`,`created_at`),
  KEY `ix_audit_entity` (`entity_type`,`entity_id`,`created_at`),
  KEY `ix_audit_actor_time` (`actor_account_id`,`created_at`),
  CONSTRAINT `fk_audit_v2_actor` FOREIGN KEY (`actor_account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_audit_v2_institution` FOREIGN KEY (`institution_id`) REFERENCES `institutions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `audit_events_v2`
--

LOCK TABLES `audit_events_v2` WRITE;
/*!40000 ALTER TABLE `audit_events_v2` DISABLE KEYS */;
/*!40000 ALTER TABLE `audit_events_v2` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_sessions`
--

DROP TABLE IF EXISTS `auth_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_sessions` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `account_id` bigint unsigned NOT NULL,
  `token_hash` varbinary(64) NOT NULL,
  `expires_at` datetime NOT NULL,
  `revoked_at` datetime DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `ip_address` varbinary(16) DEFAULT NULL,
  `user_agent` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_auth_session_token_hash` (`token_hash`),
  KEY `ix_auth_sessions_account_expiry` (`account_id`,`expires_at`,`revoked_at`),
  CONSTRAINT `fk_auth_sessions_account` FOREIGN KEY (`account_id`) REFERENCES `accounts` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_sessions`
--

LOCK TABLES `auth_sessions` WRITE;
/*!40000 ALTER TABLE `auth_sessions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_sessions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `blind_test_assignments`
--

DROP TABLE IF EXISTS `blind_test_assignments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `blind_test_assignments` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `campaign_id` bigint unsigned NOT NULL,
  `report_version_id` bigint unsigned NOT NULL,
  `blind_reviewer_account_id` bigint unsigned DEFAULT NULL,
  `anonymized_case_code` varchar(100) NOT NULL,
  `assignment_status` varchar(25) NOT NULL DEFAULT 'queued',
  `selected_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `started_at` datetime DEFAULT NULL,
  `completed_at` datetime DEFAULT NULL,
  `reviewer_score` decimal(8,4) DEFAULT NULL,
  `reviewer_decision` varchar(30) DEFAULT NULL,
  `reviewer_notes` text,
  `conflict_checked_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_blind_campaign_report_version` (`campaign_id`,`report_version_id`),
  UNIQUE KEY `uq_blind_case_code` (`anonymized_case_code`),
  KEY `ix_blind_reviewer_queue` (`blind_reviewer_account_id`,`assignment_status`,`selected_at`),
  KEY `ix_blind_assignment_status` (`campaign_id`,`assignment_status`),
  KEY `fk_blind_assignment_version` (`report_version_id`),
  CONSTRAINT `fk_blind_assignment_campaign` FOREIGN KEY (`campaign_id`) REFERENCES `blind_test_campaigns` (`id`),
  CONSTRAINT `fk_blind_assignment_reviewer` FOREIGN KEY (`blind_reviewer_account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_blind_assignment_version` FOREIGN KEY (`report_version_id`) REFERENCES `report_versions` (`id`),
  CONSTRAINT `ck_blind_assignment_decision` CHECK (((`reviewer_decision` is null) or (`reviewer_decision` in (_utf8mb4'pass',_utf8mb4'fail',_utf8mb4'needs_review')))),
  CONSTRAINT `ck_blind_assignment_status` CHECK ((`assignment_status` in (_utf8mb4'queued',_utf8mb4'assigned',_utf8mb4'in_progress',_utf8mb4'completed',_utf8mb4'conflict',_utf8mb4'cancelled'))),
  CONSTRAINT `ck_blind_assignment_times` CHECK (((`completed_at` is null) or (`started_at` is null) or (`completed_at` >= `started_at`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `blind_test_assignments`
--

LOCK TABLES `blind_test_assignments` WRITE;
/*!40000 ALTER TABLE `blind_test_assignments` DISABLE KEYS */;
/*!40000 ALTER TABLE `blind_test_assignments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `blind_test_campaigns`
--

DROP TABLE IF EXISTS `blind_test_campaigns`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `blind_test_campaigns` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `institution_id` bigint unsigned DEFAULT NULL,
  `name` varchar(200) NOT NULL,
  `sampling_method` varchar(30) NOT NULL DEFAULT 'random',
  `sample_percentage` decimal(5,2) DEFAULT NULL,
  `sample_size` int unsigned DEFAULT NULL,
  `seed_reference` varchar(200) DEFAULT NULL,
  `starts_at` datetime NOT NULL,
  `ends_at` datetime DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'draft',
  `created_by_account_id` bigint unsigned NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_blind_campaign_scope_status` (`institution_id`,`status`,`starts_at`),
  KEY `fk_blind_campaign_creator` (`created_by_account_id`),
  CONSTRAINT `fk_blind_campaign_creator` FOREIGN KEY (`created_by_account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_blind_campaign_institution` FOREIGN KEY (`institution_id`) REFERENCES `institutions` (`id`),
  CONSTRAINT `ck_blind_campaign_dates` CHECK (((`ends_at` is null) or (`ends_at` >= `starts_at`))),
  CONSTRAINT `ck_blind_campaign_method` CHECK ((`sampling_method` in (_utf8mb4'random',_utf8mb4'percentage',_utf8mb4'stratified_random'))),
  CONSTRAINT `ck_blind_campaign_percentage` CHECK (((`sample_percentage` is null) or ((`sample_percentage` > 0) and (`sample_percentage` <= 100)))),
  CONSTRAINT `ck_blind_campaign_status` CHECK ((`status` in (_utf8mb4'draft',_utf8mb4'scheduled',_utf8mb4'running',_utf8mb4'completed',_utf8mb4'cancelled')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `blind_test_campaigns`
--

LOCK TABLES `blind_test_campaigns` WRITE;
/*!40000 ALTER TABLE `blind_test_campaigns` DISABLE KEYS */;
/*!40000 ALTER TABLE `blind_test_campaigns` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cohorts`
--

DROP TABLE IF EXISTS `cohorts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cohorts` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `programme_id` bigint unsigned NOT NULL,
  `label` varchar(100) NOT NULL,
  `entry_year` smallint unsigned DEFAULT NULL,
  `expected_graduation_year` smallint unsigned DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'active',
  `name` varchar(100) DEFAULT NULL,
  `graduation_year` smallint unsigned DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `academic_year_id` bigint unsigned DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_cohort_programme_label` (`programme_id`,`label`),
  CONSTRAINT `fk_cohort_programme` FOREIGN KEY (`programme_id`) REFERENCES `programmes` (`id`),
  CONSTRAINT `ck_cohort_status` CHECK ((`status` in (_utf8mb4'active',_utf8mb4'completed',_utf8mb4'inactive')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cohorts`
--

LOCK TABLES `cohorts` WRITE;
/*!40000 ALTER TABLE `cohorts` DISABLE KEYS */;
/*!40000 ALTER TABLE `cohorts` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `departments`
--

DROP TABLE IF EXISTS `departments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `departments` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `school_id` bigint unsigned NOT NULL,
  `name` varchar(200) NOT NULL,
  `code` varchar(50) DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_active` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_departments_school_name` (`school_id`,`name`),
  UNIQUE KEY `uq_departments_school_code` (`school_id`,`code`),
  CONSTRAINT `fk_departments_school` FOREIGN KEY (`school_id`) REFERENCES `schools` (`id`),
  CONSTRAINT `ck_departments_status` CHECK ((`status` in (_utf8mb4'active',_utf8mb4'inactive')))
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `departments`
--

LOCK TABLES `departments` WRITE;
/*!40000 ALTER TABLE `departments` DISABLE KEYS */;
INSERT INTO `departments` VALUES (1,1,'Academic Programmes','SoCIS-GEN','active','2026-10-24 12:07:48','2026-10-24 12:07:48',1),(2,4,'Academic Programmes','SoCFS-GEN','active','2026-10-24 12:07:48','2026-10-24 12:07:48',1),(3,3,'Academic Programmes','SoCIT-GEN','active','2026-10-24 12:07:48','2026-10-24 12:07:48',1),(4,2,'Academic Programmes','SoLS-GEN','active','2026-10-24 12:07:48','2026-10-24 12:07:48',1),(5,5,'Academic Programmes','SoME-GEN','active','2026-10-24 12:07:48','2026-10-24 12:07:48',1);
/*!40000 ALTER TABLE `departments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `employer_invitations`
--

DROP TABLE IF EXISTS `employer_invitations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `employer_invitations` (
  `id` varchar(36) NOT NULL,
  `organization_id` varchar(36) NOT NULL,
  `email` varchar(255) NOT NULL,
  `role` varchar(20) NOT NULL,
  `token_hash` varchar(64) NOT NULL,
  `expires_at` timestamp NOT NULL,
  `invited_by_account_id` varchar(36) NOT NULL,
  `accepted_at` timestamp NULL DEFAULT NULL,
  `revoked_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_employer_invitations_token_hash` (`token_hash`),
  KEY `ix_employer_invitations_organization_id` (`organization_id`),
  KEY `ix_employer_invitations_email` (`email`),
  CONSTRAINT `fk_employer_invitation_organization` FOREIGN KEY (`organization_id`) REFERENCES `employer_organizations` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `employer_invitations`
--

LOCK TABLES `employer_invitations` WRITE;
/*!40000 ALTER TABLE `employer_invitations` DISABLE KEYS */;
/*!40000 ALTER TABLE `employer_invitations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `employer_memberships`
--

DROP TABLE IF EXISTS `employer_memberships`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `employer_memberships` (
  `id` varchar(36) NOT NULL,
  `organization_id` varchar(36) NOT NULL,
  `account_id` varchar(36) NOT NULL,
  `role` varchar(20) NOT NULL DEFAULT 'VIEWER',
  `status` varchar(20) NOT NULL DEFAULT 'ACTIVE',
  `invited_by_account_id` varchar(36) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_employer_membership_account` (`organization_id`,`account_id`),
  KEY `ix_employer_memberships_organization_id` (`organization_id`),
  KEY `ix_employer_memberships_account_id` (`account_id`),
  CONSTRAINT `fk_employer_membership_organization` FOREIGN KEY (`organization_id`) REFERENCES `employer_organizations` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `employer_memberships`
--

LOCK TABLES `employer_memberships` WRITE;
/*!40000 ALTER TABLE `employer_memberships` DISABLE KEYS */;
/*!40000 ALTER TABLE `employer_memberships` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `employer_organizations`
--

DROP TABLE IF EXISTS `employer_organizations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `employer_organizations` (
  `id` varchar(36) NOT NULL,
  `legal_name` varchar(255) NOT NULL,
  `display_name` varchar(255) NOT NULL,
  `normalized_name` varchar(255) NOT NULL,
  `organization_type` varchar(40) NOT NULL DEFAULT 'COMPANY',
  `industry` varchar(120) DEFAULT NULL,
  `description` text,
  `website_url` varchar(2048) DEFAULT NULL,
  `business_email` varchar(255) DEFAULT NULL,
  `phone` varchar(40) DEFAULT NULL,
  `country` varchar(100) DEFAULT NULL,
  `state` varchar(100) DEFAULT NULL,
  `city` varchar(100) DEFAULT NULL,
  `postal_code` varchar(30) DEFAULT NULL,
  `headquarters_address` varchar(500) DEFAULT NULL,
  `company_size` varchar(30) DEFAULT NULL,
  `founded_year` int DEFAULT NULL,
  `registration_identifier` varchar(120) DEFAULT NULL,
  `careers_url` varchar(2048) DEFAULT NULL,
  `logo_storage_key` varchar(500) DEFAULT NULL,
  `cover_storage_key` varchar(500) DEFAULT NULL,
  `status` varchar(30) NOT NULL DEFAULT 'PENDING_VERIFICATION',
  `created_by_account_id` varchar(36) NOT NULL,
  `reviewed_by_account_id` varchar(36) DEFAULT NULL,
  `reviewed_at` timestamp NULL DEFAULT NULL,
  `review_notes` text,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_employer_org_normalized_name` (`normalized_name`),
  UNIQUE KEY `uq_employer_org_registration_identifier` (`registration_identifier`),
  KEY `ix_employer_organizations_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `employer_organizations`
--

LOCK TABLES `employer_organizations` WRITE;
/*!40000 ALTER TABLE `employer_organizations` DISABLE KEYS */;
/*!40000 ALTER TABLE `employer_organizations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `evaluation_attempts`
--

DROP TABLE IF EXISTS `evaluation_attempts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `evaluation_attempts` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `evaluation_request_id` bigint unsigned NOT NULL,
  `attempt_number` int unsigned NOT NULL,
  `attempt_status` varchar(30) NOT NULL DEFAULT 'created',
  `idempotency_key` varchar(200) NOT NULL,
  `request_correlation_id` varchar(200) DEFAULT NULL,
  `started_at` datetime DEFAULT NULL,
  `finished_at` datetime DEFAULT NULL,
  `error_code` varchar(100) DEFAULT NULL,
  `error_message` text,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_eval_attempt_number` (`evaluation_request_id`,`attempt_number`),
  UNIQUE KEY `uq_eval_attempt_idempotency` (`idempotency_key`),
  KEY `ix_eval_attempt_status_created` (`attempt_status`,`created_at`),
  CONSTRAINT `fk_eval_attempt_request` FOREIGN KEY (`evaluation_request_id`) REFERENCES `evaluation_requests` (`id`),
  CONSTRAINT `ck_eval_attempt_status` CHECK ((`attempt_status` in (_utf8mb4'created',_utf8mb4'dispatched',_utf8mb4'running',_utf8mb4'succeeded',_utf8mb4'failed',_utf8mb4'timed_out',_utf8mb4'cancelled'))),
  CONSTRAINT `ck_eval_attempt_times` CHECK (((`finished_at` is null) or (`started_at` is null) or (`finished_at` >= `started_at`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `evaluation_attempts`
--

LOCK TABLES `evaluation_attempts` WRITE;
/*!40000 ALTER TABLE `evaluation_attempts` DISABLE KEYS */;
/*!40000 ALTER TABLE `evaluation_attempts` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `evaluation_outcomes`
--

DROP TABLE IF EXISTS `evaluation_outcomes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `evaluation_outcomes` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `submission_id` bigint unsigned NOT NULL,
  `report_version_id` bigint unsigned NOT NULL,
  `outcome_code` varchar(40) NOT NULL,
  `decided_by_account_id` bigint unsigned DEFAULT NULL,
  `decided_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `rationale` text,
  `supersedes_outcome_id` bigint unsigned DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_outcome_submission_time` (`submission_id`,`decided_at`),
  KEY `ix_outcome_version_time` (`report_version_id`,`decided_at`),
  KEY `fk_outcome_decider` (`decided_by_account_id`),
  KEY `fk_outcome_supersedes` (`supersedes_outcome_id`),
  CONSTRAINT `fk_outcome_decider` FOREIGN KEY (`decided_by_account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_outcome_submission` FOREIGN KEY (`submission_id`) REFERENCES `report_submissions` (`id`),
  CONSTRAINT `fk_outcome_supersedes` FOREIGN KEY (`supersedes_outcome_id`) REFERENCES `evaluation_outcomes` (`id`),
  CONSTRAINT `fk_outcome_version` FOREIGN KEY (`report_version_id`) REFERENCES `report_versions` (`id`),
  CONSTRAINT `ck_outcome_code` CHECK ((`outcome_code` in (_utf8mb4'accepted',_utf8mb4'rejected',_utf8mb4'changes_requested',_utf8mb4'incomplete',_utf8mb4'withdrawn')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `evaluation_outcomes`
--

LOCK TABLES `evaluation_outcomes` WRITE;
/*!40000 ALTER TABLE `evaluation_outcomes` DISABLE KEYS */;
/*!40000 ALTER TABLE `evaluation_outcomes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `evaluation_requests`
--

DROP TABLE IF EXISTS `evaluation_requests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `evaluation_requests` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `submission_id` bigint unsigned NOT NULL,
  `report_version_id` bigint unsigned NOT NULL,
  `stage_id` bigint unsigned NOT NULL,
  `workflow_status` varchar(30) NOT NULL DEFAULT 'pending',
  `created_by_account_id` bigint unsigned DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `completed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_eval_request_version_stage` (`report_version_id`,`stage_id`),
  KEY `ix_eval_request_pending` (`stage_id`,`workflow_status`,`created_at`),
  KEY `ix_eval_request_submission` (`submission_id`,`created_at`),
  KEY `fk_eval_request_creator` (`created_by_account_id`),
  CONSTRAINT `fk_eval_request_creator` FOREIGN KEY (`created_by_account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_eval_request_stage` FOREIGN KEY (`stage_id`) REFERENCES `evaluation_stages` (`id`),
  CONSTRAINT `fk_eval_request_submission` FOREIGN KEY (`submission_id`) REFERENCES `report_submissions` (`id`),
  CONSTRAINT `fk_eval_request_version` FOREIGN KEY (`report_version_id`) REFERENCES `report_versions` (`id`),
  CONSTRAINT `ck_eval_request_status` CHECK ((`workflow_status` in (_utf8mb4'pending',_utf8mb4'queued',_utf8mb4'in_progress',_utf8mb4'completed',_utf8mb4'failed',_utf8mb4'cancelled',_utf8mb4'skipped')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `evaluation_requests`
--

LOCK TABLES `evaluation_requests` WRITE;
/*!40000 ALTER TABLE `evaluation_requests` DISABLE KEYS */;
/*!40000 ALTER TABLE `evaluation_requests` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `evaluation_results`
--

DROP TABLE IF EXISTS `evaluation_results`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `evaluation_results` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `evaluation_attempt_id` bigint unsigned NOT NULL,
  `result_status` varchar(30) NOT NULL,
  `score` decimal(8,4) DEFAULT NULL,
  `score_type` varchar(80) DEFAULT NULL,
  `structured_result` json DEFAULT NULL,
  `raw_result` json DEFAULT NULL,
  `result_sha256` char(64) DEFAULT NULL,
  `received_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `reviewed_by_account_id` bigint unsigned DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  `review_decision` varchar(30) DEFAULT NULL,
  `review_notes` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_evaluation_result_attempt` (`evaluation_attempt_id`),
  KEY `ix_evaluation_result_status_received` (`result_status`,`received_at`),
  KEY `fk_evaluation_result_reviewer` (`reviewed_by_account_id`),
  CONSTRAINT `fk_evaluation_result_attempt` FOREIGN KEY (`evaluation_attempt_id`) REFERENCES `evaluation_attempts` (`id`),
  CONSTRAINT `fk_evaluation_result_reviewer` FOREIGN KEY (`reviewed_by_account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `ck_evaluation_result_score` CHECK (((`score` is null) or (`score` >= 0))),
  CONSTRAINT `ck_evaluation_result_status` CHECK ((`result_status` in (_utf8mb4'available',_utf8mb4'invalid',_utf8mb4'superseded')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `evaluation_results`
--

LOCK TABLES `evaluation_results` WRITE;
/*!40000 ALTER TABLE `evaluation_results` DISABLE KEYS */;
/*!40000 ALTER TABLE `evaluation_results` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `evaluation_stages`
--

DROP TABLE IF EXISTS `evaluation_stages`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `evaluation_stages` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `code` varchar(60) NOT NULL,
  `name` varchar(150) NOT NULL,
  `sequence_no` smallint unsigned NOT NULL,
  `evaluator_type` varchar(30) NOT NULL,
  `is_required` tinyint(1) NOT NULL DEFAULT '1',
  `active` tinyint(1) NOT NULL DEFAULT '1',
  `configuration` json DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_evaluation_stage_code` (`code`),
  UNIQUE KEY `uq_evaluation_stage_sequence` (`sequence_no`),
  CONSTRAINT `ck_evaluation_stage_type` CHECK ((`evaluator_type` in (_utf8mb4'external_system',_utf8mb4'faculty',_utf8mb4'internal_service',_utf8mb4'committee')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `evaluation_stages`
--

LOCK TABLES `evaluation_stages` WRITE;
/*!40000 ALTER TABLE `evaluation_stages` DISABLE KEYS */;
/*!40000 ALTER TABLE `evaluation_stages` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `faculty`
--

DROP TABLE IF EXISTS `faculty`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `faculty` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `account_id` bigint unsigned NOT NULL,
  `employee_number` varchar(80) DEFAULT NULL,
  `display_name` varchar(200) NOT NULL,
  `employment_status` varchar(20) NOT NULL DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `employee_code` varchar(80) DEFAULT NULL,
  `department_id` bigint unsigned DEFAULT NULL,
  `designation` varchar(150) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_faculty_account` (`account_id`),
  UNIQUE KEY `uq_faculty_employee_number` (`employee_number`),
  CONSTRAINT `fk_faculty_account` FOREIGN KEY (`account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `ck_faculty_status` CHECK ((`employment_status` in (_utf8mb4'active',_utf8mb4'inactive',_utf8mb4'ended')))
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `faculty`
--

LOCK TABLES `faculty` WRITE;
/*!40000 ALTER TABLE `faculty` DISABLE KEYS */;
INSERT INTO `faculty` VALUES (11,73001,'EMP-01','Vishal Hairth','active','2026-10-25 10:05:58','EMP-01',3,'23sc06007@gsfcuniversity.ac.in');
/*!40000 ALTER TABLE `faculty` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `faculty_affiliations`
--

DROP TABLE IF EXISTS `faculty_affiliations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `faculty_affiliations` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `faculty_id` bigint unsigned NOT NULL,
  `department_id` bigint unsigned NOT NULL,
  `starts_on` date NOT NULL,
  `ends_on` date DEFAULT NULL,
  `is_primary` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `ix_faculty_affiliation_dates` (`faculty_id`,`starts_on`,`ends_on`),
  KEY `ix_faculty_affiliation_department` (`department_id`,`starts_on`,`ends_on`),
  CONSTRAINT `fk_affiliation_department` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`),
  CONSTRAINT `fk_affiliation_faculty` FOREIGN KEY (`faculty_id`) REFERENCES `faculty` (`id`),
  CONSTRAINT `ck_affiliation_dates` CHECK (((`ends_on` is null) or (`ends_on` >= `starts_on`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `faculty_affiliations`
--

LOCK TABLES `faculty_affiliations` WRITE;
/*!40000 ALTER TABLE `faculty_affiliations` DISABLE KEYS */;
/*!40000 ALTER TABLE `faculty_affiliations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `faculty_mentorships`
--

DROP TABLE IF EXISTS `faculty_mentorships`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `faculty_mentorships` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `institution_id` bigint unsigned NOT NULL,
  `faculty_id` bigint unsigned NOT NULL,
  `student_id` bigint unsigned NOT NULL,
  `academic_year_id` bigint unsigned DEFAULT NULL,
  `starts_on` date NOT NULL,
  `ends_on` date DEFAULT NULL,
  `is_primary` tinyint(1) NOT NULL DEFAULT '1',
  `status` varchar(20) NOT NULL DEFAULT 'active',
  `assigned_by_account_id` bigint unsigned DEFAULT NULL,
  `notes` text,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_mentorship_faculty_status` (`institution_id`,`faculty_id`,`status`,`starts_on`),
  KEY `ix_mentorship_student_status` (`institution_id`,`student_id`,`status`,`starts_on`),
  KEY `fk_mentorship_faculty` (`faculty_id`),
  KEY `fk_mentorship_student` (`student_id`),
  KEY `fk_mentorship_year` (`academic_year_id`),
  KEY `fk_mentorship_assigner` (`assigned_by_account_id`),
  CONSTRAINT `fk_mentorship_assigner` FOREIGN KEY (`assigned_by_account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_mentorship_faculty` FOREIGN KEY (`faculty_id`) REFERENCES `faculty` (`id`),
  CONSTRAINT `fk_mentorship_institution` FOREIGN KEY (`institution_id`) REFERENCES `institutions` (`id`),
  CONSTRAINT `fk_mentorship_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`),
  CONSTRAINT `fk_mentorship_year` FOREIGN KEY (`academic_year_id`) REFERENCES `academic_years` (`id`),
  CONSTRAINT `ck_mentorship_dates` CHECK (((`ends_on` is null) or (`ends_on` >= `starts_on`))),
  CONSTRAINT `ck_mentorship_status` CHECK ((`status` in (_utf8mb4'active',_utf8mb4'ended',_utf8mb4'revoked')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `faculty_mentorships`
--

LOCK TABLES `faculty_mentorships` WRITE;
/*!40000 ALTER TABLE `faculty_mentorships` DISABLE KEYS */;
/*!40000 ALTER TABLE `faculty_mentorships` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `griffin_integrations`
--

DROP TABLE IF EXISTS `griffin_integrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `griffin_integrations` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `evaluation_attempt_id` bigint unsigned NOT NULL,
  `provider_code` varchar(50) NOT NULL DEFAULT 'griffin',
  `external_project_id` varchar(191) DEFAULT NULL,
  `external_report_id` varchar(191) DEFAULT NULL,
  `external_job_id` varchar(191) DEFAULT NULL,
  `external_result_id` varchar(191) DEFAULT NULL,
  `external_project_status` varchar(40) DEFAULT NULL,
  `external_report_status` varchar(40) DEFAULT NULL,
  `external_job_status` varchar(40) DEFAULT NULL,
  `last_sync_at` datetime DEFAULT NULL,
  `result_snapshot` json DEFAULT NULL,
  `result_snapshot_sha256` char(64) DEFAULT NULL,
  `external_metadata` json DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_griffin_attempt` (`evaluation_attempt_id`),
  UNIQUE KEY `uq_griffin_external_job` (`provider_code`,`external_job_id`),
  KEY `ix_griffin_job_status_sync` (`external_job_status`,`last_sync_at`),
  KEY `ix_griffin_report` (`provider_code`,`external_report_id`),
  KEY `ix_griffin_project` (`provider_code`,`external_project_id`),
  CONSTRAINT `fk_griffin_attempt` FOREIGN KEY (`evaluation_attempt_id`) REFERENCES `evaluation_attempts` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `griffin_integrations`
--

LOCK TABLES `griffin_integrations` WRITE;
/*!40000 ALTER TABLE `griffin_integrations` DISABLE KEYS */;
/*!40000 ALTER TABLE `griffin_integrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `industry_mentor_assignments`
--

DROP TABLE IF EXISTS `industry_mentor_assignments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `industry_mentor_assignments` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `participation_id` bigint unsigned NOT NULL,
  `industry_mentor_id` bigint unsigned NOT NULL,
  `assigned_by_account_id` bigint unsigned DEFAULT NULL,
  `starts_on` date NOT NULL,
  `ends_on` date DEFAULT NULL,
  `is_primary` tinyint(1) NOT NULL DEFAULT '1',
  `status` varchar(20) NOT NULL DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_industry_assignment_participation` (`participation_id`,`status`,`starts_on`),
  KEY `ix_industry_assignment_mentor` (`industry_mentor_id`,`status`,`starts_on`),
  KEY `fk_industry_assignment_assigner` (`assigned_by_account_id`),
  CONSTRAINT `fk_industry_assignment_assigner` FOREIGN KEY (`assigned_by_account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_industry_assignment_mentor` FOREIGN KEY (`industry_mentor_id`) REFERENCES `industry_mentors` (`id`),
  CONSTRAINT `fk_industry_assignment_participation` FOREIGN KEY (`participation_id`) REFERENCES `internship_participations` (`id`),
  CONSTRAINT `ck_industry_assignment_dates` CHECK (((`ends_on` is null) or (`ends_on` >= `starts_on`))),
  CONSTRAINT `ck_industry_assignment_status` CHECK ((`status` in (_utf8mb4'active',_utf8mb4'ended',_utf8mb4'revoked')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `industry_mentor_assignments`
--

LOCK TABLES `industry_mentor_assignments` WRITE;
/*!40000 ALTER TABLE `industry_mentor_assignments` DISABLE KEYS */;
/*!40000 ALTER TABLE `industry_mentor_assignments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `industry_mentors`
--

DROP TABLE IF EXISTS `industry_mentors`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `industry_mentors` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `account_id` bigint unsigned DEFAULT NULL,
  `provider_id` bigint unsigned NOT NULL,
  `full_name` varchar(200) NOT NULL,
  `email` varchar(254) DEFAULT NULL,
  `job_title` varchar(150) DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_industry_mentor_provider_status` (`provider_id`,`status`),
  KEY `ix_industry_mentor_account` (`account_id`),
  CONSTRAINT `fk_industry_mentor_account` FOREIGN KEY (`account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_industry_mentor_provider` FOREIGN KEY (`provider_id`) REFERENCES `internship_providers` (`id`),
  CONSTRAINT `ck_industry_mentor_status` CHECK ((`status` in (_utf8mb4'active',_utf8mb4'inactive')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `industry_mentors`
--

LOCK TABLES `industry_mentors` WRITE;
/*!40000 ALTER TABLE `industry_mentors` DISABLE KEYS */;
/*!40000 ALTER TABLE `industry_mentors` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `institution_domains`
--

DROP TABLE IF EXISTS `institution_domains`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `institution_domains` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `institution_id` bigint unsigned NOT NULL,
  `normalized_domain` varchar(253) NOT NULL,
  `is_verified` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_institution_domains_domain` (`normalized_domain`),
  KEY `ix_institution_domains_institution_id` (`institution_id`),
  CONSTRAINT `fk_institution_domains_institution` FOREIGN KEY (`institution_id`) REFERENCES `institutions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `institution_domains`
--

LOCK TABLES `institution_domains` WRITE;
/*!40000 ALTER TABLE `institution_domains` DISABLE KEYS */;
INSERT INTO `institution_domains` VALUES (1,11,'gsfcuniversity.ac.in',1,'2026-10-24 09:46:06');
/*!40000 ALTER TABLE `institution_domains` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `institution_memberships`
--

DROP TABLE IF EXISTS `institution_memberships`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `institution_memberships` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `institution_id` bigint unsigned NOT NULL,
  `account_id` bigint unsigned NOT NULL,
  `membership_type` varchar(30) NOT NULL,
  `membership_status` varchar(20) NOT NULL DEFAULT 'active',
  `joined_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `ended_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_membership_institution_account` (`institution_id`,`account_id`),
  KEY `ix_membership_account_status` (`account_id`,`membership_status`),
  KEY `ix_membership_institution_type` (`institution_id`,`membership_type`,`membership_status`),
  CONSTRAINT `fk_membership_account` FOREIGN KEY (`account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_membership_institution` FOREIGN KEY (`institution_id`) REFERENCES `institutions` (`id`),
  CONSTRAINT `ck_membership_dates` CHECK (((`ended_at` is null) or (`ended_at` >= `joined_at`))),
  CONSTRAINT `ck_membership_status` CHECK ((`membership_status` in (_utf8mb4'invited',_utf8mb4'active',_utf8mb4'suspended',_utf8mb4'ended'))),
  CONSTRAINT `ck_membership_type` CHECK ((`membership_type` in (_utf8mb4'institution_admin',_utf8mb4'faculty',_utf8mb4'student',_utf8mb4'industry_mentor',_utf8mb4'coordinator',_utf8mb4'reviewer')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `institution_memberships`
--

LOCK TABLES `institution_memberships` WRITE;
/*!40000 ALTER TABLE `institution_memberships` DISABLE KEYS */;
/*!40000 ALTER TABLE `institution_memberships` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `institutions`
--

DROP TABLE IF EXISTS `institutions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `institutions` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `code` varchar(50) DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `slug` varchar(200) DEFAULT NULL,
  `contact_email` varchar(255) DEFAULT NULL,
  `institution_type` varchar(100) DEFAULT NULL,
  `registration_number` varchar(100) DEFAULT NULL,
  `description` text,
  `address` text,
  `country` varchar(100) DEFAULT NULL,
  `state` varchar(100) DEFAULT NULL,
  `city` varchar(100) DEFAULT NULL,
  `postal_code` varchar(20) DEFAULT NULL,
  `logo_storage_key` varchar(500) DEFAULT NULL,
  `website_url` varchar(500) DEFAULT NULL,
  `created_by_account_id` bigint unsigned DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_institutions_code` (`code`),
  CONSTRAINT `ck_institutions_status` CHECK ((`status` in (_utf8mb4'active',_utf8mb4'inactive')))
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `institutions`
--

LOCK TABLES `institutions` WRITE;
/*!40000 ALTER TABLE `institutions` DISABLE KEYS */;
INSERT INTO `institutions` VALUES (1,'Ahmedabad University','GUJ-AHMEDABAD-UNIV','active','2026-10-24 09:40:11','2026-10-24 09:40:11',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(2,'Gujarat University','GUJ-GUJARAT-UNIV','active','2026-10-24 09:40:11','2026-10-24 09:40:11',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(3,'The Maharaja Sayajirao University of Baroda','GUJ-MSU-BARODA','active','2026-10-24 09:40:11','2026-10-24 09:40:11',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(4,'Sardar Patel University','GUJ-SPU','active','2026-10-24 09:40:11','2026-10-24 09:40:11',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(5,'Saurashtra University','GUJ-SAU','active','2026-10-24 09:40:11','2026-10-24 09:40:11',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(6,'Veer Narmad South Gujarat University','GUJ-VNSGU','active','2026-10-24 09:40:11','2026-10-24 09:40:11',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(7,'Gujarat Technological University','GUJ-GTU','active','2026-10-24 09:40:11','2026-10-24 09:40:11',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(8,'Central University of Gujarat','GUJ-CUG','active','2026-10-24 09:40:11','2026-10-24 09:40:11',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(9,'Pandit Deendayal Energy University','GUJ-PDEU','active','2026-10-24 09:40:11','2026-10-24 09:40:11',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(10,'Nirma University','GUJ-NIRMA','active','2026-10-24 09:40:11','2026-10-24 09:40:11',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(11,'GSFC University','GUJ-GSFC-UNIV','active','2026-10-24 09:49:11','2026-10-24 09:49:11',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(12,'GSFC University','GSFCU','active','2026-10-24 12:07:48','2026-10-24 12:07:48','gsfc-university',NULL,'University',NULL,NULL,NULL,'India','Gujarat','Vadodara',NULL,NULL,NULL,NULL);
/*!40000 ALTER TABLE `institutions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `internship_applications`
--

DROP TABLE IF EXISTS `internship_applications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `internship_applications` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `opportunity_id` bigint unsigned NOT NULL,
  `student_id` bigint unsigned NOT NULL,
  `applied_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `status` varchar(25) NOT NULL DEFAULT 'submitted',
  `cover_letter` text,
  `reviewed_by_account_id` bigint unsigned DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  `review_notes` text,
  `recruitment_stage` varchar(20) NOT NULL DEFAULT 'SUBMITTED',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_application_student_opportunity` (`student_id`,`opportunity_id`),
  KEY `ix_applications_opportunity_status` (`opportunity_id`,`status`,`applied_at`),
  KEY `ix_applications_student_status` (`student_id`,`status`,`applied_at`),
  KEY `fk_application_reviewer` (`reviewed_by_account_id`),
  KEY `ix_internship_applications_recruitment_stage` (`recruitment_stage`),
  CONSTRAINT `fk_application_opportunity` FOREIGN KEY (`opportunity_id`) REFERENCES `internship_opportunities` (`id`),
  CONSTRAINT `fk_application_reviewer` FOREIGN KEY (`reviewed_by_account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_application_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`),
  CONSTRAINT `ck_application_status` CHECK ((`status` in (_utf8mb4'submitted',_utf8mb4'under_review',_utf8mb4'shortlisted',_utf8mb4'accepted',_utf8mb4'rejected',_utf8mb4'withdrawn')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `internship_applications`
--

LOCK TABLES `internship_applications` WRITE;
/*!40000 ALTER TABLE `internship_applications` DISABLE KEYS */;
/*!40000 ALTER TABLE `internship_applications` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `internship_daily_logs`
--

DROP TABLE IF EXISTS `internship_daily_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `internship_daily_logs` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `participation_id` bigint unsigned NOT NULL,
  `student_id` bigint unsigned NOT NULL,
  `log_date` date NOT NULL,
  `work_summary` text NOT NULL,
  `tasks_completed` text,
  `hours_worked` decimal(5,2) DEFAULT NULL,
  `skills_used` json DEFAULT NULL,
  `blockers` text,
  `learning_outcomes` text,
  `next_day_plan` text,
  `status` varchar(20) NOT NULL DEFAULT 'draft',
  `submitted_at` datetime DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `faculty_review_status` enum('pending','acknowledged','revision_required') NOT NULL DEFAULT 'pending',
  `faculty_feedback` text,
  `faculty_reviewed_by_faculty_id` bigint unsigned DEFAULT NULL,
  `faculty_reviewed_at` datetime DEFAULT NULL,
  `industry_review_status` enum('pending','acknowledged','revision_required') NOT NULL DEFAULT 'pending',
  `industry_feedback` text,
  `industry_reviewed_by_mentor_id` bigint unsigned DEFAULT NULL,
  `industry_reviewed_at` datetime DEFAULT NULL,
  `placement_id` bigint unsigned DEFAULT NULL,
  `work_date` date DEFAULT NULL,
  `summary` varchar(255) DEFAULT NULL,
  `challenges` text,
  `next_steps` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_daily_log_participation_date` (`participation_id`,`log_date`),
  KEY `ix_daily_log_student_date` (`student_id`,`log_date`),
  KEY `ix_daily_log_participation_status` (`participation_id`,`status`,`log_date`),
  KEY `ix_daily_log_faculty_reviewer` (`faculty_reviewed_by_faculty_id`),
  KEY `ix_daily_log_industry_reviewer` (`industry_reviewed_by_mentor_id`),
  KEY `ix_internship_work_logs_placement_date` (`placement_id`,`log_date`),
  CONSTRAINT `fk_daily_log_faculty_reviewer` FOREIGN KEY (`faculty_reviewed_by_faculty_id`) REFERENCES `faculty` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_daily_log_industry_reviewer` FOREIGN KEY (`industry_reviewed_by_mentor_id`) REFERENCES `industry_mentors` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_daily_log_participation` FOREIGN KEY (`participation_id`) REFERENCES `internship_participations` (`id`),
  CONSTRAINT `fk_daily_log_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`),
  CONSTRAINT `fk_internship_daily_logs_placement_id` FOREIGN KEY (`placement_id`) REFERENCES `internship_placements` (`id`) ON DELETE CASCADE,
  CONSTRAINT `ck_daily_log_hours` CHECK (((`hours_worked` is null) or ((`hours_worked` >= 0) and (`hours_worked` <= 24)))),
  CONSTRAINT `ck_daily_log_status` CHECK ((`status` in (_utf8mb4'draft',_utf8mb4'submitted',_utf8mb4'locked')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `internship_daily_logs`
--

LOCK TABLES `internship_daily_logs` WRITE;
/*!40000 ALTER TABLE `internship_daily_logs` DISABLE KEYS */;
/*!40000 ALTER TABLE `internship_daily_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `internship_opportunities`
--

DROP TABLE IF EXISTS `internship_opportunities`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `internship_opportunities` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `provider_id` bigint unsigned DEFAULT NULL,
  `created_by_account_id` bigint unsigned NOT NULL,
  `title` varchar(250) NOT NULL,
  `description` text,
  `location` varchar(250) DEFAULT NULL,
  `work_mode` varchar(30) DEFAULT NULL,
  `opportunity_type` varchar(50) DEFAULT NULL,
  `application_deadline` datetime DEFAULT NULL,
  `starts_on` date DEFAULT NULL,
  `ends_on` date DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'draft',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `stipend_amount` decimal(10,2) NOT NULL DEFAULT '0.00',
  `is_active` tinyint(1) NOT NULL DEFAULT '0',
  `summary` text,
  `lifecycle_status` varchar(20) DEFAULT NULL,
  `employment_type` varchar(50) DEFAULT NULL,
  `department` varchar(150) DEFAULT NULL,
  `experience_min_years` int DEFAULT NULL,
  `experience_max_years` int DEFAULT NULL,
  `compensation_min` decimal(10,2) DEFAULT NULL,
  `compensation_max` decimal(10,2) DEFAULT NULL,
  `compensation_currency` varchar(3) DEFAULT 'INR',
  `compensation_period` varchar(20) DEFAULT NULL,
  `compensation_visible` tinyint(1) NOT NULL DEFAULT '1',
  `openings` int NOT NULL DEFAULT '1',
  `required_skills` json DEFAULT NULL,
  `preferred_skills` json DEFAULT NULL,
  `education_requirements` text,
  `public_application_url` varchar(2048) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_opportunity_status_deadline` (`status`,`application_deadline`),
  KEY `ix_opportunity_provider` (`provider_id`,`status`),
  KEY `fk_opportunity_creator` (`created_by_account_id`),
  CONSTRAINT `fk_opportunity_creator` FOREIGN KEY (`created_by_account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_opportunity_provider` FOREIGN KEY (`provider_id`) REFERENCES `internship_providers` (`id`),
  CONSTRAINT `ck_opportunity_dates` CHECK (((`starts_on` is null) or (`ends_on` is null) or (`ends_on` >= `starts_on`))),
  CONSTRAINT `ck_opportunity_status` CHECK ((`status` in (_utf8mb4'draft',_utf8mb4'published',_utf8mb4'closed',_utf8mb4'cancelled',_utf8mb4'archived')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `internship_opportunities`
--

LOCK TABLES `internship_opportunities` WRITE;
/*!40000 ALTER TABLE `internship_opportunities` DISABLE KEYS */;
/*!40000 ALTER TABLE `internship_opportunities` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `internship_participations`
--

DROP TABLE IF EXISTS `internship_participations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `internship_participations` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `student_id` bigint unsigned NOT NULL,
  `opportunity_id` bigint unsigned DEFAULT NULL,
  `application_id` bigint unsigned DEFAULT NULL,
  `provider_id` bigint unsigned DEFAULT NULL,
  `supervisor_name` varchar(200) DEFAULT NULL,
  `supervisor_email` varchar(254) DEFAULT NULL,
  `title` varchar(250) DEFAULT NULL,
  `starts_on` date NOT NULL,
  `ends_on` date DEFAULT NULL,
  `status` varchar(25) NOT NULL DEFAULT 'planned',
  `completion_confirmed_at` datetime DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_participation_student_dates` (`student_id`,`starts_on`,`ends_on`),
  KEY `ix_participation_status_dates` (`status`,`starts_on`,`ends_on`),
  KEY `fk_participation_opportunity` (`opportunity_id`),
  KEY `fk_participation_application` (`application_id`),
  KEY `fk_participation_provider` (`provider_id`),
  CONSTRAINT `fk_participation_application` FOREIGN KEY (`application_id`) REFERENCES `internship_applications` (`id`),
  CONSTRAINT `fk_participation_opportunity` FOREIGN KEY (`opportunity_id`) REFERENCES `internship_opportunities` (`id`),
  CONSTRAINT `fk_participation_provider` FOREIGN KEY (`provider_id`) REFERENCES `internship_providers` (`id`),
  CONSTRAINT `fk_participation_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`),
  CONSTRAINT `ck_participation_dates` CHECK (((`ends_on` is null) or (`ends_on` >= `starts_on`))),
  CONSTRAINT `ck_participation_status` CHECK ((`status` in (_utf8mb4'planned',_utf8mb4'active',_utf8mb4'completed',_utf8mb4'terminated',_utf8mb4'cancelled')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `internship_participations`
--

LOCK TABLES `internship_participations` WRITE;
/*!40000 ALTER TABLE `internship_participations` DISABLE KEYS */;
/*!40000 ALTER TABLE `internship_participations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `internship_placements`
--

DROP TABLE IF EXISTS `internship_placements`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `internship_placements` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `application_id` bigint unsigned NOT NULL,
  `student_id` bigint unsigned NOT NULL,
  `faculty_supervisor_id` bigint unsigned DEFAULT NULL,
  `industry_mentor_account_id` bigint unsigned DEFAULT NULL,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `status` enum('ONGOING','COMPLETED','TERMINATED') NOT NULL DEFAULT 'ONGOING',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_internship_placements_application` (`application_id`),
  UNIQUE KEY `uq_internship_placements_id_student` (`id`,`student_id`),
  KEY `ix_internship_placements_student` (`student_id`),
  KEY `ix_internship_placements_supervisor` (`faculty_supervisor_id`),
  KEY `ix_internship_placements_industry_mentor_account_id` (`industry_mentor_account_id`),
  CONSTRAINT `fk_internship_placements_application` FOREIGN KEY (`application_id`) REFERENCES `internship_applications` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_internship_placements_industry_mentor_account` FOREIGN KEY (`industry_mentor_account_id`) REFERENCES `accounts` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_internship_placements_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_internship_placements_supervisor` FOREIGN KEY (`faculty_supervisor_id`) REFERENCES `faculty` (`id`) ON DELETE SET NULL,
  CONSTRAINT `chk_internship_placements_dates` CHECK ((`end_date` >= `start_date`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `internship_placements`
--

LOCK TABLES `internship_placements` WRITE;
/*!40000 ALTER TABLE `internship_placements` DISABLE KEYS */;
/*!40000 ALTER TABLE `internship_placements` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `internship_providers`
--

DROP TABLE IF EXISTS `internship_providers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `internship_providers` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `website` varchar(500) DEFAULT NULL,
  `contact_email` varchar(254) DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `employer_organization_id` varchar(36) DEFAULT NULL,
  `company_name` varchar(200) DEFAULT NULL,
  `industry_sector` varchar(150) DEFAULT NULL,
  `contact_person_name` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_internship_provider_employer_org` (`employer_organization_id`),
  KEY `ix_provider_name` (`name`),
  KEY `ix_internship_providers_employer_organization_id` (`employer_organization_id`),
  CONSTRAINT `fk_internship_provider_employer_org` FOREIGN KEY (`employer_organization_id`) REFERENCES `employer_organizations` (`id`) ON DELETE SET NULL,
  CONSTRAINT `ck_provider_status` CHECK ((`status` in (_utf8mb4'active',_utf8mb4'inactive')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `internship_providers`
--

LOCK TABLES `internship_providers` WRITE;
/*!40000 ALTER TABLE `internship_providers` DISABLE KEYS */;
/*!40000 ALTER TABLE `internship_providers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `internship_weekly_feedback`
--

DROP TABLE IF EXISTS `internship_weekly_feedback`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `internship_weekly_feedback` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `participation_id` bigint unsigned NOT NULL,
  `week_start` date NOT NULL,
  `reviewer_type` varchar(25) NOT NULL,
  `reviewer_account_id` bigint unsigned DEFAULT NULL,
  `industry_mentor_id` bigint unsigned DEFAULT NULL,
  `overall_rating` decimal(4,2) DEFAULT NULL,
  `strengths` text,
  `improvement_areas` text,
  `attendance_rating` tinyint unsigned DEFAULT NULL,
  `technical_rating` tinyint unsigned DEFAULT NULL,
  `communication_rating` tinyint unsigned DEFAULT NULL,
  `feedback_text` text,
  `status` varchar(20) NOT NULL DEFAULT 'draft',
  `submitted_at` datetime DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_weekly_feedback_reviewer` (`participation_id`,`week_start`,`reviewer_type`,`reviewer_account_id`,`industry_mentor_id`),
  KEY `ix_weekly_feedback_participation_week` (`participation_id`,`week_start`,`status`),
  KEY `ix_weekly_feedback_reviewer` (`reviewer_account_id`,`week_start`),
  KEY `fk_weekly_feedback_industry_mentor` (`industry_mentor_id`),
  CONSTRAINT `fk_weekly_feedback_industry_mentor` FOREIGN KEY (`industry_mentor_id`) REFERENCES `industry_mentors` (`id`),
  CONSTRAINT `fk_weekly_feedback_participation` FOREIGN KEY (`participation_id`) REFERENCES `internship_participations` (`id`),
  CONSTRAINT `fk_weekly_feedback_reviewer` FOREIGN KEY (`reviewer_account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `ck_weekly_feedback_attendance` CHECK (((`attendance_rating` is null) or (`attendance_rating` between 1 and 5))),
  CONSTRAINT `ck_weekly_feedback_communication` CHECK (((`communication_rating` is null) or (`communication_rating` between 1 and 5))),
  CONSTRAINT `ck_weekly_feedback_overall_rating` CHECK (((`overall_rating` is null) or ((`overall_rating` >= 0) and (`overall_rating` <= 5)))),
  CONSTRAINT `ck_weekly_feedback_reviewer_type` CHECK ((`reviewer_type` in (_utf8mb4'student_self',_utf8mb4'faculty_mentor',_utf8mb4'industry_mentor'))),
  CONSTRAINT `ck_weekly_feedback_status` CHECK ((`status` in (_utf8mb4'draft',_utf8mb4'submitted',_utf8mb4'returned',_utf8mb4'locked'))),
  CONSTRAINT `ck_weekly_feedback_technical` CHECK (((`technical_rating` is null) or (`technical_rating` between 1 and 5)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `internship_weekly_feedback`
--

LOCK TABLES `internship_weekly_feedback` WRITE;
/*!40000 ALTER TABLE `internship_weekly_feedback` DISABLE KEYS */;
/*!40000 ALTER TABLE `internship_weekly_feedback` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `internship_work_feedback`
--

DROP TABLE IF EXISTS `internship_work_feedback`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `internship_work_feedback` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `daily_log_id` bigint unsigned NOT NULL,
  `reviewer_type` enum('faculty_mentor','industry_mentor') NOT NULL,
  `reviewer_account_id` bigint unsigned NOT NULL,
  `faculty_id` bigint unsigned DEFAULT NULL,
  `industry_mentor_id` bigint unsigned DEFAULT NULL,
  `decision` enum('acknowledged','revision_required') NOT NULL,
  `feedback_text` text NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_work_feedback_log_created` (`daily_log_id`,`created_at`),
  KEY `ix_work_feedback_reviewer_created` (`reviewer_account_id`,`created_at`),
  KEY `ix_work_feedback_faculty` (`faculty_id`),
  KEY `ix_work_feedback_industry_mentor` (`industry_mentor_id`),
  CONSTRAINT `fk_work_feedback_account` FOREIGN KEY (`reviewer_account_id`) REFERENCES `accounts` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_work_feedback_daily_log` FOREIGN KEY (`daily_log_id`) REFERENCES `internship_daily_logs` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_work_feedback_faculty` FOREIGN KEY (`faculty_id`) REFERENCES `faculty` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_work_feedback_industry_mentor` FOREIGN KEY (`industry_mentor_id`) REFERENCES `industry_mentors` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `chk_work_feedback_reviewer` CHECK ((((`reviewer_type` = _utf8mb4'faculty_mentor') and (`faculty_id` is not null) and (`industry_mentor_id` is null)) or ((`reviewer_type` = _utf8mb4'industry_mentor') and (`industry_mentor_id` is not null) and (`faculty_id` is null))))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `internship_work_feedback`
--

LOCK TABLES `internship_work_feedback` WRITE;
/*!40000 ALTER TABLE `internship_work_feedback` DISABLE KEYS */;
/*!40000 ALTER TABLE `internship_work_feedback` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `outbox_events`
--

DROP TABLE IF EXISTS `outbox_events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `outbox_events` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `event_type` varchar(120) NOT NULL,
  `aggregate_type` varchar(100) NOT NULL,
  `aggregate_id` varchar(100) NOT NULL,
  `idempotency_key` varchar(200) NOT NULL,
  `payload` json NOT NULL,
  `event_status` varchar(20) NOT NULL DEFAULT 'pending',
  `attempts` int unsigned NOT NULL DEFAULT '0',
  `available_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `locked_at` datetime DEFAULT NULL,
  `published_at` datetime DEFAULT NULL,
  `last_error` text,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_outbox_idempotency` (`idempotency_key`),
  KEY `ix_outbox_dispatch` (`event_status`,`available_at`,`id`),
  CONSTRAINT `ck_outbox_status` CHECK ((`event_status` in (_utf8mb4'pending',_utf8mb4'processing',_utf8mb4'published',_utf8mb4'failed')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `outbox_events`
--

LOCK TABLES `outbox_events` WRITE;
/*!40000 ALTER TABLE `outbox_events` DISABLE KEYS */;
/*!40000 ALTER TABLE `outbox_events` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `permissions`
--

DROP TABLE IF EXISTS `permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `permissions` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `code` varchar(100) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_permissions_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `permissions`
--

LOCK TABLES `permissions` WRITE;
/*!40000 ALTER TABLE `permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `programme_specialisations`
--

DROP TABLE IF EXISTS `programme_specialisations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `programme_specialisations` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `programme_id` bigint unsigned NOT NULL,
  `name` varchar(150) NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'active',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_programme_specialisation` (`programme_id`,`name`),
  CONSTRAINT `fk_specialisation_programme` FOREIGN KEY (`programme_id`) REFERENCES `programmes` (`id`),
  CONSTRAINT `ck_specialisation_status` CHECK ((`status` in (_utf8mb4'active',_utf8mb4'inactive')))
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `programme_specialisations`
--

LOCK TABLES `programme_specialisations` WRITE;
/*!40000 ALTER TABLE `programme_specialisations` DISABLE KEYS */;
INSERT INTO `programme_specialisations` VALUES (1,17,'Data Science','active'),(2,17,'Artificial Intelligence & Machine Learning','active'),(3,17,'IoT & Automation','active'),(4,17,'Cyber Security','active'),(5,26,'Human Resource Management','active'),(6,26,'Marketing','active'),(7,26,'Accounting & Finance','active'),(8,26,'Information Technology Management','active');
/*!40000 ALTER TABLE `programme_specialisations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `programmes`
--

DROP TABLE IF EXISTS `programmes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `programmes` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `department_id` bigint unsigned NOT NULL,
  `name` varchar(200) NOT NULL,
  `code` varchar(50) DEFAULT NULL,
  `award_level` varchar(80) DEFAULT NULL,
  `duration_semesters` smallint unsigned DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'active',
  `degree_level` varchar(80) DEFAULT NULL,
  `duration_years` decimal(4,2) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_programmes_department_code` (`department_id`,`code`),
  CONSTRAINT `fk_programmes_department` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`),
  CONSTRAINT `ck_programmes_duration` CHECK (((`duration_semesters` is null) or (`duration_semesters` > 0))),
  CONSTRAINT `ck_programmes_status` CHECK ((`status` in (_utf8mb4'active',_utf8mb4'inactive')))
) ENGINE=InnoDB AUTO_INCREMENT=64 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `programmes`
--

LOCK TABLES `programmes` WRITE;
/*!40000 ALTER TABLE `programmes` DISABLE KEYS */;
INSERT INTO `programmes` VALUES (1,1,'B.Sc. Data Science','SOCIS-BSC-DS','Undergraduate',NULL,'active',NULL,NULL,1),(2,1,'B.Sc. (Hons.) Chemistry','SOCIS-BSC-HONS-CHEM','Undergraduate',NULL,'active',NULL,NULL,1),(3,1,'Integrated B.Sc.–M.Sc. Chemistry','SOCIS-INT-CHEM','Integrated UG-PG',NULL,'active',NULL,NULL,1),(4,1,'Integrated B.Sc. (Hons.)–M.Sc. Data Science','SOCIS-INT-DS','Integrated UG-PG',NULL,'active',NULL,NULL,1),(5,1,'M.Sc. Chemistry (Organic / Analytical Chemistry)','SOCIS-MSC-CHEM','Postgraduate',NULL,'active',NULL,NULL,1),(6,1,'M.Sc. Data Science','SOCIS-MSC-DS','Postgraduate',NULL,'active',NULL,NULL,1),(7,1,'Ph.D. Chemistry','SOCIS-PHD-CHEM','Doctoral',NULL,'active',NULL,NULL,1),(8,1,'Ph.D. Mathematics','SOCIS-PHD-MATH','Doctoral',NULL,'active',NULL,NULL,1),(9,4,'B.Sc. (Hons.) Biotechnology','SOLS-BSC-BIOTECH','Undergraduate',NULL,'active',NULL,NULL,1),(10,4,'B.Sc. (Hons.) Microbiology','SOLS-BSC-MICRO','Undergraduate',NULL,'active',NULL,NULL,1),(11,4,'Integrated BS (Hons.)–MS Pharmaceutical Science','SOLS-INT-PHARMA','Integrated UG-PG',NULL,'active',NULL,NULL,1),(12,4,'M.Sc. Biotechnology','SOLS-MSC-BIOTECH','Postgraduate',NULL,'active',NULL,NULL,1),(13,4,'M.Sc. Microbiology','SOLS-MSC-MICRO','Postgraduate',NULL,'active',NULL,NULL,1),(14,4,'Ph.D. Biotechnology','SOLS-PHD-BIOTECH','Doctoral',NULL,'active',NULL,NULL,1),(15,4,'Ph.D. Microbiology','SOLS-PHD-MICRO','Doctoral',NULL,'active',NULL,NULL,1),(16,3,'BCA — Bachelor of Computer Applications','SOCIT-BCA','Undergraduate',NULL,'active',NULL,NULL,1),(17,3,'B.Tech. Computer Science & Engineering','SOCIT-BTECH-CSE','Undergraduate',NULL,'active',NULL,NULL,1),(18,3,'B.Tech. Electronics & Communication Engineering','SOCIT-BTECH-ECE','Undergraduate',NULL,'active',NULL,NULL,1),(19,3,'M.Tech. Computer Science & Engineering','SOCIT-MTECH-CSE','Postgraduate',NULL,'active',NULL,NULL,1),(20,3,'Ph.D. Computer Science & Engineering','SOCIT-PHD-CSE','Doctoral',NULL,'active',NULL,NULL,1),(21,2,'B.Tech. Chemical Engineering','SOCFS-BTECH-CHEM','Undergraduate',NULL,'active',NULL,NULL,1),(22,2,'B.Tech. Fire & Environment, Health & Safety (F&EHS)','SOCFS-BTECH-FEHS','Undergraduate',NULL,'active',NULL,NULL,1),(23,2,'M.Tech. Industrial Safety & Engineering','SOCFS-MTECH-SAFETY','Postgraduate',NULL,'active',NULL,NULL,1),(24,2,'PG Diploma in Industrial Safety','SOCFS-PGD-SAFETY','Diploma',NULL,'active',NULL,NULL,1),(25,5,'BBA — Business Analytics','SOME-BBA-BA','Undergraduate',NULL,'active',NULL,NULL,1),(26,5,'BBA — General','SOME-BBA-GEN','Undergraduate',NULL,'active',NULL,NULL,1),(27,5,'B.Com. / B.Com. (Hons.)','SOME-BCOM','Undergraduate',NULL,'active',NULL,NULL,1),(28,5,'Integrated BBA–MBA (with AI in Business)','SOME-INT-BBA-MBA','Integrated UG-PG',NULL,'active',NULL,NULL,1),(29,5,'MBA — Business Analytics','SOME-MBA-BA','Postgraduate',NULL,'active',NULL,NULL,1),(30,5,'MBA — Finance','SOME-MBA-FIN','Postgraduate',NULL,'active',NULL,NULL,1),(31,5,'MBA — Human Resource Management','SOME-MBA-HRM','Postgraduate',NULL,'active',NULL,NULL,1),(32,5,'MBA — Marketing','SOME-MBA-MKT','Postgraduate',NULL,'active',NULL,NULL,1),(33,5,'Ph.D. Management','SOME-PHD-MGMT','Doctoral',NULL,'active',NULL,NULL,1);
/*!40000 ALTER TABLE `programmes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recruitment_drive_opportunities`
--

DROP TABLE IF EXISTS `recruitment_drive_opportunities`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `recruitment_drive_opportunities` (
  `drive_id` varchar(36) NOT NULL,
  `opportunity_id` bigint unsigned NOT NULL,
  `added_by_account_id` bigint unsigned NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`drive_id`,`opportunity_id`),
  KEY `ix_recruitment_drive_opportunity_opportunity` (`opportunity_id`),
  KEY `ix_recruitment_drive_opportunity_added_by` (`added_by_account_id`),
  CONSTRAINT `fk_rdo_added_by` FOREIGN KEY (`added_by_account_id`) REFERENCES `accounts` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_rdo_drive` FOREIGN KEY (`drive_id`) REFERENCES `recruitment_drives` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_rdo_opportunity` FOREIGN KEY (`opportunity_id`) REFERENCES `internship_opportunities` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recruitment_drive_opportunities`
--

LOCK TABLES `recruitment_drive_opportunities` WRITE;
/*!40000 ALTER TABLE `recruitment_drive_opportunities` DISABLE KEYS */;
/*!40000 ALTER TABLE `recruitment_drive_opportunities` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recruitment_drives`
--

DROP TABLE IF EXISTS `recruitment_drives`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `recruitment_drives` (
  `id` varchar(36) NOT NULL,
  `institution_id` bigint unsigned NOT NULL,
  `academic_year_id` bigint unsigned DEFAULT NULL,
  `name` varchar(255) NOT NULL,
  `description` text,
  `starts_on` date DEFAULT NULL,
  `ends_on` date DEFAULT NULL,
  `application_opens_at` timestamp NULL DEFAULT NULL,
  `application_closes_at` timestamp NULL DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'DRAFT',
  `created_by_account_id` bigint unsigned NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_recruitment_drives_institution` (`institution_id`),
  KEY `ix_recruitment_drives_academic_year` (`academic_year_id`),
  KEY `ix_recruitment_drives_creator` (`created_by_account_id`),
  CONSTRAINT `fk_recruitment_drives_academic_year` FOREIGN KEY (`academic_year_id`) REFERENCES `academic_years` (`id`),
  CONSTRAINT `fk_recruitment_drives_creator` FOREIGN KEY (`created_by_account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_recruitment_drives_institution` FOREIGN KEY (`institution_id`) REFERENCES `institutions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recruitment_drives`
--

LOCK TABLES `recruitment_drives` WRITE;
/*!40000 ALTER TABLE `recruitment_drives` DISABLE KEYS */;
/*!40000 ALTER TABLE `recruitment_drives` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `report_requirements`
--

DROP TABLE IF EXISTS `report_requirements`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `report_requirements` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `institution_id` bigint unsigned NOT NULL,
  `programme_id` bigint unsigned DEFAULT NULL,
  `name` varchar(200) NOT NULL,
  `due_after_completion_days` int unsigned DEFAULT NULL,
  `is_mandatory` tinyint(1) NOT NULL DEFAULT '1',
  `active` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `ix_report_requirement_scope` (`institution_id`,`programme_id`,`active`),
  KEY `fk_report_requirement_programme` (`programme_id`),
  CONSTRAINT `fk_report_requirement_institution` FOREIGN KEY (`institution_id`) REFERENCES `institutions` (`id`),
  CONSTRAINT `fk_report_requirement_programme` FOREIGN KEY (`programme_id`) REFERENCES `programmes` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `report_requirements`
--

LOCK TABLES `report_requirements` WRITE;
/*!40000 ALTER TABLE `report_requirements` DISABLE KEYS */;
/*!40000 ALTER TABLE `report_requirements` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `report_submissions`
--

DROP TABLE IF EXISTS `report_submissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `report_submissions` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `participation_id` bigint unsigned NOT NULL,
  `placement_id` bigint unsigned DEFAULT NULL,
  `requirement_id` bigint unsigned DEFAULT NULL,
  `current_version_id` bigint unsigned DEFAULT NULL,
  `accepted_version_id` bigint unsigned DEFAULT NULL,
  `workflow_status` varchar(30) NOT NULL DEFAULT 'awaiting_submission',
  `due_at` datetime DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `title` varchar(255) NOT NULL DEFAULT 'Internship report',
  `latest_version_number` int unsigned NOT NULL DEFAULT '1',
  `status` varchar(30) NOT NULL DEFAULT 'DRAFT',
  `review_feedback` text,
  `reviewed_by_account_id` bigint unsigned DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_report_submission_participation_requirement` (`participation_id`,`requirement_id`),
  KEY `ix_report_submission_status_due` (`workflow_status`,`due_at`),
  KEY `fk_report_submission_requirement` (`requirement_id`),
  KEY `fk_report_submission_current_version` (`current_version_id`),
  KEY `fk_report_submission_accepted_version` (`accepted_version_id`),
  KEY `ix_report_submissions_placement_status` (`placement_id`,`status`,`updated_at`),
  KEY `ix_report_submissions_reviewed_by` (`reviewed_by_account_id`),
  CONSTRAINT `fk_report_submission_accepted_version` FOREIGN KEY (`accepted_version_id`) REFERENCES `report_versions` (`id`),
  CONSTRAINT `fk_report_submission_current_version` FOREIGN KEY (`current_version_id`) REFERENCES `report_versions` (`id`),
  CONSTRAINT `fk_report_submission_participation` FOREIGN KEY (`participation_id`) REFERENCES `internship_participations` (`id`),
  CONSTRAINT `fk_report_submission_requirement` FOREIGN KEY (`requirement_id`) REFERENCES `report_requirements` (`id`),
  CONSTRAINT `fk_report_submissions_placement` FOREIGN KEY (`placement_id`) REFERENCES `internship_placements` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_report_submissions_reviewed_by` FOREIGN KEY (`reviewed_by_account_id`) REFERENCES `accounts` (`id`) ON DELETE SET NULL,
  CONSTRAINT `ck_report_submission_status` CHECK ((`workflow_status` in (_utf8mb4'awaiting_submission',_utf8mb4'submitted',_utf8mb4'under_evaluation',_utf8mb4'changes_requested',_utf8mb4'accepted',_utf8mb4'rejected',_utf8mb4'closed')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `report_submissions`
--

LOCK TABLES `report_submissions` WRITE;
/*!40000 ALTER TABLE `report_submissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `report_submissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `report_versions`
--

DROP TABLE IF EXISTS `report_versions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `report_versions` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `submission_id` bigint unsigned NOT NULL,
  `version_number` int unsigned NOT NULL,
  `storage_key` varchar(1000) NOT NULL,
  `original_filename` varchar(255) NOT NULL,
  `mime_type` varchar(150) NOT NULL,
  `size_bytes` bigint unsigned NOT NULL,
  `sha256` char(64) NOT NULL,
  `submitted_by_account_id` bigint unsigned NOT NULL,
  `submitted_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `student_note` text,
  `is_withdrawn` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_report_version_number` (`submission_id`,`version_number`),
  UNIQUE KEY `uq_report_version_id_submission` (`id`,`submission_id`),
  KEY `ix_report_version_submitted_at` (`submission_id`,`submitted_at`),
  KEY `ix_report_version_hash` (`sha256`),
  KEY `fk_report_version_submitter` (`submitted_by_account_id`),
  CONSTRAINT `fk_report_version_submission` FOREIGN KEY (`submission_id`) REFERENCES `report_submissions` (`id`),
  CONSTRAINT `fk_report_version_submitter` FOREIGN KEY (`submitted_by_account_id`) REFERENCES `accounts` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `report_versions`
--

LOCK TABLES `report_versions` WRITE;
/*!40000 ALTER TABLE `report_versions` DISABLE KEYS */;
/*!40000 ALTER TABLE `report_versions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `reviewer_conflicts`
--

DROP TABLE IF EXISTS `reviewer_conflicts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `reviewer_conflicts` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `reviewer_account_id` bigint unsigned NOT NULL,
  `student_id` bigint unsigned DEFAULT NULL,
  `faculty_id` bigint unsigned DEFAULT NULL,
  `institution_id` bigint unsigned DEFAULT NULL,
  `provider_id` bigint unsigned DEFAULT NULL,
  `conflict_type` varchar(40) NOT NULL,
  `reason` text,
  `active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_reviewer_conflict_reviewer` (`reviewer_account_id`,`active`),
  KEY `ix_reviewer_conflict_institution` (`institution_id`,`reviewer_account_id`,`active`),
  KEY `fk_reviewer_conflict_student` (`student_id`),
  KEY `fk_reviewer_conflict_faculty` (`faculty_id`),
  KEY `fk_reviewer_conflict_provider` (`provider_id`),
  CONSTRAINT `fk_reviewer_conflict_account` FOREIGN KEY (`reviewer_account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_reviewer_conflict_faculty` FOREIGN KEY (`faculty_id`) REFERENCES `faculty` (`id`),
  CONSTRAINT `fk_reviewer_conflict_institution` FOREIGN KEY (`institution_id`) REFERENCES `institutions` (`id`),
  CONSTRAINT `fk_reviewer_conflict_provider` FOREIGN KEY (`provider_id`) REFERENCES `internship_providers` (`id`),
  CONSTRAINT `fk_reviewer_conflict_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`),
  CONSTRAINT `ck_reviewer_conflict_type` CHECK ((`conflict_type` in (_utf8mb4'same_institution',_utf8mb4'former_mentor',_utf8mb4'same_provider',_utf8mb4'personal',_utf8mb4'other')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `reviewer_conflicts`
--

LOCK TABLES `reviewer_conflicts` WRITE;
/*!40000 ALTER TABLE `reviewer_conflicts` DISABLE KEYS */;
/*!40000 ALTER TABLE `reviewer_conflicts` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `role_permissions`
--

DROP TABLE IF EXISTS `role_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `role_permissions` (
  `role_id` bigint unsigned NOT NULL,
  `permission_id` bigint unsigned NOT NULL,
  PRIMARY KEY (`role_id`,`permission_id`),
  KEY `fk_role_permissions_permission` (`permission_id`),
  CONSTRAINT `fk_role_permissions_permission` FOREIGN KEY (`permission_id`) REFERENCES `permissions` (`id`),
  CONSTRAINT `fk_role_permissions_role` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `role_permissions`
--

LOCK TABLES `role_permissions` WRITE;
/*!40000 ALTER TABLE `role_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `role_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `roles`
--

DROP TABLE IF EXISTS `roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `roles` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `code` varchar(60) NOT NULL,
  `name` varchar(120) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_roles_code` (`code`)
) ENGINE=InnoDB AUTO_INCREMENT=7006 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `roles`
--

LOCK TABLES `roles` WRITE;
/*!40000 ALTER TABLE `roles` DISABLE KEYS */;
INSERT INTO `roles` VALUES (7001,'STUDENT','STUDENT',NULL),(7005,'FACULTY','FACULTY',NULL);
/*!40000 ALTER TABLE `roles` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `schools`
--

DROP TABLE IF EXISTS `schools`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `schools` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `institution_id` bigint unsigned NOT NULL,
  `name` varchar(200) NOT NULL,
  `code` varchar(50) DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_schools_institution_name` (`institution_id`,`name`),
  UNIQUE KEY `uq_schools_institution_code` (`institution_id`,`code`),
  CONSTRAINT `fk_schools_institution` FOREIGN KEY (`institution_id`) REFERENCES `institutions` (`id`),
  CONSTRAINT `ck_schools_status` CHECK ((`status` in (_utf8mb4'active',_utf8mb4'inactive')))
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `schools`
--

LOCK TABLES `schools` WRITE;
/*!40000 ALTER TABLE `schools` DISABLE KEYS */;
INSERT INTO `schools` VALUES (1,11,'School of Chemical & Industrial Sciences','SoCIS','active','2026-10-24 12:07:48','2026-10-24 12:26:48',1),(2,11,'School of Life Sciences','SoLS','active','2026-10-24 12:07:48','2026-10-24 12:26:48',1),(3,11,'School of Information & Communication Technology','SoCIT','active','2026-10-24 12:07:48','2026-10-24 12:26:48',1),(4,11,'School of Chemical Engineering & Fire Safety','SoCFS','active','2026-10-24 12:07:48','2026-10-24 12:26:48',1),(5,11,'School of Management & Entrepreneurship','SoME','active','2026-10-24 12:07:48','2026-10-24 12:26:49',1);
/*!40000 ALTER TABLE `schools` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `semesters`
--

DROP TABLE IF EXISTS `semesters`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `semesters` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `academic_year_id` bigint unsigned NOT NULL,
  `label` varchar(50) NOT NULL,
  `sequence_no` smallint unsigned DEFAULT NULL,
  `starts_on` date DEFAULT NULL,
  `ends_on` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_semester_label` (`academic_year_id`,`label`),
  CONSTRAINT `fk_semester_year` FOREIGN KEY (`academic_year_id`) REFERENCES `academic_years` (`id`),
  CONSTRAINT `ck_semester_dates` CHECK (((`starts_on` is null) or (`ends_on` is null) or (`ends_on` >= `starts_on`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `semesters`
--

LOCK TABLES `semesters` WRITE;
/*!40000 ALTER TABLE `semesters` DISABLE KEYS */;
/*!40000 ALTER TABLE `semesters` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `storage_files`
--

DROP TABLE IF EXISTS `storage_files`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `storage_files` (
  `id` varchar(36) NOT NULL,
  `original_name` varchar(255) NOT NULL,
  `file_path` varchar(512) NOT NULL,
  `file_size_bytes` bigint unsigned NOT NULL,
  `mime_type` varchar(150) NOT NULL,
  `sha256_hash` char(64) NOT NULL,
  `uploaded_by_account_id` bigint unsigned NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_storage_files_hash` (`sha256_hash`),
  KEY `ix_storage_files_uploader_created` (`uploaded_by_account_id`,`created_at`),
  CONSTRAINT `fk_storage_files_uploaded_by` FOREIGN KEY (`uploaded_by_account_id`) REFERENCES `accounts` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `storage_files`
--

LOCK TABLES `storage_files` WRITE;
/*!40000 ALTER TABLE `storage_files` DISABLE KEYS */;
INSERT INTO `storage_files` VALUES ('b19b35f4-991c-46e2-9c3a-5df4b85846c8','Dhruv_Verma_resume.pdf','files/ff13bb11-d7a7-429d-95d8-6c59bad4e5e6/b19b35f4-991c-46e2-9c3a-5df4b85846c8.pdf',148490,'application/pdf','62f0593953de92932d3b7b294a813d29ae1c876f42a2f41ef4f1226d43d6a5bd',2,'2026-10-24 17:42:55');
/*!40000 ALTER TABLE `storage_files` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student_academic_records`
--

DROP TABLE IF EXISTS `student_academic_records`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `student_academic_records` (
  `id` varchar(36) NOT NULL,
  `student_profile_id` bigint unsigned NOT NULL,
  `institution_name` varchar(255) NOT NULL,
  `qualification` varchar(255) NOT NULL,
  `field_of_study` varchar(255) DEFAULT NULL,
  `start_date` date DEFAULT NULL,
  `end_date` date DEFAULT NULL,
  `semester` varchar(32) DEFAULT NULL,
  `grade_value` decimal(8,3) DEFAULT NULL,
  `grade_max` decimal(8,3) DEFAULT NULL,
  `grading_scale` varchar(100) DEFAULT NULL,
  `description` text,
  `is_verified` tinyint(1) NOT NULL DEFAULT '0',
  `verified_by_account_id` bigint unsigned DEFAULT NULL,
  `verified_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_student_academic_records_owner_dates` (`student_profile_id`,`start_date`,`end_date`),
  KEY `ix_student_academic_records_verifier` (`verified_by_account_id`),
  CONSTRAINT `fk_student_academic_records_profile` FOREIGN KEY (`student_profile_id`) REFERENCES `student_profiles` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_student_academic_records_verifier` FOREIGN KEY (`verified_by_account_id`) REFERENCES `accounts` (`id`) ON DELETE SET NULL,
  CONSTRAINT `ck_academic_grade_max_positive` CHECK (((`grade_max` is null) or (`grade_max` > 0))),
  CONSTRAINT `ck_academic_grade_nonnegative` CHECK (((`grade_value` is null) or (`grade_value` >= 0))),
  CONSTRAINT `ck_academic_grade_within_max` CHECK (((`grade_value` is null) or (`grade_max` is null) or (`grade_value` <= `grade_max`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student_academic_records`
--

LOCK TABLES `student_academic_records` WRITE;
/*!40000 ALTER TABLE `student_academic_records` DISABLE KEYS */;
/*!40000 ALTER TABLE `student_academic_records` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student_enrollments`
--

DROP TABLE IF EXISTS `student_enrollments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `student_enrollments` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `student_id` bigint unsigned NOT NULL,
  `cohort_id` bigint unsigned NOT NULL,
  `academic_year_id` bigint unsigned NOT NULL,
  `semester_id` bigint unsigned DEFAULT NULL,
  `starts_on` date NOT NULL,
  `ends_on` date DEFAULT NULL,
  `enrollment_status` varchar(20) NOT NULL DEFAULT 'active',
  `recorded_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_enrollment_student_dates` (`student_id`,`starts_on`,`ends_on`),
  KEY `ix_enrollment_cohort_year` (`cohort_id`,`academic_year_id`,`enrollment_status`),
  KEY `fk_enrollment_year` (`academic_year_id`),
  KEY `fk_enrollment_semester` (`semester_id`),
  CONSTRAINT `fk_enrollment_cohort` FOREIGN KEY (`cohort_id`) REFERENCES `cohorts` (`id`),
  CONSTRAINT `fk_enrollment_semester` FOREIGN KEY (`semester_id`) REFERENCES `semesters` (`id`),
  CONSTRAINT `fk_enrollment_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`),
  CONSTRAINT `fk_enrollment_year` FOREIGN KEY (`academic_year_id`) REFERENCES `academic_years` (`id`),
  CONSTRAINT `ck_enrollment_dates` CHECK (((`ends_on` is null) or (`ends_on` >= `starts_on`))),
  CONSTRAINT `ck_enrollment_status` CHECK ((`enrollment_status` in (_utf8mb4'active',_utf8mb4'completed',_utf8mb4'withdrawn',_utf8mb4'suspended')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student_enrollments`
--

LOCK TABLES `student_enrollments` WRITE;
/*!40000 ALTER TABLE `student_enrollments` DISABLE KEYS */;
/*!40000 ALTER TABLE `student_enrollments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student_portfolio_entries`
--

DROP TABLE IF EXISTS `student_portfolio_entries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `student_portfolio_entries` (
  `id` varchar(36) NOT NULL,
  `student_profile_id` bigint unsigned NOT NULL,
  `kind` varchar(32) NOT NULL,
  `title` varchar(255) NOT NULL,
  `description` text,
  `organization` varchar(255) DEFAULT NULL,
  `url` varchar(2048) DEFAULT NULL,
  `credential_id` varchar(255) DEFAULT NULL,
  `proficiency` varchar(64) DEFAULT NULL,
  `start_date` date DEFAULT NULL,
  `end_date` date DEFAULT NULL,
  `issued_date` date DEFAULT NULL,
  `is_verified` tinyint(1) NOT NULL DEFAULT '0',
  `verified_by_account_id` bigint unsigned DEFAULT NULL,
  `verified_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_portfolio_entries_owner_kind` (`student_profile_id`,`kind`),
  KEY `ix_portfolio_entries_owner_dates` (`student_profile_id`,`start_date`,`end_date`),
  KEY `ix_student_portfolio_entries_verifier` (`verified_by_account_id`),
  CONSTRAINT `fk_student_portfolio_entries_profile` FOREIGN KEY (`student_profile_id`) REFERENCES `student_profiles` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_student_portfolio_entries_verifier` FOREIGN KEY (`verified_by_account_id`) REFERENCES `accounts` (`id`) ON DELETE SET NULL,
  CONSTRAINT `ck_portfolio_entry_kind` CHECK ((`kind` in (_utf8mb4'skill',_utf8mb4'project',_utf8mb4'certification',_utf8mb4'experience',_utf8mb4'research',_utf8mb4'award',_utf8mb4'achievement',_utf8mb4'activity')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student_portfolio_entries`
--

LOCK TABLES `student_portfolio_entries` WRITE;
/*!40000 ALTER TABLE `student_portfolio_entries` DISABLE KEYS */;
/*!40000 ALTER TABLE `student_portfolio_entries` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student_profiles`
--

DROP TABLE IF EXISTS `student_profiles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `student_profiles` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `student_id` bigint unsigned NOT NULL,
  `account_id` bigint unsigned NOT NULL,
  `enrollment_number` varchar(80) NOT NULL,
  `profile_photo_url` varchar(500) DEFAULT NULL,
  `bio` text,
  `linkedin_url` varchar(500) DEFAULT NULL,
  `github_url` varchar(500) DEFAULT NULL,
  `portfolio_url` varchar(500) DEFAULT NULL,
  `cgpa` decimal(4,2) DEFAULT NULL,
  `profile_visibility` varchar(20) NOT NULL DEFAULT 'private',
  `is_profile_complete` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `department_id` bigint unsigned DEFAULT NULL,
  `programme_id` bigint unsigned DEFAULT NULL,
  `cohort_id` bigint unsigned DEFAULT NULL,
  `current_semester` int NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_student_profiles_student` (`student_id`),
  UNIQUE KEY `uq_student_profiles_account` (`account_id`),
  UNIQUE KEY `uq_student_profiles_enrollment_number` (`enrollment_number`),
  KEY `ix_student_profiles_department` (`department_id`),
  KEY `ix_student_profiles_programme` (`programme_id`),
  KEY `ix_student_profiles_cohort` (`cohort_id`),
  CONSTRAINT `fk_student_profiles_account` FOREIGN KEY (`account_id`) REFERENCES `accounts` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_student_profiles_cohort` FOREIGN KEY (`cohort_id`) REFERENCES `cohorts` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_student_profiles_department` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_student_profiles_programme` FOREIGN KEY (`programme_id`) REFERENCES `programmes` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_student_profiles_student` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `ck_student_profiles_cgpa` CHECK (((`cgpa` is null) or ((`cgpa` >= 0) and (`cgpa` <= 10)))),
  CONSTRAINT `ck_student_profiles_visibility` CHECK ((`profile_visibility` in (_utf8mb4'private',_utf8mb4'institution',_utf8mb4'public')))
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student_profiles`
--

LOCK TABLES `student_profiles` WRITE;
/*!40000 ALTER TABLE `student_profiles` DISABLE KEYS */;
INSERT INTO `student_profiles` VALUES (1,1,2,'23sc06007',NULL,NULL,NULL,NULL,NULL,NULL,'private',0,'2026-10-24 14:28:20','2026-10-24 14:36:39',NULL,NULL,NULL,1);
/*!40000 ALTER TABLE `student_profiles` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student_resumes`
--

DROP TABLE IF EXISTS `student_resumes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `student_resumes` (
  `id` varchar(36) NOT NULL,
  `student_profile_id` bigint unsigned NOT NULL,
  `storage_file_id` varchar(36) NOT NULL,
  `label` varchar(255) NOT NULL,
  `is_primary` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_student_resume_storage` (`student_profile_id`,`storage_file_id`),
  KEY `ix_student_resumes_student_profile_id` (`student_profile_id`),
  KEY `ix_student_resumes_storage_file_id` (`storage_file_id`),
  CONSTRAINT `fk_student_resumes_profile` FOREIGN KEY (`student_profile_id`) REFERENCES `student_profiles` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student_resumes`
--

LOCK TABLES `student_resumes` WRITE;
/*!40000 ALTER TABLE `student_resumes` DISABLE KEYS */;
INSERT INTO `student_resumes` VALUES ('ab640b0a-35d8-48e0-9d62-4683d517d749',1,'b19b35f4-991c-46e2-9c3a-5df4b85846c8','Dhruv_Verma_resume.pdf',1,'2026-10-24 17:42:58');
/*!40000 ALTER TABLE `student_resumes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `students`
--

DROP TABLE IF EXISTS `students`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `students` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `account_id` bigint unsigned NOT NULL,
  `student_number` varchar(80) NOT NULL,
  `legal_name` varchar(200) NOT NULL,
  `date_of_birth` date DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_students_account` (`account_id`),
  UNIQUE KEY `uq_students_number` (`student_number`),
  CONSTRAINT `fk_students_account` FOREIGN KEY (`account_id`) REFERENCES `accounts` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `students`
--

LOCK TABLES `students` WRITE;
/*!40000 ALTER TABLE `students` DISABLE KEYS */;
INSERT INTO `students` VALUES (1,2,'23sc06007','Dhruv Verma',NULL,'2026-10-24 13:59:19');
/*!40000 ALTER TABLE `students` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `teaching_assignments`
--

DROP TABLE IF EXISTS `teaching_assignments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `teaching_assignments` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `faculty_id` bigint unsigned NOT NULL,
  `cohort_id` bigint unsigned NOT NULL,
  `semester_id` bigint unsigned NOT NULL,
  `subject_name` varchar(200) DEFAULT NULL,
  `starts_on` date DEFAULT NULL,
  `ends_on` date DEFAULT NULL,
  `assignment_status` varchar(20) NOT NULL DEFAULT 'active',
  PRIMARY KEY (`id`),
  KEY `ix_teaching_faculty_semester` (`faculty_id`,`semester_id`,`assignment_status`),
  KEY `ix_teaching_cohort_semester` (`cohort_id`,`semester_id`),
  KEY `fk_teaching_semester` (`semester_id`),
  CONSTRAINT `fk_teaching_cohort` FOREIGN KEY (`cohort_id`) REFERENCES `cohorts` (`id`),
  CONSTRAINT `fk_teaching_faculty` FOREIGN KEY (`faculty_id`) REFERENCES `faculty` (`id`),
  CONSTRAINT `fk_teaching_semester` FOREIGN KEY (`semester_id`) REFERENCES `semesters` (`id`),
  CONSTRAINT `ck_teaching_dates` CHECK (((`starts_on` is null) or (`ends_on` is null) or (`ends_on` >= `starts_on`))),
  CONSTRAINT `ck_teaching_status` CHECK ((`assignment_status` in (_utf8mb4'active',_utf8mb4'ended',_utf8mb4'cancelled')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `teaching_assignments`
--

LOCK TABLES `teaching_assignments` WRITE;
/*!40000 ALTER TABLE `teaching_assignments` DISABLE KEYS */;
/*!40000 ALTER TABLE `teaching_assignments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `team_memberships`
--

DROP TABLE IF EXISTS `team_memberships`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `team_memberships` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `team_id` bigint unsigned NOT NULL,
  `account_id` bigint unsigned NOT NULL,
  `membership_role` varchar(30) NOT NULL DEFAULT 'member',
  `membership_status` varchar(20) NOT NULL DEFAULT 'active',
  `joined_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `ended_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_team_account_membership` (`team_id`,`account_id`),
  KEY `ix_team_membership_account` (`account_id`,`membership_status`),
  CONSTRAINT `fk_team_membership_account` FOREIGN KEY (`account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_team_membership_team` FOREIGN KEY (`team_id`) REFERENCES `teams` (`id`),
  CONSTRAINT `ck_team_membership_role` CHECK ((`membership_role` in (_utf8mb4'member',_utf8mb4'lead',_utf8mb4'manager'))),
  CONSTRAINT `ck_team_membership_status` CHECK ((`membership_status` in (_utf8mb4'invited',_utf8mb4'active',_utf8mb4'left',_utf8mb4'removed')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `team_memberships`
--

LOCK TABLES `team_memberships` WRITE;
/*!40000 ALTER TABLE `team_memberships` DISABLE KEYS */;
/*!40000 ALTER TABLE `team_memberships` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `teams`
--

DROP TABLE IF EXISTS `teams`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `teams` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `institution_id` bigint unsigned NOT NULL,
  `name` varchar(150) NOT NULL,
  `description` text,
  `created_by_account_id` bigint unsigned NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_team_institution_name` (`institution_id`,`name`),
  KEY `fk_team_creator` (`created_by_account_id`),
  CONSTRAINT `fk_team_creator` FOREIGN KEY (`created_by_account_id`) REFERENCES `accounts` (`id`),
  CONSTRAINT `fk_team_institution` FOREIGN KEY (`institution_id`) REFERENCES `institutions` (`id`),
  CONSTRAINT `ck_team_status` CHECK ((`status` in (_utf8mb4'active',_utf8mb4'archived')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `teams`
--

LOCK TABLES `teams` WRITE;
/*!40000 ALTER TABLE `teams` DISABLE KEYS */;
/*!40000 ALTER TABLE `teams` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_preferences`
--

DROP TABLE IF EXISTS `user_preferences`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_preferences` (
  `account_id` bigint unsigned NOT NULL,
  `accent_color` varchar(16) NOT NULL DEFAULT 'teal',
  `font_size` varchar(16) NOT NULL DEFAULT 'default',
  `interface_density` varchar(16) NOT NULL DEFAULT 'comfortable',
  `theme_mode` varchar(16) NOT NULL DEFAULT 'system',
  `email_notifications_enabled` tinyint(1) NOT NULL DEFAULT '1',
  `notification_preferences` json NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`account_id`),
  CONSTRAINT `fk_user_preferences_account` FOREIGN KEY (`account_id`) REFERENCES `accounts` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_preferences`
--

LOCK TABLES `user_preferences` WRITE;
/*!40000 ALTER TABLE `user_preferences` DISABLE KEYS */;
INSERT INTO `user_preferences` VALUES (2,'neutral','default','comfortable','system',1,'{}','2026-10-25 08:23:37','2026-10-25 08:25:51'),(73001,'neutral','default','comfortable','system',1,'{}','2026-10-25 10:28:10','2026-10-25 11:05:59');
/*!40000 ALTER TABLE `user_preferences` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping events for database 'kairos'
--

--
-- Dumping routines for database 'kairos'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-10-25 16:46:30
