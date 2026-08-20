"""
CompassIQ - Similarity Engine Builder
=======================================
Builds the TF-IDF vector matrix over all 20,000 historical
tickets so that the application can find similar past tickets
using cosine similarity at query time.

This is NOT a trained classifier — it is a vector store.
At runtime, a new ticket's vector is compared against all
stored vectors to return the top-N most similar tickets.

Usage:
    python ml/similarity.py

Output files:
    models/similarity_vectorizer.pkl  →  fitted TF-IDF object
    models/ticket_vectors.pkl         →  sparse matrix (20000 x features)
    models/similarity_data.pkl        →  DataFrame with ticket metadata
"""

import os
import sys
import pandas as pd
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer

# Allow importing preprocessing.py from same ml/ folder
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
print("COMPASSIQ - SIMILARITY ENGINE SETUP")
print("=" * 60)

print("\nLoading dataset...")

df = pd.read_csv(DATASET_PATH)

print(f"Dataset loaded: {df.shape[0]} records, {df.shape[1]} columns")


# ============================================================
# HANDLE MISSING VALUES
# ============================================================

df["Ticket_Subject"]     = df["Ticket_Subject"].fillna("")
df["Ticket_Description"] = df["Ticket_Description"].fillna("")


# ============================================================
# COMBINE TEXT
# ============================================================

df["combined_text"] = (
    df["Ticket_Subject"].astype(str)
    + " "
    + df["Ticket_Description"].astype(str)
)


# ============================================================
# NLP PREPROCESSING
# ============================================================

print("\nPreprocessing all historical tickets...")
print("(NLP cleaning: lowercase -> remove stopwords -> lemmatize)")

df["clean_text"] = df["combined_text"].apply(preprocess_text)

# Drop any rows where cleaning produced empty text
df = df[df["clean_text"].str.strip() != ""].copy()

print(f"Tickets available for similarity search: {len(df)}")


# ============================================================
# TF-IDF VECTORIZATION
# ============================================================

print("\nBuilding TF-IDF matrix for similarity search...")
print("(max_features=15000, ngram_range=(1,2))")

similarity_vectorizer = TfidfVectorizer(
    max_features=15000,
    ngram_range=(1, 2),
    min_df=2,
    sublinear_tf=True
)

# fit_transform produces the full historical vector matrix
ticket_vectors = similarity_vectorizer.fit_transform(
    df["clean_text"]
)

print(f"\nVector matrix shape: {ticket_vectors.shape}")
print("(rows = tickets, columns = TF-IDF features)")


# ============================================================
# PREPARE METADATA STORE
# ============================================================

# Only store columns needed at query time to keep .pkl small
similarity_data = df[
    [
        "Ticket_ID",
        "Ticket_Subject",
        "Ticket_Description",
        "Issue_Category",
        "Priority_Level",
        "Resolution_Time_Hours",
        "Satisfaction_Score"
    ]
].copy()


# ============================================================
# SAVE FILES
# ============================================================

print("\nSaving similarity files...")

joblib.dump(
    similarity_vectorizer,
    os.path.join(MODEL_DIR, "similarity_vectorizer.pkl")
)

joblib.dump(
    ticket_vectors,
    os.path.join(MODEL_DIR, "ticket_vectors.pkl")
)

joblib.dump(
    similarity_data,
    os.path.join(MODEL_DIR, "similarity_data.pkl")
)


# ============================================================
# DONE
# ============================================================

print("\n" + "=" * 60)
print("SIMILARITY ENGINE SETUP COMPLETED")
print("=" * 60)

print(f"\nVectors stored for {len(df)} historical tickets.")

print("\nCreated files:")
print("  1. similarity_vectorizer.pkl")
print("  2. ticket_vectors.pkl")
print("  3. similarity_data.pkl")

print("\nNext step: Run python ml/test_model.py")
print("=" * 60)
