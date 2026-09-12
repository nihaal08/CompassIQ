"""
CompassIQ — AI Engine Inference Module
===========================================
Lightweight ML inference module for ticket classification.
- Loads 3 serialized joblib models (TF-IDF vectorizer, Category classifier, Priority classifier)
- Performs text preprocessing and real-time predictions
- Provides safe fallback defaults for academic demonstration

ML Pipeline (Viva Defense):
1. Text Preprocessing: Lowercasing, regex cleaning, stopword removal, lemmatization
2. Feature Extraction: TF-IDF vectorization (max_features=5000, ngrams=(1,2))
3. Classification: Logistic Regression with probability estimation
4. Fallback: Rule-based heuristic if models unavailable
"""

import os
import re
import joblib
import numpy as np
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

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
_is_initialized = False


def clean_text(text: str) -> str:
    """
    Text preprocessing for TF-IDF feature extraction.
    - Converts to lowercase
    - Removes URLs and special characters
    - Removes stopwords and short words
    - Applies lemmatization
    """
    if not isinstance(text, str):
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove URLs
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    
    # Remove special characters, keep only letters and spaces
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    
    # Tokenize and clean
    tokens = text.split()
    cleaned_tokens = [
        lemmatizer.lemmatize(word)
        for word in tokens
        if word not in stop_words and len(word) > 2
    ]
    
    return ' '.join(cleaned_tokens)


def load_ai_engine(force_reload: bool = False):
    """
    Loads the 3 required ML model artifacts for fast startup.
    - tfidf_vectorizer.joblib: TF-IDF feature extractor
    - category_model.joblib: Ticket category classifier
    - priority_model.joblib: Ticket priority classifier
    
    Returns True if successful, False otherwise.
    """
    global vectorizer, category_model, priority_model, _is_initialized

    if _is_initialized and not force_reload:
        return True

    # Define model file paths
    p_vectorizer = os.path.join(MODELS_DIR, 'tfidf_vectorizer.joblib')
    p_cat = os.path.join(MODELS_DIR, 'category_model.joblib')
    p_prio = os.path.join(MODELS_DIR, 'priority_model.joblib')

    # Check for missing model files
    missing_files = [p for p in [p_vectorizer, p_cat, p_prio] if not os.path.exists(p)]
    
    if missing_files:
        print(f"[AI Engine] Missing model artifacts: {missing_files}. Run train_model.py to build them.")
        return False

    try:
        # Load the 3 model artifacts
        vectorizer = joblib.load(p_vectorizer)
        category_model = joblib.load(p_cat)
        priority_model = joblib.load(p_prio)
        _is_initialized = True
        print("[AI Engine] Successfully loaded TF-IDF vectorizer and classification models.")
        return True
    except Exception as e:
        print(f"[AI Engine] Error loading models: {e}")
        return False


def _heuristic_fallback(subject: str, description: str):
    """
    Rule-based fallback for when ML models are unavailable.
    Uses keyword matching to predict category and priority.
    Safe defaults: 'General Inquiry', 'Medium', 'Technical'
    """
    text_lower = f"{subject} {description}".lower()

    # Technical issues (keywords: error, crash, bug, fail, sync, 502, 404, api, gateway, freeze, broken)
    if any(k in text_lower for k in ['error', 'crash', 'bug', 'fail', 'sync', '502', '404', 'api', 'gateway', 'freeze', 'broken']):
        cat = 'Technical'
        prio = 'High' if ('crash' in text_lower or '502' in text_lower or 'critical' in text_lower) else 'Medium'
    
    # Billing issues (keywords: charge, refund, invoice, payment, card, billing, subscription, renew, dollar, $, fee)
    elif any(k in text_lower for k in ['charge', 'refund', 'invoice', 'payment', 'card', 'billing', 'subscription', 'renew', 'dollar', '$', 'fee']):
        cat = 'Billing'
        prio = 'High' if ('unauthorized' in text_lower or 'overcharge' in text_lower or 'double' in text_lower) else 'Medium'
    
    # Account issues (keywords: login, password, 2fa, reset, profile, email, delete account, permission, username)
    elif any(k in text_lower for k in ['login', 'password', '2fa', 'reset', 'profile', 'email', 'delete account', 'permission', 'username']):
        cat = 'Account'
        prio = 'Medium'
    
    # Default fallback
    else:
        cat = 'General Inquiry'
        prio = 'Low'

    # Map category to department
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
    Main AI inference function for ticket classification.
    
    Process:
    1. Validates input text
    2. Preprocesses text (cleaning, tokenization)
    3. Transforms text using TF-IDF vectorizer
    4. Predicts category and priority using Logistic Regression
    5. Calculates confidence scores using predict_proba()
    6. Returns clean prediction dictionary
    
    Args:
        subject: Ticket subject line
        description: Ticket description text
        top_k: Kept for API compatibility (not used in simplified version)
    
    Returns:
        Dictionary with predicted_category, predicted_priority, assigned_department,
        confidence scores, and empty similar_tickets array
    """
    global vectorizer, category_model, priority_model, _is_initialized

    # Step 1: Input validation
    if not subject or not description or not isinstance(subject, str) or not isinstance(description, str):
        print("[AI Engine] Warning: Empty or invalid input, using safe fallback")
        return {
            'predicted_category': 'General Inquiry',
            'predicted_priority': 'Medium',
            'assigned_department': 'Technical',
            'category_confidence': '50.0%',
            'priority_confidence': '50.0%',
            'low_confidence': True,
            'fraud_flagged': False,
            'similar_tickets': []
        }

    try:
        # Step 2: Load models if not already loaded
        if not _is_initialized:
            load_ai_engine()

        # Step 3: Text preprocessing
        raw_combined = f"{subject} {description}"
        cleaned = clean_text(raw_combined)

        # Step 4: Use heuristic fallback if models unavailable
        if not _is_initialized or vectorizer is None:
            result = _heuristic_fallback(subject, description)
            return result

        # Step 5: Transform text using TF-IDF vectorizer
        input_tfidf = vectorizer.transform([cleaned])

        # Step 6: Predict category and priority with confidence scoring
        category_confidence = 0.0
        priority_confidence = 0.0
        low_confidence_flag = False
        fraud_flagged = False

        try:
            # Category prediction with probability estimation
            predicted_category = category_model.predict(input_tfidf)[0]
            
            # Calculate confidence score using predict_proba
            cat_proba = category_model.predict_proba(input_tfidf)[0]
            cat_classes = category_model.classes_
            cat_max_idx = np.argmax(cat_proba)
            category_confidence = float(cat_proba[cat_max_idx]) * 100.0

            # Priority prediction with probability estimation
            predicted_priority = priority_model.predict(input_tfidf)[0]
            
            # Calculate confidence score using predict_proba
            prio_proba = priority_model.predict_proba(input_tfidf)[0]
            prio_classes = priority_model.classes_
            prio_max_idx = np.argmax(prio_proba)
            priority_confidence = float(prio_proba[prio_max_idx]) * 100.0

            # Low confidence flag for manual review (< 45% confidence)
            if category_confidence < 45.0:
                low_confidence_flag = True

            # Map category to department (1:1 mapping for simplicity)
            if predicted_category in ['Technical', 'Billing', 'Account', 'General Inquiry']:
                assigned_dept = predicted_category
            else:
                assigned_dept = 'General Inquiry'

        except Exception as e:
            print(f"[AI Engine] ML prediction error: {e}, using safe fallback")
            # Safe fallback on ML errors
            predicted_category = 'General Inquiry'
            predicted_priority = 'Medium'
            assigned_dept = 'Technical'
            category_confidence = 50.0
            priority_confidence = 50.0
            low_confidence_flag = True
            fraud_flagged = False

        # Step 7: Return clean prediction dictionary
        return {
            'predicted_category': predicted_category,
            'predicted_priority': predicted_priority,
            'assigned_department': assigned_dept,
            'category_confidence': f"{category_confidence:.1f}%",
            'priority_confidence': f"{priority_confidence:.1f}%",
            'low_confidence': low_confidence_flag,
            'fraud_flagged': fraud_flagged,
            'similar_tickets': []  # Empty array for API compatibility
        }

    except Exception as e:
        print(f"[AI Engine] Unexpected error in predict_and_retrieve: {e}, using safe fallback")
        return {
            'predicted_category': 'General Inquiry',
            'predicted_priority': 'Medium',
            'assigned_department': 'Technical',
            'category_confidence': '50.0%',
            'priority_confidence': '50.0%',
            'low_confidence': True,
            'fraud_flagged': False,
            'similar_tickets': []
        }


# Note: AI engine loading is controlled explicitly in app.py to prevent
# double-loading during Flask debug reloader parent/child process spawning
