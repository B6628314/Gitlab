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
        self.assertIn(b"Inputs", response.data)
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


if __name__ == "__main__":
    unittest.main()
