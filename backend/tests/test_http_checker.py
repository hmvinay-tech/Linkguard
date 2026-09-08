import unittest

from app.crawler.http_checker import classify_response


class HttpCheckerTests(unittest.TestCase):
    def test_200_is_healthy(self) -> None:
        self.assertEqual(classify_response(200), "healthy")

    def test_404_is_critical(self) -> None:
        self.assertEqual(classify_response(404), "critical")

    def test_403_is_warning(self) -> None:
        self.assertEqual(classify_response(403), "warning")

    def test_server_error_is_critical(self) -> None:
        self.assertEqual(classify_response(500), "critical")

    def test_excessive_redirects_are_warning(self) -> None:
        self.assertEqual(classify_response(200, redirect_count=3), "warning")

    def test_linkedin_restricted_response_is_warning(self) -> None:
        self.assertEqual(classify_response(999, url="https://www.linkedin.com/in/example"), "warning")


if __name__ == "__main__":
    unittest.main()
