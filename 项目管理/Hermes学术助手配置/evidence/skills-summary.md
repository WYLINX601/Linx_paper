# Academic skills Linux acceptance — 2026-10-26

## Package and discovery

- The migration manifest contains 31 skills. Linux discovered 32 direct skill folders and 33 recursive `SKILL.md` files; the additional profile skills are `academic-workspace` and nested `autonomous-ai-agents/hermes-agent`.
- After the approved portability cleanup, 1,191 manifest-listed files were checked: 0 missing, 0 hash mismatches, and 0 unmanifested files. `hash-discovery.json` records the per-skill results.
- Removed only two upstream repository CI/development checkers from the Hermes ARS copy: `check_spec_consistency.py` and `check_claim_standing_candidate_ledger_integration.py`. Their original SHA-256 values and reasons are in `manifest.json` under `portability_removals`. The source Mac Codex skills were not edited.
- Repaired the direct references in ARS contract/helper documentation. The claim-standing protocol retains its academic safety contract while distinguishing upstream CI evidence from checks run in this Hermes profile. The Hermes capability row is marked `NONE` because the repository-only conformance checker is not packaged.
- Deleted 1,437 migration-created AppleDouble sidecars and 59 test-generated Python bytecode files; no source files were changed in that cleanup.

## Runtime smoke checks

- Python CLI help: 179 retained argparse entrypoints; 178 passed. Five `ruamel.yaml` paths passed after `ruamel.yaml 0.19.1` was installed. The sole remaining blocked help path is `fetch_calibration_corpus.py`, which imports optional `openreview` before parsing arguments. No retrieval/API workflow was run.
- Mindmap: copied installed Simple Mind Map 0.2.10 resources into the temporary test vault only. `doctor`, native create, optimistic-hash edit, validate (`ok: true`), and read passed; visual rendering was not exercised.
- Statistics: the assumption-check helper passed on synthetic two-group data and wrote `/tmp/hermes-academic-skills-acceptance-20261026/statistical-assumption-check.png`. A deterministic synthetic scientific-figure preview also exported PNG and SVG.
- Draw.io: Mac CLI 32.4.1 exported a temporary diagram to a 414 × 204 PNG. The parent visually reviewed it. Electron printed a keychain interaction warning, but the export and PNG checks succeeded.

## Remaining optional checks

- Install `openreview` only if calibration-corpus retrieval is needed, then exercise it only with appropriate user authorization; its network workflow was not tested.
- Credential-backed transcription, AI schematic generation, live Zotero/Neo4j/MCP calls, and real Paper vault writes were not tested.
- Use Obsidian visual review for diagrams requiring image previews, free layout, or linked annotations; the tested CLI file workflow uses the installed plugin reader and does not exercise rendering.
- Word, PowerPoint, and spreadsheet acceptance was assigned separately and is not covered here.

## Evidence paths

- Linux reports: `/home/linx/.hermes/profiles/academic/verification/skills-acceptance-20261026/`
- Mac draw.io source/preview: `/private/tmp/hermes-academic-validation/academic-skills-smoke.drawio` and `/private/tmp/hermes-academic-validation/academic-skills-smoke.png`
- Mac statistical figure for review: `/private/tmp/hermes-academic-validation/statistical-assumption-check.png`
