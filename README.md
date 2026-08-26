# CompassIQ — AI-Powered Customer Support Ticket Management System

An end-to-end, production-grade, AI-powered customer support ticket intelligence platform built with **Python Flask**, **MySQL**, **scikit-learn**, **SMOTE**, **NLTK**, and a futuristic **Glassmorphism UI** (Bootstrap 5, Custom CSS3, Vanilla JS, Chart.js).

---

## 🌟 Key Features

1. **AI Automated Categorization & Priority Assignment**:
   - Classifies customer tickets into *Technical*, *Billing*, *Account*, *General Inquiry*, or *Fraud* with high precision.
   - Assigns priority (*Low*, *Medium*, *High*, *Critical*) and routes to department queues automatically.
2. **Top-3 Nearest Historical Ticket Matching (Cosine Similarity)**:
   - Evaluates TF-IDF vector embeddings against historical customer support tickets.
   - Provides agents with instant context, past resolution times, satisfaction ratings, and solutions.
3. **Role-Based Access Control (RBAC)**:
   - **Customer Portal**: Minimal, ultra-fast ticket submission, live visual step tracker (`Submitted` → `Under Review` → `In Progress` → `Resolved` → `Closed`), conversation thread, and post-resolution CSAT star rating.
   - **Department Agent Portal**: Dedicated department-scoped queue (`Technical`, `Billing`, `Account`, `General Inquiry`), dual-pane split workspace (conversation + AI similarity panel), one-click "Use Solution" macro.
   - **Administrator Console**: Real-time system analytics telemetry, User Verification Queue (`PENDING` customer approvals/rejections), and AI Fraud Escalation Center (one-click user bans / ticket closures).
4. **Futuristic Glassmorphism Theme**:
   - Dark charcoal palette (`#121824`), electric blue accents (`#0066FF` / `#00D2FF`), translucent glass cards with `backdrop-filter: blur(16px)`, neon borders, and centered modal alerts with dedicated top-left `X` close buttons.

---

## 📂 Project Architecture

```
CompassIQ-AI/
├── app.py                             # Flask application backend & RBAC routes
├── ai_engine.py                       # AI inference & Top-3 cosine similarity engine
├── train_model.py                     # ML training, SMOTE balancing, EDA & export pipeline
├── config.py                          # Application & MySQL configuration
├── db.py                              # PyMySQL database connection layer
├── schema.sql                         # MySQL database schema & seed data
├── requirements.txt                   # Project dependencies
├── .env.example                       # Environment variables template
├── models/                            # Serialized ML artifacts (joblib)
│   ├── tfidf_vectorizer.joblib
│   ├── category_model.joblib
│   ├── priority_model.joblib
│   └── historical_corpus.joblib
├── static/
│   ├── css/
│   │   └── style.css                  # Custom Glassmorphism styles & animations
│   ├── js/
│   │   └── main.js                    # Modal controls, AJAX handlers & Chart.js logic
│   └── plots/                         # Generated EDA visualization plots
├── templates/
│   ├── base.html                      # Base template & top-left close alert modals
│   ├── login.html                     # Glassmorphism authentication
│   ├── register.html                  # Customer registration with Product ID
│   ├── customer_dashboard.html        # Step tracker & live conversation
│   ├── department_dashboard.html      # Agent split-screen intelligence workspace
│   └── admin_dashboard.html           # Analytics, Verification Queue & Fraud Center
└── enhanced_customer_support_data.csv # 20,000+ support ticket dataset
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- MySQL Server (e.g. MySQL 8.0, XAMPP, or MariaDB)

### 2. Environment Setup & Dependencies
```bash
# Clone or navigate to the workspace
cd CompassIQ-AI

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Configuration
1. Configure your MySQL credentials in `.env` (or copy from `.env.example`):
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=compassiq_db
```

2. Initialize database schema & seed data:
```bash
# Option A: Run directly in MySQL CLI / phpMyAdmin
mysql -u root -p < schema.sql

# Option B: Run via Flask CLI
flask init-db
```

### 4. Train Machine Learning Models
Generate exploratory data analysis plots, balance classes with SMOTE, and serialize model artifacts:
```bash
python train_model.py
```
*This produces `tfidf_vectorizer.joblib`, `category_model.joblib`, `priority_model.joblib`, `historical_corpus.joblib` in the `models/` directory.*

### 5. Launch Application
```bash
python app.py
```
Open your browser at **`http://localhost:5000`**.

---

## 🔑 Default Seed Accounts & Credentials

| Role | Email | Password | Scope / Details |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@compassiq.com` | `admin123` | Global Analytics, User Approval Queue, Fraud Center |
| **Tech Agent** | `agent.tech@compassiq.com` | `agent123` | Technical Operations Queue & AI Assistant |
| **Billing Agent** | `agent.billing@compassiq.com` | `agent123` | Billing & Invoice Queue |
| **Account Agent** | `agent.account@compassiq.com` | `agent123` | Account & 2FA Security Queue |
| **Inquiry Agent** | `agent.inquiry@compassiq.com` | `agent123` | General Questions & Sales Queue |
| **Customer (Approved)** | `david.miller@example.com` | `customer123` | Verified customer portal access |
| **Customer (Pending)** | `samantha.reed@example.com` | `customer123` | Demonstrates pending verification modal alert |

---

## 🛡️ Verification & Fraud Workflow

1. **Customer Registration**: New customers register with their Name, Email, Password, and Bill No/Product ID. Accounts start in `PENDING` status.
2. **Login Protection**: Pending customers receive a centered modal alert: *"Your account is pending admin approval. Please wait for verification."*
3. **Admin Verification**: Administrator approves or rejects pending accounts with one click in the Command Center.
4. **AI Fraud Escalation**: Any ticket mentioning unauthorized charges, compromised accounts, or phishing is automatically flagged with `predicted_category = 'Fraud'`, assigned `Critical` priority, and routed to the Administrator Fraud Center for immediate user bans or investigation.
