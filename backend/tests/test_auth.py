import unittest
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.services import auth


class AuthTests(unittest.TestCase):
    def test_password_hash_verifies_original_password(self) -> None:
        password_hash = auth.hash_password("correct-horse-battery")

        self.assertTrue(auth.verify_password("correct-horse-battery", password_hash))
        self.assertFalse(auth.verify_password("wrong-password", password_hash))

    def test_access_token_round_trip(self) -> None:
        token = auth.create_access_token(42)

        self.assertEqual(auth.verify_access_token(token), 42)

    def test_expired_access_token_is_rejected(self) -> None:
        expired = int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp())
        payload = auth._b64encode(b'{"sub":42,"exp":%d}' % expired)
        token = f"{payload}.{auth._sign(payload)}"

        with self.assertRaises(HTTPException):
            auth.verify_access_token(token)

    def test_auth_rate_limit_blocks_repeated_failures(self) -> None:
        key = "login:rate@example.com"
        auth._auth_attempts.clear()

        for _ in range(auth.AUTH_RATE_LIMIT_ATTEMPTS):
            auth._record_auth_failure(key)

        with self.assertRaises(HTTPException) as error:
            auth._check_auth_rate_limit(key)

        self.assertEqual(error.exception.status_code, 429)
        auth._auth_attempts.clear()

    def test_auth_rate_limit_can_clear_after_success(self) -> None:
        key = "login:clear@example.com"
        auth._auth_attempts.clear()
        auth._record_auth_failure(key)

        auth._clear_auth_failures(key)

        self.assertNotIn(key, auth._auth_attempts)


if __name__ == "__main__":
    unittest.main()
