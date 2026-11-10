# BJT Common-Emitter DC Bias Web App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Flask web app that computes the DC operating point of a voltage-divider common-emitter BJT bias circuit, validates input, reports the region, and cross-checks the exact solution against the stiff-divider approximation.

**Architecture:** Pure engineering math in `bjt_bias/engineering.py` (no Flask imports), a thin blueprint in `bjt_bias/routes.py` that parses the form and hands a result object to Jinja, and server-rendered templates with one CSS file. Tests are `unittest`, split into math tests and Flask test-client tests.

**Tech Stack:** Python 3.12.7, Flask 3.x, Jinja2, plain CSS, `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-ce-bias-design.md`

## Global Constraints

- Python 3.12.7. Flask is not installed; use a local `.venv` (already gitignored).
- `requirements.txt` pins Flask to the version actually installed (`Flask>=3.0,<4.0`, then record the resolved version).
- `unittest` only. No pytest, no extra dependencies.
- Test command (run from repo root): `python -m unittest discover -s tests -t . -v`
- `bjt_bias/engineering.py` must not import Flask.
- Every displayed number carries a unit. Currents: mA for IC/IE, µA for IB. Voltages: V. Resistances: kΩ. 4 significant digits via `f"{value:.4g}"`.
- UI text is English. No JavaScript. No database.
- `VCE_SAT = 0.2`, `NEAR_SAT_VCE = 0.7`, `STIFF_FACTOR = 10.0`, `BETA_WARN_RANGE = (20.0, 500.0)`, `VBE_WARN_RANGE = (0.5, 0.9)`, `VCC_WARN_MAX = 30.0`.
- Every reported current is ≥ 0 and `0 <= VCE <= VCC` in every region.
- Commit after every task. Final push to `origin/main`.

## Review Focus

These are the input classes the spec implies but no reference case exercises. Each one gets a test in the task that owns the code.

1. `nan` / `inf` / `-inf` input — `float()` accepts them; they must be rejected as invalid input, never produce an operating point.
2. Locale-formatted numbers (`"47,000"`, `"47 000"`) — must raise a clear validation error, never a 500.
3. Extreme-but-valid values (`RE = 0.001`, `beta = 10000`, `VCC = 1000000`) — must not crash or overflow; region detection stays correct.
4. Boundary-adjacent values (VCE just above `VCE_SAT`, VTH just below VBE, beta exactly 20/500) — deterministic region and warnings.
5. Invalid resubmission — the user's typed values stay in the form after an error; nothing is silently discarded.

---

### Task 1: Environment, package skeleton, input validation

**Files:**
- Create: `requirements.txt`
- Create: `bjt_bias/__init__.py` (empty package marker; filled in Task 4)
- Create: `bjt_bias/engineering.py`
- Create: `tests/__init__.py` (empty)
- Create: `tests/test_engineering.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `class InputError(ValueError)`
  - `@dataclass(frozen=True) class BiasInputs` with float fields `vcc, r1, r2, rc, re, beta, vbe`
  - `parse_inputs(form: Mapping[str, str]) -> BiasInputs`

- [ ] **Step 1: Create the virtualenv and install Flask**

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install "Flask>=3.0,<4.0"
.venv\Scripts\python -m pip freeze | Select-String -Pattern '^Flask=='
```

Write the resolved `Flask==<version>` line into `requirements.txt`.

- [ ] **Step 2: Write the failing tests**

Create `tests/__init__.py` (empty) and `tests/test_engineering.py`:

```python
import unittest

from bjt_bias.engineering import BiasInputs, InputError, parse_inputs


def valid_form(**overrides):
    form = {
        "vcc": "12", "r1": "47000", "r2": "10000", "rc": "2200",
        "re": "1000", "beta": "150", "vbe": "0.7",
    }
    form.update(overrides)
    return form


class ParseInputsTest(unittest.TestCase):
    def test_valid_form(self):
        inputs = parse_inputs(valid_form())
        self.assertIsInstance(inputs, BiasInputs)
        self.assertAlmostEqual(inputs.vcc, 12.0)
        self.assertAlmostEqual(inputs.r1, 47000.0)
        self.assertAlmostEqual(inputs.beta, 150.0)
        self.assertAlmostEqual(inputs.vbe, 0.7)

    def test_whitespace_is_tolerated(self):
        self.assertAlmostEqual(parse_inputs(valid_form(vcc=" 12 ")).vcc, 12.0)

    def test_missing_field_is_error(self):
        form = valid_form()
        del form["beta"]
        with self.assertRaises(InputError):
            parse_inputs(form)

    def test_empty_field_is_error(self):
        with self.assertRaises(InputError):
            parse_inputs(valid_form(vcc=""))

    def test_non_numeric_is_error(self):
        with self.assertRaises(InputError):
            parse_inputs(valid_form(vcc="abc"))

    def test_locale_formatted_number_is_error(self):
        for bad in ("47,000", "47 000"):
            with self.subTest(bad=bad), self.assertRaises(InputError):
                parse_inputs(valid_form(r1=bad))

    def test_nan_and_inf_are_errors(self):
        for bad in ("nan", "inf", "-inf", "NaN"):
            with self.subTest(bad=bad), self.assertRaises(InputError):
                parse_inputs(valid_form(vcc=bad))

    def test_non_positive_vcc_is_error(self):
        for bad in ("0", "-5"):
            with self.subTest(bad=bad), self.assertRaises(InputError):
                parse_inputs(valid_form(vcc=bad))

    def test_non_positive_resistor_is_error(self):
        for field in ("r1", "r2", "rc", "re"):
            for bad in ("0", "-1"):
                with self.subTest(field=field, bad=bad), self.assertRaises(InputError):
                    parse_inputs(valid_form(**{field: bad}))

    def test_beta_at_or_below_one_is_error(self):
        for bad in ("1", "0", "-150"):
            with self.subTest(bad=bad), self.assertRaises(InputError):
                parse_inputs(valid_form(beta=bad))

    def test_negative_vbe_is_error(self):
        with self.assertRaises(InputError):
            parse_inputs(valid_form(vbe="-0.1"))

    def test_beta_bounds_are_accepted(self):
        self.assertAlmostEqual(parse_inputs(valid_form(beta="20")).beta, 20.0)
        self.assertAlmostEqual(parse_inputs(valid_form(beta="500")).beta, 500.0)

    def test_extreme_but_valid_values_are_accepted(self):
        inputs = parse_inputs(valid_form(re="0.001", beta="10000", vcc="1000000"))
        self.assertAlmostEqual(inputs.re, 0.001)
        self.assertAlmostEqual(inputs.beta, 10000.0)
        self.assertAlmostEqual(inputs.vcc, 1000000.0)
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python -m unittest discover -s tests -t . -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bjt_bias'` (or `ImportError`).

- [ ] **Step 4: Implement `parse_inputs`**

In `bjt_bias/engineering.py`: a frozen dataclass `BiasInputs`, `InputError(ValueError)`, and `parse_inputs` that reads the seven keys, converts with `float()`, converts `ValueError`/`TypeError`/`KeyError` into `InputError` with a message naming the field, then rejects non-finite values (`math.isfinite`), `vcc <= 0`, any resistance `<= 0`, `beta <= 1`, `vbe < 0`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m unittest discover -s tests -t . -v`
Expected: PASS, 13 tests.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt bjt_bias/__init__.py bjt_bias/engineering.py tests/__init__.py tests/test_engineering.py
git commit -m "feat: add BJT bias input validation"
```

---

### Task 2: Operating point with region handling

**Files:**
- Modify: `bjt_bias/engineering.py`
- Test: `tests/test_engineering.py` (append `AnalyzeTest`)

**Interfaces:**
- Consumes: `BiasInputs`, `InputError` from Task 1.
- Produces:
  - `class Region(str, Enum)` with `ACTIVE = "active"`, `CUTOFF = "cutoff"`, `SATURATION = "saturation"`
  - `@dataclass(frozen=True) class BiasResult` with float fields `ib_a, ic_a, ie_a, vce_v, vb_v, vc_v, ve_v, vth_v, rth_ohm`, a `region: Region`, and `warnings: tuple[str, ...]`
  - `analyze(inputs: BiasInputs) -> BiasResult`
  - constants `VCE_SAT`, `NEAR_SAT_VCE`, `STIFF_FACTOR`, `BETA_WARN_RANGE`, `VBE_WARN_RANGE`, `VCC_WARN_MAX`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_engineering.py`:

```python
from bjt_bias.engineering import Region, analyze


class AnalyzeTest(unittest.TestCase):
    def test_reference_case_is_active(self):
        r = analyze(parse_inputs(valid_form()))
        self.assertEqual(r.region, Region.ACTIVE)
        self.assertAlmostEqual(r.vth_v, 2.105263, places=5)
        self.assertAlmostEqual(r.rth_ohm, 8245.614, places=2)
        self.assertAlmostEqual(r.ib_a, 8.824501e-6, places=11)
        self.assertAlmostEqual(r.ic_a, 1.323675e-3, places=8)
        self.assertAlmostEqual(r.ie_a, 1.332500e-3, places=8)
        self.assertAlmostEqual(r.vce_v, 7.755415, places=5)
        self.assertAlmostEqual(r.ve_v, 1.332500, places=5)
        self.assertAlmostEqual(r.vb_v, 2.032500, places=5)
        self.assertAlmostEqual(r.vc_v, 9.087915, places=5)

    def test_cutoff_clamps_to_zero_current(self):
        r = analyze(parse_inputs(valid_form(r2="2200")))
        self.assertEqual(r.region, Region.CUTOFF)
        self.assertAlmostEqual(r.vth_v, 0.536585, places=5)
        self.assertEqual((r.ib_a, r.ic_a, r.ie_a), (0.0, 0.0, 0.0))
        self.assertAlmostEqual(r.vce_v, 12.0)
        self.assertAlmostEqual(r.ve_v, 0.0)
        self.assertAlmostEqual(r.vb_v, r.vth_v)
        self.assertAlmostEqual(r.vc_v, 12.0)

    def test_saturation_uses_external_limit(self):
        r = analyze(parse_inputs(valid_form(re="100")))
        self.assertEqual(r.region, Region.SATURATION)
        self.assertAlmostEqual(r.vce_v, 0.2)
        self.assertAlmostEqual(r.ic_a, 5.130435e-3, places=8)
        self.assertAlmostEqual(r.ib_a, 106.9087e-6, places=9)
        self.assertAlmostEqual(r.ie_a, 5.237344e-3, places=8)
        self.assertAlmostEqual(r.vb_v, 1.223734, places=5)
        self.assertAlmostEqual(r.vc_v, 0.713043, places=5)

    def test_near_saturation_warns_but_stays_active(self):
        r = analyze(parse_inputs(valid_form(re="242")))
        self.assertEqual(r.region, Region.ACTIVE)
        self.assertAlmostEqual(r.vce_v, 0.4994, places=3)
        self.assertTrue(any("saturation" in w for w in r.warnings))

    def test_every_region_has_physical_output(self):
        for form in (valid_form(), valid_form(r2="2200"), valid_form(re="100")):
            r = analyze(parse_inputs(form))
            self.assertGreaterEqual(min(r.ib_a, r.ic_a, r.ie_a), 0.0)
            self.assertGreaterEqual(r.vce_v, 0.0)
            self.assertLessEqual(r.vce_v, 12.0)

    def test_extreme_values_do_not_crash(self):
        r = analyze(parse_inputs(valid_form(re="0.001", beta="10000", vcc="1000000")))
        self.assertIn(r.region, (Region.ACTIVE, Region.SATURATION, Region.CUTOFF))
        self.assertGreaterEqual(r.ic_a, 0.0)

    def test_non_stiff_divider_warns(self):
        r = analyze(parse_inputs(valid_form(r1="10000", r2="10000", rc="100",
                                            re="100", beta="20")))
        self.assertEqual(r.region, Region.ACTIVE)
        self.assertTrue(any("not stiff" in w for w in r.warnings))

    def test_implausible_inputs_warn_but_still_analyze(self):
        r = analyze(parse_inputs(valid_form(vbe="0.95", beta="10", vcc="40")))
        self.assertTrue(any("VBE" in w for w in r.warnings))
        self.assertTrue(any("beta" in w for w in r.warnings))
        self.assertTrue(any("VCC" in w for w in r.warnings))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest discover -s tests -t . -v`
Expected: FAIL — `ImportError: cannot import name 'Region'`.

- [ ] **Step 3: Implement `analyze` and region handling**

Compute `VTH = vcc * r2 / (r1 + r2)` and `RTH = r1 * r2 / (r1 + r2)`, then branch:

- `vth <= vbe` → cutoff: zero currents, `vce = vcc`, `vb = vth`, `ve = 0`, `vc = vcc`.
- otherwise compute the exact active solution. If `vce <= VCE_SAT` → saturation:
  `ic = (vcc - VCE_SAT) / (rc + re)`, `vce = VCE_SAT`,
  `ib = max(0.0, (vth - vbe - ic * re) / (rth + re))`, `ie = ic + ib`,
  `vb = ie * re + vbe`, `vc = vcc - ic * rc`, `ve = ie * re`.
- otherwise active with the exact equations from the spec.

Build `warnings` as a tuple, appending the messages from the spec: input plausibility
(`VBE` outside 0.5–0.9, `beta` outside 20–500, `VCC` above 30), region messages
containing the words `cutoff` / `saturation`, the near-saturation message containing
`saturation`, and the non-stiff message containing the exact text `not stiff`.
The non-stiff test is `beta * re < STIFF_FACTOR * rth`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -s tests -t . -v`
Expected: PASS, 21 tests.

- [ ] **Step 5: Commit**

```bash
git add bjt_bias/engineering.py tests/test_engineering.py
git commit -m "feat: compute BJT operating point with region handling"
```

---

### Task 3: Exact vs. approximate cross-check

**Files:**
- Modify: `bjt_bias/engineering.py`
- Test: `tests/test_engineering.py` (append `CompareTest`)

**Interfaces:**
- Consumes: `BiasInputs`, `BiasResult`, `Region`, `STIFF_FACTOR` from Tasks 1–2.
- Produces:
  - `@dataclass(frozen=True) class Comparison` with float fields `approx_ib_a, approx_ic_a, approx_vce_v, delta_ic_pct, delta_vce_pct, stiffness_ratio` and bool `stiff`
  - `compare(inputs: BiasInputs, result: BiasResult) -> Comparison | None`

- [ ] **Step 1: Write the failing tests**

```python
from bjt_bias.engineering import compare


class CompareTest(unittest.TestCase):
    def test_reference_case_comparison(self):
        inputs = parse_inputs(valid_form())
        c = compare(inputs, analyze(inputs))
        self.assertAlmostEqual(c.approx_ic_a, 1.405263e-3, places=8)
        self.assertAlmostEqual(c.approx_vce_v, 7.503158, places=5)
        self.assertAlmostEqual(c.approx_ib_a, 9.368421e-6, places=10)
        self.assertAlmostEqual(c.delta_ic_pct, 6.164, places=2)
        self.assertAlmostEqual(c.delta_vce_pct, 3.253, places=2)
        self.assertAlmostEqual(c.stiffness_ratio, 18.191, places=2)
        self.assertTrue(c.stiff)

    def test_non_stiff_divider_is_flagged(self):
        inputs = parse_inputs(valid_form(r1="10000", r2="10000", rc="100",
                                         re="100", beta="20"))
        c = compare(inputs, analyze(inputs))
        self.assertFalse(c.stiff)
        self.assertAlmostEqual(c.stiffness_ratio, 0.4, places=6)

    def test_no_comparison_outside_active_region(self):
        for form in (valid_form(r2="2200"), valid_form(re="100")):
            inputs = parse_inputs(form)
            self.assertIsNone(compare(inputs, analyze(inputs)))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest discover -s tests -t . -v`
Expected: FAIL — `ImportError: cannot import name 'compare'`.

- [ ] **Step 3: Implement `compare`**

Return `None` unless `result.region is Region.ACTIVE`. Otherwise compute the stiff-divider
approximation (`vb = vth`, `ve = vb - vbe`, `ie = ve / re`, `ic = ie`, `ib = ic / beta`,
`vce = vcc - ic * rc - ie * re`), then
`delta_ic_pct = abs(approx_ic - exact_ic) / exact_ic * 100` (same for VCE), and
`stiffness_ratio = beta * re / rth`, `stiff = stiffness_ratio >= STIFF_FACTOR`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -s tests -t . -v`
Expected: PASS, 24 tests.

- [ ] **Step 5: Commit**

```bash
git add bjt_bias/engineering.py tests/test_engineering.py
git commit -m "feat: cross-check exact and approximate bias solutions"
```

---

### Task 4: Flask app, routes, template, CSS

**Files:**
- Modify: `bjt_bias/__init__.py` (app factory)
- Create: `bjt_bias/routes.py`
- Create: `bjt_bias/templates/base.html`
- Create: `bjt_bias/templates/index.html`
- Create: `bjt_bias/static/style.css`
- Create: `run.py`
- Test: `tests/test_routes.py`

**Interfaces:**
- Consumes: `parse_inputs`, `InputError`, `analyze`, `compare` from Tasks 1–3.
- Produces:
  - `create_app() -> Flask` in `bjt_bias/__init__.py`, registering the blueprint and a Jinja filter `sig` (`f"{value:.4g}"`)
  - blueprint `bp` in `bjt_bias/routes.py` with `GET /` and `POST /`
  - template context keys: `form`, `error`, `result`, `comparison`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_routes.py`:

```python
import unittest

from bjt_bias import create_app


def form(**overrides):
    data = {
        "vcc": "12", "r1": "47000", "r2": "10000", "rc": "2200",
        "re": "1000", "beta": "150", "vbe": "0.7",
    }
    data.update(overrides)
    return data


class RoutesTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_shows_form(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"DC Operating Point", response.data)
        self.assertIn(b"VCC", response.data)

    def test_post_reference_case(self):
        response = self.client.post("/", data=form())
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"1.324", response.data)
        self.assertIn(b"7.755", response.data)
        self.assertIn(b"active", response.data)
        self.assertIn(b"6.164", response.data)

    def test_post_cutoff_case(self):
        response = self.client.post("/", data=form(r2="2200"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"cutoff", response.data)

    def test_post_saturation_case(self):
        response = self.client.post("/", data=form(re="100"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"saturation", response.data)
        self.assertIn(b"5.13", response.data)

    def test_invalid_input_returns_400_and_keeps_values(self):
        response = self.client.post("/", data=form(vcc="0"))
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"must be greater than zero", response.data)
        self.assertIn(b'value="0"', response.data)

    def test_nan_input_returns_400(self):
        response = self.client.post("/", data=form(vcc="nan"))
        self.assertEqual(response.status_code, 400)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest discover -s tests -t . -v`
Expected: FAIL — `ImportError: cannot import name 'create_app'`.

- [ ] **Step 3: Implement the app factory, route, template and CSS**

`create_app()` builds the Flask app, registers the blueprint, and adds the `sig` filter.
`GET /` renders `index.html` with `form={}` and no result. `POST /` calls
`parse_inputs(request.form)`; on `InputError` renders the template with
`error=str(exc)`, `form=request.form`, status 400. On success calls `analyze` and
`compare`, renders with `result` and `comparison`.

`index.html` extends `base.html` and renders: the form (field names `vcc, r1, r2, rc,
re, beta, vbe`, each `value="{{ form.get('name', '') }}"`), an error block when
`error` is set, a results table with units, a region badge, a warnings list, and —
only when `comparison` is not `None` — the cross-check panel with exact vs.
approximate IC/VCE, Δ%, stiffness ratio and verdict. When `result` exists but
`comparison` is `None`, render the note that the cross-check applies to the active
region only. Numbers use `{{ (result.ic_a * 1000) | sig }}` (parentheses matter).

`style.css` gives the page a readable single-column layout, a distinct region badge
per region, and a red-tinted error block. `run.py` calls `create_app().run(debug=True)`
on `127.0.0.1:5000`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -s tests -t . -v`
Expected: PASS, 30 tests.

- [ ] **Step 5: Commit**

```bash
git add bjt_bias run.py tests/test_routes.py
git commit -m "feat: add Flask UI for BJT bias analysis"
```

---

### Task 5: README, cleanup, final verification, push

**Files:**
- Delete: `itive resistance?`, `t? verify DC circuit results?`, `? start DC circuit calculator?`
- Modify: `README.md`

**Interfaces:**
- Consumes: everything above.
- Produces: documentation and a pushed `main`.

- [ ] **Step 1: Delete the three junk diff-dump files**

```bash
git rm -- "itive resistance*" "t? verify DC circuit results*" "? start DC circuit calculator*"
```

Confirm with `git ls-files` that only `.gitignore`, `README.md`, `electrical.py`,
`test_electrical.py`, `bjt_bias/`, `tests/`, `run.py`, `requirements.txt` and
`docs/` remain.

- [ ] **Step 2: Rewrite `README.md`**

Sections: what the app does; the bias circuit and its equations (Thevenin form);
the region rules and `VCE_SAT`; how to run (`python -m venv .venv`, pip install,
`python run.py`, open `http://127.0.0.1:5000`); how to test; the three reference
cases with expected numbers; a short Thai summary paragraph.

- [ ] **Step 3: Run the full suite**

Run: `python -m unittest discover -s tests -t . -v`
Expected: PASS, 30 tests, 0 failures.

- [ ] **Step 4: Verify the running server**

```powershell
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "run.py"
Start-Sleep -Seconds 3
Invoke-WebRequest http://127.0.0.1:5000 -UseBasicParsing | Select-Object -ExpandProperty StatusCode
```

Expected: `200`. Then POST the reference case with `Invoke-WebRequest -Method POST -Body @{vcc="12";r1="47000";r2="10000";rc="2200";re="1000";beta="150";vbe="0.7"}`
and confirm the body contains `1.324` and `active`. Stop the server afterwards.

- [ ] **Step 5: Commit and push**

```bash
git add README.md
git commit -m "docs: document BJT bias app and remove stray diff dumps"
git push origin main
```

Expected: push succeeds; `git status` is clean.

---

## Self-Review

- **Spec coverage:** inputs/validation (Task 1), operating point + units (Task 2),
  region warnings (Task 2), cross-check (Task 3), separate routes/templates/CSS/tests
  (Task 4), localhost demo + GitHub commit (Task 5). No AC/FET/editor code anywhere.
- **Step scan:** every step names a file, a command, or a test with literal assertions.
  No "handle edge cases" lines; each Review Focus item maps to a named test.
- **Type consistency:** `BiasInputs` fields are lowercase (`vcc, r1, r2, rc, re, beta,
  vbe`); `BiasResult` uses unit suffixes (`ib_a`, `vce_v`, `rth_ohm`); `Comparison` uses
  `approx_*` prefixes. `compare` returns `None` outside the active region and the route
  checks for that.
- **Review Focus:** nan/inf (Task 1), locale numbers (Task 1), extreme values (Tasks 1–2),
  boundary-adjacent VCE/VTH/beta (Task 2), value preservation on error (Task 4).
- **Proportion:** 5 tasks, ~30 tests; code blocks are test assertions, not implementation
  bodies.
