#!/usr/bin/env python3
"""Declarative, reviewed operations on the Paper outline.

This is the structural-edit layer that was missing: change stable node IDs,
parent/child placement, order, inclusion and fields without hand-editing YAML.

All writes go through mac-paper. The default is dry-run; ``--write`` is explicit.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import date
from io import StringIO
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[2]
OUTLINE_REL = Path("论文章节/大纲结构.yaml")
BRIDGE = Path(os.environ.get("MAC_PAPER", "/Users/wangyuelin/.hermes/profiles/academic/bin/mac-paper"))


class OutlineError(RuntimeError):
    """A rejected outline operation or invalid outline."""


@dataclass
class Ref:
    kind: str
    node: Any
    parent: Any
    container: list
    chapter: Any


def _yaml_rt():
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    return y


def load_outline(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        data = _yaml_rt().load(f)
    if not isinstance(data, dict):
        raise OutlineError("outline root must be a YAML mapping")
    return data


def dump_outline(data: Any) -> str:
    buf = StringIO()
    _yaml_rt().dump(data, buf)
    return buf.getvalue()


def refs(data: Any):
    chapters = data.get("chapters")
    if not isinstance(chapters, list):
        raise OutlineError("outline.chapters must be a list")
    for chapter in chapters:
        yield Ref("chapter", chapter, None, chapters, chapter)
        sections = chapter.get("sections")
        if sections is None:
            continue
        if not isinstance(sections, list):
            raise OutlineError(f"chapter {chapter.get('id')} sections must be a list")
        for section in sections:
            yield Ref("section", section, chapter, sections, chapter)
            subsections = section.get("subsections")
            if subsections is None:
                continue
            if not isinstance(subsections, list):
                raise OutlineError(f"section {section.get('id')} subsections must be a list")
            for sub in subsections:
                yield Ref("subsection", sub, section, subsections, chapter)


def find_ref(data: Any, node_id: str) -> Ref:
    for ref in refs(data):
        if ref.node.get("id") == node_id:
            return ref
    raise OutlineError(f"outline node not found: {node_id}")


def validate(data: Any, root: Path | None = None) -> list[str]:
    """Validate identity, required fields and the supported three-level shape."""
    errors: list[str] = []
    seen: dict[str, str] = {}
    paths: set[str] = set()
    chapters = data.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        return ["outline must contain a non-empty chapters list"]

    def require(node: Any, kind: str, fields: tuple[str, ...]) -> None:
        if not isinstance(node, dict):
            errors.append(f"{kind} must be a mapping")
            return
        for key in fields:
            if key not in node:
                errors.append(f"{kind} {node.get('id', '<no id>')} missing field: {key}")
        if not isinstance(node.get("included", True), bool):
            errors.append(f"{kind} {node.get('id', '<no id>')} included must be boolean")

    for chapter in chapters:
        require(chapter, "chapter", ("id", "title", "included", "path"))
        cid = chapter.get("id", "<no id>")
        if cid in seen:
            errors.append(f"duplicate id: {cid} ({seen[cid]} and chapter)")
        seen[cid] = "chapter"
        path = chapter.get("path")
        if not isinstance(path, str) or not path.startswith("论文章节/章节导航/") or not path.endswith(".md"):
            errors.append(f"chapter {cid} path must be under 论文章节/章节导航/: {path!r}")
        elif path in paths:
            errors.append(f"duplicate chapter path: {path}")
        paths.add(path)
        if root is not None and isinstance(path, str) and not (root / path).is_file():
            errors.append(f"chapter {cid} path does not exist: {path}")

        sections = chapter.get("sections", [])
        if not isinstance(sections, list):
            errors.append(f"chapter {cid} sections must be a list")
            continue
        for section in sections:
            require(section, "section", ("id", "title", "included", "purpose", "status"))
            sid = section.get("id", "<no id>")
            if sid in seen:
                errors.append(f"duplicate id: {sid} ({seen[sid]} and section)")
            seen[sid] = "section"
            if section.get("subsections") is not None:
                subs = section.get("subsections")
                if not isinstance(subs, list):
                    errors.append(f"section {sid} subsections must be a list")
                    continue
                for sub in subs:
                    require(sub, "subsection", ("id", "title", "included", "purpose", "status", "change_note"))
                    sub_id = sub.get("id", "<no id>")
                    if sub_id in seen:
                        errors.append(f"duplicate id: {sub_id} ({seen[sub_id]} and subsection)")
                    seen[sub_id] = "subsection"
                    if sub.get("subsections") is not None:
                        errors.append(f"subsection {sub_id} cannot contain subsections (three levels only)")
    return errors


def ensure_valid(data: Any, root: Path | None = None) -> None:
    errors = validate(data, root)
    if errors:
        raise OutlineError("\n".join(errors))


def counts(data: Any) -> dict[str, int]:
    chapters = sum(1 for c in data.get("chapters", []) if c.get("included", True))
    sections = 0
    subsections = 0
    for c in data.get("chapters", []):
        for s in c.get("sections", []) or []:
            if s.get("included", True):
                sections += 1
            for sub in s.get("subsections", []) or []:
                if sub.get("included", True):
                    subsections += 1
    return {"chapters": chapters, "sections": sections, "subsections": subsections}


def _insert(container: list, node: Any, op: dict) -> None:
    target_id = op.get("before") or op.get("after")
    if target_id:
        for i, item in enumerate(container):
            if item.get("id") == target_id:
                index = i if op.get("before") else i + 1
                container.insert(index, node)
                return
        raise OutlineError(f"position target not found in parent: {target_id}")
    container.append(node)


def _remove(data: Any, ref: Ref) -> Any:
    try:
        ref.container.remove(ref.node)
    except ValueError as exc:
        raise OutlineError(f"node not in expected parent: {ref.node.get('id')}") from exc
    return ref.node


def _parent_for_add(data: Any, parent_id: str, as_kind: str) -> tuple[Any, list]:
    parent = find_ref(data, parent_id)
    if as_kind == "section":
        if parent.kind != "chapter":
            raise OutlineError(f"parent for section must be a chapter: {parent_id} is {parent.kind}")
        sections = parent.node.setdefault("sections", [])
        return parent.node, sections
    if as_kind == "subsection":
        if parent.kind != "section":
            raise OutlineError(f"parent for subsection must be a section: {parent_id} is {parent.kind}")
        subs = parent.node.setdefault("subsections", [])
        return parent.node, subs
    raise OutlineError(f"unsupported add kind: {as_kind}")


def op_add(data: Any, op: dict) -> None:
    node_id = op.get("id") or op.get("target")
    if not node_id:
        raise OutlineError("add requires id")
    if any(r.node.get("id") == node_id for r in refs(data)):
        raise OutlineError(f"id already exists: {node_id}")
    parent_id = op.get("parent") or op.get("under")
    if not parent_id:
        raise OutlineError("add requires parent/under")
    as_kind = op.get("as")
    parent_ref = find_ref(data, parent_id)
    if not as_kind:
        as_kind = "section" if parent_ref.kind == "chapter" else "subsection"
    node = dict(op.get("fields") or {})
    node.update({"id": node_id, "included": True})
    required = ("title", "purpose", "status")
    if as_kind == "subsection":
        required = required + ("change_note",)
    for field in required:
        if not node.get(field):
            raise OutlineError(f"add {node_id} missing required field: {field}")
    _, container = _parent_for_add(data, parent_id, as_kind)
    _insert(container, node, op)


def op_move(data: Any, op: dict) -> None:
    node_id = op.get("id") or op.get("target")
    if not node_id:
        raise OutlineError("move requires id")
    parent_id = op.get("under") or op.get("parent")
    if not parent_id:
        raise OutlineError("move requires under/parent")
    src = find_ref(data, node_id)
    if src.kind == "chapter":
        raise OutlineError("chapters cannot be moved by this operation")
    if parent_id == node_id:
        raise OutlineError("cannot move a node under itself")
    target = find_ref(data, parent_id)
    as_kind = op.get("as")
    if not as_kind:
        as_kind = "section" if target.kind == "chapter" else "subsection"

    if as_kind == "subsection":
        if target.kind != "section":
            raise OutlineError(f"subsection target must be a section: {parent_id} is {target.kind}")
        if src.kind == "section" and any(x.get("id") == parent_id for x in src.node.get("subsections", []) or []):
            raise OutlineError("cannot move a section under its own subsection")
        if src.kind == "section" and src.node.get("subsections"):
            raise OutlineError("cannot demote a section that already has subsections; move its children first")
        _remove(data, src)
        if not src.node.get("change_note"):
            src.node["change_note"] = f"{date.today().isoformat()} outline_ops moved under {parent_id} as subsection"
        target.node.setdefault("subsections", [])
        _insert(target.node["subsections"], src.node, op)
        return

    if as_kind == "section":
        if target.kind != "chapter":
            raise OutlineError(f"section target must be a chapter: {parent_id} is {target.kind}")
        _remove(data, src)
        target.node.setdefault("sections", [])
        _insert(target.node["sections"], src.node, op)
        return

    raise OutlineError(f"unsupported move kind: {as_kind}")


def op_reorder(data: Any, op: dict) -> None:
    node_id = op.get("id") or op.get("target")
    before = op.get("before")
    after = op.get("after")
    if not node_id or bool(before) == bool(after):
        raise OutlineError("reorder requires id and exactly one of before/after")
    ref = find_ref(data, node_id)
    target_id = before or after
    target_ref = find_ref(data, target_id)
    if ref.container is not target_ref.container:
        raise OutlineError("reorder requires sibling nodes in the same parent")
    if node_id == target_id:
        raise OutlineError("cannot reorder a node against itself")
    _remove(data, ref)
    _insert(ref.container, ref.node, {"before": before, "after": after})


def op_rename(data: Any, op: dict) -> None:
    ref = find_ref(data, op.get("id") or op.get("target") or "")
    title = op.get("title")
    if not title:
        raise OutlineError("rename requires title")
    ref.node["title"] = title


def op_set(data: Any, op: dict) -> None:
    ref = find_ref(data, op.get("id") or op.get("target") or "")
    field = op.get("field")
    if not field or field in {"id", "included", "sections", "subsections"}:
        raise OutlineError("set requires a non-structural field")
    if "value" not in op:
        raise OutlineError("set requires value")
    ref.node[field] = op["value"]


def op_retire(data: Any, op: dict) -> None:
    ref = find_ref(data, op.get("id") or op.get("target") or "")
    if ref.kind == "chapter":
        raise OutlineError("chapters cannot be retired by this operation")
    successors = op.get("superseded_by")
    if successors:
        if isinstance(successors, str):
            successors = [successors]
        for successor in successors:
            if successor == ref.node.get("id"):
                raise OutlineError("a node cannot supersede itself")
            find_ref(data, successor)
        ref.node["superseded_by"] = list(successors)
    ref.node["included"] = False
    reason = op.get("reason")
    if reason:
        old = str(ref.node.get("change_note", "")).strip()
        ref.node["change_note"] = (old + "；" if old else "") + reason


OPERATIONS = {
    "add": op_add,
    "move": op_move,
    "reorder": op_reorder,
    "rename": op_rename,
    "set": op_set,
    "set_field": op_set,
    "retire": op_retire,
}


def apply_operations(data: Any, operations: list[dict]) -> Any:
    if not isinstance(operations, list) or not operations:
        raise OutlineError("plan operations must be a non-empty list")
    for op in operations:
        if not isinstance(op, dict):
            raise OutlineError("each operation must be a mapping")
        name = op.get("op")
        if name not in OPERATIONS:
            raise OutlineError(f"unsupported operation: {name}")
        OPERATIONS[name](data, op)
    return data


def check_assertions(data: Any, assertions: dict | None) -> None:
    if not assertions:
        return
    actual = counts(data)
    for key, expected in (assertions.get("counts") or {}).items():
        if key not in actual:
            raise OutlineError(f"unknown count assertion: {key}")
        if actual[key] != expected:
            raise OutlineError(f"count assertion failed: {key}={actual[key]}, expected {expected}")
    for node_id in assertions.get("exists", []) or []:
        find_ref(data, node_id)


def load_plan(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        plan = YAML(typ="safe").load(f)
    if not isinstance(plan, dict):
        raise OutlineError("plan must be a mapping")
    return plan


def diff_text(before: str, after: str, limit: int = 200) -> str:
    lines = list(difflib.unified_diff(before.splitlines(), after.splitlines(), fromfile="before", tofile="after", lineterm=""))
    if len(lines) > limit:
        lines = lines[:limit] + [f"... ({len(lines) - limit} more diff lines)"]
    return "\n".join(lines)


def _bridge_read(rel: str) -> tuple[str, str]:
    result = subprocess.run(
        [str(BRIDGE), "--timeout", "30", "read", rel],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise OutlineError(result.stderr.strip() or f"mac-paper read failed: {rel}")
    payload = json.loads(result.stdout)
    if not payload.get("ok"):
        raise OutlineError(str(payload))
    return payload["result"]["text"], payload["result"]["sha256"]


def write_outline(root: Path, data: Any, old_text: str) -> None:
    if root.resolve() != ROOT.resolve():
        raise OutlineError("--write is only allowed for the live Paper root")
    rel = str(OUTLINE_REL)
    current, sha = _bridge_read(rel)
    if current != old_text:
        raise OutlineError("outline changed since the plan was prepared; re-read and merge")
    text = dump_outline(data)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".yaml", delete=False) as f:
        f.write(text)
        temp = Path(f.name)
    try:
        result = subprocess.run(
            [str(BRIDGE), "--timeout", "60", "upload", str(temp), rel, "--expected-sha256", sha],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise OutlineError(result.stderr.strip() or "mac-paper upload failed")
        payload = json.loads(result.stdout)
        if not payload.get("ok"):
            raise OutlineError(str(payload))
        print(f"wrote {rel} ({sha[:12]} -> {payload['result']['sha256'][:12]})")
    finally:
        temp.unlink(missing_ok=True)


def run_plan(plan: dict, root: Path, write: bool) -> None:
    current = root / OUTLINE_REL
    before_text = current.read_text(encoding="utf-8")
    data = load_outline(current)
    original = dump_outline(data)
    operations = plan.get("operations")
    apply_operations(data, operations)
    check_assertions(data, plan.get("assertions"))
    ensure_valid(data, root)
    after = dump_outline(data)
    print(json.dumps({"plan": plan.get("id"), "operations": len(operations), "counts": counts(data)}, ensure_ascii=False, indent=2))
    if original.strip() == after.strip():
        print("no changes")
        return
    print(diff_text(original, after))
    if write:
        write_outline(root, data, before_text)
    else:
        print("dry-run: no files written; pass --write to publish through mac-paper")


def parse_value(raw: str) -> Any:
    value = YAML(typ="safe").load(raw)
    return raw if value is None and raw.strip() not in {"null", "~"} else value


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT, help="Paper root (tests may use a fixture)")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="validate the outline schema")
    p.set_defaults(func=lambda a: print(json.dumps(counts(load_outline(a.root / OUTLINE_REL)), ensure_ascii=False, indent=2)))

    p = sub.add_parser("apply-plan", help="apply a declarative plan")
    p.add_argument("plan", type=Path)
    p.add_argument("--write", action="store_true", help="publish through mac-paper (default: dry-run)")
    p.set_defaults(func=lambda a: run_plan(load_plan(a.plan), a.root, a.write))

    for name in ("move", "rename", "reorder", "retire", "set", "add"):
        p = sub.add_parser(name, help=f"{name} one node (default: dry-run)")
        p.add_argument("--id", required=True)
        p.add_argument("--under", "--parent", dest="under")
        p.add_argument("--as", dest="as_kind", choices=("section", "subsection"))
        p.add_argument("--before")
        p.add_argument("--after")
        p.add_argument("--title")
        p.add_argument("--field")
        p.add_argument("--value")
        p.add_argument("--reason")
        p.add_argument("--superseded-by", action="append", default=[])
        p.add_argument("--write", action="store_true")
        p.set_defaults(func=_run_single)

    args = ap.parse_args(argv)
    try:
        if args.command == "validate":
            data = load_outline(args.root / OUTLINE_REL)
            errors = validate(data, args.root)
            if errors:
                print("\n".join(errors), file=sys.stderr)
                return 1
            print(json.dumps(counts(data), ensure_ascii=False, indent=2))
            return 0
        return args.func(args)
    except OutlineError as exc:
        print(f"outline error: {exc}", file=sys.stderr)
        return 2


def _run_single(args) -> int:
    op: dict[str, Any] = {"op": args.command, "id": args.id}
    if args.under:
        op["under"] = args.under
    if args.as_kind:
        op["as"] = args.as_kind
    if args.before:
        op["before"] = args.before
    if args.after:
        op["after"] = args.after
    if args.title:
        op["title"] = args.title
    if args.field:
        op["field"] = args.field
    if args.value is not None:
        op["value"] = parse_value(args.value)
    if args.reason:
        op["reason"] = args.reason
    if args.superseded_by:
        op["superseded_by"] = args.superseded_by
    if args.command == "add":
        raise OutlineError("use apply-plan for add, or provide a plan with fields")
    run_plan({"id": "single-op", "operations": [op]}, args.root, args.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
