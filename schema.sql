-- ============================================================================
-- CompassIQ — AI-Powered Customer Support Ticket Management System
-- Database Schema & Seed Data (SQLite3)
-- ============================================================================

-- Drop tables if they already exist in reverse order of foreign keys
DROP TABLE IF EXISTS ticket_replies;
DROP TABLE IF EXISTS ticket_similar_matches;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS users;

-- ----------------------------------------------------------------------------
-- 1. Users Table
-- ----------------------------------------------------------------------------
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'customer' CHECK(role IN ('customer', 'agent', 'admin')),
    department TEXT DEFAULT 'None' CHECK(department IN ('Technical', 'Billing', 'Account', 'General Inquiry', 'None')),
    bill_no_product_id TEXT,
    account_status TEXT DEFAULT 'PENDING' CHECK(account_status IN ('PENDING', 'APPROVED', 'REJECTED', 'BANNED')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 2. Tickets Table
-- ----------------------------------------------------------------------------
CREATE TABLE tickets (
    ticket_id TEXT PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    predicted_category TEXT NOT NULL CHECK(predicted_category IN ('Technical', 'Billing', 'Account', 'General Inquiry', 'Fraud')),
    predicted_priority TEXT NOT NULL CHECK(predicted_priority IN ('Low', 'Medium', 'High', 'Critical')),
    assigned_department TEXT NOT NULL CHECK(assigned_department IN ('Technical', 'Billing', 'Account', 'General Inquiry', 'Admin_Fraud')),
    status TEXT DEFAULT 'Submitted' CHECK(status IN ('Submitted', 'Under Review', 'In Progress', 'Resolved', 'Closed')),
    assigned_agent_id INTEGER,
    resolution_notes TEXT,
    satisfaction_score INTEGER CHECK(satisfaction_score BETWEEN 1 AND 5),
    customer_feedback TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME,
    CONSTRAINT fk_ticket_customer FOREIGN KEY (customer_id) REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT fk_ticket_agent FOREIGN KEY (assigned_agent_id) REFERENCES users (user_id) ON DELETE SET NULL
);

-- ----------------------------------------------------------------------------
-- 3. Ticket Similar Matches Table
-- ----------------------------------------------------------------------------
CREATE TABLE ticket_similar_matches (
    match_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT NOT NULL,
    similar_ticket_ref_id TEXT NOT NULL,
    similarity_score REAL NOT NULL,
    similar_subject TEXT NOT NULL,
    similar_description TEXT NOT NULL,
    historical_resolution_hours INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_similar_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- 4. Ticket Replies Table
-- ----------------------------------------------------------------------------
CREATE TABLE ticket_replies (
    reply_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT NOT NULL,
    sender_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reply_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id) ON DELETE CASCADE,
    CONSTRAINT fk_reply_sender FOREIGN KEY (sender_id) REFERENCES users (user_id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- Seed Data
-- Demo Credentials (Password: Admin@Compass2026 for admin, Tech@Support2026 for tech support, etc.)
-- ----------------------------------------------------------------------------

INSERT INTO users (user_id, full_name, email, password_hash, role, department, bill_no_product_id, account_status) VALUES
-- Administrator
(1, 'System Administrator', 'admin@compassiq.com', 'scrypt:32768:8:1$MCtblGWUGAD1EsDz$8c86480446d9585633ce60fcab1c8069fa3206b0fdcbd3aa7124166a7508fa5eac3d85b2e269c27e44bcd47fdaa18de2c6d1b3d63c20b8ac1a102c4879be7b25', 'admin', 'None', 'ADMIN-ROOT', 'APPROVED'),

-- Department Support Agents
(2, 'Technical Support Agent', 'tech.support@compassiq.com', 'scrypt:32768:8:1$41LC77CMSkCZvn1S$52aec941b3e86314c172e1ca10999edade497e4b2a87074d951d0c59010c3aa330a0a4ffe279a4a5d4a23a9911070da9135c5a955300937f60ac4a825644acdc', 'agent', 'Technical', 'EMP-TECH-101', 'APPROVED'),
(3, 'Billing Support Agent', 'billing.support@compassiq.com', 'scrypt:32768:8:1$y6WhHAO3i5UjLD1S$6fb1676d0ac0d747ee19cfe107cd7c1a133a90a3d2adbdba5b6a9911c8289397cc6d1e40a697eb0a635af541483e082c5080f2b16c0dff52745d6c2dd86c17a5', 'agent', 'Billing', 'EMP-BILL-202', 'APPROVED'),

-- Customer Accounts
(4, 'Alex Morgan', 'alex.morgan@customer.com', 'scrypt:32768:8:1$wUlaa4YY8azRrBAR$595e72001b6675635945049fa4b63bc8a022c447f5cc2013c375461cc0233bf1ca150c664ea078847b956614b860041a506e07c9709d23b1db0b44df95ae181c', 'customer', 'None', 'INV-2026-8801', 'APPROVED'),

-- Pending Verification Customer
(5, 'Jordan Lee', 'jordan.lee@customer.com', 'scrypt:32768:8:1$4YEsKGVvgicyo5jF$91f462f09be44df01ca3a665e4959a28986b848a6a5a5c07dfaba51b05d893120ce4f7dfcc2de0fadbbcbd09b0c2468fe7483e28912f2073b2bfc9797fd3fb40', 'customer', 'None', 'INV-2026-9942', 'PENDING');

-- Seed Sample Tickets
INSERT INTO tickets (ticket_id, customer_id, subject, description, predicted_category, predicted_priority, assigned_department, status, assigned_agent_id, resolution_notes, satisfaction_score, customer_feedback, created_at, resolved_at) VALUES
('TKT-100001', 4, 'Cloud sync fails with Error Code 502', 'Hi team, whenever I upload data larger than 50MB, the desktop app crashes with a 502 gateway error.', 'Technical', 'High', 'Technical', 'In Progress', 2, NULL, NULL, NULL, datetime('now', '-2 days'), NULL),
('TKT-100002', 4, 'Charged twice for Pro annual subscription renewal', 'I noticed two identical charges of $199 on my credit card statement for invoice #88912.', 'Billing', 'High', 'Billing', 'Resolved', 3, 'Processed refund for duplicate charge via Stripe gateway. Reference: RFD-88219.', 5, 'Quick response and smooth refund! Thank you.', datetime('now', '-5 days'), datetime('now', '-4 days')),
('TKT-100003', 4, 'How do I add team members to our workspace?', 'Looking for documentation or instructions on adding 5 new team members with editor permissions.', 'General Inquiry', 'Low', 'General Inquiry', 'Resolved', NULL, 'Sent step-by-step invite guide and granted license seats.', 5, 'Great support, solved within 20 mins!', datetime('now', '-7 days'), datetime('now', '-7 days'));

-- Seed Sample Similar Matches for TKT-100001
INSERT INTO ticket_similar_matches (ticket_id, similar_ticket_ref_id, similarity_score, similar_subject, similar_description, historical_resolution_hours) VALUES
('TKT-100001', 'HIST-40192', 88.50, 'Data not syncing - Cloud connection drop', 'Desktop application crashes during heavy upload payloads above 40MB.', 4),
('TKT-100001', 'HIST-31102', 82.10, 'Sync error 502 Gateway Timeout on large batch', 'Encountering 502 gateway timeouts when transferring binary media files.', 6),
('TKT-100001', 'HIST-19044', 76.40, 'Application freeze during sync operation', 'Sync process hangs on 100% and does not complete database write.', 8);

-- Seed Sample Replies for TKT-100001
INSERT INTO ticket_replies (reply_id, ticket_id, sender_id, message, created_at) VALUES
(1, 'TKT-100001', 4, 'Hi team, whenever I upload data larger than 50MB, the desktop app crashes with a 502 gateway error.', datetime('now', '-2 days')),
(2, 'TKT-100001', 2, 'Hello Alex, thank you for reaching out. We have identified a potential chunk-size limit in our reverse proxy. We are deploying a patch to test server now.', datetime('now', '-1 days')),
(3, 'TKT-100001', 4, 'Understood, let me know when I can re-test the upload.', datetime('now', '-12 hours'));