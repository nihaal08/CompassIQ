"""
CompassIQ - Prediction Module
==============================
Loads pre-trained models at startup and exposes three functions
that Flask (app.py) will call for every incoming ticket:

    predict_category(text)    →  str  (e.g. "Billing")
    predict_priority(text)    →  str  (e.g. "High")
    find_similar_tickets(text, top_n=3) → list[dict]
    analyze_ticket(subject, description) → dict

Models are loaded once at module import time, not on every
request, so inference is fast.

Dependencies:
    Run ml/train_models.py and ml/similarity.py first to
    generate the required .pkl files before importing this.
"""

import os
import sys
import joblib

from sklearn.metrics.pairwise import cosine_similarity

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

MODEL_DIR = os.path.join(
    BASE_DIR,
    "models"
)


# ============================================================
# LOAD MODELS (done once at import time)
# ============================================================

category_model = joblib.load(
    os.path.join(MODEL_DIR, "category_model.pkl")
)

category_vectorizer = joblib.load(
    os.path.join(MODEL_DIR, "category_vectorizer.pkl")
)

priority_model = joblib.load(
    os.path.join(MODEL_DIR, "priority_model.pkl")
)

priority_vectorizer = joblib.load(
    os.path.join(MODEL_DIR, "priority_vectorizer.pkl")
)

# Similarity engine files
similarity_vectorizer = joblib.load(
    os.path.join(MODEL_DIR, "similarity_vectorizer.pkl")
)

ticket_vectors = joblib.load(
    os.path.join(MODEL_DIR, "ticket_vectors.pkl")
)

similarity_data = joblib.load(
    os.path.join(MODEL_DIR, "similarity_data.pkl")
)


# ============================================================
# DEPARTMENT MAPPING
# Maps predicted Issue_Category → Department name
# ============================================================

DEPARTMENT_MAPPING = {
    "Technical":       "Technical Support",
    "Billing":         "Billing",
    "Account":         "Account Support",
    "General Inquiry": "General Inquiry",
    "Fraud":           "Fraud & Security"
}


# ============================================================
# PREDICT CATEGORY
# ============================================================

def predict_category(text):
    """
    Predict the issue category of a support ticket.

    Args:
        text (str): Combined subject + description text.

    Returns:
        str: One of Technical | Billing | Account |
             General Inquiry | Fraud
    """

    clean_text = preprocess_text(text)

    vector = category_vectorizer.transform([clean_text])

    prediction = category_model.predict(vector)[0]

    return prediction


# ============================================================
# PREDICT PRIORITY
# ============================================================

def predict_priority(text):
    """
    Predict the urgency/priority level of a support ticket.

    Args:
        text (str): Combined subject + description text.

    Returns:
        str: One of Low | Medium | High | Critical
    """

    clean_text = preprocess_text(text)

    vector = priority_vectorizer.transform([clean_text])

    prediction = priority_model.predict(vector)[0]

    return prediction


# ============================================================
# FIND SIMILAR TICKETS
# ============================================================

def find_similar_tickets(text, top_n=3):
    """
    Find the most similar historical tickets using cosine
    similarity over TF-IDF vectors.

    Args:
        text  (str): Combined subject + description of new ticket.
        top_n (int): Number of similar tickets to return.

    Returns:
        list[dict]: Each dict contains:
            Ticket_ID, Subject, Description,
            Category, Priority, Similarity (%)
    """

    clean_text = preprocess_text(text)

    # Vectorize the new ticket using the same fitted vectorizer
    new_vector = similarity_vectorizer.transform([clean_text])

    # Compute cosine similarity against all stored ticket vectors
    similarities = cosine_similarity(
        new_vector,
        ticket_vectors
    ).flatten()

    # Get indices of top-N highest similarity scores
    top_indices = similarities.argsort()[::-1][:top_n]

    results = []

    for index in top_indices:

        ticket = similarity_data.iloc[index]

        results.append({
            "Ticket_ID":   ticket["Ticket_ID"],
            "Subject":     ticket["Ticket_Subject"],
            "Description": ticket["Ticket_Description"],
            "Category":    ticket["Issue_Category"],
            "Priority":    ticket["Priority_Level"],
            "Similarity":  round(similarities[index] * 100, 2)
        })

    return results


# ============================================================
# FULL TICKET ANALYSIS (main entry point for Flask)
# ============================================================

def analyze_ticket(subject, description):
    """
    Run the full CompassIQ AI pipeline on a new support ticket.

    Args:
        subject     (str): Ticket subject line.
        description (str): Ticket description body.

    Returns:
        dict: {
            "category":        str,
            "priority":        str,
            "department":      str,
            "similar_tickets": list[dict]
        }
    """

    # Combine subject and description for unified prediction
    text = f"{subject} {description}"

    category = predict_category(text)

    priority = predict_priority(text)

    similar_tickets = find_similar_tickets(text, top_n=3)

    # Map category → routed department
    department = DEPARTMENT_MAPPING.get(
        category,
        "General Inquiry"
    )

    return {
        "category":        category,
        "priority":        priority,
        "department":      department,
        "similar_tickets": similar_tickets
    }
