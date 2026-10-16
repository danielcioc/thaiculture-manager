from __future__ import annotations

import json
import os
import re
import socket
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env.staging"
COMPOSE_FILE = ROOT / "docker-compose.staging.yml"
PROJECT = "thaiculture-staging-approval"
REQUIRED_KEYS = (
    "DATABASE_URL",
    "THAICULTURE_DB_PASSWORD",
    "AUTH_JWT_SECRET",
    "AUTH_JWT_ISSUER",
    "AUTH_JWT_AUDIENCE",
)
EXPECTED_SERVICES = ("postgres", "backend")
EXPECTED_CONTAINERS = tuple(f"{PROJECT}-{service}-1" for service in EXPECTED_SERVICES)
EXPECTED_VOLUMES = ("thaiculture-staging-approval-postgres-data",)
EXPECTED_NETWORKS = ("thaiculture-staging-approval-network",)
EXPECTED_PORTS = (55441, 18080)
TEST_DATABASE = "thaiculture_manager_staging_test"
LABEL_PROJECT = "com.thaiculture.project"
LABEL_ENVIRONMENT = "com.thaiculture.environment"
LABEL_STAGE = "staging"
COMPOSE_PROJECT_LABEL = "com.docker.compose.project"
COMPOSE_SERVICE_LABEL = "com.docker.compose.service"


@dataclass
class Preflight:
    values: dict[str, str]
    resources: dict[str, Any]
    problems: list[str]

    @property
    def ok(self) -> bool:
        return not self.problems


@dataclass
class RuntimeInventory:
    status: str
    services: dict[str, str] = field(default_factory=dict)
    volumes: dict[str, str] = field(default_factory=dict)
    networks: dict[str, str] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems and self.status in {"PASS", "NOT_CREATED_YET"}


def parse_env_file() -> dict[str, str]:
    if not ENV_FILE.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key in REQUIRED_KEYS:
            values[key] = value
    return values


def _clean_compose_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in REQUIRED_KEYS:
        env.pop(key, None)
    return env


def compose_command(*args: str) -> list[str]:
    return [
        "docker", "compose", "--project-name", PROJECT,
        "--env-file", str(ENV_FILE), "-f", str(COMPOSE_FILE), *args,
    ]


def _run_hidden(command: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            input=input_text,
            capture_output=True,
            text=True,
            env=_clean_compose_env(),
            cwd=ROOT,
        )
    except OSError:
        return subprocess.CompletedProcess(command, 127, "", "")


def _target_matches_config(values: dict[str, str], postgres_env: dict[str, Any]) -> bool:
    try:
        parsed = urlsplit(values.get("DATABASE_URL", ""))
        return bool(
            parsed.scheme in {"postgres", "postgresql"}
            and parsed.hostname == "postgres"
            and parsed.port == 5432
            and parsed.username == postgres_env.get("POSTGRES_USER")
            and postgres_env.get("POSTGRES_DB")
            and parsed.path.lstrip("/") == postgres_env.get("POSTGRES_DB")
            and unquote(parsed.password or "")
            and unquote(parsed.password or "") == values.get("THAICULTURE_DB_PASSWORD")
            and unquote(parsed.password or "") == postgres_env.get("POSTGRES_PASSWORD")
        )
    except ValueError:
        return False


def _resources_from_config(raw: str) -> dict[str, Any] | None:
    try:
        config = json.loads(raw)
    except json.JSONDecodeError:
        return None
    project = config.get("name")
    services = config.get("services", {})
    containers = {
        name: service.get("container_name") or f"{project}-{name}-1"
        for name, service in services.items()
    }
    fixed_container_names = {
        name: service["container_name"]
        for name, service in services.items()
        if service.get("container_name")
    }
    volumes = {
        name: item.get("name") or f"{project}_{name}"
        for name, item in config.get("volumes", {}).items()
    }
    networks = {
        name: item.get("name") or f"{project}_{name}"
        for name, item in config.get("networks", {}).items()
    }
    expected_labels = {
        LABEL_PROJECT: PROJECT,
        LABEL_ENVIRONMENT: LABEL_STAGE,
        "com.thaiculture.managed-by": "staging-tools",
    }
    label_objects = [
        *(service.get("labels", {}) for service in services.values()),
        *(volume.get("labels", {}) for volume in config.get("volumes", {}).values()),
        *(network.get("labels", {}) for network in config.get("networks", {}).values()),
    ]
    labels_ok = all(
        all(labels.get(key) == value for key, value in expected_labels.items())
        for labels in label_objects
    ) and bool(label_objects)
    expected_bindings = {(5432, "55441"), (8000, "18080")}
    actual_bindings = {
        (port.get("target"), str(port.get("published")))
        for service in services.values()
        for port in service.get("ports", [])
        if port.get("host_ip") == "127.0.0.1"
    }
    postgres = services.get("postgres", {})
    return {
        "project": project,
        "services": list(services),
        "containers": containers,
        "fixed_container_names": fixed_container_names,
        "volumes": volumes,
        "networks": networks,
        "postgres_environment": postgres.get("environment", {}) or {},
        "project_ok": project == PROJECT,
        "labels_ok": labels_ok,
        "ports_ok": actual_bindings == expected_bindings,
    }


def run_static_preflight() -> Preflight:
    """Validate local staging configuration without contacting the Docker daemon."""
    values = parse_env_file()
    problems: list[str] = []
    resources: dict[str, Any] = {
        "services": [], "containers": {}, "volumes": {}, "networks": {},
    }

    if not ENV_FILE.is_file():
        problems.append(".env.staging is missing")
    else:
        mode = ENV_FILE.stat().st_mode & 0o777
        if mode & 0o077:
            problems.append(".env.staging permissions must be 0600 or stricter")
    missing = [key for key in REQUIRED_KEYS if not values.get(key)]
    if missing:
        problems.append("required staging keys missing: " + ", ".join(missing))
    if values.get("AUTH_JWT_SECRET") and len(values["AUTH_JWT_SECRET"].encode("utf-8")) < 32:
        problems.append("AUTH_JWT_SECRET does not meet the minimum length")
    if problems:
        return Preflight(values, resources, problems)

    config_result = _run_hidden(compose_command("config", "--format", "json"))
    if config_result.returncode:
        problems.append("Docker Compose configuration is invalid; raw output suppressed")
        return Preflight(values, resources, problems)
    configured = _resources_from_config(config_result.stdout)
    if configured is None:
        problems.append("Docker Compose returned invalid configuration; raw output suppressed")
        return Preflight(values, resources, problems)
    resources = configured

    if set(configured["services"]) != set(EXPECTED_SERVICES):
        problems.append("configured services must be postgres and backend")
    if configured["fixed_container_names"]:
        problems.append("staging services must not set fixed container_name values")
    if not configured["project_ok"]:
        problems.append("configured Compose project name does not match the staging project")
    if not configured["labels_ok"]:
        problems.append("configured staging labels are missing or inconsistent")
    if set(configured["volumes"].values()) != set(EXPECTED_VOLUMES):
        problems.append("configured volume names do not match the isolated staging volume")
    if set(configured["networks"].values()) != set(EXPECTED_NETWORKS):
        problems.append("configured network names do not match the isolated staging network")
    if not configured["ports_ok"]:
        problems.append("configured localhost port bindings do not match the isolated staging ports")
    if any(not name.startswith(PROJECT) for name in configured["containers"].values()):
        problems.append("a configured container name lacks the staging project prefix")
    if any(not name.startswith(PROJECT) for name in configured["volumes"].values()):
        problems.append("a configured volume name lacks the staging project prefix")
    if any(not name.startswith(PROJECT) for name in configured["networks"].values()):
        problems.append("a configured network name lacks the staging project prefix")
    if not _target_matches_config(values, configured["postgres_environment"]):
        problems.append("DATABASE_URL does not match the isolated staging postgres service")

    return Preflight(values, resources, problems)


def _host_port_available(port: int) -> bool | None:
    """Return None only when host restrictions prevent a meaningful probe."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as exc:
            if getattr(exc, "errno", None) in {48, 98, 10048}:
                return False
            return None
    return True


def inspect_runtime_inventory(
    configured: dict[str, Any],
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = _run_hidden,
    port_probe: Callable[[int], bool | None] = _host_port_available,
) -> RuntimeInventory:
    """Inspect project/service labels after static preflight, without treating absence as failure."""
    info = runner(["docker", "info", "--format", "{{.ServerVersion}}"])
    if info.returncode:
        return RuntimeInventory("SKIPPED: Docker daemon unavailable")

    result = RuntimeInventory("NOT_CREATED_YET")
    running_services: set[str] = set()
    project_filter = f"label={COMPOSE_PROJECT_LABEL}={PROJECT}"
    for service in EXPECTED_SERVICES:
        service_filter = f"label={COMPOSE_SERVICE_LABEL}={service}"
        listed = runner([
            "docker", "ps", "-a", "--filter", project_filter,
            "--filter", service_filter, "--format", "{{.Names}}",
        ])
        if listed.returncode:
            result.problems.append(f"Docker inventory failed for staging service {service}")
            continue
        names = [line.strip() for line in listed.stdout.splitlines() if line.strip()]
        if not names:
            result.services[service] = "NOT_CREATED_YET"
            continue
        expected_name = configured["containers"].get(service)
        if set(names) != {expected_name}:
            result.problems.append(f"unexpected container inventory for staging service {service}")
        else:
            result.services[service] = "PRESENT"
            inspected = runner(["docker", "inspect", expected_name])
            if inspected.returncode:
                result.problems.append(f"Docker metadata is unavailable for staging service {service}")
                continue
            try:
                container = json.loads(inspected.stdout)[0]
            except (json.JSONDecodeError, IndexError, TypeError):
                result.problems.append(f"Docker metadata is unreadable for staging service {service}")
                continue
            labels = container.get("Config", {}).get("Labels") or {}
            if labels.get(COMPOSE_PROJECT_LABEL) != PROJECT or labels.get(COMPOSE_SERVICE_LABEL) != service:
                result.problems.append(f"Docker labels do not match staging service {service}")
            if labels.get(LABEL_PROJECT) != PROJECT or labels.get(LABEL_ENVIRONMENT) != LABEL_STAGE:
                result.problems.append(f"staging labels do not match service {service}")
            target_port, host_port = {
                "postgres": ("5432/tcp", "55441"),
                "backend": ("8000/tcp", "18080"),
            }[service]
            bindings = (container.get("HostConfig", {}).get("PortBindings") or {}).get(target_port) or []
            binding_ok = any(
                item.get("HostIp") == "127.0.0.1" and item.get("HostPort") == host_port
                for item in bindings
            )
            if not binding_ok:
                result.problems.append(f"staging port binding does not match service {service}")
            if container.get("State", {}).get("Running") and binding_ok:
                running_services.add(service)

    for kind, expected_names, list_args in (
        ("volumes", set(configured["volumes"].values()), ["docker", "volume", "ls"]),
        ("networks", set(configured["networks"].values()), ["docker", "network", "ls"]),
    ):
        labelled = runner([
            *list_args, "--filter", project_filter, "--format", "{{.Name}}",
        ])
        all_named = runner([*list_args, "--format", "{{.Name}}"])
        if labelled.returncode or all_named.returncode:
            result.problems.append(f"Docker {kind} inventory is unavailable")
            continue
        labelled_names = set(labelled.stdout.splitlines())
        all_names = set(all_named.stdout.splitlines())
        for name in expected_names:
            if name in labelled_names:
                if kind == "volumes":
                    result.volumes[name] = "PRESENT"
                else:
                    result.networks[name] = "PRESENT"
            elif name in all_names:
                result.problems.append(f"staging {kind[:-1]} name exists without the staging project label")
            elif kind == "volumes":
                result.volumes[name] = "NOT_CREATED_YET"
            else:
                result.networks[name] = "NOT_CREATED_YET"

    # Existing Docker-published ports are checked separately from config bindings.
    all_containers = runner(["docker", "ps", "-a", "--format", "{{.Names}}|{{.Ports}}|{{.Labels}}"])
    if all_containers.returncode:
        result.problems.append("Docker container inventory is unavailable for port checks")
    else:
        port_pattern = re.compile(r"(?:^|[, ])(?:127\.0\.0\.1|0\.0\.0\.0|\[::\]|[^:, ]+):(\d+)->")
        for row in all_containers.stdout.splitlines():
            parts = row.split("|", 2)
            if len(parts) != 3:
                continue
            name, ports, labels = parts
            if f"{COMPOSE_PROJECT_LABEL}={PROJECT}" in labels:
                continue
            published = {int(value) for value in port_pattern.findall(ports)}
            if published.intersection(EXPECTED_PORTS):
                result.problems.append("a staging host port is already published by another container")
    service_ports = {"postgres": 55441, "backend": 18080}
    for service, port in service_ports.items():
        if service in running_services:
            continue
        available = port_probe(port)
        if available is False:
            result.problems.append(f"staging host port {port} is already in use")

    any_resources = any(v == "PRESENT" for v in result.services.values()) or any(
        v == "PRESENT" for v in (*result.volumes.values(), *result.networks.values())
    )
    result.status = "PASS" if not result.problems and any_resources else "NOT_CREATED_YET"
    return result


def run_preflight(*, check_docker_conflicts: bool | None = None) -> Preflight:
    """Compatibility alias for the static preflight; it never contacts Docker daemon."""
    return run_static_preflight()


def staging_runtime_problems() -> list[str]:
    """Verify DB-access scripts can reach only the labelled staging stack."""
    static = run_static_preflight()
    if not static.ok:
        return ["staging static preflight failed"]
    inventory = inspect_runtime_inventory(static.resources)
    problems = list(inventory.problems)
    if inventory.status.startswith("SKIPPED:"):
        return ["Docker daemon unavailable; staging database operation skipped"]
    for service, state in inventory.services.items():
        if state != "PRESENT":
            problems.append(f"staging {service} container is not running or not created")
    for name, state in inventory.volumes.items():
        if state != "PRESENT":
            problems.append("staging PostgreSQL data volume is unavailable")
    for name, state in inventory.networks.items():
        if state != "PRESENT":
            problems.append("staging network is unavailable")
    if inventory.status != "PASS" and not problems:
        problems.append("staging runtime resources are not ready")
    return problems


def print_preflight(report: Preflight) -> None:
    print("STATIC PREFLIGHT: PASS" if report.ok else "STATIC PREFLIGHT: FAIL")
    for key in REQUIRED_KEYS:
        print(f"{key}: {'set' if report.values.get(key) else 'missing'}")
    print("services:", ", ".join(report.resources.get("services", [])) or "none")
    print("containers:", ", ".join(report.resources.get("containers", {}).values()) or "none")
    print("volumes:", ", ".join(report.resources.get("volumes", {}).values()) or "none")
    print("networks:", ", ".join(report.resources.get("networks", {}).values()) or "none")
    for problem in report.problems:
        print("reason:", problem)
