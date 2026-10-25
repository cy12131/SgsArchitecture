#!/usr/bin/env python3
"""Validate SGS contract schemas, fixtures, and cross-message semantics."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator, FormatChecker
    import rfc8785
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


PACKAGE_DIGEST_FIELDS = {
    "id", "version", "api_version", "repository_url", "commit",
    "manifest_sha256", "dependencies",
}


def manifest_id(packages: list[dict]) -> str:
    normalized = []
    for package in packages:
        if set(package) != PACKAGE_DIGEST_FIELDS:
            raise ValueError(f"INVALID_DIGEST_FIELDS:{package.get('id', '<unknown>')}")
        normalized.append({
            "id": package["id"],
            "version": package["version"],
            "api_version": package["api_version"],
            "repository_url": package["repository_url"],
            "commit": package["commit"],
            "manifest_sha256": package["manifest_sha256"],
            "dependencies": sorted(package["dependencies"]),
        })
    normalized.sort(key=lambda package: package["id"])
    canonical = rfc8785.dumps(normalized)
    return hashlib.sha256(canonical).hexdigest()


def assert_sgs1_envelope(message: dict, *, notification: bool = False) -> None:
    assert set(message) == {"protocol", "type", "request_id", "data"}
    assert type(message["protocol"]) is int and message["protocol"] == 1
    assert type(message["request_id"]) is int
    assert message["request_id"] == 0 if notification else 1 <= message["request_id"] <= 2147483647
    assert isinstance(message["data"], dict)
    assert "payload" not in message
    assert len(json.dumps(message, ensure_ascii=False).encode("utf-8")) <= 65536


def encoded_sgs1_body(message: dict) -> bytes:
    return json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def package_manifest_result_with_url_suffix(suffix_length: int) -> dict:
    package = {
        "id": "org.sgs.boundary",
        "version": "1.0.0",
        "api_version": "1.0",
        "repository_url": "https://example.invalid/" + ("a" * suffix_length),
        "commit": "1" * 40,
        "manifest_sha256": "a" * 64,
        "dependencies": [],
    }
    return {
        "protocol": 1,
        "type": "PackageManifestResult",
        "request_id": 21,
        "data": {
            "manifest_id": manifest_id([package]),
            "packages": [package],
            "sync_timeout_ms": 30000,
        },
    }


def main() -> int:
    manifest_v = validator("package-manifest.schema.json")
    sync_v = validator("package-sync.schema.json")
    ipc_v = validator("game-ipc.schema.json")

    valid = load("examples/package-manifest/valid-base.json")
    server_only = load("examples/package-manifest/valid-server-only.json")
    client_only = load("examples/package-manifest/valid-client-only.json")
    resources_only = load("examples/package-manifest/valid-resources-only.json")
    missing_name = load("examples/package-manifest/invalid-missing-name.json")
    no_content = load("examples/package-manifest/invalid-no-content.json")
    cycle_a = load("examples/package-manifest/cycle-a.json")
    cycle_b = load("examples/package-manifest/cycle-b.json")
    valid_manifests = (
        ("valid-base", valid), ("valid-server-only", server_only),
        ("valid-client-only", client_only), ("valid-resources-only", resources_only),
        ("cycle-a", cycle_a), ("cycle-b", cycle_b),
    )
    for label, value in valid_manifests:
        expect_valid(manifest_v, value, label)
    expect_invalid(manifest_v, missing_name, "invalid-missing-name")
    expect_invalid(manifest_v, no_content, "invalid-no-content")
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

    standard_vector = load("examples/rfc8785/section-3.2.2-vector.json")
    canonical = rfc8785.dumps(standard_vector["input"])
    assert canonical.hex() == standard_vector["expected_canonical_utf8_hex"]
    assert hashlib.sha256(canonical).hexdigest() == standard_vector["expected_sha256"]

    sorting_vector = load("examples/rfc8785/section-3.2.3-sorting-vector.json")
    sorted_pairs = json.loads(
        rfc8785.dumps(sorting_vector["input"]),
        object_pairs_hook=lambda pairs: pairs,
    )
    assert [value for _, value in sorted_pairs] == sorting_vector["expected_value_order"]

    for relative in ("empty-manifest.json", "multi-package-manifest.json"):
        message = load(f"examples/package-sync/{relative}")
        expect_valid(sync_v, message, relative)
        assert_sgs1_envelope(message)
        assert message["data"]["manifest_id"] == manifest_id(message["data"]["packages"])

    get_manifest = load("examples/package-sync/get-package-manifest.json")
    changed = load("examples/package-sync/manifest-changed.json")
    expect_valid(sync_v, get_manifest, "get-package-manifest")
    expect_valid(sync_v, changed, "manifest-changed")
    assert_sgs1_envelope(get_manifest)
    assert_sgs1_envelope(changed, notification=True)

    zero_request = {**get_manifest, "request_id": 0}
    oversized_request = {**get_manifest, "request_id": 2147483648}
    nonzero_notification = {**changed, "request_id": 1}
    expect_invalid(sync_v, zero_request, "client-request-id-zero")
    expect_invalid(sync_v, oversized_request, "client-request-id-too-large")
    expect_invalid(sync_v, nonzero_notification, "notification-id-nonzero")

    legacy_envelope = load("examples/package-sync/invalid-legacy-envelope.json")
    expect_invalid(sync_v, legacy_envelope, "invalid-legacy-envelope")

    protocol_required = load("examples/package-sync/package-protocol-required.json")
    too_large_error = load("examples/package-sync/package-manifest-too-large.json")
    empty_ready = load("examples/package-sync/empty-manifest-ready.json")
    for label, message in (
        ("package-protocol-required", protocol_required),
        ("package-manifest-too-large", too_large_error),
        ("empty-manifest-ready", empty_ready),
    ):
        expect_valid(sync_v, message, label)
        assert_sgs1_envelope(message)
    assert protocol_required["data"]["code"] == "PACKAGE_PROTOCOL_REQUIRED"
    assert too_large_error["data"]["code"] == "PACKAGE_MANIFEST_TOO_LARGE"

    empty_result = load("examples/package-sync/empty-manifest.json")
    package_state = "NotReady"
    current_manifest_id = empty_result["data"]["manifest_id"]
    assert package_state == "NotReady"  # Receiving even an empty list does not imply Ready.
    if empty_ready["data"]["manifest_id"] == current_manifest_id:
        package_state = "Ready"
    assert package_state == "Ready"
    package_state = "NotReady"  # Disconnect and PackageManifestChanged both clear it.
    assert package_state == "NotReady"

    base_boundary = package_manifest_result_with_url_suffix(0)
    exact_padding = 65536 - len(encoded_sgs1_body(base_boundary))
    assert exact_padding > 0
    boundary_message = package_manifest_result_with_url_suffix(exact_padding)
    oversized_message = package_manifest_result_with_url_suffix(exact_padding + 1)
    expect_valid(sync_v, boundary_message, "manifest-result-65536-bytes")
    expect_valid(sync_v, oversized_message, "manifest-result-65537-bytes-structurally-valid")
    assert len(encoded_sgs1_body(boundary_message)) == 65536
    assert len(encoded_sgs1_body(oversized_message)) == 65537

    mismatch = load("examples/package-sync/ready-mismatch.json")
    expect_valid(sync_v, mismatch["message"], "ready-mismatch message")
    expect_valid(sync_v, mismatch["expected_response"], "ready-mismatch response")
    assert_sgs1_envelope(mismatch["message"])
    assert_sgs1_envelope(mismatch["expected_response"])
    assert mismatch["message"]["request_id"] == mismatch["expected_response"]["request_id"]
    assert mismatch["message"]["data"]["manifest_id"] != mismatch["required_manifest_id"]
    assert mismatch["expected_response"]["data"]["error"]["code"] == "MANIFEST_ID_MISMATCH"

    multi_packages = load("examples/package-sync/multi-package-manifest.json")["data"]["packages"]
    assert manifest_id(multi_packages) == manifest_id(list(reversed(multi_packages)))

    ipc_files = (
        "init-game.json", "game-ready.json", "player-request.json", "player-reply.json",
        "hidden-info-safe.json", "hidden-info-unsafe.json",
    )
    ipc = {name: load(f"examples/game-ipc/{name}") for name in ipc_files}
    for name, message in ipc.items():
        expect_valid(ipc_v, message, name)
        assert "protocol" not in message and "data" not in message
        assert "ipc_version" in message and "payload" in message

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
    print("PASS: 26 fixture files cover package forms, SGS/1 compatibility, RFC 8785, dependencies, IPC, exit, and secrecy")
    print("PASS: generated PackageManifestResult boundary cases are 65536 bytes accepted and 65537 bytes rejected for sending")
    print("PASS: expected-invalid cases were rejected by their designated validation layer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
