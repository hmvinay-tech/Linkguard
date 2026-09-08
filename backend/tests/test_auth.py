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


if __name__ == "__main__":
    unittest.main()
