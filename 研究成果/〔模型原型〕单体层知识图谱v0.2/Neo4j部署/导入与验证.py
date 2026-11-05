#!/usr/bin/env python3
"""Import and verify the v0.2 dwelling graph through Neo4j's HTTP API.

Only Python's standard library is used. The importer owns the kgv02:* UID
namespace, never clears the database, and pins every input namespace to its
source-file SHA-256. A changed source requires a new namespace/migration.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODEL_FILE = "模型定义.json"
LITERATURE_FILE = "案例图谱.json"
DEMO_FILE = "空间关系演示.json"
OPTIONAL_SNAPSHOTS = ("优化依据.json", "优化记录.json")
UID_PREFIX = "kgv02:"
TX_PATH = "/db/neo4j/tx/commit"
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
DATASETS = (
    ("literature", "Literature", LITERATURE_FILE),
    ("demo", "Demo", DEMO_FILE),
)


class ImportErrorWithContext(Exception):
    """A safe-to-display input, HTTP, or graph validation error."""


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def record_uid(dataset: str, kind: str, source_id: str) -> str:
    return f"{UID_PREFIX}{dataset}:{kind}:{source_id}"


def snapshot_uid(namespace: str) -> str:
    return f"{UID_PREFIX}{namespace}:snapshot"


def read_json_file(path: Path) -> tuple[Any, str, str]:
    try:
        raw_bytes = path.read_bytes()
        raw = raw_bytes.decode("utf-8")
    except OSError as exc:
        raise ImportErrorWithContext(f"Cannot read input file: {path.name}") from exc
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ImportErrorWithContext(
            f"Invalid JSON in {path.name} at line {exc.lineno}, column {exc.colno}"
        ) from exc
    digest = hashlib.sha256(raw_bytes).hexdigest()
    return value, raw, digest


def check_identifier(value: Any, context: str) -> str:
    if not isinstance(value, str) or not SAFE_IDENTIFIER.fullmatch(value):
        raise ImportErrorWithContext(f"Unsafe or missing Cypher identifier in {context}")
    return value


def assert_unique(records: list[dict[str, Any]], key: str, context: str) -> None:
    values = [record.get(key) for record in records]
    if any(not isinstance(value, str) or not value for value in values):
        raise ImportErrorWithContext(f"Missing {key} in {context}")
    if len(values) != len(set(values)):
        raise ImportErrorWithContext(f"Duplicate {key} in {context}")


def load_sources(source_dir: Path) -> dict[str, Any]:
    names = (MODEL_FILE, LITERATURE_FILE, DEMO_FILE) + OPTIONAL_SNAPSHOTS
    files: dict[str, dict[str, Any]] = {}
    for name in names:
        path = source_dir / name
        if not path.exists() and name in OPTIONAL_SNAPSHOTS:
            continue
        value, raw, digest = read_json_file(path)
        if not isinstance(value, dict):
            raise ImportErrorWithContext(f"Top-level JSON value must be an object: {name}")
        files[name] = {"value": value, "raw": raw, "sha256": digest}

    for required in (MODEL_FILE, LITERATURE_FILE, DEMO_FILE):
        if required not in files:
            raise ImportErrorWithContext(f"Missing required input file: {required}")

    return files


def object_index(dataset: dict[str, Any], dataset_name: str) -> dict[str, dict[str, Any]]:
    nodes = dataset.get("nodes")
    if not isinstance(nodes, list) or any(not isinstance(row, dict) for row in nodes):
        raise ImportErrorWithContext(f"{dataset_name}: nodes must be a list of objects")
    assert_unique(nodes, "id", f"{dataset_name}.nodes")
    for node in nodes:
        check_identifier(node.get("class"), f"{dataset_name}.nodes.class")
        if not isinstance(node.get("label"), str):
            raise ImportErrorWithContext(f"{dataset_name}: entity {node.get('id')} has no label")
        if node.get("class") == "TypeConcept" and node.get("scheme") is not None:
            if node["scheme"] not in {item["id"] for item in nodes}:
                raise ImportErrorWithContext(
                    f"{dataset_name}: TypeConcept {node['id']} has an unknown source scheme"
                )
            if next(item for item in nodes if item["id"] == node["scheme"])["class"] != "TypeScheme":
                raise ImportErrorWithContext(
                    f"{dataset_name}: TypeConcept {node['id']} scheme is not a TypeScheme"
                )
    return {node["id"]: node for node in nodes}


def validate_dataset(dataset: dict[str, Any], dataset_name: str) -> dict[str, Any]:
    index = object_index(dataset, dataset_name)
    for key in ("sources", "evidence", "assertions", "classifications"):
        rows = dataset.get(key, [])
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ImportErrorWithContext(f"{dataset_name}: {key} must be a list of objects")
        if key in ("sources", "evidence", "assertions", "classifications"):
            assert_unique(rows, "id", f"{dataset_name}.{key}")

    source_ids = {row["id"] for row in dataset.get("sources", [])}
    evidence_ids = {row["id"] for row in dataset.get("evidence", [])}
    assertion_ids = {row["id"] for row in dataset.get("assertions", [])}

    for evidence in dataset.get("evidence", []):
        if evidence.get("source") not in source_ids:
            raise ImportErrorWithContext(
                f"{dataset_name}: evidence {evidence['id']} has no source in its dataset"
            )
    for assertion in dataset.get("assertions", []):
        if assertion.get("subject") not in index:
            raise ImportErrorWithContext(
                f"{dataset_name}: assertion {assertion['id']} has an unknown subject"
            )
        check_identifier(assertion.get("predicate"), f"{dataset_name}.assertions.predicate")
        for evidence_id in assertion.get("evidence", []):
            if evidence_id not in evidence_ids:
                raise ImportErrorWithContext(
                    f"{dataset_name}: assertion {assertion['id']} has unknown evidence {evidence_id}"
                )
        for evidence_id in assertion.get("conflictingEvidence", []):
            if evidence_id not in evidence_ids:
                raise ImportErrorWithContext(
                    f"{dataset_name}: assertion {assertion['id']} has unknown conflicting evidence"
                )
        target = assertion.get("object")
        if target is not None and target not in index:
            raise ImportErrorWithContext(
                f"{dataset_name}: assertion {assertion['id']} has an unknown object"
            )

    for classification in dataset.get("classifications", []):
        for endpoint in ("subject", "type", "scheme"):
            if classification.get(endpoint) not in index:
                raise ImportErrorWithContext(
                    f"{dataset_name}: classification {classification['id']} has an unknown {endpoint}"
                )
        for evidence_id in classification.get("evidence", []):
            if evidence_id not in evidence_ids:
                raise ImportErrorWithContext(
                    f"{dataset_name}: classification {classification['id']} has unknown evidence"
                )
        for criterion in classification.get("criteriaResults", []):
            assertion_id = criterion.get("assertion")
            if assertion_id and assertion_id not in assertion_ids:
                raise ImportErrorWithContext(
                    f"{dataset_name}: classification {classification['id']} has unknown input assertion"
                )

    return index


def validate_access(dataset: dict[str, Any], nodes: dict[str, dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    assertions = dataset["assertions"]
    direct = [row for row in assertions if row.get("predicate") == "direct_access_to"]
    interfaces: dict[str, set[str]] = defaultdict(set)
    for row in assertions:
        if row.get("predicate") == "interface_of" and row.get("object"):
            interfaces[row["subject"]].add(row["object"])
    for row in direct:
        context = row.get("accessContext")
        if not row.get("via") or not isinstance(context, dict):
            issues.append(f"{row['id']} must retain via and accessContext")
            continue
        if not {"scenario", "agent", "mode"}.issubset(context):
            issues.append(f"{row['id']} accessContext is missing scenario, agent, or mode")
        if row["via"] not in nodes or nodes[row["via"]].get("class") != "Interface":
            issues.append(f"{row['id']} via does not identify an Interface")
        if row["subject"] not in interfaces[row["via"]] or row.get("object") not in interfaces[row["via"]]:
            issues.append(f"{row['id']} via Interface does not connect both endpoints")
    if len(direct) != 2:
        issues.append(f"expected 2 explicit directed access assertions, found {len(direct)}")
    expected_access = {
        "ACCESS_HV": ("S_HALL", "S_VERANDA", "I_OPEN"),
        "ACCESS_VH": ("S_VERANDA", "S_HALL", "I_OPEN"),
    }
    by_id = {row["id"]: row for row in direct}
    if set(by_id) != set(expected_access):
        issues.append("the only explicit demo access assertions must be ACCESS_HV and ACCESS_VH")
    else:
        contexts = []
        for assertion_id, (subject, object_id, via) in expected_access.items():
            row = by_id[assertion_id]
            if (row.get("subject"), row.get("object"), row.get("via")) != (subject, object_id, via):
                issues.append(f"{assertion_id} has an unexpected direction or via Interface")
            context = row.get("accessContext")
            if not isinstance(context, dict) or any(not context.get(key) for key in ("scenario", "agent", "mode")):
                issues.append(f"{assertion_id} accessContext fields must be non-empty")
            else:
                contexts.append(context)
        if len(contexts) == 2 and contexts[0] != contexts[1]:
            issues.append("ACCESS_HV and ACCESS_VH must retain the same stated access context")
    return issues


def validate_all(files: dict[str, Any]) -> dict[str, Any]:
    model = files[MODEL_FILE]["value"]
    literature = files[LITERATURE_FILE]["value"]
    demo = files[DEMO_FILE]["value"]
    literature_nodes = validate_dataset(literature, "literature")
    demo_nodes = validate_dataset(demo, "demo")
    issues: list[str] = []

    entity_count = len(literature_nodes) + len(demo_nodes)
    assertion_count = len(literature["assertions"]) + len(demo["assertions"])
    classification_count = len(literature["classifications"]) + len(demo["classifications"])
    if (len(literature_nodes), len(demo_nodes), assertion_count, classification_count) != (14, 7, 55, 4):
        issues.append("input counts differ from acceptance values 14/7 entities, 55 assertions, 4 classifications")
    if len(literature["assertions"]) != 27 or len(demo["assertions"]) != 28:
        issues.append("assertion counts must be 27 Literature and 28 Demo")

    # Every complex JSON record must round-trip without changing its data.
    round_trip_ok = all(json.loads(json_text(record)) == record for dataset in (literature, demo)
                        for key in ("nodes", "sources", "evidence", "assertions", "classifications")
                        for record in dataset.get(key, []))
    if not round_trip_ok:
        issues.append("at least one projected record failed JSON round-trip validation")

    if validate_access(demo, demo_nodes):
        issues.extend(validate_access(demo, demo_nodes))
    if any(row.get("predicate") == "direct_access_to" for row in literature["assertions"]):
        issues.append("Literature dataset must not contain direct_access_to assertions")

    positive = [row for row in literature["classifications"]
                if row.get("decision") == "criteria_match"]
    if len(positive) != 2:
        issues.append(f"expected 2 criteria_match classifications, found {len(positive)}")
    if any(row.get("id") == "PROTO_8" for row in positive):
        issues.append("PROTO_8 must not be a positive criteria_match classification")

    roof = next((row for row in literature["assertions"] if row.get("id") == "F_1_roof_layered"), None)
    if not roof or roof.get("value") is not True or roof.get("status") != "disputed":
        issues.append("F_1_roof_layered must retain disputed true source value")
    elif set(roof.get("evidence", [])) != {"E_Z1"} or set(roof.get("conflictingEvidence", [])) != {"E_COMMON"}:
        issues.append("F_1_roof_layered must separate supporting E_Z1 from conflicting E_COMMON")

    proto8 = next((row for row in literature["classifications"] if row.get("id") == "PROTO_8"), None)
    if not proto8 or len(proto8.get("criteriaResults", [])) != 4:
        issues.append("PROTO_8 source classification must retain all four criteria results in raw data")
    elif not any(row.get("assertion") == "F_8_roof_layered" for row in proto8["criteriaResults"]):
        issues.append("PROTO_8 must retain its roof-layer criterion input")

    # Classification criterion inputs must agree with the linked assertion value,
    # except explicitly unknown results retained for disputed source material.
    assertion_by_id = {row["id"]: row for row in literature["assertions"]}
    criterion_count = 0
    for classification in literature["classifications"]:
        for criterion in classification.get("criteriaResults", []):
            assertion = assertion_by_id.get(criterion.get("assertion"))
            if not assertion:
                issues.append(f"{classification['id']} criterion points to a missing assertion")
                continue
            criterion_count += 1
            if criterion.get("result") != "unknown" and "value" in assertion:
                if criterion.get("actual") != assertion.get("value"):
                    issues.append(
                        f"{classification['id']} criterion actual differs from {assertion['id']}"
                    )

    if issues:
        raise ImportErrorWithContext("Input validation failed: " + "; ".join(issues))

    return {
        "entities": entity_count,
        "literatureEntities": len(literature_nodes),
        "demoEntities": len(demo_nodes),
        "assertions": assertion_count,
        "literatureAssertions": len(literature["assertions"]),
        "demoAssertions": len(demo["assertions"]),
        "classifications": classification_count,
        "evidence": len(literature["evidence"]) + len(demo["evidence"]),
        "sources": len(literature["sources"]) + len(demo["sources"]),
        "classificationCriteria": criterion_count,
        "rawJsonRoundTrip": round_trip_ok,
        "sourceFiles": {
            name: {"sha256": content["sha256"], "bytes": len(content["raw"].encode("utf-8"))}
            for name, content in files.items()
        },
        "checks": {
            "accessOnlyInDemoWithViaAndContext": True,
            "literatureHasNoAccessAssertion": True,
            "positiveHasTypeCount": 2,
            "proto8NotProjectedAsPositiveType": True,
            "disputedRoofValueAndEvidencePreserved": True,
            "conflictingEvidenceUsesSeparateProjection": True,
            "classificationCriteriaLinkedAndConsistent": True,
        },
        "modelSnapshotKeys": sorted(model.keys()),
        "optionalSnapshots": [name for name in OPTIONAL_SNAPSHOTS if name in files],
        "note": "Local dry-run only; no Neo4j connection was made.",
    }


def props_from_record(record: dict[str, Any], source_hash: str,
                      dataset_kind: str, source_id_key: str = "id") -> dict[str, Any]:
    props: dict[str, Any] = {
        "uid": "",
        "datasetKind": dataset_kind,
        "sourceId": record.get(source_id_key),
        "rawJson": json_text(record),
        "sourceHash": source_hash,
    }
    label = record.get("label")
    name = record.get("name")
    if isinstance(label, str):
        props["label"] = label
    if isinstance(name, str):
        props["name"] = name
    elif isinstance(label, str):
        props["name"] = label
    return props


def snapshot_record(namespace: str, label: str, file_name: str,
                    content: dict[str, Any]) -> dict[str, Any]:
    return {
        "uid": snapshot_uid(namespace),
        "sourceHash": content["sha256"],
        "rawJson": content["raw"],
        "datasetKind": namespace,
        "sourceId": file_name,
        "label": file_name,
        "name": file_name,
        "snapshotType": label,
    }


def import_plan(files: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build parameterized Cypher statements; all dynamic identifiers are checked."""
    snapshots: list[dict[str, Any]] = [
        snapshot_record("model", "ModelSnapshot", MODEL_FILE, files[MODEL_FILE]),
        snapshot_record("literature", "DatasetSnapshot", LITERATURE_FILE, files[LITERATURE_FILE]),
        snapshot_record("demo", "DatasetSnapshot", DEMO_FILE, files[DEMO_FILE]),
    ]
    for optional in OPTIONAL_SNAPSHOTS:
        if optional in files:
            snapshots.append(snapshot_record("supplement:" + optional.removesuffix(".json"),
                                             "SupplementSnapshot", optional, files[optional]))

    statements: list[dict[str, Any]] = [{
        "statement": (
            "CREATE CONSTRAINT kgitem_uid_unique IF NOT EXISTS "
            "FOR (n:KGItem) REQUIRE n.uid IS UNIQUE"
        ),
        "parameters": {},
    }]
    # MERGE on both UID and source hash. If an owned UID already has another
    # hash, the global UID constraint rejects the attempted second node and
    # rolls back the entire transactional import.
    snapshots_by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for snapshot in snapshots:
        snapshots_by_label[snapshot["snapshotType"]].append(snapshot)
    for label, rows in sorted(snapshots_by_label.items()):
        check_identifier(label, "snapshot label")
        statements.append({
            "statement": (
                f"UNWIND $rows AS row MERGE (n:KGItem:{label} "
                "{uid: row.uid, sourceHash: row.sourceHash}) SET n = row"
            ),
            "parameters": {"rows": rows},
        })

    expected: dict[str, Any] = {"nodes": {}, "counts": Counter(), "uids": set()}

    def add_rows(label: str, dataset: str, rows: list[dict[str, Any]],
                 kind: str, source_hash: str, dataset_kind: str,
                 extra_labels: list[str] | None = None) -> None:
        if not rows:
            return
        labels = ["KGItem", label, dataset] + (extra_labels or [])
        for item in labels:
            check_identifier(item, f"label {item}")
        query_labels = ":".join(labels)
        for row in rows:
            expected["nodes"][row["uid"]] = {
                "properties": dict(row),
                "labels": labels,
            }
            expected["uids"].add(row["uid"])
        statement = (
            f"UNWIND $rows AS row MERGE (n:{query_labels} {{uid: row.uid}}) "
            "SET n = row"
        )
        statements.append({"statement": statement, "parameters": {"rows": rows}})
        expected["counts"][f"{dataset}:{label}"] += len(rows)

    for namespace, dataset_label, file_name in DATASETS:
        content = files[file_name]
        dataset = content["value"]
        dataset_kind = dataset.get("datasetKind", namespace)
        nodes = dataset["nodes"]
        # Group entities by source class so the class is represented as a Neo4j label.
        by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in nodes:
            class_name = check_identifier(record["class"], f"{file_name}.nodes.class")
            props = props_from_record(record, content["sha256"], dataset_kind)
            props.update({"uid": record_uid(namespace, "entity", record["id"]),
                          "class": class_name})
            if class_name == "TypeConcept" and isinstance(record.get("scheme"), str):
                props["scheme"] = record["scheme"]
            by_class[class_name].append(props)
        for class_name, rows in sorted(by_class.items()):
            add_rows("Entity", dataset_label, rows, "entity", content["sha256"],
                     dataset_kind, [class_name])

        # TypeConcept.scheme is a source-node field. Project it as in_scheme
        # only with explicit provenance to that field, not as an inferred fact.
        for record in nodes:
            if record.get("class") == "TypeConcept" and record.get("scheme"):
                projection_id = f"node.scheme:{record['id']}"
                statements.append({
                    "statement": (
                        "MATCH (a:KGItem {uid: $fromUid}), (b:KGItem {uid: $toUid}) "
                        "MERGE (a)-[r:in_scheme {projectionId: $projectionId}]->(b) "
                        "SET r.sourceField = $sourceField, r.qualifiers = $qualifiers"
                    ),
                    "parameters": {
                        "fromUid": record_uid(namespace, "entity", record["id"]),
                        "toUid": record_uid(namespace, "entity", record["scheme"]),
                        "projectionId": projection_id,
                        "sourceField": "node.scheme",
                        "qualifiers": json_text({"sourceField": "node.scheme"}),
                    },
                })

        for kind, label in (("sources", "Source"), ("evidence", "Evidence"),
                            ("assertions", "Assertion"), ("classifications", "Classification")):
            rows = []
            for record in dataset.get(kind, []):
                props = props_from_record(record, content["sha256"], dataset_kind)
                props["uid"] = record_uid(namespace, kind[:-1] if kind.endswith("s") else kind,
                                           record["id"])
                # JSON strings preserve nulls and arbitrary nested qualifier values.
                if kind == "assertions":
                    props["predicate"] = record["predicate"]
                    for scalar in ("subject", "object", "value", "scope", "status", "attribution",
                                   "temporalScope", "via", "note", "method", "observer", "recordedAt",
                                   "normalizedTerm"):
                        if scalar in record and record[scalar] is not None and isinstance(
                                record[scalar], (str, int, float, bool)):
                            props[scalar] = record[scalar]
                    props["hasValue"] = "value" in record
                    if "value" in record:
                        props["valueJson"] = json_text(record["value"])
                    for complex_key in ("accessContext", "derivedFrom", "conflictingEvidence"):
                        if complex_key in record:
                            props[complex_key + "Json"] = json_text(record[complex_key])
                    props["evidenceIdsJson"] = json_text(record.get("evidence", []))
                elif kind == "classifications":
                    for scalar in ("subject", "type", "scheme", "decision", "attribution",
                                   "temporalScope", "note"):
                        if scalar in record and record[scalar] is not None:
                            props[scalar] = record[scalar]
                    props["criteriaResultsJson"] = json_text(record.get("criteriaResults", []))
                    props["evidenceIdsJson"] = json_text(record.get("evidence", []))
                elif kind == "evidence":
                    if "source" in record:
                        props["sourceRef"] = record["source"]
                if kind in ("sources", "evidence"):
                    for field, value in record.items():
                        if field == "id":
                            continue
                        if value is None:
                            props[field + "Present"] = True
                            props[field + "Json"] = "null"
                        elif isinstance(value, (str, int, float, bool)):
                            props[field] = value
                        elif (isinstance(value, list) and value
                              and all(isinstance(item, (str, int, float, bool)) for item in value)
                              and len({type(item) for item in value}) == 1):
                            props[field] = value
                        else:
                            props[field + "Json"] = json_text(value)
                rows.append(props)
            add_rows(label, dataset_label, rows, kind, content["sha256"], dataset_kind)

        # Assertion reification and provenance edges.
        for assertion in dataset.get("assertions", []):
            uid = record_uid(namespace, "assertion", assertion["id"])
            subject_uid = record_uid(namespace, "entity", assertion["subject"])
            rel_specs = [("SUBJECT", subject_uid)]
            if assertion.get("object") is not None:
                rel_specs.append(("OBJECT", record_uid(namespace, "entity", assertion["object"])))
            if assertion.get("via"):
                rel_specs.append(("VIA", record_uid(namespace, "entity", assertion["via"])))
            for evidence_id in assertion.get("evidence", []):
                rel_specs.append(("EVIDENCED_BY", record_uid(namespace, "evidence", evidence_id)))
            for evidence_id in assertion.get("conflictingEvidence", []):
                rel_specs.append(("CONFLICTING_EVIDENCE", record_uid(namespace, "evidence", evidence_id)))
            for relation_type, target_uid in rel_specs:
                statements.append({
                    "statement": (
                        f"MATCH (a:KGItem {{uid: $fromUid}}), (b:KGItem {{uid: $toUid}}) "
                        f"MERGE (a)-[:{relation_type} {{linkId: $linkId}}]->(b)"
                    ),
                    "parameters": {"fromUid": uid, "toUid": target_uid,
                                   "linkId": f"{assertion['id']}:{relation_type}:{target_uid}"},
                })
            if assertion.get("object") is not None:
                qualifiers = {key: value for key, value in assertion.items()
                              if key not in ("id", "subject", "object", "predicate")}
                predicate = check_identifier(assertion["predicate"], "assertion predicate")
                statements.append({
                    "statement": (
                        f"MATCH (a:KGItem {{uid: $fromUid}}), (b:KGItem {{uid: $toUid}}) "
                        f"MERGE (a)-[r:{predicate} {{assertionId: $assertionId}}]->(b) "
                        "SET r.qualifiers = $qualifiers"
                    ),
                    "parameters": {"fromUid": subject_uid,
                                   "toUid": record_uid(namespace, "entity", assertion["object"]),
                                   "assertionId": assertion["id"],
                                   "qualifiers": json_text(qualifiers)},
                })

        # Classification records and their evidence/input links. Only
        # criteria_match produces the positive :has_type display relationship.
        for classification in dataset.get("classifications", []):
            uid = record_uid(namespace, "classification", classification["id"])
            links = [
                ("SUBJECT", record_uid(namespace, "entity", classification["subject"])),
                ("TYPE", record_uid(namespace, "entity", classification["type"])),
                ("SCHEME", record_uid(namespace, "entity", classification["scheme"])),
            ]
            for criterion in classification.get("criteriaResults", []):
                assertion_id = criterion.get("assertion")
                if assertion_id:
                    links.append(("INPUT", record_uid(namespace, "assertion", assertion_id)))
            for evidence_id in classification.get("evidence", []):
                links.append(("EVIDENCED_BY", record_uid(namespace, "evidence", evidence_id)))
            for relation_type, target_uid in links:
                statements.append({
                    "statement": (
                        f"MATCH (a:KGItem {{uid: $fromUid}}), (b:KGItem {{uid: $toUid}}) "
                        f"MERGE (a)-[:{relation_type} {{linkId: $linkId}}]->(b)"
                    ),
                    "parameters": {"fromUid": uid, "toUid": target_uid,
                                   "linkId": f"{classification['id']}:{relation_type}:{target_uid}"},
                })
            if classification.get("decision") == "criteria_match":
                qualifiers = {key: value for key, value in classification.items()
                              if key not in ("id", "subject", "type", "scheme")}
                statements.append({
                    "statement": (
                        "MATCH (a:KGItem {uid: $fromUid}), (b:KGItem {uid: $toUid}) "
                        "MERGE (a)-[r:has_type {assertionId: $assertionId}]->(b) "
                        "SET r.qualifiers = $qualifiers"
                    ),
                    "parameters": {
                        "fromUid": record_uid(namespace, "entity", classification["subject"]),
                        "toUid": record_uid(namespace, "entity", classification["type"]),
                        "assertionId": classification["id"],
                        "qualifiers": json_text(qualifiers),
                    },
                })

        # Evidence nodes are isolated by dataset and point only to their own source nodes.
        for evidence in dataset.get("evidence", []):
            statements.append({
                "statement": (
                    "MATCH (e:KGItem {uid: $fromUid}), (s:KGItem {uid: $toUid}) "
                    "MERGE (e)-[:FROM_SOURCE {linkId: $linkId}]->(s)"
                ),
                "parameters": {"fromUid": record_uid(namespace, "evidence", evidence["id"]),
                               "toUid": record_uid(namespace, "source", evidence["source"]),
                               "linkId": f"{evidence['id']}:FROM_SOURCE"},
            })

    for snapshot in snapshots:
        expected["uids"].add(snapshot["uid"])
        expected["nodes"][snapshot["uid"]] = {
            "properties": dict(snapshot),
            "labels": ["KGItem", snapshot["snapshotType"]],
        }
    expected["counts"] = dict(expected["counts"])
    expected["snapshots"] = snapshots
    expected["relationshipCounter"] = expected_relationship_counter(statements)
    expected["relationships"] = sum(expected["relationshipCounter"].values())
    evidence_relationships = {}
    for item in statements:
        match = re.search(
            r"MERGE \(a\)-\[:([A-Z_]+) \{linkId: \$linkId\}\]->\(b\)",
            item["statement"],
        )
        if match:
            params = item["parameters"]
            evidence_relationships[(params["fromUid"], params["toUid"])] = match.group(1)
    for namespace, _, file_name in DATASETS:
        for assertion in files[file_name]["value"].get("assertions", []):
            for evidence_id in assertion.get("conflictingEvidence", []):
                key = (record_uid(namespace, "assertion", assertion["id"]),
                       record_uid(namespace, "evidence", evidence_id))
                if evidence_relationships.get(key) != "CONFLICTING_EVIDENCE":
                    raise ImportErrorWithContext(
                        f"conflictingEvidence projection is incorrect for {assertion['id']}"
                    )
                if any(
                    item["parameters"].get("fromUid") == key[0]
                    and item["parameters"].get("toUid") == key[1]
                    and "MERGE (a)-[:EVIDENCED_BY" in item["statement"]
                    for item in statements
                ):
                    raise ImportErrorWithContext(
                        f"conflicting evidence must not also be EVIDENCED_BY for {assertion['id']}"
                    )
    return statements, expected


def relationship_key(from_uid: str, relation: str, to_uid: str,
                     link_id: str | None, assertion_id: str | None,
                     projection_id: str | None, source_field: str | None,
                     qualifiers: str | None) -> tuple[Any, ...]:
    return (from_uid, relation, to_uid, link_id or assertion_id or projection_id,
            source_field, qualifiers)


def expected_relationship_counter(statements: list[dict[str, Any]]) -> Counter:
    link_pattern = re.compile(
        r"MERGE \([a-z]+\)-\[:([A-Za-z][A-Za-z0-9_]*) \{linkId: \$linkId\}\]->\([a-z]+\)"
    )
    assertion_pattern = re.compile(
        r"MERGE \(a\)-\[r:([A-Za-z][A-Za-z0-9_]*) \{assertionId: \$assertionId\}\]->\(b\)"
    )
    projection_pattern = re.compile(
        r"MERGE \(a\)-\[r:([A-Za-z][A-Za-z0-9_]*) \{projectionId: \$projectionId\}\]->\(b\)"
    )
    expected: Counter = Counter()
    for item in statements:
        query = item["statement"]
        params = item["parameters"]
        match = link_pattern.search(query)
        if match:
            key = relationship_key(params["fromUid"], match.group(1), params["toUid"],
                                   params["linkId"], None, None, None, None)
        else:
            match = assertion_pattern.search(query)
            if match:
                key = relationship_key(params["fromUid"], match.group(1), params["toUid"],
                                       None, params["assertionId"], None, None,
                                       params["qualifiers"])
            else:
                match = projection_pattern.search(query)
                if not match:
                    continue
                key = relationship_key(params["fromUid"], match.group(1), params["toUid"],
                                       None, None, params["projectionId"],
                                       params["sourceField"], params["qualifiers"])
        if expected[key]:
            raise ImportErrorWithContext(
                f"Duplicate relationship identity in import plan: {key[1]} {key[3]}"
            )
        expected[key] = 1
    return expected


def normalize_endpoint(value: str) -> str:
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise ImportErrorWithContext("--endpoint must be an http(s) URL without embedded credentials")
    path = parts.path.rstrip("/")
    if path.endswith(TX_PATH):
        endpoint_path = path
    elif path.endswith("/db/neo4j/tx"):
        endpoint_path = path + "/commit"
    else:
        endpoint_path = path + TX_PATH
    return urlunsplit((parts.scheme, parts.netloc, endpoint_path, "", ""))


def load_credentials(path: Path) -> tuple[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImportErrorWithContext("Cannot read credentials JSON file") from exc
    if not isinstance(data, dict):
        username, password = None, None
    else:
        username, password = data.get("username"), data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        raise ImportErrorWithContext("Credentials JSON must contain string username and password fields")
    return username, password


def post_transaction(endpoint: str, credentials: tuple[str, str],
                     statements: list[dict[str, Any]], timeout: float = 30.0) -> list[dict[str, Any]]:
    user, password = credentials
    auth = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"statements": statements}, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "Authorization": f"Basic {auth}"},
        method="POST",
    )
    # Empty proxy map intentionally bypasses HTTP(S)_PROXY / ALL_PROXY so a
    # tailnet endpoint is reached directly. HTTPS still uses normal CA checks.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise ImportErrorWithContext(f"Neo4j HTTP request failed with status {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, ssl.SSLError) or isinstance(exc, ssl.SSLError):
            message = "Neo4j HTTPS connection failed certificate/TLS validation"
        elif isinstance(reason, TimeoutError) or isinstance(exc, TimeoutError):
            message = "Neo4j HTTP request timed out"
        else:
            message = "Neo4j HTTP connection failed"
        raise ImportErrorWithContext(message) from None
    try:
        result = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ImportErrorWithContext("Neo4j returned a non-JSON response") from None
    errors = result.get("errors", [])
    if errors:
        messages = [f"{error.get('code', 'Neo4jError')}: {error.get('message', 'query failed')}"
                    for error in errors]
        raise ImportErrorWithContext("Neo4j transaction failed: " + " | ".join(messages))
    return result.get("results", [])


def row_list(result: dict[str, Any]) -> list[list[Any]]:
    return [item.get("row", []) for item in result.get("data", [])]


def verify_graph(files: dict[str, Any], endpoint: str,
                 credentials: tuple[str, str]) -> dict[str, Any]:
    _, expected = import_plan(files)
    response = post_transaction(endpoint, credentials, [{
        "statement": (
            "MATCH (n:KGItem) WHERE n.uid STARTS WITH $prefix "
            "RETURN n.uid, properties(n), labels(n)"
        ),
        "parameters": {"prefix": UID_PREFIX},
    }, {
        "statement": (
            "MATCH (a:KGItem)-[r]->(b:KGItem) "
            "WHERE a.uid STARTS WITH $prefix AND b.uid STARTS WITH $prefix "
            "RETURN a.uid, type(r), b.uid, r.linkId, r.assertionId, "
            "r.projectionId, r.sourceField, r.qualifiers"
        ),
        "parameters": {"prefix": UID_PREFIX},
    }])
    if len(response) != 2:
        raise ImportErrorWithContext(
            f"Neo4j verification returned {len(response)} of 2 expected query results"
        )
    actual_rows = row_list(response[0])
    actual: dict[str, dict[str, Any]] = {}
    for uid, properties, labels in actual_rows:
        if uid in actual:
            raise ImportErrorWithContext(f"Duplicate UID in Neo4j: {uid}")
        actual[uid] = {"properties": properties, "labels": labels}

    expected_uids = expected["uids"]
    missing = sorted(expected_uids - set(actual))
    unexpected = sorted(set(actual) - expected_uids)
    if missing or unexpected:
        raise ImportErrorWithContext(
            f"Neo4j namespace node set differs (missing={len(missing)}, unexpected={len(unexpected)})"
        )
    mismatched_properties = [
        uid for uid, expected_node in expected["nodes"].items()
        # Canonical JSON preserves bool versus numeric types (False != 0),
        # unlike Python dict equality, while ignoring map key order.
        if json.dumps(actual[uid]["properties"], sort_keys=True, ensure_ascii=False)
        != json.dumps(expected_node["properties"], sort_keys=True, ensure_ascii=False)
    ]
    mismatched_labels = [
        uid for uid, expected_node in expected["nodes"].items()
        if Counter(actual[uid]["labels"]) != Counter(expected_node["labels"])
    ]
    if mismatched_properties or mismatched_labels:
        raise ImportErrorWithContext(
            "Neo4j node projection mismatch: "
            f"properties={len(mismatched_properties)}, labels={len(mismatched_labels)}; "
            f"first UID: {(mismatched_properties or mismatched_labels)[0]}"
        )
    expected_hashes = {snapshot["uid"]: snapshot["sourceHash"]
                       for snapshot in expected["snapshots"]}
    mismatched_hashes = [uid for uid, digest in expected_hashes.items()
                         if actual[uid]["properties"].get("sourceHash") != digest]
    if mismatched_hashes:
        raise ImportErrorWithContext("Neo4j source snapshot hash mismatch")

    expected_relationships = expected["relationshipCounter"]
    actual_relationships = Counter(relationship_key(*row) for row in row_list(response[1]))
    if actual_relationships != expected_relationships:
        missing_relationships = sum((expected_relationships - actual_relationships).values())
        unexpected_relationships = sum((actual_relationships - expected_relationships).values())
        raise ImportErrorWithContext(
            "Neo4j relationship multiset differs "
            f"(missing={missing_relationships}, unexpected={unexpected_relationships})"
        )

    count = len(actual)
    return {
        "mode": "verify",
        "status": "passed",
        "namespaceNodes": count,
        "expectedNamespaceNodes": len(expected_uids),
        "propertyNodesVerified": len(expected["nodes"]),
        "projectedPropertyValuesVerified": sum(
            len(node["properties"]) for node in expected["nodes"].values()
        ),
        "labelNodesVerified": len(expected["nodes"]),
        "labelsVerified": sum(
            len(node["labels"]) for node in expected["nodes"].values()
        ),
        "expectedLabels": sum(
            len(node["labels"]) for node in expected["nodes"].values()
        ),
        "namespaceRelationships": sum(actual_relationships.values()),
        "expectedNamespaceRelationships": sum(expected_relationships.values()),
        "rawJsonRoundTrip": True,
        "snapshotHashes": "matched",
        "verifiedAt": datetime.now(timezone.utc).isoformat(),
        "note": "Database read verification completed. Import runtime is evidenced only if this follows a successful import.",
    }


def write_report(output_dir: Path, report: dict[str, Any], filename: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import or verify the v0.2 Neo4j graph")
    parser.add_argument("--source-dir", required=True, type=Path,
                        help="directory containing the v0.2 JSON source files")
    parser.add_argument("--endpoint", help="Neo4j HTTP(S) base URL or transactional endpoint")
    parser.add_argument("--credentials-file", type=Path,
                        help="JSON file with username and password; never printed")
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="directory for the sanitized result JSON")
    parser.add_argument("--mode", required=True, choices=("import", "verify", "dry-run"))
    parser.add_argument("--timeout", type=float, default=30.0,
                        help="HTTP timeout in seconds (default: 30)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode in ("import", "verify") and (not args.endpoint or not args.credentials_file):
        raise ImportErrorWithContext("--endpoint and --credentials-file are required for import/verify")
    if args.timeout <= 0:
        raise ImportErrorWithContext("--timeout must be greater than zero")

    files = load_sources(args.source_dir)
    counts = validate_all(files)
    statements, expected = import_plan(files)

    if args.mode == "dry-run":
        report = {
            "mode": "dry-run",
            "status": "passed",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "namespace": UID_PREFIX,
            "counts": counts,
            "plannedParameterizedStatements": len(statements),
            "plannedRelationshipStatements": expected["relationships"],
            "uniqueConstraint": "KGItem(uid)",
            "sourceHashPolicy": "Same UID namespace with changed sourceHash fails transaction; no automatic overwrite or database clearing.",
            "verificationBoundary": "Local input and mapping checks only; no Neo4j connection was made.",
        }
        report_path = write_report(args.output_dir, report, "导入自测.json")
        print(f"dry-run passed: {counts['entities']} entities, {counts['assertions']} assertions, "
              f"{counts['classifications']} classifications; report: {report_path}")
        return 0

    endpoint = normalize_endpoint(args.endpoint)
    credentials = load_credentials(args.credentials_file)
    if args.mode == "import":
        # Commit the schema prerequisite first; Neo4j must make the UID constraint
        # available before snapshot hash pins and graph records are written.
        post_transaction(endpoint, credentials, statements[:1], timeout=args.timeout)
        results = post_transaction(endpoint, credentials, statements[1:], timeout=args.timeout)
        report = {
            "mode": "import",
            "status": "passed",
            "completedAt": datetime.now(timezone.utc).isoformat(),
            "endpoint": endpoint,
            "counts": counts,
            "transactionResults": len(results),
            "namespaceNodesExpected": len(expected["uids"]),
        }
    else:
        report = verify_graph(files, endpoint, credentials)
        report["counts"] = counts
    report_path = write_report(args.output_dir, report, "最近运行.json")
    print(f"{args.mode} {report['status']}: report: {report_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ImportErrorWithContext as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
