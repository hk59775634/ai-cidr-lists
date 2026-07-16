import unittest

from ai_cidr_lists.cidr import merge_cidrs, normalize_cidr, parse_cidr_lines


class CidrTests(unittest.TestCase):
    def test_normalize_host(self):
        self.assertEqual(normalize_cidr("1.2.3.4"), "1.2.3.4/32")

    def test_parse_comments(self):
        text = "# head\n8.8.8.8/32\n1.1.1.1 # cf\n\n8.8.8.8/32\n"
        self.assertEqual(parse_cidr_lines(text), ["8.8.8.8/32", "1.1.1.1/32"])

    def test_merge_sort(self):
        self.assertEqual(
            merge_cidrs([["10.0.0.2/32", "10.0.0.1/32"], ["10.0.0.1/32"]]),
            ["10.0.0.1/32", "10.0.0.2/32"],
        )

    def test_reject_ipv6(self):
        with self.assertRaises(ValueError):
            normalize_cidr("2001:db8::1")


if __name__ == "__main__":
    unittest.main()
