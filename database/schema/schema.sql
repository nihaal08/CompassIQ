-- ============================================================================
-- CompassIQ — AI-Powered Customer Support Ticket Management System
-- Database Schema (SQLite3) - Chen ER Diagram Implementation
-- ============================================================================

-- Drop tables if they already exist in reverse order of foreign keys
DROP TABLE IF EXISTS ticket_replies;
DROP TABLE IF EXISTS ticket_similar_matches;
DROP TABLE IF EXISTS complaints;
DROP TABLE IF EXISTS department_agents;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS departments;

-- ----------------------------------------------------------------------------
-- 1. Departments Table (DEPARTMENT Entity)
-- ----------------------------------------------------------------------------
CREATE TABLE departments (
    deptid INTEGER PRIMARY KEY AUTOINCREMENT,
    deptname TEXT NOT NULL UNIQUE,
    sla_target_hours INTEGER DEFAULT 24
);

-- Seed default departments
INSERT INTO departments (deptid, deptname, sla_target_hours) VALUES
(1, 'Technical Support', 12),
(2, 'Billing Support', 24),
(3, 'Account Support', 24),
(4, 'General Inquiry', 48),
(5, 'Fraud & Security', 12);

-- ----------------------------------------------------------------------------
-- 2. Customers Table (CUSTOMER Entity - External Clients Only)
-- ----------------------------------------------------------------------------
CREATE TABLE customers (
    custid INTEGER PRIMARY KEY AUTOINCREMENT,
    custname TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    phone_no TEXT,
    account_status TEXT DEFAULT 'APPROVED' CHECK(account_status IN ('PENDING', 'APPROVED', 'REJECTED', 'BANNED')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 3. Department Agents Table (Internal Staff & Administrators)
-- ----------------------------------------------------------------------------
CREATE TABLE department_agents (
    agent_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    deptid INTEGER REFERENCES departments(deptid) ON DELETE SET NULL,
    role TEXT DEFAULT 'agent' CHECK(role IN ('agent', 'admin')),
    account_status TEXT DEFAULT 'APPROVED' CHECK(account_status IN ('PENDING', 'APPROVED', 'BANNED')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 4. Complaints Table (COMPLAINT Entity)
-- ----------------------------------------------------------------------------
CREATE TABLE complaints (
    ticketno TEXT PRIMARY KEY,
    custid INTEGER NOT NULL REFERENCES customers(custid) ON DELETE CASCADE,
    deptid INTEGER NOT NULL REFERENCES departments(deptid) ON DELETE RESTRICT,
    assigned_agent_id INTEGER REFERENCES department_agents(agent_id) ON DELETE SET NULL,
    submitdate DATETIME DEFAULT CURRENT_TIMESTAMP,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    predicted_priority TEXT CHECK(predicted_priority IN ('Low', 'Medium', 'High', 'Critical')),
    status TEXT DEFAULT 'Submitted' CHECK(status IN ('Submitted', 'Under Review', 'In Progress', 'Resolved', 'Closed')),
    resolved_at DATETIME DEFAULT NULL,
    resolution_notes TEXT DEFAULT NULL,
    satisfaction_score INTEGER DEFAULT NULL CHECK(satisfaction_score BETWEEN 1 AND 5),
    customer_feedback TEXT DEFAULT NULL
);

-- ----------------------------------------------------------------------------
-- 5. Ticket Similar Matches Table (for AI Similar Historical Tickets)
-- ----------------------------------------------------------------------------
CREATE TABLE ticket_similar_matches (
    match_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticketno TEXT NOT NULL,
    similar_ticket_ref_id TEXT NOT NULL,
    similarity_score REAL NOT NULL,
    similar_subject TEXT NOT NULL,
    similar_description TEXT NOT NULL,
    historical_resolution_hours INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_similar_ticket FOREIGN KEY (ticketno) REFERENCES complaints(ticketno) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- 6. Ticket Replies Table (for conversation threads)
-- ----------------------------------------------------------------------------
CREATE TABLE ticket_replies (
    reply_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticketno TEXT NOT NULL,
    sender_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reply_ticket FOREIGN KEY (ticketno) REFERENCES complaints(ticketno) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- Seed Demo Accounts
-- Demo Credentials: All accounts use password "password123"
-- ----------------------------------------------------------------------------

-- Department Agents & Admin (staff accounts)
-- Admin Account (no department assignment)
INSERT INTO department_agents (agent_name, email, password, role, account_status) VALUES
('System Administrator', 'admin@compassiq.com', 'scrypt:32768:8:1$MCtblGWUGAD1EsDz$8c86480446d9585633ce60fcab1c8069fa3206b0fdcbd3aa7124166a7508fa5eac3d85b2e269c27e44bcd47fdaa18de2c6d1b3d63c20b8ac1a102c4879be7b25', 'admin', 'APPROVED');

-- Technical Support Agent (deptid = 1)
INSERT INTO department_agents (agent_name, email, password, deptid, role, account_status) VALUES
('Technical Support Agent', 'tech.support@compassiq.com', 'scrypt:32768:8:1$41LC77CMSkCZvn1S$52aec941b3e86314c172e1ca10999edade497e4b2a87074d951d0c59010c3aa330a0a4ffe279a4a5d4a23a9911070da9135c5a955300937f60ac4a825644acdc', 1, 'agent', 'APPROVED');

-- Billing Support Agent (deptid = 2)
INSERT INTO department_agents (agent_name, email, password, deptid, role, account_status) VALUES
('Billing Support Agent', 'billing.support@compassiq.com', 'scrypt:32768:8:1$y6WhHAO3i5UjLD1S$6fb1676d0ac0d747ee19cfe107cd7c1a133a90a3d2adbdba5b6a9911c8289397cc6d1e40a697eb0a635af541483e082c5080f2b16c0dff52745d6c2dd86c17a5', 2, 'agent', 'APPROVED');

-- Account Support Agent (deptid = 3)
INSERT INTO department_agents (agent_name, email, password, deptid, role, account_status) VALUES
('Account Support Agent', 'account.support@compassiq.com', 'scrypt:32768:8:1$UUYqos2NaN5hhfvQ$5f1a5221445117bd5462e63e8ba9fe9e2a2ae0c64a13a41ebc61b2caa4b7348abc400d7d1a558632a8b7ddda963e8f9d6b36bfcf08506bb134ab54eee7dfd9ce', 3, 'agent', 'APPROVED');

-- General Inquiry Agent (deptid = 4)
INSERT INTO department_agents (agent_name, email, password, deptid, role, account_status) VALUES
('General Inquiry Agent', 'general.support@compassiq.com', 'scrypt:32768:8:1$uy4tAoA7SF6xoE0R$707ce097767ad179ae509d3d62703cb2a0322b01f695bb816481ed8880de737dbc61b08e5b56dab61de932c11e5e3866c1576c97d1501c2892ab12bdbe88571a', 4, 'agent', 'APPROVED');

-- Fraud & Security Agent (deptid = 5)
INSERT INTO department_agents (agent_name, email, password, deptid, role, account_status) VALUES
('Fraud & Security Agent', 'fraud.agent@compassiq.com', 'scrypt:32768:8:1$uy4tAoA7SF6xoE0R$707ce097767ad179ae509d3d62703cb2a0322b01f695bb816481ed8880de737dbc61b08e5b56dab61de932c11e5e3866c1576c97d1501c2892ab12bdbe88571a', 5, 'agent', 'APPROVED');

-- Customer Accounts (external clients)
-- Test Customer
INSERT INTO customers (custname, email, password, phone_no, account_status) VALUES
('Alex Morgan', 'alex.morgan@customer.com', 'scrypt:32768:8:1$wUlaa4YY8azRrBAR$595e72001b6675635945049fa4b63bc8a022c447f5cc2013c375461cc0233bf1ca150c664ea078847b956614b860041a506e07c9709d23b1db0b44df95ae181c', '9876543210', 'APPROVED');
