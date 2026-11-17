# Lab 03 — Three BJT Bias Modes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing Lab 2 Flask BJT calculator with Fixed Bias and single-supply Emitter Bias, selectable by mode, without changing the voltage-divider results.

**Architecture:** Keep `bjt_bias/engineering.py` as the Flask-free calculation core. Add per-mode parsing and two analysis functions that return a shared dict of unit-suffixed keys. `routes.py` dispatches on the submitted mode and never falls back for an unknown value. The Jinja template renders only the fields of the selected mode, and the browser acceptance check is recorded in `docs/validation.md`.

**Tech Stack:** Python 3.12, Flask 3.1, Jinja2, `unittest` (existing tests only), OpenCode Browser / Playwright MCP.

**Spec:** `ENG29_2121_Lab03_BJT_Bias_Web_App.html` (course handout), plus `docs/superpowers/specs/2026-11-10-bjt-ce-bias-design.md` for the Lab 2 behaviour that must not regress.

## Global Constraints

- Inputs common to all modes: `VCC`, `RC`, `beta`, `VBE`; resistances are entered in kΩ and converted to Ω once at parse time.
- Equations exactly as in the handout:
  - Fixed: `IB = (VCC - VBE) / RB`
  - Emitter: `IB = (VCC - VBE) / (RB + (beta + 1) * RE)`
  - Divider: unchanged Lab 2 Thevenin solution
  - `IC = beta*IB`, `IE = (beta+1)*IB`, `VE = IE*RE` (Fixed: `VE = 0`), `VB = VE + VBE`, `VC = VCC - IC*RC`, `VCE = VC - VE`
- Hard error (no result, HTTP 400): missing/non-numeric/non-finite field, `VCC <= 0.2`, any resistance `<= 0`, `beta <= 1`, `VBE < 0`, unknown mode.
- Model warning (result still shown): valid input but `IB <= 0` or `VCE <= 0.2 V` → forward-active model may not be valid.
- Unknown mode must error; do not default it to divider. A missing mode field on POST defaults to `divider` for Lab 2 compatibility.
- Do not add new `unittest` cases (handout); existing 41 tests must keep passing. Only header-string assertions may be updated.
- Divider code path, clamping and cross-check stay byte-for-byte behaviourally identical so A1 equals the Lab 2 result.
- No AC/transient, load line, bypass capacitors, SPICE, or JavaScript requirement.

## Review Focus

- A zero or negative resistance in the selected mode must produce an error message, not a divide-by-zero page.
- Unknown `mode` (e.g. `?mode=xyz` or a tampered hidden field) must not silently calculate a divider result.
- Switching modes must show only that mode's fields and must never show the previous run's result.
- Very large finite inputs must not render `nan`/`inf`.
- A failed submit must keep the user's entered values so they can correct one field.

---

### Task 1: Engineering core — mode parsing, Fixed and Emitter analysis

**Files:**
- Modify: `bjt_bias/engineering.py`

**Interfaces:**
- Consumes: existing `InputError`, `VCE_SAT`, `BETA_WARN_RANGE`, `VBE_WARN_RANGE`, `VCC_WARN_MAX`, `_fmt`, `_check_finite`, `parse_inputs`, `analyze`.
- Produces:
  - `MODES = ("divider", "fixed", "emitter")`
  - `MODE_LABELS: dict[str, str]`
  - `FixedInputs(vcc, rb, rc, beta, vbe)`
  - `EmitterInputs(vcc, rb, rc, re, beta, vbe)`
  - `parse_mode_inputs(form, mode, resistor_scale=1.0)` → one of `BiasInputs | FixedInputs | EmitterInputs`; raises `InputError` for an unknown mode.
  - `analyze_fixed(inputs: FixedInputs) -> dict`
  - `analyze_emitter(inputs: EmitterInputs) -> dict`
  - Result dict keys: `mode`, `mode_label`, `ib_ma`, `ic_ma`, `ie_ma`, `vb_v`, `ve_v`, `vc_v`, `vce_v`, `region`, `warnings`; `region` is `"active"` or `"model-warning"`.

- [ ] **Step 1: Add mode constants, labels and input dataclasses** in `bjt_bias/engineering.py`, after `LABELS`.
- [ ] **Step 2: Add `parse_mode_inputs`** that delegates `"divider"` to the existing `parse_inputs`, validates only the mode's fields, and raises `InputError("Unknown bias mode: ...")` otherwise. Reuse one helper for finite/positive checks so new paths cannot skip them.
- [ ] **Step 3: Add `analyze_fixed` and `analyze_emitter`** implementing the handout equations and returning the shared unit-suffixed dict. Emit model warnings when `ib <= 0` or `vce <= VCE_SAT`; reuse the VBE/beta/VCC plausibility warnings with the existing message text.
- [ ] **Step 4: Verify against hand calculations** with a shell one-liner for A2–A4:
  - A2 Fixed RB 1 MΩ → IC 1.130 mA, VCE 9.514 V
  - A3 Emitter RB 1 MΩ, RE 1 kΩ → IC 1.026 mA, VCE 8.705 V
  - A4 Emitter RE 2 kΩ → IC 0.9401 mA, VCE 8.033 V
  - RB = 0 in fixed mode → `InputError`
- [ ] **Step 5: Run existing tests**: `.venv\Scripts\python -m unittest discover -s tests -t .` → `Ran 41 tests ... OK`.
- [ ] **Step 6: Commit** `feat: add fixed and emitter bias calculations`.

### Task 2: Routes — mode dispatch and per-mode validation

**Files:**
- Modify: `bjt_bias/routes.py`

**Interfaces:**
- Consumes: `parse_mode_inputs`, `analyze_fixed`, `analyze_emitter`, `analyze`, `compare`, `InputError`, `MODES`, `MODE_LABELS`.
- Produces: template context `mode`, `mode_label`, `values`, `error`, `point`, `comparison`.

- [ ] **Step 1: Add per-mode defaults** (`divider` unchanged; `fixed` RB 1000 kΩ; `emitter` RB 1000 kΩ, RE 1 kΩ).
- [ ] **Step 2: GET `/` reads `request.args.get("mode", "divider")`**, validates against `MODES`, renders the matching defaults; invalid value → 400 with an error and divider form.
- [ ] **Step 3: POST reads `request.form.get("mode") or "divider"`**, rejects an unknown value with `InputError`, otherwise dispatches to the mode's parser/analyzer in `if/elif`. Divider builds a dict from the existing `BiasResult` so the template sees one result shape; only divider passes a `comparison`.
- [ ] **Step 4: Verify via Flask test client** that: GET `?mode=fixed` contains `rb` and not `r1`; POST fixed A2 returns 200 with `1.13`/`9.514`; POST `mode=xyz` returns 400 and no result; POST fixed with `rb=0` returns 400 and keeps `value="0"`.
- [ ] **Step 5: Run existing tests** (all 41 still pass; existing POSTs without `mode` still calculate a divider).
- [ ] **Step 6: Commit** `feat: dispatch bias calculation by selected mode`.

### Task 3: Form, schematic and results template

**Files:**
- Modify: `bjt_bias/templates/index.html`, `bjt_bias/templates/base.html`, `bjt_bias/static/style.css`

**Interfaces:**
- Consumes: context from Task 2 and result dict keys from Task 1.
- Produces: accessible labels/ids `mode`, `vcc`, `rb`, `r1`, `r2`, `rc`, `re`, `beta`, `vbe`; result table in V/mA/µA; mode name in the results header.

- [ ] **Step 1: Add a GET mode picker** (`select#mode` + `Load circuit` button) above the POST form, and a hidden `mode` input in the POST form.
- [ ] **Step 2: Render only the selected mode's resistor fields** (`rb` for fixed/emitter; `r1`/`r2` only for divider; `re` for divider/emitter) while keeping every `<label for>` matched to its `id`.
- [ ] **Step 3: Render results from `point`** with a visible mode tag; keep the active/cutoff/saturation boxes, add a `model-warning` box, and keep the cross-check strip for the divider only.
- [ ] **Step 4: Adapt the SVG schematic**: reuse the left branch as `RB` for fixed/emitter, hide the `R2` branch, and hide `RE` with a direct emitter-to-ground wire in fixed mode.
- [ ] **Step 5: Update `base.html`** to Lab 03 titles/goal (and adjust the two existing header assertions in `tests/test_routes.py`).
- [ ] **Step 6: Verify** GET pages for all three modes contain the right field ids and no stale result, and the full test suite still passes.
- [ ] **Step 7: Commit** `feat: add mode picker and per-mode result display`.

### Task 4: Docs and project MCP config

**Files:**
- Modify: `README.md`
- Create: `docs/validation.md`, `opencode.json`

**Interfaces:**
- Consumes: final behaviour from Tasks 1–3.
- Produces: run instructions, formulas, A1–A5 table, method/evidence columns, Playwright MCP config (OpenCode V2 `mcp.servers.playwright`, Chrome, isolated).

- [ ] **Step 1: Rewrite the README** for three modes: formulas, default inputs, run/test commands, reference cases, AI-assisted parts, MCP/browser check, and a short Thai summary.
- [ ] **Step 2: Write `docs/validation.md`** with the A1–A5 table, independently hand-calculated expected values, tolerance (IC ±0.01 mA, VCE ±0.02 V), observation and evidence columns left pending.
- [ ] **Step 3: Add `opencode.json`** with the V2 Playwright MCP entry from the handout.
- [ ] **Step 4: Commit** `docs: document three bias modes and validation plan`.

### Task 5: Browser acceptance A1–A5

**Files:**
- Modify: `docs/validation.md`
- Create: `docs/evidence/lab03-*.png` (at least one screenshot)

**Interfaces:**
- Consumes: running Flask at `http://127.0.0.1:5000/`, mode UI from Task 3.
- Produces: observed values, PASS/FAIL/NOT RUN per case, method = OpenCode Browser, screenshot path.

- [ ] **Step 1: Start Flask** in the background (`.venv\Scripts\python run.py`).
- [ ] **Step 2: For each of A1–A5**, navigate, select mode, fill the real fields, submit, read the fresh snapshot, and record the observed IC/VCE or error text. Confirm A4 changes only `re`.
- [ ] **Step 3: Capture a screenshot** for at least one case and save it under `docs/evidence/`.
- [ ] **Step 4: Fill the observed/method/status columns** and add a short "how RE reaches the equation" trace.
- [ ] **Step 5: Commit** `test: record browser acceptance A1-A5`.

### Task 6: Final verification and push

**Files:**
- No source changes expected.

- [ ] **Step 1: Run the full test suite** and confirm `OK` (41 tests).
- [ ] **Step 2: Re-run A1** in the browser and confirm it still matches the pre-change Lab 2 result (IC 1.23 mA, VCE 8.052 V).
- [ ] **Step 3: Review `git diff` and `git diff --staged`**, confirm no `.venv`, `.env`, credentials or `__pycache__` are staged.
- [ ] **Step 4: Commit any remaining docs** and push to `origin/main`.
- [ ] **Step 5: Report GitHub URL and commit SHA** from `git rev-parse HEAD`.
