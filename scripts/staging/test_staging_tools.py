import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from common import (
    COMPOSE_FILE,
    EXPECTED_CONTAINERS,
    EXPECTED_NETWORKS,
    EXPECTED_SERVICES,
    EXPECTED_VOLUMES,
    PROJECT,
    REQUIRED_KEYS,
    _resources_from_config,
    inspect_runtime_inventory,
    run_static_preflight,
)
from migration_contract import EXPECTED_COLUMNS, EXPECTED_INDEXES, MIGRATIONS, schema_gaps


def compose_config(*, project=PROJECT, order=("postgres", "backend"), fixed=False):
    labels = {
        "com.thaiculture.project": PROJECT,
        "com.thaiculture.environment": "staging",
        "com.thaiculture.managed-by": "staging-tools",
    }
    services = {}
    for name in order:
        service = {"labels": labels.copy()}
        if fixed:
            service["container_name"] = "fixed-container-name"
        service["ports"] = ([
            {"target": 5432, "published": "55441", "host_ip": "127.0.0.1"}
        ] if name == "postgres" else [
            {"target": 8000, "published": "18080", "host_ip": "127.0.0.1"}
        ])
        if name == "postgres":
            service["environment"] = {
                "POSTGRES_USER": "tct_admin",
                "POSTGRES_DB": "thaiculture_manager_staging_test",
                "POSTGRES_PASSWORD": "test-only-postgres-password",
            }
        services[name] = service
    return {
        "name": project,
        "services": services,
        "volumes": {"staging_postgres_data": {
            "name": EXPECTED_VOLUMES[0], "labels": labels.copy(),
        }},
        "networks": {"staging_net": {
            "name": EXPECTED_NETWORKS[0], "labels": labels.copy(),
        }},
    }


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
            "DATABASE_URL": database_url or (
                "postgresql://tct_admin:test-only-postgres-password@postgres:5432/"
                "thaiculture_manager_staging_test"
            ),
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

    def static_runner(self, config=None):
        payload = json.dumps(config or compose_config())
        return CompletedProcess([], 0, payload, "")

    def test_missing_settings_block_before_compose_config(self):
        self.write_settings(missing=("AUTH_JWT_ISSUER",))
        with patch("common._run_hidden") as runner:
            result = run_static_preflight()
        self.assertFalse(result.ok)
        self.assertTrue(any("required staging keys missing" in item for item in result.problems))
        runner.assert_not_called()

    def test_services_are_order_independent_and_project_names_are_distinct(self):
        raw = json.dumps(compose_config(order=("backend", "postgres")))
        resources = _resources_from_config(raw)
        self.assertEqual(set(resources["services"]), set(EXPECTED_SERVICES))
        self.assertEqual(resources["containers"]["postgres"], EXPECTED_CONTAINERS[0])
        self.assertEqual(resources["containers"]["backend"], EXPECTED_CONTAINERS[1])
        self.assertEqual(resources["project"], "thaiculture-staging-approval")
        self.assertNotEqual(resources["project"], "thaiculture-manager")

    def test_static_preflight_does_not_contact_docker_inventory(self):
        self.write_settings()
        with patch("common._run_hidden", return_value=self.static_runner()) as runner:
            result = run_static_preflight()
        self.assertTrue(result.ok, result.problems)
        runner.assert_called_once()
        self.assertIn("config", runner.call_args.args[0])

    def test_fixed_container_name_is_rejected(self):
        self.write_settings()
        with patch("common._run_hidden", return_value=self.static_runner(compose_config(fixed=True))):
            result = run_static_preflight()
        self.assertTrue(any("fixed container_name" in item for item in result.problems))

    def test_project_name_mismatch_is_rejected(self):
        self.write_settings()
        with patch("common._run_hidden", return_value=self.static_runner(compose_config(project="local-stack"))):
            result = run_static_preflight()
        self.assertTrue(any("project name" in item for item in result.problems))

    def test_port_binding_mismatch_is_rejected(self):
        self.write_settings()
        config = compose_config()
        config["services"]["postgres"]["ports"][0]["published"] = "5432"
        with patch("common._run_hidden", return_value=self.static_runner(config)):
            result = run_static_preflight()
        self.assertTrue(any("port bindings" in item for item in result.problems))

    def test_database_url_mismatch_is_rejected_without_showing_values(self):
        self.write_settings(database_url="postgresql://tct_admin:wrong@postgres:5432/other")
        with patch("common._run_hidden", return_value=self.static_runner()):
            result = run_static_preflight()
        self.assertTrue(any("DATABASE_URL" in item for item in result.problems))
        self.assertNotIn("other", " ".join(result.problems))

    def test_staging_compose_has_no_fixed_container_name(self):
        self.assertNotIn("container_name:", COMPOSE_FILE.read_text(encoding="utf-8"))

    def test_staging_compose_configures_website_flag_and_same_origin_cors(self):
        compose = COMPOSE_FILE.read_text(encoding="utf-8")
        self.assertIn("WEBSITE_INTEGRATION_ENABLED: ${WEBSITE_INTEGRATION_ENABLED:-false}", compose)
        self.assertIn("CORS_ALLOWED_ORIGINS: ${CORS_ALLOWED_ORIGINS:-}", compose)

    def test_migration_manifest_includes_website_quote_idempotency(self):
        self.assertEqual(MIGRATIONS[-1].name, "20261016_add_website_quote_idempotency.sql")
        self.assertTrue(MIGRATIONS[-1].is_file())
        self.assertIn("website_quote_previews.id|uuid|NO", EXPECTED_COLUMNS)
        self.assertIn("website_booking_idempotency.idempotency_key|uuid|NO", EXPECTED_COLUMNS)
        self.assertIn("idx_website_quote_previews_expires_at", EXPECTED_INDEXES)

    def test_schema_contract_detects_missing_website_column_and_index(self):
        lines = [*EXPECTED_COLUMNS]
        lines.extend(
            f"INDEX|{table}|{name}|CREATE INDEX ON public.{table} {fragments[0]} {fragments[1]}"
            for name, (table, *fragments) in EXPECTED_INDEXES.items()
        )
        missing_columns, missing_indexes = schema_gaps(lines)
        self.assertEqual(missing_columns, set())
        self.assertEqual(missing_indexes, set())

        missing_columns, missing_indexes = schema_gaps([
            line for line in lines
            if line != "website_quote_previews.expires_at|timestamp with time zone|NO"
            and not line.startswith("INDEX|website_quote_previews|")
        ])
        self.assertIn("website_quote_previews.expires_at|timestamp with time zone|NO", missing_columns)
        self.assertIn("idx_website_quote_previews_expires_at", missing_indexes)

    def test_daemon_unavailable_skips_runtime_inventory(self):
        calls = []

        def runner(command):
            calls.append(command)
            return CompletedProcess(command, 1, "", "daemon unavailable")

        inventory = inspect_runtime_inventory(_resources_from_config(json.dumps(compose_config())), runner=runner)
        self.assertEqual(inventory.status, "SKIPPED: Docker daemon unavailable")
        self.assertEqual(calls, [["docker", "info", "--format", "{{.ServerVersion}}"]])

    def test_missing_resources_before_up_are_not_created_yet(self):
        def runner(command):
            if command[:2] == ["docker", "info"]:
                return CompletedProcess(command, 0, "test-version", "")
            if command[:2] == ["docker", "ps"]:
                return CompletedProcess(command, 0, "", "")
            return CompletedProcess(command, 0, "", "")

        inventory = inspect_runtime_inventory(
            _resources_from_config(json.dumps(compose_config())),
            runner=runner, port_probe=lambda _port: True,
        )
        self.assertEqual(inventory.status, "NOT_CREATED_YET")
        self.assertTrue(inventory.ok)
        self.assertEqual(inventory.services, {"postgres": "NOT_CREATED_YET", "backend": "NOT_CREATED_YET"})

    def test_runtime_inventory_uses_project_and_service_labels(self):
        calls = []

        def runner(command):
            calls.append(command)
            if command[:2] == ["docker", "info"]:
                return CompletedProcess(command, 0, "test-version", "")
            if command[:2] == ["docker", "inspect"]:
                name = command[2]
                service = "postgres" if name.endswith("postgres-1") else "backend"
                target, published = ("5432/tcp", "55441") if service == "postgres" else ("8000/tcp", "18080")
                details = [{
                    "Config": {"Labels": {
                        "com.docker.compose.project": PROJECT,
                        "com.docker.compose.service": service,
                        "com.thaiculture.project": PROJECT,
                        "com.thaiculture.environment": "staging",
                    }},
                    "HostConfig": {"PortBindings": {target: [{"HostIp": "127.0.0.1", "HostPort": published}]}},
                    "State": {"Running": True},
                }]
                return CompletedProcess(command, 0, json.dumps(details), "")
            if command[:2] == ["docker", "ps"] and "{{.Names}}" in command:
                service = next((arg.rsplit("=", 1)[1] for arg in command if arg.startswith("label=com.docker.compose.service=")), None)
                name = f"{PROJECT}-{service}-1"
                return CompletedProcess(command, 0, name, "")
            if command[:2] in (["docker", "volume"], ["docker", "network"]):
                is_volume = command[1] == "volume"
                expected = EXPECTED_VOLUMES[0] if is_volume else EXPECTED_NETWORKS[0]
                return CompletedProcess(command, 0, expected, "")
            if command[:2] == ["docker", "ps"]:
                return CompletedProcess(command, 0, "", "")
            return CompletedProcess(command, 0, "", "")

        inventory = inspect_runtime_inventory(
            _resources_from_config(json.dumps(compose_config())),
            runner=runner, port_probe=lambda _port: True,
        )
        self.assertEqual(inventory.status, "PASS", repr(inventory))
        service_filters = [
            arg for call in calls for arg in call
            if arg.startswith("label=com.docker.compose.service=")
        ]
        self.assertEqual(set(service_filters), {
            "label=com.docker.compose.service=postgres",
            "label=com.docker.compose.service=backend",
        })
        service_calls = [call for call in calls if any(arg.startswith("label=com.docker.compose.service=") for arg in call)]
        self.assertTrue(service_calls)
        self.assertTrue(all("label=com.docker.compose.project=thaiculture-staging-approval" in call for call in service_calls))

    def test_port_conflict_is_reported(self):
        def runner(command):
            if command[:2] == ["docker", "info"]:
                return CompletedProcess(command, 0, "test-version", "")
            return CompletedProcess(command, 0, "", "")

        inventory = inspect_runtime_inventory(
            _resources_from_config(json.dumps(compose_config())),
            runner=runner, port_probe=lambda port: port != 55441,
        )
        self.assertTrue(any("55441" in item and "already in use" in item for item in inventory.problems))

    def test_volume_and_network_name_conflicts_are_reported(self):
        def runner(command):
            if command[:2] == ["docker", "info"]:
                return CompletedProcess(command, 0, "test-version", "")
            if command[1] in {"volume", "network"}:
                name = EXPECTED_VOLUMES[0] if command[1] == "volume" else EXPECTED_NETWORKS[0]
                # Present in global inventory, absent from inventory carrying the staging label.
                return CompletedProcess(command, 0, name if "--filter" not in command else "", "")
            return CompletedProcess(command, 0, "", "")

        inventory = inspect_runtime_inventory(
            _resources_from_config(json.dumps(compose_config())),
            runner=runner, port_probe=lambda _port: True,
        )
        self.assertTrue(any("volume name exists" in item for item in inventory.problems))
        self.assertTrue(any("network name exists" in item for item in inventory.problems))


if __name__ == "__main__":
    unittest.main()
