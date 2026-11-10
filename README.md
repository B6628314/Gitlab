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
| Saturation | active-model `VCE <= 0.2 V` | `VCE = 0.2 V`, `IC = (VCC - 0.2) / (RC + RE)`, `IB` from the base loop |
| Active | otherwise | exact solution above |

Every reported current is non-negative and `0 <= VCE <= VCC`. The cross-check
panel is shown only in the active region, where both derivations are valid.

## Run it

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS / Linux

python run.py
```

Open <http://127.0.0.1:5000>, fill the form, press **Analyze**.

Resistances are entered in ohms: 47 kOhm is `47000`. Results are shown in mA,
microamps and volts, with 4 significant digits.

## Tests

```bash
python -m unittest discover -s tests -t . -v
```

30 tests cover input validation, the three operating regions, the cross-check,
and the HTTP layer.

## Reference cases

| VCC | R1 | R2 | RC | RE | beta | VBE | Expected |
|---|---|---|---|---|---|---|---|
| 12 V | 47 k | 10 k | 2.2 k | 1 k | 150 | 0.7 V | active: IC 1.324 mA, VCE 7.755 V, delta IC 6.164 %, stiff |
| 12 V | 47 k | 2.2 k | 2.2 k | 1 k | 150 | 0.7 V | cutoff: all currents 0, VCE 12 V |
| 12 V | 47 k | 10 k | 2.2 k | 100 | 150 | 0.7 V | saturation: IC 5.130 mA, VCE 0.2 V |

## Validation

Hard errors (no result is shown): non-numeric, `nan` or `inf` input, `VCC <= 0`,
any resistance `<= 0`, `beta <= 1`, negative `VBE`.

Warnings (result is still shown): `VBE` outside 0.5-0.9 V, `beta` outside
20-500, `VCC` above 30 V, cutoff, saturation, operation within 0.5 V of
saturation, and a non-stiff divider.

## Layout

```
bjt_bias/
  __init__.py      Flask app factory and the `sig` formatting filter
  engineering.py   pure math: inputs, validation, operating point, cross-check
  routes.py        GET / (form) and POST / (analyze)
  templates/       base.html, index.html
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

รันด้วย `python run.py` แล้วเปิด <http://127.0.0.1:5000>
