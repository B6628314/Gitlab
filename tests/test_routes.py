import unittest

from bjt_bias import create_app


def form(**overrides):
    data = {
        "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2",
        "re": "1.0", "beta": "100", "vbe": "0.7",
    }
    data.update(overrides)
    return data


class RoutesTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_shows_form(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Input Parameters", response.data)
        self.assertIn(b"Calculate DC Bias", response.data)
        self.assertIn(b"DC Bias Results", response.data)
        self.assertIn(b"Circuit: Common-Emitter Amplifier", response.data)
        self.assertIn(b"Week 2 Goal", response.data)

    def test_get_prefills_the_mockup_defaults(self):
        response = self.client.get("/")
        self.assertIn(b'value="12.0"', response.data)
        self.assertIn(b'value="100"', response.data)
        self.assertIn(b'value="0.70"', response.data)

    def test_post_reference_case(self):
        response = self.client.post("/", data=form())
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"1.23", response.data)
        self.assertIn(b"8.052", response.data)
        self.assertIn(b"transistor in active region", response.data)
        self.assertIn(b"19.03", response.data)
        self.assertIn(b"not stiff", response.data)

    def test_post_cutoff_case(self):
        response = self.client.post("/", data=form(r2="2.2"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"cutoff", response.data)

    def test_post_saturation_case(self):
        response = self.client.post("/", data=form(re="0.1"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"saturation", response.data)
        self.assertIn(b"5.126", response.data)

    def test_invalid_input_returns_400_and_keeps_values(self):
        response = self.client.post("/", data=form(vcc="0"))
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"must be greater than zero", response.data)
        self.assertIn(b'value="0"', response.data)

    def test_nan_input_returns_400(self):
        response = self.client.post("/", data=form(vcc="nan"))
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
