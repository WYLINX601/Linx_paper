#!/usr/bin/env python3
"""Paper maintenance orchestration: check, sync and diagnose derived views.

This is deliberately a thin wrapper around the existing generators and checkers.
It does not rewrite research content and does not publish anything unless
``sync --apply`` is explicitly requested.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEALTH = ROOT / "项目管理/健康检查"
BRIDGE = Path(os.environ.get("MAC_PAPER", "/Users/wangyuelin/.hermes/profiles/academic/bin/mac-paper"))
GENERATORS = {
    "outline": "research_structure.py",
    "alignment": "chapter_alignment.py",
    "claims": "research_claims.py",
    "artifacts": "topic_artifact_views.py",
    "literature": "literature_views.py",
    "materials": "materials_views.py",
}
CHECKS = list(GENERATORS.items())


def _run(cmd: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def _print_result(name: str, result: subprocess.CompletedProcess) -> None:
    if result.returncode == 0:
        print(f"  ok   {name}")
        return
    print(f"  FAIL {name}")
    if result.stdout.strip():
        print(result.stdout.strip()[-2000:])
    if result.stderr.strip():
        print(result.stderr.strip()[-2000:])


def check(skip_tests: bool = False) -> int:
    print("Paper check")
    failures = 0
    for name, script in CHECKS:
        result = _run([sys.executable, str(HEALTH / script), "--check"])
        _print_result(name, result)
        failures += result.returncode != 0
    if not skip_tests:
        result = _run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(HEALTH), "-p", "test_*.py"],
            cwd=ROOT,
        )
        _print_result("tests", result)
        failures += result.returncode != 0
    print("result:", "ok" if failures == 0 else f"{failures} failure(s)")
    return 1 if failures else 0


def _generated_files(outdir: Path) -> list[str]:
    files: list[str] = []
    for path in sorted(outdir.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            files.append(str(path.relative_to(outdir)))
    return files


def _read_current(rel: str) -> tuple[str, str] | None:
    result = _run([str(BRIDGE), "--timeout", "30", "read", rel])
    if result.returncode:
        return None
    payload = json.loads(result.stdout)
    if not payload.get("ok"):
        return None
    return payload["result"]["text"], payload["result"]["sha256"]


def sync(apply: bool) -> int:
    outdir = Path(tempfile.mkdtemp(prefix="paper-maintain-", dir=os.environ.get("TMPDIR")))
    print(f"Paper sync (output: {outdir})")
    for name, script in GENERATORS.items():
        result = _run([sys.executable, str(HEALTH / script), "--output-dir", str(outdir)])
        _print_result(f"generate {name}", result)
        if result.returncode:
            print("generation failed; no files published")
            return 1

    changed: list[str] = []
    for rel in _generated_files(outdir):
        source = outdir / rel
        target = ROOT / rel
        if not target.exists():
            changed.append(rel)
        elif target.read_text(encoding="utf-8", errors="replace") != source.read_text(encoding="utf-8", errors="replace"):
            changed.append(rel)

    if not changed:
        print("result: derived views already in sync")
        return 0
    print(f"changed: {len(changed)}")
    for rel in changed:
        print(f"  {'new' if not (ROOT / rel).exists() else 'update'}  {rel}")
    if not apply:
        print("dry-run: no files written; rerun with --apply after review")
        return 0

    print("publishing through mac-paper")
    failures = 0
    for rel in changed:
        source = outdir / rel
        current = _read_current(rel) if (ROOT / rel).exists() else None
        if (ROOT / rel).exists() and current is None:
            print(f"  FAIL {rel}: cannot read current file")
            failures += 1
            continue
        cmd = [str(BRIDGE), "--timeout", "60", "upload", str(source), rel]
        if current is None:
            cmd.append("--expect-missing")
        else:
            cmd.extend(["--expected-sha256", current[1]])
        result = _run(cmd)
        _print_result(rel, result)
        failures += result.returncode != 0
    if failures:
        print("publish incomplete; rerun after reading current state")
        return 1
    print("running final checks")
    return check()


def doctor(output: Path | None = None, strict: bool = False) -> int:
    out = output or Path(tempfile.mkdtemp(prefix="paper-health-", dir=os.environ.get("TMPDIR"))) / "health.json"
    baseline = HEALTH / "依赖基线.json"
    cmd = [
        sys.executable,
        str(HEALTH / "wiki_health.py"),
        "--root",
        str(ROOT),
        "--output",
        str(out),
        "--baseline",
        str(baseline),
    ]
    print(f"Paper doctor (report: {out})")
    result = _run(cmd)
    _print_result("wiki_health", result)
    if result.returncode:
        return 1
    report = json.loads(out.read_text(encoding="utf-8"))
    counts = report.get("counts", {})
    print("summary:", json.dumps(counts, ensure_ascii=False))
    codes = Counter(i.get("code") for i in report.get("issues", []) if i.get("code"))
    for code, count in codes.most_common(10):
        print(f"  {count:4d}  {code}")
    if strict and counts.get("error", 0):
        print("strict: errors present")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", help="run derived-view checks and tests (read-only)")
    p.add_argument("--skip-tests", action="store_true")
    p.set_defaults(func=lambda a: check(a.skip_tests))

    p = sub.add_parser("sync", help="generate derived views and optionally publish")
    p.add_argument("--apply", action="store_true", help="publish changed views through mac-paper")
    p.set_defaults(func=lambda a: sync(a.apply))

    p = sub.add_parser("doctor", help="run full wiki health report")
    p.add_argument("--output", type=Path)
    p.add_argument("--strict", action="store_true", help="fail when the report contains errors")
    p.set_defaults(func=lambda a: doctor(a.output, a.strict))

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
