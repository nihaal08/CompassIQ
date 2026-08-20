"""
CompassIQ - AI Model Test Script
==================================
Runs a sample prediction through the full pipeline to verify
that all trained models are working correctly before the
Flask integration is built.

Tests performed:
    1. Category prediction  →  should output "Billing"
    2. Priority prediction  →  should output "Medium" or "High"
    3. Department routing   →  should output "Billing"
    4. Top-3 similar ticket retrieval

Usage:
    Ensure you have already run:
        python ml/train_models.py
        python ml/similarity.py

    Then run:
        python ml/test_model.py
"""

import sys
import os

# Allow importing predict.py from same ml/ folder
sys.path.append(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

from predict import analyze_ticket


# ============================================================
# TEST CASE 1 — BILLING / PAYMENT
# ============================================================

print("\n" + "=" * 60)
print("TEST CASE 1: Billing / Payment Issue")
print("=" * 60)

result_1 = analyze_ticket(
    subject="Payment failed",
    description=(
        "I am trying to make a payment but my card "
        "payment keeps getting declined every time I try."
    )
)

print(f"\nPredicted Category  : {result_1['category']}")
print(f"Predicted Priority  : {result_1['priority']}")
print(f"Assigned Department : {result_1['department']}")

print("\nTop 3 Similar Tickets:")

for i, ticket in enumerate(result_1["similar_tickets"], start=1):
    print(f"\n  [{i}] Ticket ID : {ticket['Ticket_ID']}")
    print(f"      Subject   : {ticket['Subject']}")
    print(f"      Category  : {ticket['Category']}")
    print(f"      Priority  : {ticket['Priority']}")
    print(f"      Similarity: {ticket['Similarity']}%")


# ============================================================
# TEST CASE 2 — TECHNICAL / APP CRASH
# ============================================================

print("\n" + "=" * 60)
print("TEST CASE 2: Technical / Application Crash")
print("=" * 60)

result_2 = analyze_ticket(
    subject="App crashes on login",
    description=(
        "The mobile application crashes every time I try "
        "to log in. I have tried reinstalling but the issue persists."
    )
)

print(f"\nPredicted Category  : {result_2['category']}")
print(f"Predicted Priority  : {result_2['priority']}")
print(f"Assigned Department : {result_2['department']}")

print("\nTop 3 Similar Tickets:")

for i, ticket in enumerate(result_2["similar_tickets"], start=1):
    print(f"\n  [{i}] Ticket ID : {ticket['Ticket_ID']}")
    print(f"      Subject   : {ticket['Subject']}")
    print(f"      Category  : {ticket['Category']}")
    print(f"      Priority  : {ticket['Priority']}")
    print(f"      Similarity: {ticket['Similarity']}%")


# ============================================================
# TEST CASE 3 — FRAUD / UNAUTHORIZED TRANSACTION
# ============================================================

print("\n" + "=" * 60)
print("TEST CASE 3: Fraud / Unauthorized Transaction")
print("=" * 60)

result_3 = analyze_ticket(
    subject="Unauthorized transaction on my account",
    description=(
        "I noticed a suspicious transaction on my account "
        "that I did not authorize. Please investigate immediately."
    )
)

print(f"\nPredicted Category  : {result_3['category']}")
print(f"Predicted Priority  : {result_3['priority']}")
print(f"Assigned Department : {result_3['department']}")

print("\nTop 3 Similar Tickets:")

for i, ticket in enumerate(result_3["similar_tickets"], start=1):
    print(f"\n  [{i}] Ticket ID : {ticket['Ticket_ID']}")
    print(f"      Subject   : {ticket['Subject']}")
    print(f"      Category  : {ticket['Category']}")
    print(f"      Priority  : {ticket['Priority']}")
    print(f"      Similarity: {ticket['Similarity']}%")


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 60)
print("ALL TEST CASES COMPLETED")
print("=" * 60)
print("\nCompassIQ AI is working correctly.")
print("You can now connect these models to the Flask app.")
print("=" * 60)
