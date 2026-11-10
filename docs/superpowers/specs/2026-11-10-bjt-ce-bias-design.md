# BJT Common-Emitter DC Bias Web App — Design

**Course:** ENG29 2121 · **Date:** 2026-11-10 · **Status:** awaiting approval

## Intent

A small Flask app for the lab: enter the voltage-divider common-emitter bias
values, get the DC operating point with units, validation and region warnings,
plus a cross-check between two independent engineering calculations.

The lab's lesson is that the stiff-divider approximation is only valid when the
divider is stiff. Showing the exact and approximate solutions side by side, with
their difference, makes that visible instead of asserted.

## Goals

- One page: input form and results. No login, no database, no JS framework.
- Engineering math in a pure, Flask-free module with unit tests.
- Validation: hard errors for impossible input, warnings for implausible or
  out-of-region physics.
- Cross-check panel: exact vs. approximate, Δ%, stiffness ratio, verdict.
- Runs on localhost with two commands; tests green; committed to GitHub today.

## Non-goals

- No AC, transient, frequency response, gain or load-line plot.
- No schematic editor, netlist, or circuit drawing.
- No FET/MOSFET; no other bias topologies (fixed-base, collector feedback).
- No database, auth, deployment, Docker, or build step.

## Anti-goals (failures even if the page renders)

- Two formulas copy-pasted so the "independent check" agrees by construction.
- Engineering math inside route handlers or templates.
- A result shown without units, or nonsense input accepted silently.
- The approximation presented as equally valid regardless of stiffness.

## Constraints

- Python 3.12.7. Flask is **not installed** → `requirements.txt` + venv install.
- Repo `github.com/B6628314/Gitlab`, branch `main`.
- Existing repo content is unrelated: `electrical.py` (V=IR helper),
  a README about a plant-watering project, and three tracked files that are
  saved `git diff` dumps with mangled names.
- Repo convention is `unittest` → stay on `unittest`, do not add pytest.
- Due today.

## Topology and equations (decided)

Voltage-divider bias: `R1` from VCC to base, `R2` base to ground, `RC` at the
collector, `RE` at the emitter, with `beta` and `VBE`.

Thevenin equivalent of the base divider:

```
VTH = VCC * R2 / (R1 + R2)
RTH = R1 * R2 / (R1 + R2)
```

**Exact** (accounts for base current):

```
IB  = (VTH - VBE) / (RTH + (beta + 1) * RE)
IC  = beta * IB
IE  = (beta + 1) * IB
VCE = VCC - IC * RC - IE * RE
VB  = IE * RE + VBE
VC  = VCC - IC * RC
VE  = IE * RE
```

**Approximate** (stiff divider, `IB ≈ 0`):

```
VB  = VTH
VE  = VB - VBE
IE  = VE / RE
IC  = IE
IB  = IC / beta
VCE = VCC - IC * RC - IE * RE
```

**Region:**

- cutoff when `VTH <= VBE` (the divider cannot turn the device on)
- saturation when the active-model `VCE <= 0.2 V` (`VCE_SAT` constant, shown in the UI)
- otherwise active
- near-saturation warning when `0.2 V < VCE <= 0.7 V`

**Stiffness:** `beta * RE >= 10 * RTH` → approximation is valid.

### Region handling (the linear model is only valid in the active region)

The equations above assume forward-active operation. Outside it they return
non-physical values (negative currents, `VCE > VCC`), which the app must never
print. `analyze()` therefore returns a **piecewise-linear** solution:

**Cutoff** (`VTH <= VBE`): the base-emitter junction never turns on.

```
IB = IC = IE = 0
VCE = VCC
VB  = VTH          (no base current, so the divider is unloaded)
VE  = 0
VC  = VCC
```

**Saturation** (active-model `VCE <= VCE_SAT`): the collector current is set by
the external circuit, not by beta. Solve the base loop with `IE = IC + IB`:

```
IC  = (VCC - VCE_SAT) / (RC + RE)
VCE = VCE_SAT
IB  = (VTH - VBE - IC * RE) / (RTH + RE)     (floored at 0)
IE  = IC + IB
VB  = IE * RE + VBE
VC  = VCC - IC * RC
VE  = IE * RE
```

**Active:** the exact equations above.

Every reported current is non-negative and `0 <= VCE <= VCC` in all three
regions. The raw active-model values are not exposed.

**Cross-check scope:** the exact-vs-approximate panel renders **only in the
active region**. In cutoff or saturation the page shows a one-line note instead
("cross-check applies to the active region; device is in cutoff/saturation"),
because both derivations are invalid there and Δ% would be meaningless.

### Worked reference case (acceptance numbers)

Inputs: VCC 12 V, R1 47 kΩ, R2 10 kΩ, RC 2.2 kΩ, RE 1 kΩ, beta 150, VBE 0.7 V

| Quantity | Exact | Approximate |
|---|---|---|
| VTH | 2.1053 V | — |
| RTH | 8.2456 kΩ | — |
| IB | 8.825 µA | 9.369 µA (IC/beta) |
| IC | 1.3237 mA | 1.4053 mA |
| IE | 1.3326 mA | 1.4053 mA |
| VCE | 7.755 V | 7.503 V |
| ΔIC | — | 6.2 % |
| beta·RE / RTH | 18.2 (stiff) | — |

These are hand-computed and are written as literal expected values in the tests.
The approximate `IB` differs from the exact `IB` by construction (`IC/beta` vs.
the base-loop solution); it is shown for completeness but is an input to neither
method.

### Cutoff reference case

VCC 12 V, R1 47 kΩ, R2 2.2 kΩ, RC 2.2 kΩ, RE 1 kΩ, beta 150, VBE 0.7 V
→ VTH = 0.5366 V (< VBE), so cutoff. Expected: IB = IC = IE = 0, VCE = 12 V,
VB = 0.5366 V, VE = 0, VC = 12 V.

### Saturation reference case

VCC 12 V, R1 47 kΩ, R2 10 kΩ, RC 2.2 kΩ, RE 100 Ω, beta 150, VBE 0.7 V
→ active model gives VCE < 0, so saturation. Expected: IC = 5.1304 mA,
VCE = 0.2 V, IB = 106.91 µA, IE = 5.2373 mA, VB = 1.2237 V, VC = 0.7131 V.

## Approaches considered

- **A. Exact vs. approximate cross-check (chosen).** Two legitimate derivations
  from the same inputs. Teaches when the approximation holds. Needs no extra
  student input.
- **B. App vs. the student's hand calculation.** Requires a second form and
  typing; the demo cannot run without it; moves work onto the user.
- **C. Independent recomputation (node equations).** Same number computed twice,
  no teaching value, more code for a "check" that can never disagree.

A is chosen because it is the only option where two calculations can legitimately
disagree — which is exactly the lab's point.

## Architecture

```
bjt_bias/
  __init__.py      create_app() app factory
  engineering.py   pure: BiasInputs/BiasResult dataclasses, analyze(),
                   analyze_approximate(), compare(), InputError
  routes.py        Blueprint: GET / (empty form), POST / (analyze + render)
  templates/
    base.html
    index.html
  static/
    style.css
tests/
  test_engineering.py   math, regions, validation, cross-check
  test_routes.py        test client: GET 200, valid POST, invalid POST
run.py               app.run(debug=True) on 127.0.0.1:5000
requirements.txt     Flask (pinned)
README.md            rewritten for this app
```

`engineering.py` imports nothing from Flask. Routes only parse the form, call the
module, and hand a result object to the template.

## Validation

**Hard errors** (no results rendered, form keeps the user's values):

- non-numeric or missing field
- `VCC <= 0`
- `R1, R2, RC, RE <= 0`
- `beta <= 1`
- `VBE < 0`

**Warnings** (results still shown):

- `VBE` outside 0.5–0.9 V
- `beta` outside 20–500
- `VCC > 30 V`
- cutoff, saturation, near-saturation
- non-stiff divider (`beta*RE < 10*RTH`)

## Decisions made on the team's behalf

- English UI labels and English warnings; README carries a short Thai summary.
- Resistances entered in ohms (SI); results shown in mA / µA / kΩ with a hint
  that 47 kΩ is entered as `47000`.
- Exact result is primary; the approximation appears only in the comparison panel.
- `VCE_SAT = 0.2 V` as a module constant, displayed next to the region.
- Delete the three junk diff-dump files; rewrite `README.md`; leave
  `electrical.py` and `test_electrical.py` untouched.
- Commit directly to `main` and push to `origin` (single-author lab repo).
- Cutoff and saturation are reported as clamped, physically valid operating
  points, never as raw model output.
- The cross-check panel is active-region only.

## Left to the builder

- CSS layout, spacing, colors.
- Internal helper and test-fixture structure.
- Commit message wording.

## Verification

1. `python -m unittest discover -s tests -v` — all green, including the cutoff
   and saturation reference cases.
2. `python run.py` — `http://127.0.0.1:5000` serves the form.
3. POST the reference case — page shows IC ≈ 1.324 mA, VCE ≈ 7.76 V, active,
   ΔIC ≈ 6.2 %, stiff divider.
4. POST the saturation case — page shows IC ≈ 5.130 mA, VCE = 0.2 V, saturated,
   no negative numbers, cross-check panel replaced by the note.
5. Commit and push to `origin/main`.
