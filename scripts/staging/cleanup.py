#!/usr/bin/env python3
"""Remove only resources carrying this staging stack's explicit labels."""

import json
import subprocess

from common import LABEL_ENVIRONMENT, LABEL_PROJECT, PROJECT


def run(command):
    try:
        return subprocess.run(command, capture_output=True, text=True)
    except OSError:
        return subprocess.CompletedProcess(command, 127, "", "")


def labelled_ids(kind):
    result = run([
        "docker", kind, "ls", "-q",
        "--filter", f"label={LABEL_PROJECT}={PROJECT}",
        "--filter", f"label={LABEL_ENVIRONMENT}=staging",
    ])
    if result.returncode:
        return None
    return [item for item in result.stdout.splitlines() if item]


def inspect(kind, resource_id):
    result = run(["docker", kind, "inspect", resource_id])
    if result.returncode:
        return None
    try:
        data = json.loads(result.stdout)[0]
    except (json.JSONDecodeError, IndexError, TypeError):
        return None
    labels = data.get("Config", {}).get("Labels") if kind == "container" else data.get("Labels", {})
    name = data.get("Name", "").lstrip("/")
    return name, labels or {}


def remove(kind, resource_id, name):
    verb = "rm"
    args = ["docker", verb]
    if kind == "container":
        args.append("-f")
    args.append(resource_id)
    result = run(args)
    if result.returncode:
        print(f"BLOCKED: could not remove staging {kind}")
        return False
    print(f"removed {kind}: {name}")
    return True


def main():
    containers = labelled_ids("container")
    networks = labelled_ids("network")
    volumes = labelled_ids("volume")
    if containers is None or networks is None or volumes is None:
        print("BLOCKED: Docker resource inventory unavailable; nothing removed")
        return 2
    for kind, resources in (("container", containers), ("network", networks), ("volume", volumes)):
        for resource_id in resources:
            details = inspect(kind, resource_id)
            if details is None:
                print(f"BLOCKED: unable to verify a {kind} label; resource preserved")
                return 3
            name, labels = details
            if labels.get(LABEL_PROJECT) != PROJECT or labels.get(LABEL_ENVIRONMENT) != "staging":
                print(f"BLOCKED: {kind} labels did not match; resource preserved")
                return 3
            if not remove(kind, resource_id, name):
                return 4
    print("PASS: no labelled staging resources remain")
    return 0


raise SystemExit(main())
