from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import outline_ops as ops


FIXTURE = """\
schema_version: 1
chapters:
- id: chapter-1
  title: 第一章
  included: true
  path: 论文章节/章节导航/01-绪论.md
  purpose: 测试章
  status: 工作结构
  sections:
  - id: section-1-1
    title: 第一节
    included: true
    purpose: 测试
    status: 工作结构
    subsections:
    - id: sub-a
      title: 三级节
      included: true
      purpose: 测试三级
      status: 工作结构
      change_note: 初始
  - id: section-1-2
    title: 第二节
    included: true
    purpose: 测试
    status: 工作结构
  - id: section-1-3
    title: 第三节
    included: true
    purpose: 测试
    status: 工作结构
"""


class OutlineOpsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root / ops.OUTLINE_REL
        self.path.parent.mkdir(parents=True)
        self.path.write_text(FIXTURE, encoding="utf-8")
        self.nav = self.root / "论文章节/章节导航/01-绪论.md"
        self.nav.parent.mkdir(parents=True)
        self.nav.write_text("# 第一章\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def load(self):
        return ops.load_outline(self.path)

    def test_validate_fixture(self):
        data = self.load()
        self.assertEqual(ops.validate(data, self.root), [])

    def test_add_move_preserves_id_and_counts(self):
        data = self.load()
        ops.apply_operations(data, [
            {
                "op": "add",
                "id": "section-1-4",
                "parent": "chapter-1",
                "as": "section",
                "fields": {"title": "父节", "purpose": "测试", "status": "工作结构"},
            },
            {"op": "move", "id": "section-1-2", "under": "section-1-4", "as": "subsection"},
        ])
        ops.ensure_valid(data, self.root)
        ref = ops.find_ref(data, "section-1-2")
        self.assertEqual(ref.kind, "subsection")
        self.assertEqual(ref.parent["id"], "section-1-4")
        self.assertIn("section-1-2", [x["id"] for x in ref.parent["subsections"]])
        self.assertEqual(ops.counts(data), {"chapters": 1, "sections": 3, "subsections": 2})

    def test_reorder_and_rename_set(self):
        data = self.load()
        ops.apply_operations(data, [
            {"op": "reorder", "id": "section-1-3", "after": "section-1-1"},
            {"op": "rename", "id": "section-1-3", "title": "第三节改名"},
            {"op": "set", "id": "section-1-3", "field": "purpose", "value": "新任务"},
        ])
        ops.ensure_valid(data, self.root)
        chapter = data["chapters"][0]
        self.assertEqual([s["id"] for s in chapter["sections"]], ["section-1-1", "section-1-3", "section-1-2"])
        self.assertEqual(ops.find_ref(data, "section-1-3").node["title"], "第三节改名")
        self.assertEqual(ops.find_ref(data, "section-1-3").node["purpose"], "新任务")

    def test_retire(self):
        data = self.load()
        ops.apply_operations(data, [
            {"op": "retire", "id": "section-1-2", "superseded_by": ["section-1-1"], "reason": "合并"}
        ])
        ref = ops.find_ref(data, "section-1-2")
        self.assertFalse(ref.node["included"])
        self.assertEqual(ref.node["superseded_by"], ["section-1-1"])
        self.assertIn("合并", ref.node["change_note"])

    def test_duplicate_add_rejected(self):
        data = self.load()
        with self.assertRaises(ops.OutlineError):
            ops.apply_operations(data, [
                {"op": "add", "id": "section-1-1", "parent": "chapter-1", "as": "section",
                 "fields": {"title": "重复", "purpose": "测试", "status": "工作结构"}}
            ])

    def test_assertions(self):
        data = self.load()
        ops.check_assertions(data, {"counts": {"sections": 3, "subsections": 1}})
        with self.assertRaises(ops.OutlineError):
            ops.check_assertions(data, {"counts": {"sections": 99}})

    def test_roundtrip(self):
        data = self.load()
        text = ops.dump_outline(data)
        other = ops._yaml_rt().load(text)
        self.assertEqual(ops.counts(other), ops.counts(data))


if __name__ == "__main__":
    unittest.main()
