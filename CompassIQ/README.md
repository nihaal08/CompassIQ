# CompassIQ — AI-Powered Customer Support Routing System

> **MCA Final Year Project | Week 2 — AI Module**
> Student: Mohamed Nihal | Reg: MES25MCA-2037

---

## 📌 Project Overview

CompassIQ is an intelligent customer support ticket routing system that uses Machine Learning to:

- **Predict the category** of incoming tickets (Technical, Billing, Account, General Inquiry, Fraud)
- **Predict the priority level** (Low, Medium, High, Critical)
- **Route tickets to the correct department** automatically
- **Find similar historical tickets** using cosine similarity

---

## 🗂️ Project Structure

```
CompassIQ/
│
├── app.py                    ← Flask entry point (Week 3)
├── config.py                 ← App configuration
├── requirements.txt          ← Python dependencies
├── .gitignore
│
├── dataset/
│   └── customer_support_data.csv    ← 20,000 ticket dataset
│
├── ml/
│   ├── preprocessing.py      ← NLP text cleaning
│   ├── train_models.py       ← Train category + priority models
│   ├── similarity.py         ← Build similarity vector store
│   ├── predict.py            ← Runtime prediction module
│   └── test_model.py         ← Verify AI pipeline
│
├── models/                   ← Saved .pkl files (git-ignored)
│   ├── category_model.pkl
│   ├── category_vectorizer.pkl
│   ├── priority_model.pkl
│   ├── priority_vectorizer.pkl
│   ├── similarity_vectorizer.pkl
│   ├── ticket_vectors.pkl
│   └── similarity_data.pkl
│
├── templates/                ← HTML templates (Week 3)
│
└── static/                   ← CSS / JS (Week 3)
    ├── css/
    └── js/
```

---

## 🤖 AI Architecture

```
Dataset (20,000 rows)
         │
         ▼
  NLP Preprocessing
  (lowercase → stopwords → lemmatize)
         │
         ▼
  Subject + Description combined
         │
         ▼
       TF-IDF
         │
    ┌────┴────┐
    ▼         ▼
CATEGORY   PRIORITY
 Model      Model
(LR)       (LR)
    │         │
    ▼         ▼
Category  Priority
    │
    ▼
Department
Routing

Historical Tickets → TF-IDF → Cosine Similarity → Top-3 Similar
```

### Models Used

| Model | Algorithm | Target |
|---|---|---|
| Category Classifier | TF-IDF + Logistic Regression | Technical / Billing / Account / General Inquiry / Fraud |
| Priority Classifier | TF-IDF + Logistic Regression | Low / Medium / High / Critical |
| Similarity Engine | TF-IDF + Cosine Similarity | Top-3 similar past tickets |

### Department Routing

| Predicted Category | Routed To |
|---|---|
| Technical | Technical Support |
| Billing | Billing |
| Account | Account Support |
| General Inquiry | General Inquiry |
| Fraud | Fraud & Security |

---

## 🛠️ Setup Instructions

### 1. Clone / download the repository

```bash
git clone <repo-url>
cd CompassIQ
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

**Windows:**
```bash
venv\Scripts\activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Add the dataset

Place the dataset file at:
```
CompassIQ/dataset/customer_support_data.csv
```

---

## 🚀 Running the AI Pipeline

### Step 1 — Train the ML models

```bash
python ml/train_models.py
```

Expected output:
```
Category Model Accuracy: ~XX%
Priority Model Accuracy: ~XX%
Models saved to models/
```

### Step 2 — Build the similarity engine

```bash
python ml/similarity.py
```

### Step 3 — Test the AI

```bash
python ml/test_model.py
```

Sample expected output:
```
TEST CASE 1: Billing / Payment Issue
Predicted Category  : Billing
Predicted Priority  : Medium
Assigned Department : Billing
Top 3 Similar Tickets: ...
```

### Step 4 — Start Flask (Week 2 stub)

```bash
python app.py
```

Visit: http://localhost:5000

---

## 📊 Dataset

| Field | Description |
|---|---|
| Ticket_Subject | Short subject line of the ticket |
| Ticket_Description | Full description from customer |
| Issue_Category | Label: Technical / Billing / Account / General Inquiry / Fraud |
| Priority_Level | Label: Low / Medium / High / Critical |

Total records: **20,000**

---

## 📅 Development Timeline

| Week | Focus | Status |
|---|---|---|
| Week 1 | Project setup, proposal, dataset selection | ✅ Done |
| Week 2 | NLP preprocessing, model training, similarity engine | ✅ Done |
| Week 3 | Flask web application, routing, templates | 🔜 Next |
| Week 4 | MySQL integration, ticket storage, dashboards | 🔜 Upcoming |
| Week 5 | Testing, evaluation, documentation | 🔜 Upcoming |

---

## 🔗 Notes

- `.pkl` model files are git-ignored (too large for version control)
- Dataset CSV is git-ignored — add it locally before training
- Re-run `train_models.py` and `similarity.py` after any changes to the dataset
