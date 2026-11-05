import unittest,tempfile,json,hashlib,os
from pathlib import Path
from wiki_health import scan,links,resolve,adoption_view
class HealthTests(unittest.TestCase):
    def setUp(self):
        scratch=Path('/Users/wangyuelin/.hermes/profiles/academic/cache/scratch');scratch.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=scratch);self.r=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def put(self,p,t=''):
        f=self.r/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(t);return f
    def codes(self,b=None):return {x['code'] for x in scan(self.r,b)['issues']}
    def test_chinese_spaces_mixed(self):
        self.put('README.md','[a](<笔记/中文 空格.md>) [[笔记/中文 空格]] ![图](图.png)');self.put('笔记/中文 空格.md','# 标题\n');self.put('图.png');self.assertNotIn('LINK_MISSING',self.codes())
    def test_ambiguous(self):
        self.put('README.md','[[同名]]');self.put('a/同名.md');self.put('b/同名.md');self.assertIn('LINK_AMBIGUOUS',self.codes())
    def test_missing_attachment(self):
        self.put('README.md','![缺](missing.png)');self.assertIn('LINK_MISSING',self.codes())
    def test_anchors_blocks(self):
        self.put('README.md','[[b#中文 标题]] [[b#^block]] [x](b.md#中文-标题) [[b#不存在]]');self.put('b.md','# 中文 标题\ntext ^block');r=scan(self.r);self.assertEqual(sum(i['code']=='ANCHOR' for i in r['issues']),1)
    def test_code_excluded(self):
        self.put('README.md','```md\n[[不存在]]\n```\n`[[不存在]]`');self.assertNotIn('LINK_MISSING',self.codes())
    def test_archive_referenced(self):
        self.put('README.md','[[archive/a]]');self.put('archive/a.md','[[old_missing]]');self.assertNotIn('LINK_MISSING',self.codes())
    def test_zotero_not_claimed_available(self):
        self.put('README.md','[z](zotero://select/library/items/ABCDEFGH)');r=scan(self.r);self.assertEqual(r['external_not_fetched']['external'],1)
    def test_missing_baseline(self):
        self.put('README.md','---\ndepends_on: [b.md]\n---\n');self.put('b.md','x');self.assertIn('BASELINE_UNKNOWN',self.codes())
    def test_mtime_not_content(self):
        p=self.put('b.md','x');self.put('README.md','---\ndepends_on: [b.md]\n---\n');b={'README.md::b.md':hashlib.sha256(p.read_bytes()).hexdigest()};os.utime(p,(1,1));self.assertNotIn('DEPENDENCY_CHANGED',self.codes(b))
    def test_content_change(self):
        p=self.put('b.md','x');self.put('README.md','---\ndepends_on: [b.md]\n---\n');b={'README.md::b.md':hashlib.sha256(p.read_bytes()).hexdigest()};p.write_text('y');self.assertIn('DEPENDENCY_CHANGED',self.codes(b))
    def test_duplicate_ids(self):
        self.put('README.md','---\nwiki_id: x\n---\n');self.put('b.md','---\nwiki_id: x\n---\n');self.assertIn('DUPLICATE_ID',self.codes())
    def test_supersession_cycle(self):
        self.put('README.md','---\nsuperseded_by: b.md\n---\n');self.put('b.md','---\nsuperseded_by: README.md\n---\n');self.assertIn('SUPERSESSION_CYCLE',self.codes())
    def test_native_code_index(self):
        self.put('README.md','[[a.smm.md]]');self.put('a.smm.md','# metadata\n```metadata\n[[not-a-link]]\n```\n# linkdata\n- [[b.md]]_[old.md]');self.put('b.md');self.assertNotIn('LINK_MISSING',self.codes())
    def test_repeatable_readonly(self):
        p=self.put('README.md','[[missing]]');before=p.read_bytes();self.assertEqual(scan(self.r),scan(self.r));self.assertEqual(p.read_bytes(),before)
    def test_html_and_balanced_parentheses(self):
        self.put('README.md','[x](a(test).md) <img src="图.png">');self.put('a(test).md');self.put('图.png');self.assertNotIn('LINK_MISSING',self.codes())
    def test_case_sensitive_identifier(self):
        self.assertEqual(resolve('A.md','README.md',{'a.md'})[0],'missing')
    def test_bad_yaml(self):
        self.put('README.md','---\na: [\n---\n');self.assertIn('YAML',self.codes())
    def test_explicit_html_anchor(self):
        self.put('README.md','[x](a.md#带、标点)');self.put('a.md','<a id="带、标点"></a>\n# 标题');self.assertNotIn('ANCHOR',self.codes())
    def test_source_html_not_a_complete_site(self):
        self.put('研究成果/x/sources/a.html','<script>var x=\'src="fake"\';</script><img src="missing.png">');r=scan(self.r);self.assertEqual(sum(x['code']=='SOURCE_RESOURCE' for x in r['issues']),1);self.assertNotIn('LINK_MISSING',self.codes())
    def test_adoption_export(self):
        self.put('论文章节/01/章节导航.md','| 1.1 研究背景 | [[主题研究/问题/主题研究.md|问题]] | 依据 | 待核 |');rows,body=adoption_view(self.r);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['status'],'待核');self.assertIn('主题主源',body)
if __name__=='__main__':unittest.main(verbosity=2)
