import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from CompassIQ.ml_engine import get_ml_engine

# All test cases as specified
test_cases = [
    {
        "subject": "Login issue",
        "description": "I cannot log into my account.",
        "expected_category": "Account"
    },
    {
        "subject": "Account security",
        "description": "My account was hacked.",
        "expected_category": "Fraud"
    },
    {
        "subject": "Double charge",
        "description": "I was charged twice for the same purchase.",
        "expected_category": "Billing"
    },
    {
        "subject": "Payment issue",
        "description": "My payment failed.",
        "expected_category": "Billing"
    },
    {
        "subject": "Application crash",
        "description": "The application crashes when uploading a document.",
        "expected_category": "Technical"
    },
    {
        "subject": "Account requirements",
        "description": "What documents are required to create an account?",
        "expected_category": "General Inquiry"
    }
]

ml_engine = get_ml_engine()

print("FINAL COMPREHENSIVE TEST CASES")
print("=" * 80)

passed_count = 0

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
    
    if result.get('fallback_applied'):
        print(f"FALLBACK APPLIED: {result['fallback_reason']}")
    
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
    if category_match == "PASS":
        passed_count += 1
    print(f"\nCategory Match: {category_match}")
    print("=" * 80)

# Summary
print(f"\nSUMMARY:")
print(f"Total test cases: {len(test_cases)}")
print(f"Passed: {passed_count}")
print(f"Failed: {len(test_cases) - passed_count}")
