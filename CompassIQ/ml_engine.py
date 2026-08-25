"""Runtime ML service for CompassIQ.

Models are trained offline by train_model.py and loaded here only once.
"""

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from .ml.preprocessing import combine_ticket_text, preprocess_text

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
DEPARTMENT_LABELS = {
    "Account": "Account Support",
    "Billing": "Billing",
    "Technical": "Technical Support",
    "General Inquiry": "General Inquiry",
    "Fraud": "Admin",
}
MIN_SIMILARITY = 0.15
CATEGORY_REVIEW_THRESHOLD = 0.60
PRIORITY_REVIEW_THRESHOLD = 0.55


class CompassIQMLEngine:
    def __init__(self, models_dir=MODEL_DIR):
        self.models_dir = Path(models_dir)
        self.category_pipeline = None
        self.priority_pipeline = None
        self.similarity_vectorizer = None
        self.similarity_matrix = None
        self.historical_records = []
        self.metrics = {}
        self.load_saved_models()

    def load_saved_models(self):
        category_path = self.models_dir / "category_pipeline.joblib"
        priority_path = self.models_dir / "priority_pipeline.joblib"
        similarity_path = self.models_dir / "similarity_index.joblib"
        metrics_path = self.models_dir / "model_metrics.json"
        missing = [str(path.name) for path in (category_path, priority_path, similarity_path) if not path.exists()]
        if missing:
            raise FileNotFoundError(f"Missing trained CompassIQ artifacts: {', '.join(missing)}. Run python -m CompassIQ.train_model.")

        self.category_pipeline = joblib.load(category_path)
        self.priority_pipeline = joblib.load(priority_path)
        similarity_data = joblib.load(similarity_path)
        self.similarity_vectorizer = similarity_data["vectorizer"]
        self.similarity_matrix = similarity_data["matrix"]
        self.historical_records = similarity_data["records"]
        if metrics_path.exists():
            with open(metrics_path, encoding="utf-8") as handle:
                self.metrics = json.load(handle)
        print(f"[CompassIQ] Loaded trained category/priority pipelines and {len(self.historical_records)} similarity records.")

    @staticmethod
    def _prediction(pipeline, text, threshold):
        probabilities = pipeline.predict_proba([text])[0]
        classes = pipeline.classes_
        best_index = int(np.argmax(probabilities))
        confidence = float(probabilities[best_index])
        return {
            "label": str(classes[best_index]),
            "confidence": round(confidence * 100, 1),
            "probabilities": {str(label): round(float(probability) * 100, 1) for label, probability in zip(classes, probabilities)},
            "needs_review": confidence < threshold,
        }

    def predict_ticket(self, subject, description):
        text = combine_ticket_text(subject, description)
        if not text:
            return {
                "category": "General Inquiry", "category_confidence": 0.0, "category_probs": {}, "category_needs_review": True,
                "priority": "Medium", "priority_confidence": 0.0, "priority_probs": {}, "priority_needs_review": True,
            }

        category = self._prediction(self.category_pipeline, text, CATEGORY_REVIEW_THRESHOLD)
        priority = self._prediction(self.priority_pipeline, text, PRIORITY_REVIEW_THRESHOLD)
        
        # Transparent fallback for critical fraud detection (business rule override)
        # Only applied when ML fails to detect clear fraud indicators
        fraud_keywords = ['hacked', 'stolen', 'unauthorized', 'breach', 'compromised', 'security breach']
        text_lower = text.lower()
        has_fraud_indicators = any(keyword in text_lower for keyword in fraud_keywords)
        
        if has_fraud_indicators and category["label"] != "Fraud":
            # Override ML prediction for clear fraud cases
            category["label"] = "Fraud"
            category["confidence"] = 95.0  # High confidence due to clear fraud indicators
            category["needs_review"] = False
            category["fallback_applied"] = True
            category["fallback_reason"] = "Clear fraud indicators detected (hacked/stolen/unauthorized)"
        
        return {
            "category": category["label"],
            "category_confidence": category["confidence"],
            "category_probs": category["probabilities"],
            "category_needs_review": category["needs_review"],
            "priority": priority["label"],
            "priority_confidence": priority["confidence"],
            "priority_probs": priority["probabilities"],
            "priority_needs_review": priority["needs_review"],
            "assigned_department": DEPARTMENT_LABELS[category["label"]],
            "fallback_applied": category.get("fallback_applied", False),
            "fallback_reason": category.get("fallback_reason", ""),
        }

    def find_similar_tickets(self, subject, description, top_n=3):
        """Return only sufficiently similar records with actual resolutions."""
        text = preprocess_text(f"{subject or ''} {description or ''}")
        if not text or self.similarity_matrix is None:
            return []

        records_with_resolutions = [
            (index, record) for index, record in enumerate(self.historical_records)
            if record.get("status", "").lower() in {"resolved", "closed"}
            and str(record.get("resolution_notes", record.get("Resolution", ""))).strip()
        ]
        if not records_with_resolutions:
            return []

        indices = [item[0] for item in records_with_resolutions]
        query_vector = self.similarity_vectorizer.transform([text])
        scores = cosine_similarity(query_vector, self.similarity_matrix[indices])[0]
        ranked = sorted(zip(scores, records_with_resolutions), key=lambda item: item[0], reverse=True)
        results = []
        for score, (index, record) in ranked[:top_n]:
            if float(score) < MIN_SIMILARITY:
                continue
            resolution = str(record.get("status", ""))
            resolution = str(record.get("resolution_notes", record.get("Resolution", resolution))).strip()
            results.append({
                "ticket_id": str(record.get("Ticket_ID", record.get("ticket_code", f"TKT-{index}"))),
                "subject": str(record.get("Ticket_Subject", record.get("subject", ""))),
                "description": str(record.get("Ticket_Description", record.get("description", ""))),
                "category": str(record.get("Issue_Category", record.get("category", "General Inquiry"))),
                "priority": str(record.get("Priority_Level", record.get("priority", "Medium"))),
                "resolution_note": resolution,
                "similarity": round(float(score) * 100, 1),
                "similarity_score": round(float(score), 3),
                "customer_name": str(record.get("Customer_Name", record.get("customer_name", "Anonymous"))),
                "assigned_agent": str(record.get("Assigned_Agent", record.get("assigned_agent_name", "Support Team"))),
            })
        return results

    def generate_solution_recommendation(self, similar_tickets, category=None):
        if not similar_tickets:
            return {
                "primary_solution": "No reliable historical solution found. Manual review recommended.",
                "steps": ["Review the customer-provided details.", "Verify account and transaction context.", "Assign the case for manual investigation."],
                "matched_ticket_ids": [],
            }
        top_match = similar_tickets[0]
        return {
            "primary_solution": f"Review the resolution from similar case {top_match['ticket_id']} ({top_match['similarity']}% match): {top_match['resolution_note']}",
            "steps": [f"Review similar resolved case {top_match['ticket_id']}.", top_match["resolution_note"], "Confirm the resolution with the customer."],
            "matched_ticket_ids": [ticket["ticket_id"] for ticket in similar_tickets],
        }


_ml_engine_instance = None


def get_ml_engine():
    global _ml_engine_instance
    if _ml_engine_instance is None:
        _ml_engine_instance = CompassIQMLEngine()
    return _ml_engine_instance
