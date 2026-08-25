import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from CompassIQ.ml_engine import get_ml_engine

# Test cases with more realistic descriptions
test_cases = [
    {
        "subject": "Account security issue",
        "description": "My account was hacked and someone changed my password. I need immediate help to secure my account.",
        "expected_category": "Fraud"
    },
    {
        "subject": "Account creation inquiry",
        "description": "What documents are required to create an account? I want to know the requirements before signing up.",
        "expected_category": "General Inquiry"
    }
]

ml_engine = get_ml_engine()

print("IMPROVED TEST CASES WITH MORE CONTEXT")
print("=" * 80)

for i, test in enumerate(test_cases, 1):
    result = ml_engine.predict_ticket(test["subject"], test["description"])
    similar = ml_engine.find_similar_tickets(test["subject"], test["description"], top_n=3)
    rec = ml_engine.generate_solution_recommendation(similar, test["expected_category"])
    
    print(f"\nTest Case {i}:")
    print(f"Input: {test['description']}")
    print(f"Expected Category: {test['expected_category']}")
    print(f"Predicted Category: {result['category']}")
    print(f"Category Confidence: {result['category_confidence']}%")
    print(f"Predicted Priority: {result['priority']}")
    print(f"Priority Confidence: {result['priority_confidence']}%")
    print(f"Department: {result['assigned_department']}")
    
    print(f"\nTop 3 Similar Tickets:")
    if similar:
        for j, sim in enumerate(similar, 1):
            print(f"  {j}. {sim['ticket_id']} - {sim['category']} ({sim['similarity']}% match)")
    else:
        print("  No similar tickets found")
    
    print(f"\nRecommended Solution:")
    print(f"  {rec['primary_solution']}")
    
    # Check if prediction matches expected
    category_match = "PASS" if result['category'] == test['expected_category'] else "FAIL"
    print(f"\nCategory Match: {category_match}")
    print("=" * 80)
