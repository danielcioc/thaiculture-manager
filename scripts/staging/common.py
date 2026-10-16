from __future__ import annotations

import json
import os
import re
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
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
EXPECTED_CONTAINERS = (
    "thaiculture-staging-approval-postgres",
    "thaiculture-staging-approval-backend",
)
EXPECTED_VOLUMES = ("thaiculture-staging-approval-postgres-data",)
EXPECTED_NETWORKS = ("thaiculture-staging-approval-network",)
EXPECTED_PORTS = (55441, 18080)
TEST_DATABASE = "thaiculture_manager_staging_test"
LABEL_PROJECT = "com.thaiculture.project"
LABEL_ENVIRONMENT = "com.thaiculture.environment"
LABEL_STAGE = "staging"


@dataclass
class Preflight:
    values: dict[str, str]
    resources: dict[str, list[str]]
    problems: list[str]

    @property
    def ok(self) -> bool:
        return not self.problems


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


def _docker_lines(*args: str) -> list[str] | None:
    result = _run_hidden(["docker", *args])
    if result.returncode:
        return None
    return [line for line in result.stdout.splitlines() if line]


def _target_is_isolated(values: dict[str, str]) -> bool:
    try:
        parsed = urlsplit(values.get("DATABASE_URL", ""))
        password = unquote(parsed.password or "")
        return bool(
            parsed.scheme in {"postgres", "postgresql"}
            and parsed.hostname == "postgres"
            and parsed.port == 5432
            and parsed.username == "tct_admin"
            and parsed.path.lstrip("/") == TEST_DATABASE
            and password
            and password == values.get("THAICULTURE_DB_PASSWORD")
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
    containers = [
        service.get("container_name") or f"{project}-{name}-1"
        for name, service in services.items()
    ]
    volumes = [
        item.get("name") or f"{project}_{name}"
        for name, item in config.get("volumes", {}).items()
    ]
    networks = [
        item.get("name") or f"{project}_{name}"
        for name, item in config.get("networks", {}).items()
    ]
    expected_labels = {
        LABEL_PROJECT: PROJECT,
        LABEL_ENVIRONMENT: LABEL_STAGE,
        "com.thaiculture.managed-by": "staging-tools",
    }
    labelled_items = [
        *(service.get("labels", {}) for service in services.values()),
        *(volume.get("labels", {}) for volume in config.get("volumes", {}).values()),
        *(network.get("labels", {}) for network in config.get("networks", {}).values()),
    ]
    labels_ok = all(
        all(labels.get(key) == value for key, value in expected_labels.items())
        for labels in labelled_items
    ) and bool(labelled_items)
    expected_bindings = {(5432, "55441"), (8000, "18080")}
    actual_bindings = {
        (port.get("target"), str(port.get("published")))
        for service in services.values()
        for port in service.get("ports", [])
        if port.get("host_ip") == "127.0.0.1"
    }
    return {
        "services": list(services), "containers": containers,
        "volumes": volumes, "networks": networks,
        "project_ok": project == PROJECT,
        "labels_ok": labels_ok, "ports_ok": actual_bindings == expected_bindings,
    }


def run_preflight(*, check_docker_conflicts: bool = True) -> Preflight:
    values = parse_env_file()
    problems: list[str] = []
    resources = {
        "services": [], "containers": list(EXPECTED_CONTAINERS),
        "volumes": list(EXPECTED_VOLUMES), "networks": list(EXPECTED_NETWORKS),
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
    if not missing and not _target_is_isolated(values):
        problems.append("DATABASE_URL must target the isolated postgres service and staging test database")
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

    if configured["containers"] != list(EXPECTED_CONTAINERS):
        problems.append("configured container names do not match the isolated staging names")
    if configured["volumes"] != list(EXPECTED_VOLUMES):
        problems.append("configured volume names do not match the isolated staging volume")
    if configured["networks"] != list(EXPECTED_NETWORKS):
        problems.append("configured network names do not match the isolated staging network")
    if not configured["project_ok"]:
        problems.append("configured Compose project name does not match the staging project")
    if not configured["labels_ok"]:
        problems.append("configured staging labels are missing or inconsistent")
    if not configured["ports_ok"]:
        problems.append("configured localhost port bindings do not match the isolated staging ports")
    all_resources = configured["containers"] + configured["volumes"] + configured["networks"]
    if any(not name.startswith(PROJECT) for name in all_resources):
        problems.append("a configured resource lacks the staging project prefix")

    if check_docker_conflicts:
        projects = _docker_lines("compose", "ls", "--all", "--format", "json")
        if projects is None:
            problems.append("Docker project inventory is unavailable")
        else:
            try:
                if any(item.get("Name") == PROJECT for item in json.loads("\n".join(projects) or "[]")):
                    problems.append("staging project name already exists; inspect/clean it before starting")
            except json.JSONDecodeError:
                problems.append("Docker project inventory could not be parsed")

        container_rows = _docker_lines("ps", "-a", "--format", "{{json .}}")
        if container_rows is None:
            problems.append("Docker container inventory is unavailable")
        else:
            port_pattern = re.compile(r"(?:^|[, ])(?:127\.0\.0\.1|0\.0\.0\.0|\[::\]|[^:, ]+):(\d+)->")
            for row in container_rows:
                try:
                    info = json.loads(row)
                except json.JSONDecodeError:
                    continue
                if info.get("Names") in configured["containers"]:
                    problems.append("a staging container name already exists")
                published = {int(match) for match in port_pattern.findall(info.get("Ports", ""))}
                if published.intersection(EXPECTED_PORTS):
                    problems.append("a staging host port is already published")

        for port in EXPECTED_PORTS:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                try:
                    probe.bind(("127.0.0.1", port))
                except OSError:
                    problems.append(f"staging host port {port} is unavailable")

        for kind, args, expected in (
            ("volume", ("volume", "ls", "--format", "{{.Name}}"), configured["volumes"]),
            ("network", ("network", "ls", "--format", "{{.Name}}"), configured["networks"]),
        ):
            current = _docker_lines(*args)
            if current is None:
                problems.append(f"Docker {kind} inventory is unavailable")
            elif set(current).intersection(expected):
                problems.append(f"a staging {kind} name already exists")

    return Preflight(values, resources, problems)


def staging_runtime_problems() -> list[str]:
    """Verify DB-access scripts can reach only the labelled staging stack."""
    problems: list[str] = []
    expected = (
        (EXPECTED_CONTAINERS[0], "postgres", 55441, "5432/tcp"),
        (EXPECTED_CONTAINERS[1], "backend", 18080, "8000/tcp"),
    )
    for container_name, service, host_port, container_port in expected:
        result = _run_hidden(["docker", "container", "inspect", container_name])
        if result.returncode:
            problems.append(f"staging {service} container is unavailable")
            continue
        try:
            container = json.loads(result.stdout)[0]
        except (json.JSONDecodeError, IndexError, TypeError):
            problems.append(f"staging {service} container metadata is unreadable")
            continue
        labels = container.get("Config", {}).get("Labels") or {}
        if labels.get(LABEL_PROJECT) != PROJECT or labels.get(LABEL_ENVIRONMENT) != LABEL_STAGE:
            problems.append(f"staging {service} container labels do not match")
        if not container.get("State", {}).get("Running"):
            problems.append(f"staging {service} container is not running")
        if EXPECTED_NETWORKS[0] not in container.get("NetworkSettings", {}).get("Networks", {}):
            problems.append(f"staging {service} is not on the isolated network")
        bindings = container.get("HostConfig", {}).get("PortBindings") or {}
        ports = bindings.get(container_port) or []
        if not any(
            binding.get("HostIp") == "127.0.0.1" and binding.get("HostPort") == str(host_port)
            for binding in ports
        ):
            problems.append(f"staging {service} port binding does not match")
        if service == "postgres" and not any(
            mount.get("Type") == "volume"
            and mount.get("Name") == EXPECTED_VOLUMES[0]
            and mount.get("Destination") == "/var/lib/postgresql/data"
            for mount in container.get("Mounts", [])
        ):
            problems.append("staging PostgreSQL data volume does not match")

    for kind, command, name in (
        ("network", ["docker", "network", "inspect", EXPECTED_NETWORKS[0]], EXPECTED_NETWORKS[0]),
        ("volume", ["docker", "volume", "inspect", EXPECTED_VOLUMES[0]], EXPECTED_VOLUMES[0]),
    ):
        result = _run_hidden(command)
        if result.returncode:
            problems.append(f"staging {kind} is unavailable")
            continue
        try:
            labels = json.loads(result.stdout)[0].get("Labels") or {}
        except (json.JSONDecodeError, IndexError, TypeError):
            problems.append(f"staging {kind} metadata is unreadable")
            continue
        if labels.get(LABEL_PROJECT) != PROJECT or labels.get(LABEL_ENVIRONMENT) != LABEL_STAGE:
            problems.append(f"staging {kind} labels do not match")
    return problems


def print_preflight(report: Preflight) -> None:
    print("READY" if report.ok else "BLOCKED")
    for key in REQUIRED_KEYS:
        print(f"{key}: {'set' if report.values.get(key) else 'missing'}")
    for kind in ("services", "containers", "volumes", "networks"):
        print(f"{kind}: {', '.join(report.resources.get(kind, [])) or 'none'}")
    for problem in report.problems:
        print("reason:", problem)
