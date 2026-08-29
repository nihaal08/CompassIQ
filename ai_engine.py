"""
CompassIQ — AI Engine Inference & Similarity Module
===================================================
Loads pre-trained machine learning models and the historical TF-IDF corpus to
perform real-time ticket categorization, priority prediction, fraud detection,
and cosine similarity matching for top-3 historical reference tickets.
"""

import os
import re
import joblib
import numpy as np
import pandas as pd
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.metrics.pairwise import cosine_similarity, linear_kernel

# Ensure NLTK resources are available
for resource in ['stopwords', 'wordnet', 'punkt', 'punkt_tab', 'omw-1.4']:
    try:
        nltk.download(resource, quiet=True)
    except Exception:
        pass

lemmatizer = WordNetLemmatizer()
try:
    stop_words = set(stopwords.words('english'))
except Exception:
    stop_words = set()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, 'models')

# Global holders for lazy or startup loading
vectorizer = None
category_model = None
priority_model = None
historical_corpus = None
_is_initialized = False

# High-risk Fraud keywords to augment ML inference
FRAUD_INDICATORS = {
    'fraud', 'scam', 'phishing', 'hacked', 'stolen credentials', 'unauthorized charge',
    'unauthorized transaction', 'identity theft', 'fake account', 'card stolen',
    'account compromised', 'breach', 'blackmail', 'extortion', 'spoofed',
    'chargeback', 'unauthorized access', 'credential theft', 'stolen card',
    'fake invoice', 'forged', 'malicious', 'security breach'
}


def clean_text(text: str) -> str:
    """
    Cleans raw text for TF-IDF feature extraction.
    """
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    tokens = text.split()
    cleaned_tokens = [
        lemmatizer.lemmatize(word)
        for word in tokens
        if word not in stop_words and len(word) > 2
    ]
    return ' '.join(cleaned_tokens)


def load_ai_engine(force_reload: bool = False):
    """
    Loads serialized joblib models and TF-IDF corpus.
    """
    global vectorizer, category_model, priority_model, historical_corpus, _is_initialized
    
    if _is_initialized and not force_reload:
        return True

    p_vectorizer = os.path.join(MODELS_DIR, 'tfidf_vectorizer.joblib')
    p_cat = os.path.join(MODELS_DIR, 'category_model.joblib')
    p_prio = os.path.join(MODELS_DIR, 'priority_model.joblib')
    p_corpus = os.path.join(MODELS_DIR, 'historical_corpus.joblib')

    missing_files = [p for p in [p_vectorizer, p_cat, p_prio, p_corpus] if not os.path.exists(p)]
    
    if missing_files:
        print(f"[AI Engine] Notice: Some model artifacts are missing: {missing_files}. Run train_model.py to build them.")
        return False

    try:
        vectorizer = joblib.load(p_vectorizer)
        category_model = joblib.load(p_cat)
        priority_model = joblib.load(p_prio)
        historical_corpus = joblib.load(p_corpus)
        _is_initialized = True
        print("[AI Engine] Successfully loaded TF-IDF vectorizer, classification models, and historical corpus.")
        return True
    except Exception as e:
        print(f"[AI Engine] Error loading models: {e}")
        return False


def _heuristic_fallback(subject: str, description: str):
    """
    Rule-based heuristic fallback if ML models have not yet been trained.
    Returns prediction with default confidence metrics.
    """
    text_lower = f"{subject} {description}".lower()
    
    # Check fraud
    if any(k in text_lower for k in FRAUD_INDICATORS):
        return {
            'predicted_category': 'Fraud',
            'predicted_priority': 'Critical',
            'assigned_department': 'Admin_Fraud',
            'category_confidence': '90.0%',
            'priority_confidence': '90.0%',
            'low_confidence': False,
            'fraud_flagged': True,
            'similar_tickets': []
        }
        
    # Technical
    if any(k in text_lower for k in ['error', 'crash', 'bug', 'fail', 'sync', '502', '404', 'api', 'gateway', 'freeze', 'broken']):
        cat = 'Technical'
        prio = 'High' if ('crash' in text_lower or '502' in text_lower or 'critical' in text_lower) else 'Medium'
    # Billing
    elif any(k in text_lower for k in ['charge', 'refund', 'invoice', 'payment', 'card', 'billing', 'subscription', 'renew', 'dollar', '$', 'fee']):
        cat = 'Billing'
        prio = 'High' if ('unauthorized' in text_lower or 'overcharge' in text_lower or 'double' in text_lower) else 'Medium'
    # Account
    elif any(k in text_lower for k in ['login', 'password', '2fa', 'reset', 'profile', 'email', 'delete account', 'permission', 'username']):
        cat = 'Account'
        prio = 'Medium'
    else:
        cat = 'General Inquiry'
        prio = 'Low'

    dept = cat
    return {
        'predicted_category': cat,
        'predicted_priority': prio,
        'assigned_department': dept,
        'category_confidence': '75.0%',
        'priority_confidence': '75.0%',
        'low_confidence': True,
        'fraud_flagged': False,
        'similar_tickets': []
    }


def predict_and_retrieve(subject: str, description: str, top_k: int = 3) -> dict:
    """
    Given a ticket subject and description:
    1. Preprocesses the combined text.
    2. Runs TF-IDF feature extraction.
    3. Detects Fraud / predicts Category & Priority with confidence scores.
    4. Computes fast sparse cosine similarity against historical corpus.
    5. Returns prediction dictionary with confidence metrics and top-3 historical matches.
    
    ENHANCED FEATURES:
    - Prediction confidence percentages using predict_proba()
    - Low confidence flag for manual review (< 45% confidence)
    - Hybrid fraud arbitration (rule-based + ML)
    - Fast sparse matrix operations for similarity retrieval
    """
    global vectorizer, category_model, priority_model, historical_corpus, _is_initialized
    
    if not _is_initialized:
        load_ai_engine()

    raw_combined = f"{subject} {description}"
    cleaned = clean_text(raw_combined)

    # Check for direct security/fraud triggers first (Hybrid Fraud Arbitration)
    text_lower = raw_combined.lower()
    is_fraud_trigger = any(indicator in text_lower for indicator in FRAUD_INDICATORS)

    if not _is_initialized or vectorizer is None:
        result = _heuristic_fallback(subject, description)
        if is_fraud_trigger:
            result['predicted_category'] = 'Fraud'
            result['predicted_priority'] = 'Critical'
            result['assigned_department'] = 'Admin_Fraud'
            result['fraud_flagged'] = True
        return result

    # 1. Transform text using fitted vectorizer
    input_tfidf = vectorizer.transform([cleaned])

    # 2. Predict Category & Priority with Confidence Scoring
    category_confidence = 0.0
    priority_confidence = 0.0
    low_confidence_flag = False
    
    if is_fraud_trigger:
        # Hybrid Fraud Arbitration: Rule-based override
        predicted_category = 'Fraud'
        predicted_priority = 'Critical'
        assigned_dept = 'Admin_Fraud'
        category_confidence = 95.0  # High confidence for rule-based fraud detection
        priority_confidence = 95.0
        fraud_flagged = True
    else:
        # ML-based predictions with probability estimation
        predicted_category = category_model.predict(input_tfidf)[0]
        predicted_priority = priority_model.predict(input_tfidf)[0]
        
        # Calculate confidence scores using predict_proba
        cat_proba = category_model.predict_proba(input_tfidf)[0]
        cat_classes = category_model.classes_
        cat_max_idx = np.argmax(cat_proba)
        category_confidence = float(cat_proba[cat_max_idx]) * 100.0
        
        prio_proba = priority_model.predict_proba(input_tfidf)[0]
        prio_classes = priority_model.classes_
        prio_max_idx = np.argmax(prio_proba)
        priority_confidence = float(prio_proba[prio_max_idx]) * 100.0
        
        # Low confidence flag for manual review
        if category_confidence < 45.0:
            low_confidence_flag = True
        
        # Hybrid Fraud Arbitration: ML-based fraud detection
        fraud_flagged = (predicted_category == 'Fraud')
        
        # Map Category to Department
        if predicted_category in ['Technical', 'Billing', 'Account', 'General Inquiry']:
            assigned_dept = predicted_category
        elif predicted_category == 'Fraud':
            assigned_dept = 'Admin_Fraud'
            predicted_priority = 'Critical'
            fraud_flagged = True
        else:
            assigned_dept = 'General Inquiry'

    # 3. Fast Sparse Cosine Similarity Retrieval (sub-2ms)
    similar_matches = []
    if historical_corpus and 'tfidf_matrix' in historical_corpus and 'metadata' in historical_corpus:
        try:
            corpus_matrix = historical_corpus['tfidf_matrix']
            metadata_list = historical_corpus['metadata']
            
            # Use linear_kernel for faster sparse matrix operations
            # This is equivalent to cosine similarity for normalized TF-IDF vectors
            cos_sims = linear_kernel(input_tfidf, corpus_matrix).flatten()
            
            # Get top indices (sorted descending)
            top_indices = np.argsort(cos_sims)[::-1][:top_k]
            
            for idx in top_indices:
                score = float(cos_sims[idx]) * 100.0  # Percentage
                item = metadata_list[idx]
                
                similar_matches.append({
                    'similar_ticket_ref_id': str(item.get('Ticket_ID', f"HIST-{idx}")),
                    'similarity_score': round(score, 2),
                    'similar_subject': str(item.get('Ticket_Subject', 'Historical Ticket')),
                    'similar_description': str(item.get('Ticket_Description', 'No description available.')),
                    'historical_resolution_hours': int(item.get('Resolution_Time_Hours', 24)) if pd.notna(item.get('Resolution_Time_Hours')) else None,
                    'satisfaction_score': int(item.get('Satisfaction_Score', 5)) if pd.notna(item.get('Satisfaction_Score')) else None,
                    'category': str(item.get('Issue_Category', 'General Inquiry')),
                    'priority': str(item.get('Priority_Level', 'Medium'))
                })
        except Exception as e:
            print(f"[AI Engine] Error computing cosine similarities: {e}")

    return {
        'predicted_category': predicted_category,
        'predicted_priority': predicted_priority,
        'assigned_department': assigned_dept,
        'category_confidence': f"{category_confidence:.1f}%",
        'priority_confidence': f"{priority_confidence:.1f}%",
        'low_confidence': low_confidence_flag,
        'fraud_flagged': fraud_flagged,
        'similar_tickets': similar_matches
    }


# Attempt initial load upon import
load_ai_engine()
