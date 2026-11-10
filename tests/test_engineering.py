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


if __name__ == "__main__":
    unittest.main()
