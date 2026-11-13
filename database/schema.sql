CREATE DATABASE IF NOT EXISTS smartflow;
USE smartflow;

CREATE TABLE IF NOT EXISTS traffic_readings (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    road          VARCHAR(10)  NOT NULL,
    vehicle_count INT          NOT NULL,
    density_score DECIMAL(5,1) NOT NULL,
    level         VARCHAR(10)  NOT NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_traffic_time (created_at)
);

CREATE TABLE IF NOT EXISTS signal_history (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    road         VARCHAR(10)  NOT NULL,
    phase        VARCHAR(10)  NOT NULL,
    duration_sec DECIMAL(5,1) NOT NULL,
    is_emergency BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_signal_time (created_at)
);

CREATE TABLE IF NOT EXISTS emergency_events (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    road         VARCHAR(10) NOT NULL,
    vehicle_kind VARCHAR(20) NULL,
    event_type   VARCHAR(20) NOT NULL,
    created_at   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_emergency_time (created_at)
);

CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(200) NOT NULL,
    role          VARCHAR(20)  NOT NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    username   VARCHAR(50)  NOT NULL,
    role       VARCHAR(20)  NULL,
    action     VARCHAR(30)  NOT NULL,
    detail     VARCHAR(200) NULL,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_time (created_at)
);