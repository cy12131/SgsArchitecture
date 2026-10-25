#!/usr/bin/env python3
"""Validate SGS contract schemas, fixtures, and cross-message semantics."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:
    print("ERROR: install test requirements with: python -m pip install -r requirements-test.txt")
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
EXAMPLES = ROOT / "examples"


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def validator(name: str) -> Draft202012Validator:
    schema = load(f"schemas/{name}")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def expect_valid(v: Draft202012Validator, instance, label: str) -> None:
    errors = sorted(v.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        raise AssertionError(f"{label}: expected valid, got: {errors[0].message}")


def expect_invalid(v: Draft202012Validator, instance, label: str) -> None:
    if v.is_valid(instance):
        raise AssertionError(f"{label}: expected schema rejection")


def assert_dependency_graph(manifests: list[dict]) -> list[str]:
    by_id: dict[str, dict] = {}
    for manifest in manifests:
        package_id = manifest["id"]
        if package_id in by_id:
            raise ValueError(f"DUPLICATE_PACKAGE_ID:{package_id}")
        dependency_ids = [dependency["id"] for dependency in manifest["dependencies"]]
        if len(dependency_ids) != len(set(dependency_ids)):
            raise ValueError(f"DUPLICATE_DEPENDENCY:{package_id}")
        by_id[package_id] = manifest

    for package_id, manifest in by_id.items():
        for dependency in manifest["dependencies"]:
            if dependency["id"] not in by_id:
                raise ValueError(f"MISSING_DEPENDENCY:{package_id}:{dependency['id']}")

    visiting: set[str] = set()
    visited: set[str] = set()
    order: list[str] = []

    def visit(package_id: str) -> None:
        if package_id in visiting:
            raise ValueError(f"CYCLIC_DEPENDENCY:{package_id}")
        if package_id in visited:
            return
        visiting.add(package_id)
        for dependency in by_id[package_id]["dependencies"]:
            visit(dependency["id"])
        visiting.remove(package_id)
        visited.add(package_id)
        order.append(package_id)

    for package_id in sorted(by_id):
        visit(package_id)
    return order


def manifest_id(packages: list[dict]) -> str:
    # Fixtures use only strings, integers, arrays, and objects, for which this is
    # byte-identical to RFC 8785 canonicalization.
    ordered = sorted(packages, key=lambda package: package["id"])
    canonical = json.dumps(
        ordered, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def main() -> int:
    manifest_v = validator("package-manifest.schema.json")
    sync_v = validator("package-sync.schema.json")
    ipc_v = validator("game-ipc.schema.json")

    valid = load("examples/package-manifest/valid-base.json")
    missing_name = load("examples/package-manifest/invalid-missing-name.json")
    cycle_a = load("examples/package-manifest/cycle-a.json")
    cycle_b = load("examples/package-manifest/cycle-b.json")
    for label, value in (("valid-base", valid), ("cycle-a", cycle_a), ("cycle-b", cycle_b)):
        expect_valid(manifest_v, value, label)
    expect_invalid(manifest_v, missing_name, "invalid-missing-name")
    assert_dependency_graph([valid])
    try:
        assert_dependency_graph([cycle_a, cycle_b])
        raise AssertionError("cycle fixtures: expected CYCLIC_DEPENDENCY")
    except ValueError as error:
        assert str(error).startswith("CYCLIC_DEPENDENCY:")

    duplicate = [valid, dict(valid)]
    try:
        assert_dependency_graph(duplicate)
        raise AssertionError("duplicate fixture: expected DUPLICATE_PACKAGE_ID")
    except ValueError as error:
        assert str(error).startswith("DUPLICATE_PACKAGE_ID:")

    missing_dependency = dict(valid)
    missing_dependency["id"] = "org.sgs.needs_missing"
    missing_dependency["dependencies"] = [{"id": "org.sgs.absent", "version": "1.0.0"}]
    try:
        assert_dependency_graph([missing_dependency])
        raise AssertionError("missing dependency fixture: expected MISSING_DEPENDENCY")
    except ValueError as error:
        assert str(error).startswith("MISSING_DEPENDENCY:")

    for relative in ("empty-manifest.json", "multi-package-manifest.json"):
        message = load(f"examples/package-sync/{relative}")
        expect_valid(sync_v, message, relative)
        assert message["payload"]["manifest_id"] == manifest_id(message["payload"]["packages"])

    mismatch = load("examples/package-sync/ready-mismatch.json")
    expect_valid(sync_v, mismatch["message"], "ready-mismatch message")
    expect_valid(sync_v, mismatch["expected_response"], "ready-mismatch response")
    assert mismatch["message"]["payload"]["manifest_id"] != mismatch["required_manifest_id"]
    assert mismatch["expected_response"]["payload"]["error"]["code"] == "MANIFEST_ID_MISMATCH"

    ipc_files = (
        "init-game.json", "game-ready.json", "player-request.json", "player-reply.json",
        "hidden-info-safe.json", "hidden-info-unsafe.json",
    )
    ipc = {name: load(f"examples/game-ipc/{name}") for name in ipc_files}
    for name, message in ipc.items():
        expect_valid(ipc_v, message, name)

    request = ipc["player-request.json"]
    reply = ipc["player-reply.json"]
    init = ipc["init-game.json"]
    ready = ipc["game-ready.json"]
    assert init["game_id"] == ready["game_id"]
    assert init["request_token"] == ready["request_token"]
    assert request["game_id"] == reply["game_id"]
    assert request["request_token"] == reply["request_token"]
    assert reply["payload"]["player_id"] in request["payload"]["recipients"]

    safe = ipc["hidden-info-safe.json"]
    unsafe = ipc["hidden-info-unsafe.json"]
    assert safe["payload"]["data"]["visibility"] == "private"
    assert safe["payload"]["recipients"] == [safe["payload"]["data"]["owner"]]
    assert unsafe["payload"]["data"]["visibility"] == "private"
    assert unsafe["payload"]["recipients"] != [unsafe["payload"]["data"]["owner"]]

    exit_scenario = load("examples/game-ipc/process-exit.json")
    required_cleanup = {"state_failed", "cancel_outstanding_requests", "close_pipes", "async_reap_once"}
    assert exit_scenario["observed"]["pipe_eof"] is True
    assert required_cleanup.issubset(exit_scenario["expected"])

    print("PASS: 3 schemas are valid Draft 2020-12 schemas")
    print("PASS: 14 fixture files cover schema, dependency, digest, initialization, request, exit, and secrecy rules")
    print("PASS: expected-invalid cases were rejected by their designated validation layer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
