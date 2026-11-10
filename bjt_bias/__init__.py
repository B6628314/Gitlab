"""Flask application factory for the BJT bias calculator."""

from __future__ import annotations

from flask import Flask


def sig(value: float, digits: int = 4) -> str:
    """Format a number with a fixed number of significant digits."""
    return f"{float(value):.{digits}g}"


def create_app() -> Flask:
    app = Flask(__name__)
    app.add_template_filter(sig, "sig")

    from .routes import bp

    app.register_blueprint(bp)
    return app
