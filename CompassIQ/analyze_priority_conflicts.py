import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from CompassIQ.ml.preprocessing import preprocess_text
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Load dataset
df = pd.read_csv('data/enhanced_customer_support_data.csv')

# Preprocess text
df['Ticket_Subject'] = df['Ticket_Subject'].fillna('')
df['Ticket_Description'] = df['Ticket_Description'].fillna('')
df['text'] = [preprocess_text(f"{subject} {description}") for subject, description in zip(df['Ticket_Subject'], df['Ticket_Description'])]

print("Priority Model Conflicting Labels Analysis")
print("=" * 80)

# Group by similar text patterns and check priority consistency
# Focus on common patterns that might have inconsistent priorities

# Analyze "login failed" pattern specifically
login_failed = df[df['text'].str.contains('login failed', case=False, na=False)]
print(f"\n'login failed' tickets: {len(login_failed)}")
print(f"Priority distribution for 'login failed':")
print(login_failed['Priority_Level'].value_counts())

print(f"\nSample 'login failed' tickets by priority:")
for priority in ['Critical', 'High', 'Medium', 'Low']:
    samples = login_failed[login_failed['Priority_Level'] == priority].head(3)
    print(f"\n{priority} priority:")
    for idx, row in samples.iterrows():
        print(f"  - {row['Ticket_ID']}: {row['Ticket_Subject']} - {row['Ticket_Description'][:60]}...")

# Analyze "payment" patterns
payment_tickets = df[df['text'].str.contains('payment', case=False, na=False)]
print(f"\n{'='*80}")
print(f"'payment' tickets: {len(payment_tickets)}")
print(f"Priority distribution for 'payment':")
print(payment_tickets['Priority_Level'].value_counts())

print(f"\nSample 'payment' tickets by priority:")
for priority in ['Critical', 'High', 'Medium', 'Low']:
    samples = payment_tickets[payment_tickets['Priority_Level'] == priority].head(2)
    print(f"\n{priority} priority:")
    for idx, row in samples.iterrows():
        print(f"  - {row['Ticket_ID']}: {row['Ticket_Subject']} - {row['Ticket_Description'][:60]}...")

# Analyze "account" patterns
account_tickets = df[df['text'].str.contains('account', case=False, na=False)]
print(f"\n{'='*80}")
print(f"'account' tickets: {len(account_tickets)}")
print(f"Priority distribution for 'account':")
print(account_tickets['Priority_Level'].value_counts())

# Use TF-IDF to find similar tickets with different priorities
print(f"\n{'='*80}")
print("SIMILARITY ANALYSIS - Finding similar tickets with different priorities")

# Sample subset for analysis
sample_size = min(500, len(df))
df_sample = df.head(sample_size)

vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=5000)
tfidf_matrix = vectorizer.fit_transform(df_sample['text'])

# Find similar pairs with different priorities
conflicting_pairs = []
threshold = 0.8  # High similarity threshold

for i in range(sample_size):
    for j in range(i+1, sample_size):
        similarity = cosine_similarity(tfidf_matrix[i:i+1], tfidf_matrix[j:j+1])[0][0]
        if similarity > threshold:
            if df_sample.iloc[i]['Priority_Level'] != df_sample.iloc[j]['Priority_Level']:
                conflicting_pairs.append((i, j, similarity, 
                                         df_sample.iloc[i]['Priority_Level'], 
                                         df_sample.iloc[j]['Priority_Level']))

print(f"Found {len(conflicting_pairs)} similar ticket pairs with different priorities (threshold > {threshold})")

if len(conflicting_pairs) > 0:
    print(f"\nSample conflicting pairs:")
    for i, j, sim, prio1, prio2 in conflicting_pairs[:10]:
        print(f"\nSimilarity: {sim:.3f}")
        print(f"Ticket 1 (ID: {df_sample.iloc[i]['Ticket_ID']}): {prio1}")
        print(f"  Subject: {df_sample.iloc[i]['Ticket_Subject']}")
        print(f"  Description: {df_sample.iloc[i]['Ticket_Description'][:60]}...")
        print(f"Ticket 2 (ID: {df_sample.iloc[j]['Ticket_ID']}): {prio2}")
        print(f"  Subject: {df_sample.iloc[j]['Ticket_Subject']}")
        print(f"  Description: {df_sample.iloc[j]['Ticket_Description'][:60]}...")

# Category-based priority distribution
print(f"\n{'='*80}")
print("Priority distribution by category:")
print(df.groupby('Issue_Category')['Priority_Level'].value_counts().unstack().fillna(0))
