# BJT Common-Emitter DC Bias Calculator

A small Flask web app for the ENG29 2121 lab. Pick one of three
common-emitter bias circuits, enter its values and get the DC operating
point with units, input validation and region warnings.

- **Voltage Divider Bias** — the Lab 2 circuit, unchanged: `R1` from VCC to
  base, `R2` from base to ground, `RC` at the collector, `RE` at the emitter.
- **Fixed Bias** — `RB` from VCC to base, emitter grounded.
- **Emitter Bias (single supply)** — `RB` from VCC to base, `RE` from emitter
  to ground.

All three share `VCC`, `RC`, `beta` and `VBE`. The selected mode decides which
extra resistor fields are shown and validated; an unknown mode is an error, never
a silent divider.

## Run it

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS / Linux

.venv\Scripts\python run.py
```

Open <http://127.0.0.1:5000>, pick the circuit, fill the form, press
**Calculate DC Bias**.

Resistances are entered in kilohms: 1 MΩ is `1000`. Results are shown in V,
mA and µA with 4 significant digits.

## Engineering model

The model assumes constant `beta` and `VBE` in the forward-active region.
Only `VBE`, `VCC`, the resistors and `beta` are inputs; the app computes:

```
IC = beta * IB
IE = (beta + 1) * IB
VE = IE * RE                    (0 V for fixed bias)
VB = VE + VBE
VC = VCC - IC * RC
VCE = VC - VE
```

Each mode supplies its own base current:

| Mode | Base current |
|---|---|
| Fixed | `IB = (VCC - VBE) / RB` |
| Emitter | `IB = (VCC - VBE) / (RB + (beta + 1) * RE)` |
| Divider | `IB = (VTH - VBE) / (RTH + (beta + 1) * RE)` |

For the divider, the base divider is replaced by its Thevenin equivalent:

```
VTH = VCC * R2 / (R1 + R2)
RTH = R1 * R2 / (R1 + R2)
```

The divider result is the exact solution, which accounts for base current. The
app also shows the stiff-divider approximation:

```
VB = VTH
VE = VB - VBE
IE = VE / RE
IC = IE
VCE = VCC - IC * RC - IE * RE
```

The comparison panel shows both, their difference in percent, and the stiffness
ratio `beta * RE / RTH`. The approximation is valid when that ratio is at least
10.

### Operating regions

The divider path keeps the Lab 2 piecewise handling: cutoff when `VTH <= VBE`,
saturation when the active-model `VCE <= 0.2 V`, and a clamped, physically valid
result in both cases.

For Fixed and Emitter bias, the handout asks for a warning rather than a
cutoff/saturation solution. A valid input whose linear model gives `IB <= 0` or
`VCE <= 0.2 V` still returns the linear values, flags the result as
**forward-active model warning**, and explains why.

## Validation

**Hard errors** (HTTP 400, no result, the user's values are kept):

- missing or empty field required by the selected mode
- non-numeric input, `nan`, `inf`, or intermediate overflow
- `VCC <= 0`, or `VCC <= 0.2 V`
- any resistance required by the mode `<= 0`
- `beta <= 1`
- `VBE < 0`
- unknown mode

**Warnings** (result is still shown):

- `VBE` outside 0.5–0.9 V
- `beta` outside 20–500
- `VCC` above 30 V
- divider cutoff, saturation, or operation within 0.5 V of saturation
- non-stiff divider
- Fixed/Emitter model outside the forward-active region (`IB <= 0` or
  `VCE <= 0.2 V`)

## Reference cases

Common values: `VCC = 12 V`, `RC = 2.2 kΩ`, `beta = 100`, `VBE = 0.70 V`.
Expected values are hand-calculated from the equations above, not copied from
the app.

| Case | Mode | Extra inputs | Expected IC | Expected VCE |
|---|---|---|---|---|
| A1 | Divider | `R1 = 100 kΩ`, `R2 = 22 kΩ`, `RE = 1 kΩ` | 1.2298 mA | 8.0522 V |
| A2 | Fixed | `RB = 1 MΩ` | 1.1300 mA | 9.5140 V |
| A3 | Emitter | `RB = 1 MΩ`, `RE = 1 kΩ` | 1.0263 mA | 8.7054 V |
| A4 | Emitter | `RB = 1 MΩ`, `RE = 2 kΩ` | 0.9401 mA | 8.0328 V |
| A5 | Fixed | `RB = 0` | hard error | — |

A1 is the same input set the Lab 2 app accepted, and it still gives the same
result. A4 is the A3 circuit with only `RE` changed; the larger emitter
resistor lowers `IB`, so `IC` falls.

The full acceptance record, including observed values and browser evidence,
is in [`docs/validation.md`](docs/validation.md).

## Divider regression cases

| VCC | R1 | R2 | RC | RE | beta | VBE | Expected |
|---|---|---|---|---|---|---|---|
| 12 V | 47 k | 10 k | 2.2 k | 1 k | 150 | 0.7 V | active: IC 1.324 mA, VCE 7.755 V, delta IC 6.164 %, stiff |
| 12 V | 47 k | 2.2 k | 2.2 k | 1 k | 150 | 0.7 V | cutoff: all currents 0, VCE 12 V |
| 12 V | 47 k | 10 k | 2.2 k | 100 | 150 | 0.7 V | saturation: IC 5.126 mA, IB 107.0 µA, IE 5.233 mA, VCE 0.2 V |

## Tests

```bash
.venv\Scripts\python -m unittest discover -s tests -t . -v
```

41 existing tests cover divider validation, the three operating regions,
the cross-check and the HTTP layer. Per the Lab 03 handout, the new modes are
checked through the browser acceptance table instead of new `unittest` cases.

## Browser acceptance and MCP

The project includes `opencode.json` with Playwright MCP (OpenCode V2 layout):

```json
{
  "mcp": {
    "servers": {
      "playwright": {
        "type": "local",
        "command": ["npx", "-y", "@playwright/mcp@latest",
                    "--browser", "chrome", "--isolated"]
      }
    }
  }
}
```

MCP is the bridge: OpenCode is the MCP client, Playwright MCP is the server that
opens the browser, and the browser talks to Flask over ordinary HTTP. Playwright
is not a Python dependency of the app.

The A1–A5 cases were run against the live Flask server with OpenCode Browser
tools because that is the browser integration available in this environment;
the method column in `docs/validation.md` records it as `OpenCode Browser`. If
Playwright MCP is connected, the same steps work with `browser_navigate`,
`browser_snapshot`, `browser_select_option`, `browser_fill_form` and
`browser_click`.

## Layout

```
bjt_bias/
  __init__.py      Flask app factory and the `sig` formatting filter
  engineering.py   pure math: inputs, per-mode parsing, three analyses,
                   validation, divider cross-check
  routes.py        GET / (mode picker) and POST / (dispatch by mode); kΩ to Ω
  templates/       base.html (header, goal), index.html (panels + SVG)
  static/          style.css
tests/             existing engineering and route tests
docs/
  validation.md    A1–A5 acceptance record
run.py             development server on 127.0.0.1:5000
```

## AI assistance

The Lab 03 changes (Fixed/Emitter functions, mode dispatch, per-mode form and
validation, documentation) were drafted with the OpenCode agent. The equations
and sign conventions were checked against Engineering Electronics and against
the hand calculations in `docs/validation.md`; the divider path was kept intact
so its Lab 2 regression tests still pass.

## สรุปภาษาไทย

เว็บแอป Flask สำหรับคำนวณจุดทำงาน DC ของวงจรไบอัส BJT แบบ common-emitter
รองรับสามวงจร ได้แก่ voltage-divider bias (ผลเดิมจาก Lab 2), fixed bias และ
emitter bias แบบแหล่งจ่ายเดียว ผู้ใช้เลือกวงจรได้จากหน้าเว็บ ฟอร์มจะแสดงเฉพาะ
ช่องที่วงจรนั้นใช้ และตรวจอินพุตตามโหมด ผลลัพธ์แสดง VB, VE, VC, VCE, IB, IC, IE
พร้อมหน่วยและคำเตือนเมื่อแบบจำลอง forward-active อาจใช้ไม่ได้

รันด้วย `.venv\Scripts\python run.py` แล้วเปิด <http://127.0.0.1:5000>
