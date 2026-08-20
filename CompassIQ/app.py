from flask import Flask
from config import DevelopmentConfig
from ml.predict import analyze_ticket

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

@app.route("/")
def index():
    return "<h2>CompassIQ is running.</h2><p>AI models trained and ready.</p>"

@app.route("/health")
def health():
    try:
        test_result = analyze_ticket("test ticket", "health check")
        return {
            "status": "ok",
            "category": test_result["category"],
            "priority": test_result["priority"]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

# Run Flask application
if __name__ == "__main__":
    app.run(debug=True)
