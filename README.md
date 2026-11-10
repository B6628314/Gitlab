# BJT Common-Emitter DC Bias Calculator

A small Flask web app for the ENG29 2121 lab. Enter the voltage-divider bias
values of a common-emitter BJT stage and get the DC operating point, the
operating region with warnings, and a cross-check between two independent
engineering calculations.

## The circuit

Voltage-divider bias: `R1` from VCC to base, `R2` from base to ground, `RC` at
the collector, `RE` at the emitter.

Thevenin equivalent of the base divider:

```
VTH = VCC * R2 / (R1 + R2)
RTH = R1 * R2 / (R1 + R2)
```

**Exact** solution, which accounts for base current:

```
IB  = (VTH - VBE) / (RTH + (beta + 1) * RE)
IC  = beta * IB
IE  = (beta + 1) * IB
VCE = VCC - IC * RC - IE * RE
```

**Approximate** solution, valid only when the divider is stiff (`IB` assumed 0):

```
VB  = VTH
VE  = VB - VBE
IE  = VE / RE
IC  = IE
VCE = VCC - IC * RC - IE * RE
```

The app shows both, their difference in percent, and the stiffness ratio
`beta * RE / RTH`. The approximation is considered valid when that ratio is at
least 10.

## Operating regions

The linear model only holds in the forward-active region, so the app clamps the
result to a physically valid operating point:

| Region | Condition | Result |
|---|---|---|
| Cutoff | `VTH <= VBE` | all currents 0, `VCE = VCC` |
| Saturation | active-model `VCE <= 0.2 V` | `VCE = 0.2 V`; `IC` and `IB` solve `IC*(RC+RE) + IB*RE = VCC - 0.2` and `IC*RE + IB*(RTH+RE) = VTH - VBE`, so `VC - VE` still equals `VCE` |
| Active | otherwise | exact solution above |

Every reported current is non-negative and `0 <= VCE <= VCC`. The cross-check
panel is shown only in the active region, where both derivations are valid.

## Run it

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS / Linux

.venv\Scripts\python run.py
```

Open <http://127.0.0.1:5000>, fill the form, press **Calculate DC Bias**.

Resistances are entered in kilohms: 47 kOhm is `47`. Results are shown in mA,
microamps and volts, with 4 significant digits.

## Tests

```bash
.venv\Scripts\python -m unittest discover -s tests -t . -v
```

41 tests cover input validation, the three operating regions, the cross-check,
and the HTTP layer.

## Reference cases

| VCC | R1 | R2 | RC | RE | beta | VBE | Expected |
|---|---|---|---|---|---|---|---|
| 12 V | 47 k | 10 k | 2.2 k | 1 k | 150 | 0.7 V | active: IC 1.324 mA, VCE 7.755 V, delta IC 6.164 %, stiff |
| 12 V | 47 k | 2.2 k | 2.2 k | 1 k | 150 | 0.7 V | cutoff: all currents 0, VCE 12 V |
| 12 V | 47 k | 10 k | 2.2 k | 100 | 150 | 0.7 V | saturation: IC 5.126 mA, IB 107.0 uA, IE 5.233 mA, VCE 0.2 V, VC 0.723 V, VE 0.523 V |

## Validation

Hard errors (no result is shown): missing or empty field, non-numeric, `nan`
or `inf` input, `VCC <= 0`, `VCC <= 0.2 V` (`VCE_SAT`), any resistance `<= 0`,
`beta <= 1`, negative `VBE`, and inputs large enough to overflow the arithmetic.

Warnings (result is still shown): `VBE` outside 0.5-0.9 V, `beta` outside
20-500, `VCC` above 30 V, cutoff, saturation, operation within 0.5 V of
saturation, and a non-stiff divider.

## Layout

```
bjt_bias/
  __init__.py      Flask app factory and the `sig` formatting filter
  engineering.py   pure math: inputs, validation, operating point, cross-check
  routes.py        GET / (prefilled form) and POST / (analyze); kOhm to ohm
  templates/       base.html (header, goal bar), index.html (3 panels + SVG)
  static/          style.css
tests/             engineering and route tests
run.py             development server on 127.0.0.1:5000
```

## สรุปภาษาไทย

เว็บแอป Flask สำหรับคำนวณจุดทำงาน DC ของวงจรไบอัสแบบ voltage divider ของทรานซิสเตอร์ BJT
แบบ common-emitter รับค่า VCC, R1, R2, RC, RE, beta และ VBE แล้วแสดงกระแสและแรงดัน
พร้อมหน่วย ตรวจสอบความถูกต้องของข้อมูล แจ้งเตือนเมื่อทรานซิสเตอร์อยู่ในช่วง cutoff หรือ
saturation และเปรียบเทียบผลระหว่างวิธีคำนวณแบบละเอียด (Thevenin) กับแบบประมาณ
(stiff divider) ให้เห็นว่าเมื่อใดการประมาณจึงใช้ได้

รันด้วย `.venv\Scripts\python run.py` แล้วเปิด <http://127.0.0.1:5000>
