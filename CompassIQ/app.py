"""
CompassIQ - Flask Application Entry Point
==========================================
Week 2 Stub — AI integration groundwork.

This file will be fully developed in Week 3 (Flask routes,
templates, MySQL integration). For now it serves as the
verified entry point to confirm the AI layer loads correctly.

Run:
    python app.py
"""

from flask import Flask

from config import DevelopmentConfig


# ============================================================
# CREATE FLASK APP
# ============================================================

app = Flask(__name__)

app.config.from_object(DevelopmentConfig)


# ============================================================
# HEALTH CHECK ROUTE
# ============================================================

@app.route("/")
def index():
    """
    Temporary home route.
    Returns a plain confirmation that Flask is running.
    Will be replaced with the full dashboard in Week 3.
    """
    return (
        "<h2>CompassIQ is running.</h2>"
        "<p>Week 2 — AI models trained and ready.</p>"
        "<p>Flask routes will be added in Week 3.</p>"
    )


@app.route("/health")
def health():
    """
    Health check endpoint.
    Confirms Flask is up and the AI models can be imported.
    """
    try:
        from ml.predict import analyze_ticket

        test_result = analyze_ticket(
            "test ticket",
            "this is a health check"
        )

        return {
            "status": "ok",
            "ai_status": "models loaded",
            "sample_category": test_result["category"],
            "sample_priority": test_result["priority"]
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }, 500


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
