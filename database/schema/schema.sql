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
-- Demo Credentials:
-- - Admin: admin@compassiq.com / Admin@Compass2026
-- - Technical: tech.support@compassiq.com / Tech@Support2026
-- - Billing: billing.support@compassiq.com / Billing@Support2026
-- - Account: account.support@compassiq.com / Account@Support2026
-- - General Inquiry: general.support@compassiq.com / General@Support2026
-- - Customer: alex.morgan@customer.com / Customer@Demo2026
-- ----------------------------------------------------------------------------

INSERT INTO users (user_id, full_name, email, password_hash, role, department, bill_no_product_id, account_status) VALUES
(1, 'System Administrator', 'admin@compassiq.com', 'scrypt:32768:8:1$MCtblGWUGAD1EsDz$8c86480446d9585633ce60fcab1c8069fa3206b0fdcbd3aa7124166a7508fa5eac3d85b2e269c27e44bcd47fdaa18de2c6d1b3d63c20b8ac1a102c4879be7b25', 'admin', 'None', 'ADMIN-ROOT', 'APPROVED'),
(2, 'Technical Support Agent', 'tech.support@compassiq.com', 'scrypt:32768:8:1$41LC77CMSkCZvn1S$52aec941b3e86314c172e1ca10999edade497e4b2a87074d951d0c59010c3aa330a0a4ffe279a4a5d4a23a9911070da9135c5a955300937f60ac4a825644acdc', 'agent', 'Technical', 'EMP-TECH-101', 'APPROVED'),
(3, 'Billing Support Agent', 'billing.support@compassiq.com', 'scrypt:32768:8:1$y6WhHAO3i5UjLD1S$6fb1676d0ac0d747ee19cfe107cd7c1a133a90a3d2adbdba5b6a9911c8289397cc6d1e40a697eb0a635af541483e082c5080f2b16c0dff52745d6c2dd86c17a5', 'agent', 'Billing', 'EMP-BILL-202', 'APPROVED'),
(4, 'Sarah Connor', 'account.support@compassiq.com', 'scrypt:32768:8:1$UUYqos2NaN5hhfvQ$5f1a5221445117bd5462e63e8ba9fe9e2a2ae0c64a13a41ebc61b2caa4b7348abc400d7d1a558632a8b7ddda963e8f9d6b36bfcf08506bb134ab54eee7dfd9ce', 'agent', 'Account', 'EMP-ACCT-303', 'APPROVED'),
(5, 'David Miller', 'general.support@compassiq.com', 'scrypt:32768:8:1$uy4tAoA7SF6xoE0R$707ce097767ad179ae509d3d62703cb2a0322b01f695bb816481ed8880de737dbc61b08e5b56dab61de932c11e5e3866c1576c97d1501c2892ab12bdbe88571a', 'agent', 'General Inquiry', 'EMP-GEN-404', 'APPROVED'),
(6, 'Alex Morgan', 'alex.morgan@customer.com', 'scrypt:32768:8:1$wUlaa4YY8azRrBAR$595e72001b6675635945049fa4b63bc8a022c447f5cc2013c375461cc0233bf1ca150c664ea078847b956614b860041a506e07c9709d23b1db0b44df95ae181c', 'customer', 'None', 'INV-2026-8801', 'APPROVED'),
(7, 'Jordan Lee', 'jordan.lee@customer.com', 'scrypt:32768:8:1$4YEsKGVvgicyo5jF$91f462f09be44df01ca3a665e4959a28986b848a6a5a5c07dfaba51b05d893120ce4f7dfcc2de0fadbbcbd09b0c2468fe7483e28912f2073b2bfc9797fd3fb40', 'customer', 'None', 'INV-2026-9942', 'PENDING');

-- Seed Sample Tickets - Technical Support
INSERT INTO tickets (ticket_id, customer_id, subject, description, predicted_category, predicted_priority, assigned_department, status, assigned_agent_id, resolution_notes, satisfaction_score, customer_feedback, created_at, resolved_at) VALUES
('TKT-100001', 6, 'Cloud sync fails with Error Code 502', 'Hi team, whenever I upload data larger than 50MB, the desktop app crashes with a 502 gateway error.', 'Technical', 'High', 'Technical', 'In Progress', 2, NULL, NULL, NULL, '2026-01-30 00:00:00', NULL),
('TKT-100002', 6, 'Kernel panic and continuous boot loop after firmware v2.4 update', 'After installing the latest firmware update v2.4, my device enters a continuous boot loop with kernel panic errors. Cannot access recovery mode.', 'Technical', 'Critical', 'Technical', 'Submitted', NULL, NULL, NULL, NULL, '2026-01-31 00:00:00', NULL),
('TKT-100003', 6, 'Bluetooth audio stutter when connected beyond 5 meters', 'Bluetooth audio connection works fine within close range but experiences severe stuttering and dropouts when device is more than 5 meters away.', 'Technical', 'Low', 'Technical', 'Resolved', 2, 'Updated Bluetooth driver firmware to v4.2.1 - improved connection stability.', 4, 'Audio quality improved significantly after driver update.', '2026-01-22 00:00:00', '2026-01-23 00:00:00');

-- Seed Sample Tickets - Billing Support
INSERT INTO tickets (ticket_id, customer_id, subject, description, predicted_category, predicted_priority, assigned_department, status, assigned_agent_id, resolution_notes, satisfaction_score, customer_feedback, created_at, resolved_at) VALUES
('TKT-200001', 6, 'Charged twice for annual enterprise subscription renewal', 'I noticed two identical charges of $1,199 on my corporate credit card for the annual enterprise subscription renewal. Please refund the duplicate charge immediately.', 'Billing', 'Critical', 'Billing', 'Submitted', NULL, NULL, NULL, NULL, '2026-01-29 00:00:00', NULL),
('TKT-200002', 6, 'Invoice PDF not generating GST breakdown', 'When downloading invoice PDFs, the GST tax breakdown section is not appearing. Need detailed GST breakdown for accounting purposes and tax filing.', 'Billing', 'Medium', 'Billing', 'In Progress', 3, NULL, NULL, NULL, '2026-01-27 00:00:00', NULL),
('TKT-200003', 6, 'Update credit card expiration date and billing address', 'Need to update the credit card expiration date for our corporate account and change the billing address to our new office location.', 'Billing', 'Low', 'Billing', 'Resolved', 3, 'Updated payment method and billing address in billing system.', 5, 'Quick and efficient update process.', '2026-01-18 00:00:00', '2026-01-19 00:00:00');

-- Seed Sample Tickets - Account Support
INSERT INTO tickets (ticket_id, customer_id, subject, description, predicted_category, predicted_priority, assigned_department, status, assigned_agent_id, resolution_notes, satisfaction_score, customer_feedback, created_at, resolved_at) VALUES
('TKT-300001', 6, 'Two-factor authentication SMS OTP never received on international number', 'I am traveling internationally and not receiving SMS OTP codes for 2FA authentication. My local carrier works but your SMS service seems blocked for my country code.', 'Account', 'High', 'Account', 'Submitted', 4, NULL, NULL, NULL, '2026-01-28 00:00:00', NULL),
('TKT-300002', 6, 'Request to transfer account ownership to new team admin', 'Our current account admin is leaving the company. Need to transfer full account ownership and administrative privileges to our new team lead.', 'Account', 'Low', 'Account', 'Resolved', 4, 'Account ownership transferred successfully with all permissions preserved.', 5, 'Smooth transfer process, no data loss.', '2026-01-11 00:00:00', '2026-01-12 00:00:00');

-- Seed Sample Tickets - General Inquiry
INSERT INTO tickets (ticket_id, customer_id, subject, description, predicted_category, predicted_priority, assigned_department, status, assigned_agent_id, resolution_notes, satisfaction_score, customer_feedback, created_at, resolved_at) VALUES
('TKT-400001', 6, 'Inquiry regarding standard replacement warranty coverage period', 'What is the standard warranty coverage period for hardware replacements? Need to know if our devices are still under warranty for potential replacement.', 'General Inquiry', 'Low', 'General Inquiry', 'In Progress', 5, NULL, NULL, NULL, '2026-01-26 00:00:00', NULL),
('TKT-400002', 6, 'API rate limits and documentation for webhooks integration', 'We are building custom integrations and need information about API rate limits, webhook payload formats, and authentication methods for third-party app development.', 'General Inquiry', 'Medium', 'General Inquiry', 'Submitted', 5, NULL, NULL, NULL, '2026-01-30 00:00:00', NULL);

-- Seed Sample Tickets - Fraud / Security Queue
INSERT INTO tickets (ticket_id, customer_id, subject, description, predicted_category, predicted_priority, assigned_department, status, assigned_agent_id, resolution_notes, satisfaction_score, customer_feedback, created_at, resolved_at) VALUES
('TKT-500001', 6, 'Suspicious unrecognized login attempt from IP range in Eastern Europe', 'Received security alert about login attempt from IP address 185.14.x.x in Eastern Europe. I have never traveled there and do not recognize this activity. Please investigate potential account compromise.', 'Fraud', 'Critical', 'Admin_Fraud', 'Submitted', NULL, NULL, NULL, NULL, '2026-02-01 10:00:00', NULL),
('TKT-500002', 6, 'Unauthorized refund claim submitted with forged invoice number', 'Someone submitted a refund claim using forged invoice number INV-FAKE-9999. I never made this purchase and this appears to be fraudulent activity targeting our account.', 'Fraud', 'Critical', 'Admin_Fraud', 'In Progress', 1, 'Investigating fraudulent claim - account temporarily secured.', NULL, NULL, '2026-01-30 00:00:00', NULL);

-- Seed Sample Similar Matches for TKT-100001 (Technical)
INSERT INTO ticket_similar_matches (ticket_id, similar_ticket_ref_id, similarity_score, similar_subject, similar_description, historical_resolution_hours) VALUES
('TKT-100001', 'HIST-40192', 88.50, 'Data not syncing - Cloud connection drop', 'Desktop application crashes during heavy upload payloads above 40MB.', 4),
('TKT-100001', 'HIST-31102', 82.10, 'Sync error 502 Gateway Timeout on large batch', 'Encountering 502 gateway timeouts when transferring binary media files.', 6),
('TKT-100001', 'HIST-19044', 76.40, 'Application freeze during sync operation', 'Sync process hangs on 100% and does not complete database write.', 8);

-- Seed Sample Similar Matches for TKT-100002 (Technical)
INSERT INTO ticket_similar_matches (ticket_id, similar_ticket_ref_id, similarity_score, similar_subject, similar_description, historical_resolution_hours) VALUES
('TKT-100002', 'HIST-82001', 91.20, 'Boot loop after firmware update v2.3', 'Device enters continuous restart loop after automatic firmware update installation.', 12),
('TKT-100002', 'HIST-73550', 85.60, 'Kernel panic on startup sequence', 'System crashes with kernel panic during boot sequence, unable to access OS.', 8),
('TKT-100002', 'HIST-60222', 79.30, 'Recovery mode inaccessible after update', 'Cannot access recovery mode or safe mode after recent system update.', 6);

-- Seed Sample Similar Matches for TKT-100003 (Technical)
INSERT INTO ticket_similar_matches (ticket_id, similar_ticket_ref_id, similarity_score, similar_subject, similar_description, historical_resolution_hours) VALUES
('TKT-100003', 'HIST-55100', 87.80, 'Audio dropout on Bluetooth connection', 'Bluetooth audio experiences intermittent dropouts and connection instability.', 4),
('TKT-100003', 'HIST-42150', 82.40, 'Connection range limited to 3 meters', 'Bluetooth connection drops when device moves beyond 3 meters from paired device.', 3);

-- Seed Sample Similar Matches for TKT-200001 (Billing)
INSERT INTO ticket_similar_matches (ticket_id, similar_ticket_ref_id, similarity_score, similar_subject, similar_description, historical_resolution_hours) VALUES
('TKT-200001', 'HIST-99012', 93.50, 'Duplicate charge for subscription renewal', 'Customer charged twice for annual subscription renewal on same date.', 2),
('TKT-200001', 'HIST-87501', 88.20, 'Unauthorized recurring charge', 'Unexpected recurring charge appeared on credit card statement.', 4),
('TKT-200001', 'HIST-76230', 84.10, 'Billing dispute for enterprise subscription', 'Dispute over enterprise subscription billing amount and charge frequency.', 6);

-- Seed Sample Similar Matches for TKT-200002 (Billing)
INSERT INTO ticket_similar_matches (ticket_id, similar_ticket_ref_id, similarity_score, similar_subject, similar_description, historical_resolution_hours) VALUES
('TKT-200002', 'HIST-65200', 89.70, 'Missing tax breakdown on invoice PDF', 'Invoice PDF downloads without GST/tax breakdown section visible.', 3),
('TKT-200002', 'HIST-54310', 83.50, 'Tax calculation error on invoice', 'Invoice shows incorrect tax calculation for business account.', 5);

-- Seed Sample Similar Matches for TKT-200003 (Billing)
INSERT INTO ticket_similar_matches (ticket_id, similar_ticket_ref_id, similarity_score, similar_subject, similar_description, historical_resolution_hours) VALUES
('TKT-200003', 'HIST-48200', 86.30, 'Update payment method for corporate account', 'Need to change credit card on file for enterprise billing.', 2),
('TKT-200003', 'HIST-37150', 81.90, 'Change billing address for subscription', 'Request to update billing address to new corporate office location.', 1);

-- Seed Sample Similar Matches for TKT-300001 (Account)
INSERT INTO ticket_similar_matches (ticket_id, similar_ticket_ref_id, similarity_score, similar_subject, similar_description, historical_resolution_hours) VALUES
('TKT-300001', 'HIST-29200', 90.40, 'SMS OTP not received internationally', '2FA SMS codes not delivered when traveling abroad.', 8),
('TKT-300001', 'HIST-18150', 85.20, 'Authentication codes blocked for certain regions', 'OTP delivery blocked for specific country codes due to carrier restrictions.', 12);

-- Seed Sample Similar Matches for TKT-300002 (Account)
INSERT INTO ticket_similar_matches (ticket_id, similar_ticket_ref_id, similarity_score, similar_subject, similar_description, historical_resolution_hours) VALUES
('TKT-300002', 'HIST-17200', 88.60, 'Transfer admin rights to new user', 'Need to transfer administrative privileges from departing employee to replacement.', 4),
('TKT-300002', 'HIST-16300', 82.80, 'Account ownership change request', 'Request to change primary account owner and billing contact.', 6);

-- Seed Sample Similar Matches for TKT-400001 (General Inquiry)
INSERT INTO ticket_similar_matches (ticket_id, similar_ticket_ref_id, similarity_score, similar_subject, similar_description, historical_resolution_hours) VALUES
('TKT-400001', 'HIST-15200', 87.90, 'Warranty coverage expiration inquiry', 'Customer asking about warranty period for hardware devices.', 2),
('TKT-400001', 'HIST-14100', 83.40, 'Replacement policy for damaged equipment', 'Inquiry about replacement process for warranty-covered damage.', 3);

-- Seed Sample Similar Matches for TKT-400002 (General Inquiry)
INSERT INTO ticket_similar_matches (ticket_id, similar_ticket_ref_id, similarity_score, similar_subject, similar_description, historical_resolution_hours) VALUES
('TKT-400002', 'HIST-13300', 91.10, 'API integration documentation request', 'Need API documentation for third-party integration development.', 4),
('TKT-400002', 'HIST-12200', 86.70, 'Webhook payload format specification', 'Request for webhook event payload structure and authentication.', 5);

-- Seed Sample Similar Matches for TKT-500001 (Fraud)
INSERT INTO ticket_similar_matches (ticket_id, similar_ticket_ref_id, similarity_score, similar_subject, similar_description, historical_resolution_hours) VALUES
('TKT-500001', 'HIST-11100', 94.30, 'Suspicious login from foreign IP address', 'Customer reports login attempt from unrecognized international IP.', 24),
('TKT-500001', 'HIST-10100', 89.50, 'Account security alert for unusual location', 'Security system flagged login from geographic location not associated with account.', 18);

-- Seed Sample Similar Matches for TKT-500002 (Fraud)
INSERT INTO ticket_similar_matches (ticket_id, similar_ticket_ref_id, similarity_score, similar_subject, similar_description, historical_resolution_hours) VALUES
('TKT-500002', 'HIST-09100', 92.80, 'Fraudulent refund claim with fake invoice', 'Customer reports fraudulent refund request using fabricated invoice number.', 36),
('TKT-500002', 'HIST-08100', 87.40, 'Unauthorized chargeback initiated', 'Unexpected chargeback filed on legitimate transaction.', 48);

-- Seed Sample Replies for TKT-100001 (Technical)
INSERT INTO ticket_replies (reply_id, ticket_id, sender_id, message, created_at) VALUES
(1, 'TKT-100001', 6, 'Hi team, whenever I upload data larger than 50MB, the desktop app crashes with a 502 gateway error.', '2026-01-30 00:00:00'),
(2, 'TKT-100001', 2, 'Hello Alex, thank you for reaching out. We have identified a potential chunk-size limit in our reverse proxy. We are deploying a patch to test server now.', '2026-01-31 00:00:00'),
(3, 'TKT-100001', 6, 'Understood, let me know when I can re-test the upload.', '2026-02-01 10:00:00');

-- Seed Sample Replies for TKT-200001 (Billing)
INSERT INTO ticket_replies (reply_id, ticket_id, sender_id, message, created_at) VALUES
(4, 'TKT-200001', 6, 'I noticed two identical charges of $1,199 on my corporate credit card for the annual enterprise subscription renewal. Please refund the duplicate charge immediately.', '2026-01-29 00:00:00'),
(5, 'TKT-200001', 3, 'Thank you for reporting this billing issue. We are investigating the duplicate charge and will process a refund once confirmed.', '2026-01-30 00:00:00');

-- Seed Sample Replies for TKT-300001 (Account)
INSERT INTO ticket_replies (reply_id, ticket_id, sender_id, message, created_at) VALUES
(6, 'TKT-300001', 6, 'I am traveling internationally and not receiving SMS OTP codes for 2FA authentication. My local carrier works but your SMS service seems blocked for my country code.', '2026-01-28 00:00:00');

-- Seed Sample Replies for TKT-400001 (General Inquiry)
INSERT INTO ticket_replies (reply_id, ticket_id, sender_id, message, created_at) VALUES
(7, 'TKT-400001', 6, 'What is the standard warranty coverage period for hardware replacements? Need to know if our devices are still under warranty for potential replacement.', '2026-01-26 00:00:00'),
(8, 'TKT-400001', 5, 'Standard hardware warranty covers 12 months from purchase date. I can check your specific device warranty status if you provide the serial numbers.', '2026-01-27 00:00:00');

-- Seed Sample Replies for TKT-500001 (Fraud)
INSERT INTO ticket_replies (reply_id, ticket_id, sender_id, message, created_at) VALUES
(9, 'TKT-500001', 6, 'Received security alert about login attempt from IP address 185.14.x.x in Eastern Europe. I have never traveled there and do not recognize this activity. Please investigate potential account compromise.', '2026-02-01 10:00:00'),
(10, 'TKT-500001', 1, 'Security alert received. We have temporarily secured your account and are investigating the unauthorized access attempt. Please verify your identity through the secure link sent to your email.', '2026-02-01 16:00:00');