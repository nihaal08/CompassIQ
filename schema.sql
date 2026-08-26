-- ============================================================================
-- CompassIQ — AI-Powered Customer Support Ticket Management System
-- Database Schema & Seed Data
-- ============================================================================

CREATE DATABASE IF NOT EXISTS compassiq_db;
USE compassiq_db;

-- Drop tables if they already exist in reverse order of foreign keys
DROP TABLE IF EXISTS ticket_replies;
DROP TABLE IF EXISTS ticket_similar_matches;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS users;

-- ----------------------------------------------------------------------------
-- 1. Users Table
-- ----------------------------------------------------------------------------
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('customer', 'agent', 'admin') NOT NULL DEFAULT 'customer',
    department ENUM('Technical', 'Billing', 'Account', 'General Inquiry', 'None') DEFAULT 'None',
    bill_no_product_id VARCHAR(100) NULL,
    account_status ENUM('PENDING', 'APPROVED', 'REJECTED', 'BANNED') DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 2. Tickets Table
-- ----------------------------------------------------------------------------
CREATE TABLE tickets (
    ticket_id VARCHAR(30) PRIMARY KEY,
    customer_id INT NOT NULL,
    subject VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    predicted_category ENUM('Technical', 'Billing', 'Account', 'General Inquiry', 'Fraud') NOT NULL,
    predicted_priority ENUM('Low', 'Medium', 'High', 'Critical') NOT NULL,
    assigned_department ENUM('Technical', 'Billing', 'Account', 'General Inquiry', 'Admin_Fraud') NOT NULL,
    status ENUM('Submitted', 'Under Review', 'In Progress', 'Resolved', 'Closed') DEFAULT 'Submitted',
    assigned_agent_id INT NULL,
    resolution_notes TEXT NULL,
    satisfaction_score INT NULL CHECK (satisfaction_score BETWEEN 1 AND 5),
    customer_feedback TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    CONSTRAINT fk_ticket_customer FOREIGN KEY (customer_id) REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT fk_ticket_agent FOREIGN KEY (assigned_agent_id) REFERENCES users (user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 3. Ticket Similar Matches Table
-- ----------------------------------------------------------------------------
CREATE TABLE ticket_similar_matches (
    match_id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id VARCHAR(30) NOT NULL,
    similar_ticket_ref_id VARCHAR(30) NOT NULL,
    similarity_score DECIMAL(5, 2) NOT NULL,
    similar_subject VARCHAR(255) NOT NULL,
    similar_description TEXT NOT NULL,
    historical_resolution_hours INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_similar_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 4. Ticket Replies Table
-- ----------------------------------------------------------------------------
CREATE TABLE ticket_replies (
    reply_id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id VARCHAR(30) NOT NULL,
    sender_id INT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reply_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id) ON DELETE CASCADE,
    CONSTRAINT fk_reply_sender FOREIGN KEY (sender_id) REFERENCES users (user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- Seed Data
-- Default passwords:
-- Admin:    admin123
-- Agents:   agent123
-- Customer: customer123
-- ----------------------------------------------------------------------------

INSERT INTO users (user_id, full_name, email, password_hash, role, department, bill_no_product_id, account_status) VALUES
-- Admin
(1, 'System Administrator', 'admin@compassiq.com', 'scrypt:32768:8:1$W7L9N9M4o4xHqO1W$d83a1aa561cae18ef55716c525f696614138e6840ff636fe597bc8a7a974b65551f337f7dafb9bb46797203b578fa2cba4a8f9eb9d597ae33feae7f80db3ff85', 'admin', 'None', 'ADMIN-ROOT', 'APPROVED'),

-- Department Agents
(2, 'Alex Carter (Tech Lead)', 'agent.tech@compassiq.com', 'scrypt:32768:8:1$u7C5N0Q2p8yRqL4T$b03ce153835f8e52a5501869e5d4cb6bf71eb1b9b1e95ba1a646c05d762fa5ea6973ee6796c56ce6bbd7c67dfb6ef55ca7b659c25cf62a4fa9449f6ea9bbfbd8', 'agent', 'Technical', 'EMP-TECH-101', 'APPROVED'),
(3, 'Sarah Jenkins (Billing)', 'agent.billing@compassiq.com', 'scrypt:32768:8:1$u7C5N0Q2p8yRqL4T$b03ce153835f8e52a5501869e5d4cb6bf71eb1b9b1e95ba1a646c05d762fa5ea6973ee6796c56ce6bbd7c67dfb6ef55ca7b659c25cf62a4fa9449f6ea9bbfbd8', 'agent', 'Billing', 'EMP-BILL-202', 'APPROVED'),
(4, 'Marcus Vance (Account)', 'agent.account@compassiq.com', 'scrypt:32768:8:1$u7C5N0Q2p8yRqL4T$b03ce153835f8e52a5501869e5d4cb6bf71eb1b9b1e95ba1a646c05d762fa5ea6973ee6796c56ce6bbd7c67dfb6ef55ca7b659c25cf62a4fa9449f6ea9bbfbd8', 'agent', 'Account', 'EMP-ACC-303', 'APPROVED'),
(5, 'Elena Gomez (Inquiry)', 'agent.inquiry@compassiq.com', 'scrypt:32768:8:1$u7C5N0Q2p8yRqL4T$b03ce153835f8e52a5501869e5d4cb6bf71eb1b9b1e95ba1a646c05d762fa5ea6973ee6796c56ce6bbd7c67dfb6ef55ca7b659c25cf62a4fa9449f6ea9bbfbd8', 'agent', 'General Inquiry', 'EMP-INQ-404', 'APPROVED'),

-- Sample Verified Customer
(6, 'David Miller', 'david.miller@example.com', 'scrypt:32768:8:1$k4P1R8T3w7vXyZ9M$1f6d65f17cf498d98d5c48ec09b30c14b2d1ca6f1bc4e16d48ff04f144d18ec993510eecff3697e8838a3c87f0b9f939e6c6b32ea6ecf6e8aa78997a47eb866d', 'customer', 'None', 'INV-2025-88912', 'APPROVED'),

-- Sample Pending Customer (For Verification Queue Testing)
(7, 'Samantha Reed', 'samantha.reed@example.com', 'scrypt:32768:8:1$k4P1R8T3w7vXyZ9M$1f6d65f17cf498d98d5c48ec09b30c14b2d1ca6f1bc4e16d48ff04f144d18ec993510eecff3697e8838a3c87f0b9f939e6c6b32ea6ecf6e8aa78997a47eb866d', 'customer', 'None', 'PRD-OCT-99014', 'PENDING');

-- Seed Sample Tickets
INSERT INTO tickets (ticket_id, customer_id, subject, description, predicted_category, predicted_priority, assigned_department, status, assigned_agent_id, resolution_notes, satisfaction_score, customer_feedback, created_at, resolved_at) VALUES
('TKT-100001', 6, 'Cloud sync fails with Error Code 502', 'Hi team, whenever I upload data larger than 50MB, the desktop app crashes with a 502 gateway error.', 'Technical', 'High', 'Technical', 'In Progress', 2, NULL, NULL, NULL, NOW() - INTERVAL 2 DAY, NULL),
('TKT-100002', 6, 'Charged twice for Pro annual subscription renewal', 'I noticed two identical charges of $199 on my credit card statement for invoice #88912.', 'Billing', 'High', 'Billing', 'Resolved', 3, 'Processed refund for duplicate charge via Stripe gateway. Reference: RFD-88219.', 5, 'Quick response and smooth refund! Thank you Sarah.', NOW() - INTERVAL 5 DAY, NOW() - INTERVAL 4 DAY),
('TKT-100003', 6, 'How do I add team members to our workspace?', 'Looking for documentation or instructions on adding 5 new team members with editor permissions.', 'General Inquiry', 'Low', 'General Inquiry', 'Resolved', 5, 'Sent step-by-step invite guide and granted license seats.', 5, 'Great support, solved within 20 mins!', NOW() - INTERVAL 7 DAY, NOW() - INTERVAL 7 DAY);

-- Seed Sample Similar Matches for TKT-100001
INSERT INTO ticket_similar_matches (ticket_id, similar_ticket_ref_id, similarity_score, similar_subject, similar_description, historical_resolution_hours) VALUES
('TKT-100001', 'HIST-40192', 88.50, 'Data not syncing - Cloud connection drop', 'Desktop application crashes during heavy upload payloads above 40MB.', 4),
('TKT-100001', 'HIST-31102', 82.10, 'Sync error 502 Gateway Timeout on large batch', 'Encountering 502 gateway timeouts when transferring binary media files.', 6),
('TKT-100001', 'HIST-19044', 76.40, 'Application freeze during sync operation', 'Sync process hangs on 100% and does not complete database write.', 8);

-- Seed Sample Replies for TKT-100001
INSERT INTO ticket_replies (reply_id, ticket_id, sender_id, message, created_at) VALUES
('TKT-100001', 6, 'Hi team, whenever I upload data larger than 50MB, the desktop app crashes with a 502 gateway error.', NOW() - INTERVAL 2 DAY),
('TKT-100001', 2, 'Hello David, thank you for reaching out. We have identified a potential chunk-size limit in our reverse proxy. We are deploying a patch to test server now.', NOW() - INTERVAL 1 DAY),
('TKT-100001', 6, 'Understood, let me know when I can re-test the upload.', NOW() - INTERVAL 12 HOUR);
