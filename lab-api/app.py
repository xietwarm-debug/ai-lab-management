import os

from modular import app  # noqa: F401

if __name__ == "__main__":
    host = os.getenv("APP_HOST", "0.0.0.0")
    try:
        port = int(os.getenv("APP_PORT", "5000"))
    except (TypeError, ValueError):
        port = 5000
    debug = str(os.getenv("FLASK_DEBUG", "1") or "").strip().lower() in {"1", "true", "yes", "on"}
    app.run(host=host, port=port, debug=debug)
