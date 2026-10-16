import unittest

from app.config import DEFAULT_LOCAL_CORS_ORIGINS, Settings, parse_cors_origins


class DeploymentConfigurationTests(unittest.TestCase):
    def test_website_integration_is_disabled_by_default(self):
        settings = Settings(_env_file=None, database_url="postgresql://unit@localhost/test")
        self.assertFalse(settings.website_integration_enabled)

    def test_cors_origins_are_parsed_as_explicit_comma_separated_origins(self):
        self.assertEqual(
            parse_cors_origins(" https://staging.example.test/ , https://admin.example.test "),
            ["https://staging.example.test", "https://admin.example.test"],
        )
        self.assertEqual(parse_cors_origins(""), [])
        self.assertEqual(parse_cors_origins(DEFAULT_LOCAL_CORS_ORIGINS), [
            "http://localhost:5173", "http://127.0.0.1:5173",
            "http://localhost:5174", "http://127.0.0.1:5174",
        ])

    def test_cors_wildcard_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "wildcard"):
            parse_cors_origins("https://example.test, *")
        with self.assertRaisesRegex(ValueError, "wildcard"):
            parse_cors_origins("https://*.example.test")


if __name__ == "__main__":
    unittest.main()
