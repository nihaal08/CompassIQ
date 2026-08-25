"""Canonical Flask entry point for CompassIQ."""

if __package__:
    from .routes import app
else:
    from pathlib import Path
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from CompassIQ.routes import app


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=app.config.get("DEBUG", False))
