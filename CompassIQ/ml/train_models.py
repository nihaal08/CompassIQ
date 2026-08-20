"""
CompassIQ - Model Training Script
===================================
Trains two ML classifiers on 20,000 customer support tickets:

    1. Category Model  →  TF-IDF + Logistic Regression
       Predicts: Technical | Billing | Account |
                 General Inquiry | Fraud

    2. Priority Model  →  TF-IDF + Logistic Regression
       Predicts: Low | Medium | High | Critical

Both models are saved as .pkl files inside the /models directory
and are loaded at runtime by predict.py (Flask integration layer).

Usage:
    python ml/train_models.py

Output files:
    models/category_model.pkl
    models/category_vectorizer.pkl
    models/priority_model.pkl
    models/priority_vectorizer.pkl
"""

import os
import sys
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

# Allow importing preprocessing.py from the same ml/ folder
sys.path.append(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

from preprocessing import preprocess_text


# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATASET_PATH = os.path.join(
    BASE_DIR,
    "dataset",
    "customer_support_data.csv"
)

MODEL_DIR = os.path.join(
    BASE_DIR,
    "models"
)

os.makedirs(MODEL_DIR, exist_ok=True)


# ============================================================
# LOAD DATASET
# ============================================================

print("\n" + "=" * 60)
print("COMPASSIQ - MODEL TRAINING STARTED")
print("=" * 60)

print("\nLoading dataset...")

df = pd.read_csv(DATASET_PATH)

print(f"Dataset shape: {df.shape}")

print("\nColumns found:")
print(df.columns.tolist())


# ============================================================
# VALIDATE REQUIRED COLUMNS
# ============================================================

required_columns = [
    "Ticket_Subject",
    "Ticket_Description",
    "Issue_Category",
    "Priority_Level"
]

for column in required_columns:
    if column not in df.columns:
        raise ValueError(
            f"Required column '{column}' not found in dataset. "
            f"Available columns: {df.columns.tolist()}"
        )

print("\nAll required columns verified.")


# ============================================================
# HANDLE MISSING VALUES
# ============================================================

df["Ticket_Subject"] = df["Ticket_Subject"].fillna("")
df["Ticket_Description"] = df["Ticket_Description"].fillna("")
df["Issue_Category"] = df["Issue_Category"].fillna("")
df["Priority_Level"] = df["Priority_Level"].fillna("")

# Drop rows where target labels are missing or blank
df = df[
    (df["Issue_Category"].str.strip() != "") &
    (df["Priority_Level"].str.strip() != "")
].copy()

print(f"\nRecords after removing blank targets: {len(df)}")


# ============================================================
# COMBINE SUBJECT + DESCRIPTION INTO ONE TEXT FIELD
# ============================================================

# We merge subject and description so the model sees
# the full context of each ticket in a single string.
df["combined_text"] = (
    df["Ticket_Subject"].astype(str)
    + " "
    + df["Ticket_Description"].astype(str)
)


# ============================================================
# NLP PREPROCESSING
# ============================================================

print("\nRunning NLP preprocessing (this may take a moment)...")

df["clean_text"] = df["combined_text"].apply(preprocess_text)

# Drop rows where cleaning produced empty strings
df = df[df["clean_text"].str.strip() != ""].copy()

print(f"Final training records after preprocessing: {len(df)}")


# ============================================================
# CLASS DISTRIBUTION CHECK
# ============================================================

print("\nIssue Category Distribution:")
print(df["Issue_Category"].value_counts())

print("\nPriority Level Distribution:")
print(df["Priority_Level"].value_counts())


# ============================================================
# PREPARE FEATURES AND LABELS
# ============================================================

X = df["clean_text"]

y_category = df["Issue_Category"]
y_priority = df["Priority_Level"]


# ============================================================
# TRAIN / TEST SPLIT
# ============================================================

# Category split — stratified to preserve class balance
X_train, X_test, y_cat_train, y_cat_test = train_test_split(
    X,
    y_category,
    test_size=0.20,
    random_state=42,
    stratify=y_category
)

# Priority split — independent split with same seed
X_train_p, X_test_p, y_pri_train, y_pri_test = train_test_split(
    X,
    y_priority,
    test_size=0.20,
    random_state=42,
    stratify=y_priority
)

print(f"\nCategory training set: {len(X_train)} samples")
print(f"Category test set:     {len(X_test)} samples")

print(f"\nPriority training set: {len(X_train_p)} samples")
print(f"Priority test set:     {len(X_test_p)} samples")


# ============================================================
# CATEGORY MODEL — TF-IDF + LOGISTIC REGRESSION
# ============================================================

print("\n" + "=" * 60)
print("TRAINING CATEGORY MODEL")
print("=" * 60)

# TF-IDF vectorizer for category
category_vectorizer = TfidfVectorizer(
    max_features=10000,
    ngram_range=(1, 2),       # unigrams and bigrams
    min_df=2,                 # ignore very rare terms
    sublinear_tf=True         # apply log(1 + tf) scaling
)

X_cat_train_vec = category_vectorizer.fit_transform(X_train)
X_cat_test_vec  = category_vectorizer.transform(X_test)

# Logistic Regression classifier for category
category_model = LogisticRegression(
    max_iter=1000,
    class_weight="balanced",  # handles Fraud class imbalance
    random_state=42
)

category_model.fit(X_cat_train_vec, y_cat_train)

category_predictions = category_model.predict(X_cat_test_vec)

category_accuracy = accuracy_score(y_cat_test, category_predictions)

print(f"\nCategory Model Accuracy: {category_accuracy * 100:.2f}%")

print("\nClassification Report (Category):")
print(
    classification_report(
        y_cat_test,
        category_predictions
    )
)

print("Confusion Matrix (Category):")
print(
    confusion_matrix(
        y_cat_test,
        category_predictions
    )
)

# Save category model and vectorizer
joblib.dump(
    category_model,
    os.path.join(MODEL_DIR, "category_model.pkl")
)

joblib.dump(
    category_vectorizer,
    os.path.join(MODEL_DIR, "category_vectorizer.pkl")
)

print("\nCategory model saved.")


# ============================================================
# PRIORITY MODEL — TF-IDF + LOGISTIC REGRESSION
# ============================================================

print("\n" + "=" * 60)
print("TRAINING PRIORITY MODEL")
print("=" * 60)

# TF-IDF vectorizer for priority
priority_vectorizer = TfidfVectorizer(
    max_features=10000,
    ngram_range=(1, 2),
    min_df=2,
    sublinear_tf=True
)

X_pri_train_vec = priority_vectorizer.fit_transform(X_train_p)
X_pri_test_vec  = priority_vectorizer.transform(X_test_p)

# Logistic Regression classifier for priority
priority_model = LogisticRegression(
    max_iter=1000,
    class_weight="balanced",
    random_state=42
)

priority_model.fit(X_pri_train_vec, y_pri_train)

priority_predictions = priority_model.predict(X_pri_test_vec)

priority_accuracy = accuracy_score(y_pri_test, priority_predictions)

print(f"\nPriority Model Accuracy: {priority_accuracy * 100:.2f}%")

print("\nClassification Report (Priority):")
print(
    classification_report(
        y_pri_test,
        priority_predictions
    )
)

print("Confusion Matrix (Priority):")
print(
    confusion_matrix(
        y_pri_test,
        priority_predictions
    )
)

# Save priority model and vectorizer
joblib.dump(
    priority_model,
    os.path.join(MODEL_DIR, "priority_model.pkl")
)

joblib.dump(
    priority_vectorizer,
    os.path.join(MODEL_DIR, "priority_vectorizer.pkl")
)

print("\nPriority model saved.")


# ============================================================
# TRAINING COMPLETE
# ============================================================

print("\n" + "=" * 60)
print("MODEL TRAINING COMPLETED SUCCESSFULLY")
print("=" * 60)

print("\nModels saved in:")
print(MODEL_DIR)

print("\nCreated files:")
print("  1. category_model.pkl")
print("  2. category_vectorizer.pkl")
print("  3. priority_model.pkl")
print("  4. priority_vectorizer.pkl")

print("\nNext step: Run python ml/similarity.py")
print("=" * 60)
