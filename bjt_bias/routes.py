"""HTTP layer: parse the form, call the engineering core, render the page."""

from __future__ import annotations

from flask import Blueprint, render_template, request

from .engineering import InputError, analyze, compare, parse_inputs

bp = Blueprint("bias", __name__)

# The form takes kilohms for the four resistors.
RESISTOR_SCALE = 1000.0

DEFAULTS = {
    "vcc": "12.0",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1.0",
    "beta": "100",
    "vbe": "0.70",
}


@bp.get("/")
def index():
    return render_template(
        "index.html",
        values=DEFAULTS,
        error=None,
        result=None,
        comparison=None,
    )


@bp.post("/")
def analyze_form():
    try:
        inputs = parse_inputs(request.form, resistor_scale=RESISTOR_SCALE)
        result = analyze(inputs)
    except InputError as exc:
        return (
            render_template(
                "index.html",
                values=request.form,
                error=str(exc),
                result=None,
                comparison=None,
            ),
            400,
        )

    return render_template(
        "index.html",
        values=request.form,
        error=None,
        result=result,
        comparison=compare(inputs, result),
    )
