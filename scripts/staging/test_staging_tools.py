import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from common import (
    EXPECTED_CONTAINERS,
    EXPECTED_NETWORKS,
    EXPECTED_VOLUMES,
    PROJECT,
    REQUIRED_KEYS,
    run_preflight,
)


class StagingPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env_file = Path(self.temp_dir.name) / ".env.staging"
        self.env_file.touch(mode=0o600)
        self.env_file.chmod(0o600)
        self.path_patch = patch("common.ENV_FILE", self.env_file)
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)

    def write_settings(self, *, database_url="", missing=()):
        settings = {
            "DATABASE_URL": database_url,
            "THAICULTURE_DB_PASSWORD": "test-only-postgres-password",
            "AUTH_JWT_SECRET": "test-only-signing-secret-32-bytes-minimum",
            "AUTH_JWT_ISSUER": "test-only-issuer",
            "AUTH_JWT_AUDIENCE": "test-only-audience",
        }
        for key in missing:
            settings[key] = ""
        self.env_file.write_text(
            "\n".join(f"{key}={value}" for key, value in settings.items()),
            encoding="utf-8",
        )
        self.env_file.chmod(0o600)

    def test_missing_settings_block_before_running_docker(self):
        with patch("common._run_hidden") as docker:
            result = run_preflight()

        self.assertFalse(result.ok)
        self.assertTrue(any("required staging keys missing" in item for item in result.problems))
        docker.assert_not_called()

    def test_non_isolated_database_target_blocks_before_running_docker(self):
        self.write_settings(database_url="postgresql://operator@production-db.example/production")

        with patch("common._run_hidden") as docker:
            result = run_preflight()

        self.assertFalse(result.ok)
        self.assertTrue(any("isolated postgres service" in item for item in result.problems))
        docker.assert_not_called()

    def test_expected_staging_resource_names_are_explicit(self):
        self.assertEqual(PROJECT, "thaiculture-staging-approval")
        self.assertEqual(EXPECTED_CONTAINERS, (
            "thaiculture-staging-approval-postgres",
            "thaiculture-staging-approval-backend",
        ))
        self.assertEqual(EXPECTED_VOLUMES, ("thaiculture-staging-approval-postgres-data",))
        self.assertEqual(EXPECTED_NETWORKS, ("thaiculture-staging-approval-network",))
        self.assertIn("DATABASE_URL", REQUIRED_KEYS)

    def test_valid_staging_target_resolves_only_to_isolated_resources(self):
        self.write_settings(
            database_url=(
                "postgresql://tct_admin:test-only-postgres-password@postgres:5432/"
                "thaiculture_manager_staging_test"
            ),
        )
        config = {
            "name": PROJECT,
            "services": {
                "postgres": {
                    "container_name": EXPECTED_CONTAINERS[0],
                    "labels": {
                        "com.thaiculture.project": PROJECT,
                        "com.thaiculture.environment": "staging",
                        "com.thaiculture.managed-by": "staging-tools",
                    },
                    "ports": [{"target": 5432, "published": "55441", "host_ip": "127.0.0.1"}],
                },
                "backend": {
                    "container_name": EXPECTED_CONTAINERS[1],
                    "labels": {
                        "com.thaiculture.project": PROJECT,
                        "com.thaiculture.environment": "staging",
                        "com.thaiculture.managed-by": "staging-tools",
                    },
                    "ports": [{"target": 8000, "published": "18080", "host_ip": "127.0.0.1"}],
                },
            },
            "volumes": {"staging_postgres_data": {
                "name": EXPECTED_VOLUMES[0],
                "labels": {
                    "com.thaiculture.project": PROJECT,
                    "com.thaiculture.environment": "staging",
                    "com.thaiculture.managed-by": "staging-tools",
                },
            }},
            "networks": {"staging_net": {
                "name": EXPECTED_NETWORKS[0],
                "labels": {
                    "com.thaiculture.project": PROJECT,
                    "com.thaiculture.environment": "staging",
                    "com.thaiculture.managed-by": "staging-tools",
                },
            }},
        }
        fake = CompletedProcess([], 0, json.dumps(config), "")

        with patch("common._run_hidden", return_value=fake) as compose:
            result = run_preflight(check_docker_conflicts=False)

        self.assertTrue(result.ok, result.problems)
        self.assertEqual(result.resources["containers"], list(EXPECTED_CONTAINERS))
        self.assertEqual(result.resources["volumes"], list(EXPECTED_VOLUMES))
        self.assertEqual(result.resources["networks"], list(EXPECTED_NETWORKS))
        compose.assert_called_once()


if __name__ == "__main__":
    unittest.main()
