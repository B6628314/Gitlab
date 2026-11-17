"""HTTP layer: parse the form, call the engineering core, render the page."""

from __future__ import annotations

from flask import Blueprint, render_template, request

from .engineering import (
    MODE_LABELS,
    MODES,
    InputError,
    analyze,
    analyze_emitter,
    analyze_fixed,
    compare,
    parse_inputs,
    parse_mode_inputs,
)

bp = Blueprint("bias", __name__)

# The form takes kilohms for the five resistors.
RESISTOR_SCALE = 1000.0

DEFAULTS = {
    "divider": {
        "vcc": "12.0",
        "r1": "100",
        "r2": "22",
        "rc": "2.2",
        "re": "1.0",
        "beta": "100",
        "vbe": "0.70",
    },
    "fixed": {
        "vcc": "12.0",
        "rb": "1000",
        "rc": "2.2",
        "beta": "100",
        "vbe": "0.70",
    },
    "emitter": {
        "vcc": "12.0",
        "rb": "1000",
        "rc": "2.2",
        "re": "1.0",
        "beta": "100",
        "vbe": "0.70",
    },
}


def _point_from_divider(result) -> dict:
    """Adapt the Lab 2 BiasResult to the shared result-dict interface."""
    return {
        "mode": "divider",
        "mode_label": MODE_LABELS["divider"],
        "ib_ma": result.ib_a * 1000.0,
        "ic_ma": result.ic_a * 1000.0,
        "ie_ma": result.ie_a * 1000.0,
        "vb_v": result.vb_v,
        "ve_v": result.ve_v,
        "vc_v": result.vc_v,
        "vce_v": result.vce_v,
        "vth_v": result.vth_v,
        "region": result.region.value,
        "warnings": result.warnings,
    }


def _render(
    mode: str,
    values,
    *,
    error: str | None = None,
    point: dict | None = None,
    comparison=None,
    status: int = 200,
):
    return (
        render_template(
            "index.html",
            mode=mode,
            mode_label=MODE_LABELS[mode],
            values=values,
            error=error,
            point=point,
            comparison=comparison,
        ),
        status,
    )


@bp.get("/")
def index():
    requested = (request.args.get("mode") or "divider").strip()
    if requested not in MODES:
        return _render(
            "divider",
            DEFAULTS["divider"],
            error=f"Unknown bias mode: {requested!r}. Choose one of: "
            + ", ".join(MODES)
            + ".",
            status=400,
        )
    return _render(requested, DEFAULTS[requested])


@bp.post("/")
def analyze_form():
    # Lab 2 forms have no mode field; keep those posts working as divider.
    requested = (request.form.get("mode") or "divider").strip()
    if requested not in MODES:
        return _render(
            "divider",
            request.form,
            error=f"Unknown bias mode: {requested!r}. Choose one of: "
            + ", ".join(MODES)
            + ".",
            status=400,
        )

    try:
        if requested == "divider":
            inputs = parse_inputs(request.form, resistor_scale=RESISTOR_SCALE)
            result = analyze(inputs)
            point = _point_from_divider(result)
            comparison = compare(inputs, result)
        elif requested == "fixed":
            point = analyze_fixed(
                parse_mode_inputs(request.form, "fixed", RESISTOR_SCALE)
            )
            comparison = None
        elif requested == "emitter":
            point = analyze_emitter(
                parse_mode_inputs(request.form, "emitter", RESISTOR_SCALE)
            )
            comparison = None
    except InputError as exc:
        return _render(requested, request.form, error=str(exc), status=400)

    return _render(
        requested,
        request.form,
        point=point,
        comparison=comparison,
    )
