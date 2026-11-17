# Lab 03 — Browser Acceptance Record (A1–A5)

Common inputs for every case: `VCC = 12 V`, `RC = 2.2 kΩ`, `beta = 100`,
`VBE = 0.70 V`. Resistances are entered on the form in kΩ, so 1 MΩ is
`1000` and 1 kΩ is `1.0`.

Tolerance: `IC` within ±0.01 mA, `VCE` within ±0.02 V of the unrounded
hand calculation. Cases are `PASS`, `FAIL` or `NOT RUN`.

## Independent hand calculations

These values come from the equations in the handout, calculated before the
app was run.

**A1 — Voltage Divider,** `R1 = 100 kΩ`, `R2 = 22 kΩ`, `RE = 1 kΩ`

```
VTH = 12 * 22 / 122            = 2.163934 V
RTH = 100 * 22 / 122           = 18.03279 kΩ
IB  = (2.163934 - 0.70) / (18.03279 + 101) kΩ
                               = 12.2984 µA
IC  = 100 * 12.2984 µA         = 1.22984 mA
IE  = 101 * 12.2984 µA         = 1.24214 mA
VCE = 12 - 1.22984*2.2 - 1.24214*1 = 8.05221 V
```

**A2 — Fixed,** `RB = 1 MΩ`

```
IB  = (12 - 0.70) / 1,000,000  = 11.30 µA
IC  = 100 * 11.30 µA           = 1.13000 mA
IE  = 101 * 11.30 µA           = 1.14130 mA
VE  = 0 V
VCE = 12 - 1.13000*2.2         = 9.51400 V
```

**A3 — Emitter,** `RB = 1 MΩ`, `RE = 1 kΩ`

```
IB  = (12 - 0.70) / (1,000,000 + 101*1000) = 10.26340 µA
IC  = 100 * 10.26340 µA        = 1.02634 mA
IE  = 101 * 10.26340 µA        = 1.03660 mA
VE  = 1.03660 * 1 kΩ           = 1.03660 V
VCE = 12 - 1.02634*2.2 - 1.03660*1 = 8.70545 V
```

**A4 — Emitter with only `RE` changed to 2 kΩ**

```
IB  = 11.30 / (1,000,000 + 101*2000) = 9.40100 µA
IC  = 100 * 9.40100 µA         = 0.94010 mA
IE  = 101 * 9.40100 µA         = 0.94950 mA
VE  = 1.89900 V
VCE = 12 - 0.94010*2.2 - 1.89900 = 8.03278 V
```

Prediction before running: `IC` must **decrease** from A3 because the larger
`RE` raises the `(beta + 1) * RE` term in the base loop, reducing `IB`.

**A5 — Fixed with `RB = 0`**

`RB` is a resistance in the base loop, so it must be greater than zero. The
form or Flask must report an input error, the page must stay up, and no old
result may be presented as this run's result.

## Case table

| Case | Mode and inputs | Expected before running | Seen in browser | Method | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 · existing mode | Divider · R1 100, R2 22, RE 1 | IC 1.2298 mA · VCE 8.0522 V, same as Lab 2 | — | — | — | — |
| A2 · Fixed | Fixed · RB 1000 (1 MΩ) | IC 1.1300 mA · VCE 9.5140 V; no RE field needed | — | — | — | — |
| A3 · Emitter | Emitter · RB 1000, RE 1.0 | IC 1.0263 mA · VCE 8.7054 V; RE field present and used | — | — | — | — |
| A4 · one value changed | Emitter · RB 1000, RE 2.0 | IC 0.9401 mA (lower than A3) · VCE 8.0328 V | — | — | — | — |
| A5 · invalid input | Fixed · RB 0 | Error asking to correct RB; no result and no crash | — | — | — | — |

## How RE reaches the equation (A4 trace)

1. The template posts `mode=emitter` and the field `re=2.0`.
2. `routes.analyze_form` calls `parse_mode_inputs(request.form, "emitter",
   RESISTOR_SCALE)`; the parser converts `re` from kΩ to `2000.0 Ω` once.
3. `analyze_emitter` evaluates `IB = (VCC - VBE) / (RB + (beta + 1) * RE)`,
   then `IE = (beta + 1) * IB` and `VE = IE * RE`.
4. The returned dict carries `ic_ma` and `vce_v`; the template prints them
   without re-deriving the circuit.

Because `RE` appears in the denominator of `IB` and in `VE`, changing only
`RE` from 1 kΩ to 2 kΩ must change both the current and the emitter voltage.
If the page does not change, check the posted `re` value, the kΩ→Ω conversion
and the field name before touching the equations.

## Change log

- Initial record created with the independent hand calculations above.
- Browser observations are added after the live A1–A5 run.
