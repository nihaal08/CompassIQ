"""
CompassIQ — AI Engine Model Training & Evaluation Pipeline
==========================================================
Trains NLP & Machine Learning models for Ticket Category and Priority classification,
generates EDA visualizations, applies SMOTE for class balancing, builds the historical
corpus similarity matrix, and exports serialized joblib artifacts.
"""

import os
import re
import sys
import nltk
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from imblearn.over_sampling import SMOTE

# Ensure required NLTK resources are available
for resource in ['stopwords', 'wordnet', 'punkt', 'punkt_tab', 'omw-1.4']:
    try:
        nltk.download(resource, quiet=True)
    except Exception as e:
        print(f"[NLTK] Warning downloading {resource}: {e}")

lemmatizer = WordNetLemmatizer()
try:
    stop_words = set(stopwords.words('english'))
except Exception:
    stop_words = set()

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
PLOTS_DIR = os.path.join(BASE_DIR, 'static', 'plots')

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(PLOTS_DIR, exist_ok=True)


def clean_text(text: str) -> str:
    """
    Cleans raw text: lowercasing, regex stripping special chars & digits,
    stopword removal, and lemmatization.
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


def load_dataset() -> pd.DataFrame:
    """
    Finds and loads customer support ticket dataset.
    """
    candidate_paths = [
        os.path.join(BASE_DIR, 'customer_support_data.csv'),
        os.path.join(BASE_DIR, 'enhanced_customer_support_data.csv'),
    ]
    
    target_path = None
    for p in candidate_paths:
        if os.path.exists(p):
            target_path = p
            break
            
    if not target_path:
        raise FileNotFoundError(
            "Could not find customer_support_data.csv or enhanced_customer_support_data.csv in project directory."
        )
        
    print(f"[Dataset] Loading data from: {target_path}")
    df = pd.read_csv(target_path)
    print(f"[Dataset] Successfully loaded {len(df):,} records with columns: {list(df.columns)}")
    return df


def generate_eda_visualizations(df: pd.DataFrame):
    """
    Generates and saves exploratory data analysis plots.
    """
    print("[EDA] Generating Exploratory Data Analysis plots...")
    sns.set_theme(style="darkgrid", palette="muted")
    
    # 1. Issue Category Distribution
    plt.figure(figsize=(10, 5))
    if 'Issue_Category' in df.columns:
        cat_counts = df['Issue_Category'].value_counts()
        ax = sns.barplot(x=cat_counts.index, y=cat_counts.values, palette='crest')
        plt.title('Ticket Distribution by Issue Category', fontsize=14, fontweight='bold', color='#121824')
        plt.xlabel('Category', fontsize=11)
        plt.ylabel('Count', fontsize=11)
        plt.xticks(rotation=15)
        for p in ax.patches:
            ax.annotate(f'{int(p.get_height())}', (p.get_x() + p.get_width() / 2., p.get_height()),
                        ha='center', va='center', xytext=(0, 5), textcoords='offset points', fontsize=9)
        plt.tight_layout()
        plot1_path = os.path.join(PLOTS_DIR, 'eda_category_distribution.png')
        plt.savefig(plot1_path, dpi=150)
        plt.close()
        print(f" -> Saved Category Distribution plot to {plot1_path}")

    # 2. Priority Level Distribution
    plt.figure(figsize=(8, 5))
    if 'Priority_Level' in df.columns:
        prio_counts = df['Priority_Level'].value_counts()
        ax = sns.barplot(x=prio_counts.index, y=prio_counts.values, palette='magma')
        plt.title('Ticket Distribution by Priority Level', fontsize=14, fontweight='bold', color='#121824')
        plt.xlabel('Priority Level', fontsize=11)
        plt.ylabel('Count', fontsize=11)
        for p in ax.patches:
            ax.annotate(f'{int(p.get_height())}', (p.get_x() + p.get_width() / 2., p.get_height()),
                        ha='center', va='center', xytext=(0, 5), textcoords='offset points', fontsize=9)
        plt.tight_layout()
        plot2_path = os.path.join(PLOTS_DIR, 'eda_priority_distribution.png')
        plt.savefig(plot2_path, dpi=150)
        plt.close()
        print(f" -> Saved Priority Distribution plot to {plot2_path}")

    # 3. Text Length Distribution
    plt.figure(figsize=(10, 5))
    if 'raw_text' in df.columns:
        lengths = df['raw_text'].apply(lambda x: len(str(x).split()))
        sns.histplot(lengths, bins=40, kde=True, color='#0066FF')
        plt.title('Ticket Text Word Count Distribution', fontsize=14, fontweight='bold', color='#121824')
        plt.xlabel('Word Count', fontsize=11)
        plt.ylabel('Frequency', fontsize=11)
        plt.tight_layout()
        plot3_path = os.path.join(PLOTS_DIR, 'eda_text_length_distribution.png')
        plt.savefig(plot3_path, dpi=150)
        plt.close()
        print(f" -> Saved Text Length Distribution plot to {plot3_path}")


def train_and_export():
    """
    Main execution workflow for preprocessing, SMOTE balancing,
    model training, evaluation, and artifact serialization.
    """
    df = load_dataset()

    # Normalize column names if needed
    col_mapping = {
        'Ticket_ID': 'Ticket_ID',
        'Ticket_Subject': 'Ticket_Subject',
        'Ticket_Description': 'Ticket_Description',
        'Issue_Category': 'Issue_Category',
        'Priority_Level': 'Priority_Level',
        'Resolution_Time_Hours': 'Resolution_Time_Hours',
        'Satisfaction_Score': 'Satisfaction_Score'
    }
    
    # Fill NAs
    df['Ticket_Subject'] = df['Ticket_Subject'].fillna('')
    df['Ticket_Description'] = df['Ticket_Description'].fillna('')
    df['raw_text'] = df['Ticket_Subject'] + " " + df['Ticket_Description']
    
    print("[Preprocessing] Cleaning and lemmatizing text...")
    df['cleaned_text'] = df['raw_text'].apply(clean_text)

    # Filter out empty texts if any
    df = df[df['cleaned_text'].str.strip().str.len() > 0].reset_index(drop=True)

    # EDA Visualizations
    generate_eda_visualizations(df)

    # Feature Extraction with TF-IDF
    print("[TF-IDF] Extracting TF-IDF features (max_features=5000, ngrams=(1,2))...")
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), sublinear_tf=True)
    X_tfidf = vectorizer.fit_transform(df['cleaned_text'])

    # -------------------------------------------------------------------------
    # Model 1: Issue Category Classifier
    # -------------------------------------------------------------------------
    print("\n" + "="*70)
    print(" TRAINING MODEL 1: Issue Category Classifier")
    print("="*70)
    y_cat = df['Issue_Category']
    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(
        X_tfidf, y_cat, test_size=0.2, random_state=42, stratify=y_cat
    )

    print(f"[SMOTE] Balancing Category Training Set (Original: {dict(pd.Series(y_train_c).value_counts())})...")
    smote_cat = SMOTE(random_state=42)
    X_train_c_smote, y_train_c_smote = smote_cat.fit_resample(X_train_c, y_train_c)
    print(f"[SMOTE] Balanced Category Shape: {X_train_c_smote.shape}")

    cat_model = LogisticRegression(max_iter=1000, class_weight='balanced', C=1.5, solver='lbfgs')
    cat_model.fit(X_train_c_smote, y_train_c_smote)
    
    y_pred_c = cat_model.predict(X_test_c)
    print("\n--- Category Classification Report ---")
    print(classification_report(y_test_c, y_pred_c))
    cat_f1 = f1_score(y_test_c, y_pred_c, average='weighted')
    print(f"Overall Category Weighted F1-Score: {cat_f1:.4f}")

    # -------------------------------------------------------------------------
    # Model 2: Priority Level Classifier
    # -------------------------------------------------------------------------
    print("\n" + "="*70)
    print(" TRAINING MODEL 2: Priority Level Classifier")
    print("="*70)
    y_prio = df['Priority_Level']
    X_train_p, X_test_p, y_train_p, y_test_p = train_test_split(
        X_tfidf, y_prio, test_size=0.2, random_state=42, stratify=y_prio
    )

    print(f"[SMOTE] Balancing Priority Training Set (Original: {dict(pd.Series(y_train_p).value_counts())})...")
    smote_prio = SMOTE(random_state=42)
    X_train_p_smote, y_train_p_smote = smote_prio.fit_resample(X_train_p, y_train_p)
    print(f"[SMOTE] Balanced Priority Shape: {X_train_p_smote.shape}")

    prio_model = LogisticRegression(max_iter=1000, class_weight='balanced', C=1.5, solver='lbfgs')
    prio_model.fit(X_train_p_smote, y_train_p_smote)
    
    y_pred_p = prio_model.predict(X_test_p)
    print("\n--- Priority Classification Report ---")
    print(classification_report(y_test_p, y_pred_p))
    prio_f1 = f1_score(y_test_p, y_pred_p, average='weighted')
    print(f"Overall Priority Weighted F1-Score: {prio_f1:.4f}")

    # -------------------------------------------------------------------------
    # Historical Corpus Matrix for Cosine Similarity
    # -------------------------------------------------------------------------
    print("\n" + "="*70)
    print(" BUILDING HISTORICAL SIMILARITY CORPUS")
    print("="*70)
    
    # Store essential metadata in a lightweight dataframe
    metadata_cols = ['Ticket_ID', 'Ticket_Subject', 'Ticket_Description']
    if 'Resolution_Time_Hours' in df.columns:
        metadata_cols.append('Resolution_Time_Hours')
    if 'Satisfaction_Score' in df.columns:
        metadata_cols.append('Satisfaction_Score')
    if 'Issue_Category' in df.columns:
        metadata_cols.append('Issue_Category')
    if 'Priority_Level' in df.columns:
        metadata_cols.append('Priority_Level')

    # To optimize lookup speed, we can cap historical index if huge, but 20k is very fast (~15MB)
    historical_df = df[metadata_cols].copy().reset_index(drop=True)
    historical_corpus_dict = {
        'tfidf_matrix': X_tfidf,
        'metadata': historical_df.to_dict(orient='records')
    }
    print(f"[Corpus] Cached {len(historical_df):,} historical tickets with TF-IDF vectors.")

    # -------------------------------------------------------------------------
    # Serialization via Joblib
    # -------------------------------------------------------------------------
    print("\n" + "="*70)
    print(" SERIALIZING ARTIFACTS")
    print("="*70)
    
    p_vectorizer = os.path.join(MODELS_DIR, 'tfidf_vectorizer.joblib')
    p_cat = os.path.join(MODELS_DIR, 'category_model.joblib')
    p_prio = os.path.join(MODELS_DIR, 'priority_model.joblib')
    p_corpus = os.path.join(MODELS_DIR, 'historical_corpus.joblib')

    joblib.dump(vectorizer, p_vectorizer, compress=3)
    print(f" [OK] Vectorizer saved to {p_vectorizer}")

    joblib.dump(cat_model, p_cat, compress=3)
    print(f" [OK] Category Model saved to {p_cat}")

    joblib.dump(prio_model, p_prio, compress=3)
    print(f" [OK] Priority Model saved to {p_prio}")

    joblib.dump(historical_corpus_dict, p_corpus, compress=3)
    print(f" [OK] Historical Corpus saved to {p_corpus}")

    print("\n[SUCCESS] CompassIQ Training & Serialization completed successfully!")


if __name__ == '__main__':
    train_and_export()
