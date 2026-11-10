"""Pure engineering calculations for the voltage-divider BJT bias circuit.

This module must not import Flask: it is the testable core the web layer calls.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

FIELDS = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")

LABELS = {
    "vcc": "VCC",
    "r1": "R1",
    "r2": "R2",
    "rc": "RC",
    "re": "RE",
    "beta": "beta",
    "vbe": "VBE",
}


class InputError(ValueError):
    """Raised when form input cannot be used as a bias calculation input."""


@dataclass(frozen=True)
class BiasInputs:
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


def parse_inputs(form: Mapping[str, str]) -> BiasInputs:
    """Parse and validate the seven form fields into BiasInputs."""
    values: dict[str, float] = {}
    for name in FIELDS:
        raw = form.get(name)
        if raw is None or str(raw).strip() == "":
            raise InputError(f"{LABELS[name]} is required.")
        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise InputError(f"{LABELS[name]} must be a number.") from None
        if not math.isfinite(value):
            raise InputError(f"{LABELS[name]} must be a finite number.")
        values[name] = value

    if values["vcc"] <= 0:
        raise InputError("VCC must be greater than zero.")
    for name in ("r1", "r2", "rc", "re"):
        if values[name] <= 0:
            raise InputError(f"{LABELS[name]} must be greater than zero.")
    if values["beta"] <= 1:
        raise InputError("beta must be greater than 1.")
    if values["vbe"] < 0:
        raise InputError("VBE must not be negative.")

    return BiasInputs(**values)
