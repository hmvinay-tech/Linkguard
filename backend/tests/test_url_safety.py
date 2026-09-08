import unittest

from app.crawler.url_safety import UnsafeUrlError, validate_public_url


class UrlSafetyTests(unittest.TestCase):
    def test_rejects_localhost(self) -> None:
        with self.assertRaises(UnsafeUrlError):
            validate_public_url("http://localhost:8000")

    def test_rejects_private_ipv4(self) -> None:
        with self.assertRaises(UnsafeUrlError):
            validate_public_url("http://127.0.0.1")

    def test_rejects_metadata_ip(self) -> None:
        with self.assertRaises(UnsafeUrlError):
            validate_public_url("http://169.254.169.254/latest/meta-data")

    def test_allows_public_url_shape(self) -> None:
        validate_public_url("https://example.com")


if __name__ == "__main__":
    unittest.main()
