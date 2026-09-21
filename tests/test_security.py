import unittest

from autobond.config import parse_users
from autobond.security import account_label, redact_secrets


class SecurityTests(unittest.TestCase):
    def test_parse_users_does_not_echo_invalid_value(self) -> None:
        invalid = "sensitive-value-without-separator"

        with self.assertRaises(ValueError) as context:
            parse_users(invalid)

        self.assertNotIn(invalid, str(context.exception))

    def test_parse_users_rejects_empty_credentials(self) -> None:
        for value in ("account:", ":password"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_users(value)

    def test_account_label_contains_no_account_value(self) -> None:
        self.assertEqual(account_label(2), "账户#2")

    def test_redact_secrets_replaces_account_password_and_token(self) -> None:
        text = "account-123 password-456 token-789 account-123"

        result = redact_secrets(text, ("account-123", "password-456", "token-789"))

        self.assertEqual(result, "<redacted> <redacted> <redacted> <redacted>")


if __name__ == "__main__":
    unittest.main()
