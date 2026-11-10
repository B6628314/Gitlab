"""HTTP layer: parse the form, call the engineering core, render the page."""

from __future__ import annotations

from flask import Blueprint, render_template, request

from .engineering import InputError, analyze, compare, parse_inputs

bp = Blueprint("bias", __name__)


@bp.get("/")
def index():
    return render_template(
        "index.html", form={}, error=None, result=None, comparison=None
    )


@bp.post("/")
def analyze_form():
    try:
        inputs = parse_inputs(request.form)
    except InputError as exc:
        return (
            render_template(
                "index.html",
                form=request.form,
                error=str(exc),
                result=None,
                comparison=None,
            ),
            400,
        )

    result = analyze(inputs)
    return render_template(
        "index.html",
        form=request.form,
        error=None,
        result=result,
        comparison=compare(inputs, result),
    )
