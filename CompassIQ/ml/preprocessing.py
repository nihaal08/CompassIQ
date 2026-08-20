"""
CompassIQ - NLP Preprocessing Module
=====================================
Cleans and normalizes customer support ticket text
before it is fed into TF-IDF vectorizers or ML models.

Steps performed:
    1. Lowercase conversion
    2. URL removal
    3. Non-alphabetic character removal
    4. Extra whitespace removal
    5. Stopword removal
    6. Lemmatization
"""

import re
import nltk

from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer


# ============================================================
# NLTK RESOURCE DOWNLOAD (runs once on first use)
# ============================================================

try:
    stopwords.words("english")
except LookupError:
    nltk.download("stopwords")

try:
    WordNetLemmatizer().lemmatize("test")
except LookupError:
    nltk.download("wordnet")
    nltk.download("omw-1.4")


# ============================================================
# GLOBAL OBJECTS (initialized once)
# ============================================================

stop_words = set(stopwords.words("english"))

lemmatizer = WordNetLemmatizer()


# ============================================================
# PREPROCESS FUNCTION
# ============================================================

def preprocess_text(text):
    """
    Clean and preprocess customer support ticket text.

    Args:
        text (str): Raw text from Ticket_Subject or
                    Ticket_Description field.

    Returns:
        str: Cleaned, tokenized, lemmatized text string.
             Returns empty string if input is not a string.
    """

    if not isinstance(text, str):
        return ""

    # Convert to lowercase
    text = text.lower()

    # Remove URLs (http, https, www)
    text = re.sub(r"http\S+|www\S+|https\S+", "", text)

    # Keep only alphabetic characters and spaces
    text = re.sub(r"[^a-zA-Z\s]", " ", text)

    # Collapse multiple spaces into one
    text = re.sub(r"\s+", " ", text).strip()

    # Tokenize by splitting on whitespace
    words = text.split()

    # Remove stopwords and apply lemmatization
    words = [
        lemmatizer.lemmatize(word)
        for word in words
        if word not in stop_words
    ]

    return " ".join(words)
