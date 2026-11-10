import unittest

from bjt_bias.engineering import (
    BiasInputs, InputError, Region, analyze, compare, parse_inputs,
)


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

    def test_resistor_scale_converts_kilohms_to_ohms(self):
        inputs = parse_inputs(valid_form(r1="100", r2="22", rc="2.2", re="1.0"),
                              resistor_scale=1000.0)
        self.assertAlmostEqual(inputs.r1, 100000.0)
        self.assertAlmostEqual(inputs.r2, 22000.0)
        self.assertAlmostEqual(inputs.rc, 2200.0)
        self.assertAlmostEqual(inputs.re, 1000.0)
        self.assertAlmostEqual(inputs.vcc, 12.0)


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
        self.assertAlmostEqual(r.ic_a, 5.125784e-3, places=8)
        self.assertAlmostEqual(r.ib_a, 106.964537e-6, places=9)
        self.assertAlmostEqual(r.ie_a, 5.232749e-3, places=8)
        self.assertAlmostEqual(r.vb_v, 1.223275, places=5)
        self.assertAlmostEqual(r.vc_v, 0.723275, places=5)
        self.assertAlmostEqual(r.ve_v, 0.523275, places=5)

    def test_saturation_node_voltages_match_vce(self):
        r = analyze(parse_inputs(valid_form(re="100")))
        self.assertAlmostEqual(r.vc_v - r.ve_v, r.vce_v, places=9)

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
            self.assertAlmostEqual(r.vc_v - r.ve_v, r.vce_v, places=9)

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


if __name__ == "__main__":
    unittest.main()
