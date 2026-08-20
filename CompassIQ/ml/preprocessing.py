import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# Download the language resources used for cleaning.
nltk.download("stopwords", quiet=True)
nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)

# Create reusable text-cleaning helpers.
stop_words = set(stopwords.words("english"))
lemmatizer = WordNetLemmatizer()

# Clean one ticket's text.
def preprocess_text(text):
    if not isinstance(text, str):
        return ""
    
    # Normalize case.
    text = text.lower()
    
    # Remove links and punctuation.
    text = re.sub(r"http\S+|www\S+|https\S+", "", text)
    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    
    # Remove common words and reduce words to their base form.
    words = [
        lemmatizer.lemmatize(word)
        for word in text.split()
        if word not in stop_words
    ]
    
    return " ".join(words)
