from pathlib import Path

import joblib
from sklearn.metrics.pairwise import cosine_similarity

from .preprocessing import preprocess_text

# Load model files from the project directory.
MODEL_DIR = Path(__file__).resolve().parent.parent / "models"

# Load trained models and vectorizers.
category_model = joblib.load(MODEL_DIR / "category_model.pkl")
category_vectorizer = joblib.load(MODEL_DIR / "category_vectorizer.pkl")
priority_model = joblib.load(MODEL_DIR / "priority_model.pkl")
priority_vectorizer = joblib.load(MODEL_DIR / "priority_vectorizer.pkl")

# Load similarity search data.
similarity_vectorizer = joblib.load(MODEL_DIR / "similarity_vectorizer.pkl")
ticket_vectors = joblib.load(MODEL_DIR / "ticket_vectors.pkl")
similarity_data = joblib.load(MODEL_DIR / "similarity_data.pkl")

# Map each category to its department.
department_mapping = {
    "Technical": "Technical Support",
    "Billing": "Billing",
    "Account": "Account Support",
    "General Inquiry": "General Inquiry",
    "Fraud": "Fraud & Security"
}

# Predict a ticket category.
def predict_category(text):
    clean_text = preprocess_text(text)
    vector = category_vectorizer.transform([clean_text])
    return category_model.predict(vector)[0]

# Predict a ticket priority.
def predict_priority(text):
    clean_text = preprocess_text(text)
    vector = priority_vectorizer.transform([clean_text])
    return priority_model.predict(vector)[0]

# Return the closest historical tickets.
def find_similar_tickets(text, top_n=3):
    clean_text = preprocess_text(text)
    query_vector = similarity_vectorizer.transform([clean_text])
    similarities = cosine_similarity(query_vector, ticket_vectors).flatten()
    top_indices = similarities.argsort()[::-1][:top_n]
    
    results = []
    for index in top_indices:
        ticket = similarity_data.iloc[index]
        results.append({
            "Ticket_ID": ticket["Ticket_ID"],
            "Subject": ticket["Ticket_Subject"],
            "Description": ticket["Ticket_Description"],
            "Category": ticket["Issue_Category"],
            "Priority": ticket["Priority_Level"],
            "Similarity": round(similarities[index] * 100, 2)
        })
    return results

# Run the complete ticket analysis.
def analyze_ticket(subject, description):
    text = f"{subject} {description}"
    category = predict_category(text)
    priority = predict_priority(text)
    department = department_mapping.get(category, "General Inquiry")
    similar_tickets = find_similar_tickets(text, top_n=3)
    return {
        "category": category,
        "priority": priority,
        "department": department,
        "similar_tickets": similar_tickets
    }
