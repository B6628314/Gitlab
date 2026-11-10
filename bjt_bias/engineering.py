"""Pure engineering calculations for the voltage-divider BJT bias circuit.

This module must not import Flask: it is the testable core the web layer calls.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

FIELDS = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")

VCE_SAT = 0.2
NEAR_SAT_VCE = 0.7
STIFF_FACTOR = 10.0
BETA_WARN_RANGE = (20.0, 500.0)
VBE_WARN_RANGE = (0.5, 0.9)
VCC_WARN_MAX = 30.0

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


def parse_inputs(form: Mapping[str, str], resistor_scale: float = 1.0) -> BiasInputs:
    """Parse and validate the seven form fields into BiasInputs.

    ``resistor_scale`` converts the entered resistance unit to ohms: pass 1000.0
    when the form takes kilohms.
    """
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
        values[name] *= resistor_scale
        if values[name] <= 0:
            raise InputError(f"{LABELS[name]} must be greater than zero.")
    if values["beta"] <= 1:
        raise InputError("beta must be greater than 1.")
    if values["vbe"] < 0:
        raise InputError("VBE must not be negative.")

    return BiasInputs(**values)

class Region(str, Enum):
    ACTIVE = "active"
    CUTOFF = "cutoff"
    SATURATION = "saturation"


@dataclass(frozen=True)
class BiasResult:
    region: Region
    ib_a: float
    ic_a: float
    ie_a: float
    vce_v: float
    vb_v: float
    vc_v: float
    ve_v: float
    vth_v: float
    rth_ohm: float
    warnings: tuple[str, ...]


def _fmt(value: float) -> str:
    return f"{value:.4g}"


def analyze(inputs: BiasInputs) -> BiasResult:
    """Compute the DC operating point, clamped to the physical region."""
    vth = inputs.vcc * inputs.r2 / (inputs.r1 + inputs.r2)
    rth = inputs.r1 * inputs.r2 / (inputs.r1 + inputs.r2)
    warnings: list[str] = []

    if vth <= inputs.vbe:
        region = Region.CUTOFF
        ib = ic = ie = 0.0
        vce = inputs.vcc
        vb = vth
        ve = 0.0
        vc = inputs.vcc
        warnings.append(
            "Transistor is in cutoff (VTH <= VBE): the base-emitter junction is off."
        )
    else:
        ib = (vth - inputs.vbe) / (rth + (inputs.beta + 1) * inputs.re)
        ic = inputs.beta * ib
        ie = (inputs.beta + 1) * ib
        vce = inputs.vcc - ic * inputs.rc - ie * inputs.re
        if vce <= VCE_SAT:
            region = Region.SATURATION
            ic = (inputs.vcc - VCE_SAT) / (inputs.rc + inputs.re)
            vce = VCE_SAT
            ib = max(0.0, (vth - inputs.vbe - ic * inputs.re) / (rth + inputs.re))
            ie = ic + ib
            warnings.append(
                "Transistor is in saturation (VCE = VCE_SAT): IC is set by RC + RE, not by beta."
            )
        else:
            region = Region.ACTIVE
            if vce <= NEAR_SAT_VCE:
                warnings.append(
                    "VCE is within 0.5 V of saturation; the operating point is sensitive to beta."
                )
        vb = ie * inputs.re + inputs.vbe
        ve = ie * inputs.re
        vc = inputs.vcc - ic * inputs.rc

    if inputs.vbe < VBE_WARN_RANGE[0] or inputs.vbe > VBE_WARN_RANGE[1]:
        warnings.append(
            f"VBE = {_fmt(inputs.vbe)} V is outside the typical "
            f"{_fmt(VBE_WARN_RANGE[0])}-{_fmt(VBE_WARN_RANGE[1])} V range."
        )
    if inputs.beta < BETA_WARN_RANGE[0] or inputs.beta > BETA_WARN_RANGE[1]:
        warnings.append(
            f"beta = {_fmt(inputs.beta)} is outside the typical "
            f"{_fmt(BETA_WARN_RANGE[0])}-{_fmt(BETA_WARN_RANGE[1])} range."
        )
    if inputs.vcc > VCC_WARN_MAX:
        warnings.append(
            f"VCC = {_fmt(inputs.vcc)} V exceeds {_fmt(VCC_WARN_MAX)} V; "
            "check the transistor ratings."
        )
    if inputs.beta * inputs.re < STIFF_FACTOR * rth:
        warnings.append(
            "Divider is not stiff (beta*RE < 10*RTH): the stiff-divider "
            "approximation is inaccurate."
        )

    return BiasResult(
        region=region,
        ib_a=ib,
        ic_a=ic,
        ie_a=ie,
        vce_v=vce,
        vb_v=vb,
        vc_v=vc,
        ve_v=ve,
        vth_v=vth,
        rth_ohm=rth,
        warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class Comparison:
    approx_ib_a: float
    approx_ic_a: float
    approx_vce_v: float
    delta_ic_pct: float
    delta_vce_pct: float
    stiffness_ratio: float
    stiff: bool


def compare(inputs: BiasInputs, result: BiasResult) -> "Comparison | None":
    """Compare the exact active-region solution with the stiff-divider approximation.

    Returns None outside the active region, where the approximation is invalid.
    """
    if result.region is not Region.ACTIVE:
        return None

    vb = result.vth_v
    ve = vb - inputs.vbe
    ie = ve / inputs.re
    ic = ie
    ib = ic / inputs.beta
    vce = inputs.vcc - ic * inputs.rc - ie * inputs.re

    delta_ic_pct = abs(ic - result.ic_a) / result.ic_a * 100.0
    delta_vce_pct = abs(vce - result.vce_v) / result.vce_v * 100.0
    stiffness_ratio = inputs.beta * inputs.re / result.rth_ohm

    return Comparison(
        approx_ib_a=ib,
        approx_ic_a=ic,
        approx_vce_v=vce,
        delta_ic_pct=delta_ic_pct,
        delta_vce_pct=delta_vce_pct,
        stiffness_ratio=stiffness_ratio,
        stiff=stiffness_ratio >= STIFF_FACTOR,
    )
