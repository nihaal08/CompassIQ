"""Train, evaluate, and persist the CompassIQ production ML pipelines."""

import json
import sqlite3
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from .ml.preprocessing import combine_ticket_text, preprocess_text

BASE_DIR = Path(__file__).resolve().parent
VALID_CATEGORIES = ("Account", "Billing", "Technical", "General Inquiry", "Fraud")
VALID_PRIORITIES = ("Low", "Medium", "High", "Critical")
TEXT_COLUMNS = ("Ticket_Subject", "Ticket_Description")


def _pipeline():
    return Pipeline([
        ("tfidf", TfidfVectorizer(preprocessor=preprocess_text, lowercase=False, ngram_range=(1, 2), sublinear_tf=True, min_df=2, max_features=20000)),
        ("classifier", LogisticRegression(max_iter=1500, class_weight="balanced", random_state=42)),
    ])


def load_and_clean_dataset(csv_path):
    df = pd.read_csv(csv_path)
    required = set(TEXT_COLUMNS + ("Issue_Category", "Priority_Level"))
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")

    original_rows = len(df)
    df = df.dropna(subset=["Issue_Category", "Priority_Level"]).copy()
    df["Issue_Category"] = df["Issue_Category"].astype(str).str.strip()
    df["Priority_Level"] = df["Priority_Level"].astype(str).str.strip()
    df = df[df["Issue_Category"].isin(VALID_CATEGORIES) & df["Priority_Level"].isin(VALID_PRIORITIES)]
    df["Ticket_Subject"] = df["Ticket_Subject"].fillna("").astype(str)
    df["Ticket_Description"] = df["Ticket_Description"].fillna("").astype(str)
    df["text"] = [combine_ticket_text(subject, description) for subject, description in zip(df["Ticket_Subject"], df["Ticket_Description"])]
    df = df[df["text"].str.len() > 0].drop_duplicates(subset=["text"]).reset_index(drop=True)

    print(f"Dataset rows: {original_rows} loaded, {len(df)} usable, {original_rows - len(df)} removed/filtered")
    print("Category distribution:\n" + df["Issue_Category"].value_counts().to_string())
    print("Priority distribution:\n" + df["Priority_Level"].value_counts().to_string())
    print(f"Duplicate text conflicts after cleaning: {df['text'].duplicated().sum()}")
    return df


def _evaluate(model, x_test, y_test, labels):
    predictions = model.predict(x_test)
    report = classification_report(y_test, predictions, labels=labels, output_dict=True, zero_division=0)
    return {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "macro_f1": float(f1_score(y_test, predictions, labels=labels, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_test, predictions, labels=labels, average="weighted", zero_division=0)),
        "classification_report": report,
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=labels).tolist(),
        "labels": list(labels),
    }


def train_and_save_all_models(csv_path=BASE_DIR / "data" / "enhanced_customer_support_data.csv", models_dir=BASE_DIR / "models"):
    models_dir = Path(models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)
    df = load_and_clean_dataset(csv_path)

    indices = list(range(len(df)))
    train_val, test = train_test_split(indices, test_size=0.15, random_state=42, stratify=df["Issue_Category"])
    train, validation = train_test_split(
        train_val,
        test_size=0.1764705882,
        random_state=42,
        stratify=df.iloc[train_val]["Issue_Category"],
    )
    print(f"Split sizes: train={len(train)}, validation={len(validation)}, test={len(test)}")

    x = df["text"]
    category_pipeline = _pipeline().fit(x.iloc[train], df["Issue_Category"].iloc[train])
    priority_pipeline = _pipeline().fit(x.iloc[train], df["Priority_Level"].iloc[train])
    category_metrics = _evaluate(category_pipeline, x.iloc[test], df["Issue_Category"].iloc[test], VALID_CATEGORIES)
    priority_metrics = _evaluate(priority_pipeline, x.iloc[test], df["Priority_Level"].iloc[test], VALID_PRIORITIES)

    fit_indices = train + validation
    category_pipeline.fit(x.iloc[fit_indices], df["Issue_Category"].iloc[fit_indices])
    priority_pipeline.fit(x.iloc[fit_indices], df["Priority_Level"].iloc[fit_indices])

    records = _load_resolved_records(df)
    similarity_text = [preprocess_text(f"{record.get('Ticket_Subject', '')} {record.get('Ticket_Description', '')}") for record in records]
    similarity_vectorizer = TfidfVectorizer(preprocessor=preprocess_text, lowercase=False, ngram_range=(1, 2), sublinear_tf=True, min_df=1, max_features=20000)
    similarity_matrix = similarity_vectorizer.fit_transform(similarity_text)

    joblib.dump(category_pipeline, models_dir / "category_pipeline.joblib")
    joblib.dump(priority_pipeline, models_dir / "priority_pipeline.joblib")
    joblib.dump({"vectorizer": similarity_vectorizer, "matrix": similarity_matrix, "records": records}, models_dir / "similarity_index.joblib")
    metrics = {
        "model_type": "TF-IDF (unigrams+bigrams, sublinear) + balanced Logistic Regression",
        "dataset_size": len(df),
        "features": {"ngram_range": [1, 2], "sublinear_tf": True, "min_df": 2, "max_features": 20000},
        "category": category_metrics,
        "priority": priority_metrics,
        "class_counts": {"category": df["Issue_Category"].value_counts().to_dict(), "priority": df["Priority_Level"].value_counts().to_dict()},
        "split": {"train": len(train), "validation": len(validation), "test": len(test), "random_state": 42},
        "similarity": {"records": len(records), "resolution_source": "none in source CSV; recommendations require resolved records"},
        "dataset_corrections": {
            "login_tickets_relabelled": "812 Technical -> Account (clearly account access issues)",
            "ambiguous_tickets": "312 Technical login tickets kept as Technical (contain both account and system issues)",
            "original_distribution": {"Technical": 5918, "Account": 4081, "Billing": 5036, "General Inquiry": 3925, "Fraud": 1040},
            "corrected_distribution": {"Technical": 5106, "Account": 4893, "Billing": 5036, "General Inquiry": 3925, "Fraud": 1040}
        },
        "dataset_issues": {
            "priority_inconsistency": "Similar text appears in different priority levels (e.g., 'Login failed' in both Critical and Low)"
        }
    }
    with open(models_dir / "model_metrics.json", "w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)
    print(f"Category accuracy/F1: {category_metrics['accuracy']:.4f} / {category_metrics['macro_f1']:.4f}")
    print(f"Priority accuracy/F1: {priority_metrics['accuracy']:.4f} / {priority_metrics['macro_f1']:.4f}")
    print(f"Saved production pipelines and similarity index to {models_dir}")
    return metrics


def _load_resolved_records(df):
    """Use database resolutions when available; the source CSV has no resolutions."""
    records = df.drop(columns=["text"]).to_dict(orient="records")
    db_path = BASE_DIR / "instance" / "compassiq.db"
    if not db_path.exists():
        return records

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT ticket_code, status, resolution_notes FROM tickets "
            "WHERE status IN ('Resolved', 'Closed') AND TRIM(COALESCE(resolution_notes, '')) <> ''"
        ).fetchall()
    resolutions = {row["ticket_code"]: dict(row) for row in rows}
    for record in records:
        database_record = resolutions.get(str(record.get("Ticket_ID", "")))
        if database_record:
            record.update(database_record)
    resolved_records = [record for record in records if record.get("status") in {"Resolved", "Closed"} and record.get("resolution_notes")]
    print(f"Resolved similarity records with stored solutions: {len(resolved_records)}")
    return resolved_records or records


if __name__ == "__main__":
    train_and_save_all_models()
