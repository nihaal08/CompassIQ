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
    
    DATA LEAKAGE PREVENTION:
    - 80/20 train-test split performed BEFORE vectorizer fitting
    - Vectorizer fitted strictly on training data
    - SMOTE applied strictly to training TF-IDF matrix
    - Historical corpus built strictly from training partition
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

    # ==========================================================================
    # DATA LEAKAGE PREVENTION: Train-Test Split BEFORE Vectorization
    # ==========================================================================
    print("\n" + "="*70)
    print(" DATA LEAKAGE PREVENTION: Train-Test Split")
    print("="*70)
    
    # Perform 80/20 train-test split BEFORE any feature extraction
    train_df, test_df = train_test_split(
        df, test_size=0.20, stratify=df['Issue_Category'], random_state=42
    )
    
    print(f"[Split] Training set: {len(train_df):,} samples ({len(train_df)/len(df)*100:.1f}%)")
    print(f"[Split] Test set: {len(test_df):,} samples ({len(test_df)/len(df)*100:.1f}%)")
    
    # Display class distributions for imbalance analysis
    print("\n[Class Distribution] Issue_Category (Training):")
    cat_dist_train = train_df['Issue_Category'].value_counts(normalize=True) * 100
    for cat, pct in cat_dist_train.items():
        print(f"  {cat}: {pct:.2f}%")
    
    print("\n[Class Distribution] Priority_Level (Training):")
    prio_dist_train = train_df['Priority_Level'].value_counts(normalize=True) * 100
    for prio, pct in prio_dist_train.items():
        print(f"  {prio}: {pct:.2f}%")

    # ==========================================================================
    # FEATURE EXTRACTION: Vectorizer fitted STRICTLY on training data
    # ==========================================================================
    print("\n" + "="*70)
    print(" FEATURE EXTRACTION: TF-IDF Vectorization")
    print("="*70)
    print("[TF-IDF] Fitting vectorizer strictly on training data (max_features=5000, ngrams=(1,2))...")
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), sublinear_tf=True)
    X_train_tfidf = vectorizer.fit_transform(train_df['cleaned_text'])
    X_test_tfidf = vectorizer.transform(test_df['cleaned_text'])
    
    print(f"[TF-IDF] Training TF-IDF matrix shape: {X_train_tfidf.shape}")
    print(f"[TF-IDF] Test TF-IDF matrix shape: {X_test_tfidf.shape}")

    # -------------------------------------------------------------------------
    # Model 1: Issue Category Classifier
    # -------------------------------------------------------------------------
    print("\n" + "="*70)
    print(" TRAINING MODEL 1: Issue Category Classifier")
    print("="*70)
    y_train_cat = train_df['Issue_Category']
    y_test_cat = test_df['Issue_Category']

    print(f"[SMOTE] Balancing Category Training Set (Original: {dict(pd.Series(y_train_cat).value_counts())})...")
    smote_cat = SMOTE(sampling_strategy='auto', random_state=42)
    X_train_cat_smote, y_train_cat_smote = smote_cat.fit_resample(X_train_tfidf, y_train_cat)
    print(f"[SMOTE] Balanced Category Shape: {X_train_cat_smote.shape}")
    print(f"[SMOTE] Balanced Distribution: {dict(pd.Series(y_train_cat_smote).value_counts())}")

    cat_model = LogisticRegression(
        max_iter=1000, 
        class_weight='balanced', 
        C=1.5, 
        solver='lbfgs',
        multi_class='multinomial'
    )
    cat_model.fit(X_train_cat_smote, y_train_cat_smote)
    
    y_pred_cat = cat_model.predict(X_test_tfidf)
    
    # Rigorous Minority Class Evaluation
    print("\n--- Category Classification Report ---")
    print(classification_report(y_test_cat, y_pred_cat))
    
    cat_macro_f1 = f1_score(y_test_cat, y_pred_cat, average='macro')
    cat_weighted_f1 = f1_score(y_test_cat, y_pred_cat, average='weighted')
    print(f"\n[Metrics] Category Macro F1-Score: {cat_macro_f1:.4f}")
    print(f"[Metrics] Category Weighted F1-Score: {cat_weighted_f1:.4f}")
    
    # Explicit minority class metrics
    cat_report = classification_report(y_test_cat, y_pred_cat, output_dict=True)
    minority_classes = ['Fraud']  # Add other minority classes as needed
    for cls in minority_classes:
        if cls in cat_report:
            print(f"[Minority Class] {cls} - Precision: {cat_report[cls]['precision']:.4f}, Recall: {cat_report[cls]['recall']:.4f}, F1: {cat_report[cls]['f1-score']:.4f}")

    # -------------------------------------------------------------------------
    # Model 2: Priority Level Classifier
    # -------------------------------------------------------------------------
    print("\n" + "="*70)
    print(" TRAINING MODEL 2: Priority Level Classifier")
    print("="*70)
    y_train_prio = train_df['Priority_Level']
    y_test_prio = test_df['Priority_Level']

    print(f"[SMOTE] Balancing Priority Training Set (Original: {dict(pd.Series(y_train_prio).value_counts())})...")
    smote_prio = SMOTE(sampling_strategy='auto', random_state=42)
    X_train_prio_smote, y_train_prio_smote = smote_prio.fit_resample(X_train_tfidf, y_train_prio)
    print(f"[SMOTE] Balanced Priority Shape: {X_train_prio_smote.shape}")
    print(f"[SMOTE] Balanced Distribution: {dict(pd.Series(y_train_prio_smote).value_counts())}")

    prio_model = LogisticRegression(
        max_iter=1000, 
        class_weight='balanced', 
        C=1.5, 
        solver='lbfgs',
        multi_class='multinomial'
    )
    prio_model.fit(X_train_prio_smote, y_train_prio_smote)
    
    y_pred_prio = prio_model.predict(X_test_tfidf)
    
    # Rigorous Minority Class Evaluation
    print("\n--- Priority Classification Report ---")
    print(classification_report(y_test_prio, y_pred_prio))
    
    prio_macro_f1 = f1_score(y_test_prio, y_pred_prio, average='macro')
    prio_weighted_f1 = f1_score(y_test_prio, y_pred_prio, average='weighted')
    print(f"\n[Metrics] Priority Macro F1-Score: {prio_macro_f1:.4f}")
    print(f"[Metrics] Priority Weighted F1-Score: {prio_weighted_f1:.4f}")
    
    # Explicit minority class metrics
    prio_report = classification_report(y_test_prio, y_pred_prio, output_dict=True)
    minority_classes_prio = ['Critical']  # Critical is minority priority class
    for cls in minority_classes_prio:
        if cls in prio_report:
            print(f"[Minority Class] {cls} - Precision: {prio_report[cls]['precision']:.4f}, Recall: {prio_report[cls]['recall']:.4f}, F1: {prio_report[cls]['f1-score']:.4f}")

    # -------------------------------------------------------------------------
    # Historical Corpus Matrix for Cosine Similarity
    # -------------------------------------------------------------------------
    print("\n" + "="*70)
    print(" BUILDING HISTORICAL SIMILARITY CORPUS (TRAINING PARTITION ONLY)")
    print("="*70)
    
    # Store essential metadata from TRAINING partition only to prevent data leakage
    metadata_cols = ['Ticket_ID', 'Ticket_Subject', 'Ticket_Description']
    if 'Resolution_Time_Hours' in train_df.columns:
        metadata_cols.append('Resolution_Time_Hours')
    if 'Satisfaction_Score' in train_df.columns:
        metadata_cols.append('Satisfaction_Score')
    if 'Issue_Category' in train_df.columns:
        metadata_cols.append('Issue_Category')
    if 'Priority_Level' in train_df.columns:
        metadata_cols.append('Priority_Level')

    # Build historical corpus strictly from training partition
    historical_df = train_df[metadata_cols].copy().reset_index(drop=True)
    historical_corpus_dict = {
        'tfidf_matrix': X_train_tfidf,  # Use training TF-IDF matrix only
        'metadata': historical_df.to_dict(orient='records'),
        'vectorizer': vectorizer  # Include vectorizer for consistent transformation
    }
    print(f"[Corpus] Cached {len(historical_df):,} historical tickets with TF-IDF vectors (TRAINING PARTITION ONLY)")
    print(f"[Corpus] Sparse matrix shape: {X_train_tfidf.shape}, Memory: ~{X_train_tfidf.data.nbytes / 1024 / 1024:.1f} MB")

    # -------------------------------------------------------------------------
    # Serialization via Joblib with Probability Estimation Enabled
    # -------------------------------------------------------------------------
    print("\n" + "="*70)
    print(" SERIALIZING ARTIFACTS (WITH PROBABILITY ESTIMATION)")
    print("="*70)
    
    p_vectorizer = os.path.join(MODELS_DIR, 'tfidf_vectorizer.joblib')
    p_cat = os.path.join(MODELS_DIR, 'category_model.joblib')
    p_prio = os.path.join(MODELS_DIR, 'priority_model.joblib')
    p_corpus = os.path.join(MODELS_DIR, 'historical_corpus.joblib')

    joblib.dump(vectorizer, p_vectorizer, compress=3)
    print(f" [OK] Vectorizer saved to {p_vectorizer}")

    joblib.dump(cat_model, p_cat, compress=3)
    print(f" [OK] Category Model saved to {p_cat} (probability estimation enabled)")

    joblib.dump(prio_model, p_prio, compress=3)
    print(f" [OK] Priority Model saved to {p_prio} (probability estimation enabled)")

    joblib.dump(historical_corpus_dict, p_corpus, compress=3)
    print(f" [OK] Historical Corpus saved to {p_corpus} (sparse matrix + metadata)")

    print("\n" + "="*70)
    print(" TRAINING SUMMARY")
    print("="*70)
    print(f"Category Model - Macro F1: {cat_macro_f1:.4f}, Weighted F1: {cat_weighted_f1:.4f}")
    print(f"Priority Model - Macro F1: {prio_macro_f1:.4f}, Weighted F1: {prio_weighted_f1:.4f}")
    print(f"Historical Corpus - {len(historical_df):,} training samples for similarity retrieval")
    print("\n[SUCCESS] CompassIQ Training & Serialization completed successfully!")
    print("[NOTE] Data leakage prevention: Test partition remains completely unseen during training.")


if __name__ == '__main__':
    train_and_export()
